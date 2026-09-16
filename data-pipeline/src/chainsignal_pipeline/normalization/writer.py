from __future__ import annotations

import json
import os
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from chainsignal_pipeline.models.event import CanonicalEvent
from chainsignal_pipeline.quality.models import (
    DataQualitySummary,
    QuarantinedRecord,
)

NORMALIZATION_CONTRACT_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class NormalizationWriteResult:
    """Filesystem locations produced for one normalization batch."""

    output_directory: Path
    events_path: Path
    quarantine_path: Path
    quality_path: Path
    created: bool


class NormalizationWriter:
    """Persist deterministic canonical normalization outputs."""

    def __init__(
        self,
        root_path: Path,
        normalization_version: str = NORMALIZATION_CONTRACT_VERSION,
    ) -> None:
        if not normalization_version.strip():
            raise ValueError("Normalization version must not be blank")

        self._root_path = root_path
        self._normalization_version = normalization_version

    def write(
        self,
        *,
        source: str,
        batch_id: str,
        events: Sequence[CanonicalEvent],
        quarantined_records: Sequence[QuarantinedRecord],
        summary: DataQualitySummary,
    ) -> NormalizationWriteResult:
        if not source.strip():
            raise ValueError("Normalization source must not be blank")

        if not batch_id.strip():
            raise ValueError("Normalization batch_id must not be blank")

        if summary.valid_count != len(events):
            raise ValueError("Data-quality valid_count does not match canonical events")

        if summary.quarantine_count != len(quarantined_records):
            raise ValueError("Data-quality quarantine_count does not match quarantined records")

        output_directory = self._build_output_directory(
            source=source,
            batch_id=batch_id,
        )

        if output_directory.exists():
            self._validate_existing_output(
                output_directory=output_directory,
                source=source,
                batch_id=batch_id,
                events=events,
                quarantined_records=(quarantined_records),
                summary=summary,
            )

            return self._build_result(
                output_directory=output_directory,
                created=False,
            )

        output_directory.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            output_directory.mkdir()
        except FileExistsError:
            self._validate_existing_output(
                output_directory=output_directory,
                source=source,
                batch_id=batch_id,
                events=events,
                quarantined_records=(quarantined_records),
                summary=summary,
            )

            return self._build_result(
                output_directory=output_directory,
                created=False,
            )

        events_path = output_directory / "events.parquet"
        quarantine_path = output_directory / "quarantine.parquet"
        quality_path = output_directory / "quality.json"

        temporary_events_path = output_directory / ".events.parquet.tmp"
        temporary_quarantine_path = output_directory / ".quarantine.parquet.tmp"
        temporary_quality_path = output_directory / ".quality.json.tmp"

        try:
            self._write_events(
                path=temporary_events_path,
                source=source,
                batch_id=batch_id,
                events=events,
            )

            self._write_quarantine(
                path=temporary_quarantine_path,
                source=source,
                batch_id=batch_id,
                records=quarantined_records,
            )

            self._write_quality(
                path=temporary_quality_path,
                source=source,
                batch_id=batch_id,
                summary=summary,
            )

            os.replace(
                temporary_events_path,
                events_path,
            )

            os.replace(
                temporary_quarantine_path,
                quarantine_path,
            )

            os.replace(
                temporary_quality_path,
                quality_path,
            )
        except Exception:
            shutil.rmtree(
                output_directory,
                ignore_errors=True,
            )
            raise

        return self._build_result(
            output_directory=output_directory,
            created=True,
        )

    def _build_output_directory(
        self,
        *,
        source: str,
        batch_id: str,
    ) -> Path:
        return (
            self._root_path
            / f"source={source}"
            / (f"normalization_version={self._normalization_version}")
            / f"batch_id={batch_id}"
        )

    @staticmethod
    def _build_result(
        *,
        output_directory: Path,
        created: bool,
    ) -> NormalizationWriteResult:
        return NormalizationWriteResult(
            output_directory=output_directory,
            events_path=(output_directory / "events.parquet"),
            quarantine_path=(output_directory / "quarantine.parquet"),
            quality_path=(output_directory / "quality.json"),
            created=created,
        )

    def _write_events(
        self,
        *,
        path: Path,
        source: str,
        batch_id: str,
        events: Sequence[CanonicalEvent],
    ) -> None:
        rows = self._build_event_rows(events)

        schema = self._build_event_schema(
            source=source,
            batch_id=batch_id,
        )

        table = pa.Table.from_pylist(
            rows,
            schema=schema,
        )

        pq.write_table(
            table,
            path,
            compression="zstd",
        )

    def _write_quarantine(
        self,
        *,
        path: Path,
        source: str,
        batch_id: str,
        records: Sequence[QuarantinedRecord],
    ) -> None:
        rows = self._build_quarantine_rows(records)

        schema = self._build_quarantine_schema(
            source=source,
            batch_id=batch_id,
        )

        table = pa.Table.from_pylist(
            rows,
            schema=schema,
        )

        pq.write_table(
            table,
            path,
            compression="zstd",
        )

    def _write_quality(
        self,
        *,
        path: Path,
        source: str,
        batch_id: str,
        summary: DataQualitySummary,
    ) -> None:
        payload = self._quality_payload(
            source=source,
            batch_id=batch_id,
            summary=summary,
        )

        path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _validate_existing_output(
        self,
        *,
        output_directory: Path,
        source: str,
        batch_id: str,
        events: Sequence[CanonicalEvent],
        quarantined_records: Sequence[QuarantinedRecord],
        summary: DataQualitySummary,
    ) -> None:
        events_path = output_directory / "events.parquet"
        quarantine_path = output_directory / "quarantine.parquet"
        quality_path = output_directory / "quality.json"

        expected_paths = (
            events_path,
            quarantine_path,
            quality_path,
        )

        if not all(path.is_file() for path in expected_paths):
            raise RuntimeError(f"Normalization output directory is incomplete: {output_directory}")

        self._validate_existing_events(
            path=events_path,
            source=source,
            batch_id=batch_id,
            events=events,
        )

        self._validate_existing_quarantine(
            path=quarantine_path,
            source=source,
            batch_id=batch_id,
            records=quarantined_records,
        )

        self._validate_existing_quality(
            path=quality_path,
            source=source,
            batch_id=batch_id,
            summary=summary,
        )

    def _validate_existing_events(
        self,
        *,
        path: Path,
        source: str,
        batch_id: str,
        events: Sequence[CanonicalEvent],
    ) -> None:
        table = pq.ParquetFile(path).read()

        expected_schema = self._build_event_schema(
            source=source,
            batch_id=batch_id,
        )

        if not table.schema.equals(
            expected_schema,
            check_metadata=True,
        ):
            raise RuntimeError(
                f"Existing canonical event schema does not match normalization contract: {path}"
            )

        expected_rows = self._build_event_rows(events)

        if table.to_pylist() != expected_rows:
            raise RuntimeError(
                f"Existing canonical event output does not match normalization result: {path}"
            )

    def _validate_existing_quarantine(
        self,
        *,
        path: Path,
        source: str,
        batch_id: str,
        records: Sequence[QuarantinedRecord],
    ) -> None:
        table = pq.ParquetFile(path).read()

        expected_schema = self._build_quarantine_schema(
            source=source,
            batch_id=batch_id,
        )

        if not table.schema.equals(
            expected_schema,
            check_metadata=True,
        ):
            raise RuntimeError(
                f"Existing quarantine schema does not match normalization contract: {path}"
            )

        expected_rows = self._build_quarantine_rows(records)

        if table.to_pylist() != expected_rows:
            raise RuntimeError(
                f"Existing quarantine output does not match normalization result: {path}"
            )

    def _validate_existing_quality(
        self,
        *,
        path: Path,
        source: str,
        batch_id: str,
        summary: DataQualitySummary,
    ) -> None:
        try:
            existing_quality = json.loads(path.read_text(encoding="utf-8"))
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError(f"Existing quality output is unreadable: {path}") from exc

        expected_quality = self._quality_payload(
            source=source,
            batch_id=batch_id,
            summary=summary,
        )

        if existing_quality != expected_quality:
            raise RuntimeError(
                f"Existing quality output does not match normalization result: {path}"
            )

    @staticmethod
    def _build_event_rows(
        events: Sequence[CanonicalEvent],
    ) -> list[dict[str, object]]:
        return [
            {
                "source": event.source,
                "sourceEventId": (event.source_event_id),
                "eventType": (event.event_type.value),
                "occurredAt": (event.occurred_at.astimezone(UTC)),
                "latitude": event.latitude,
                "longitude": event.longitude,
                "severity": (event.severity.value),
                "country": event.country,
                "metadata": _serialize_json(event.metadata),
                "schemaVersion": (event.schema_version),
            }
            for event in events
        ]

    def _build_event_schema(
        self,
        *,
        source: str,
        batch_id: str,
    ) -> pa.Schema:
        return pa.schema(
            [
                pa.field(
                    "source",
                    pa.string(),
                    nullable=False,
                ),
                pa.field(
                    "sourceEventId",
                    pa.string(),
                    nullable=False,
                ),
                pa.field(
                    "eventType",
                    pa.string(),
                    nullable=False,
                ),
                pa.field(
                    "occurredAt",
                    pa.timestamp(
                        "us",
                        tz="UTC",
                    ),
                    nullable=False,
                ),
                pa.field(
                    "latitude",
                    pa.float64(),
                    nullable=False,
                ),
                pa.field(
                    "longitude",
                    pa.float64(),
                    nullable=False,
                ),
                pa.field(
                    "severity",
                    pa.string(),
                    nullable=False,
                ),
                pa.field(
                    "country",
                    pa.string(),
                    nullable=True,
                ),
                pa.field(
                    "metadata",
                    pa.string(),
                    nullable=False,
                ),
                pa.field(
                    "schemaVersion",
                    pa.string(),
                    nullable=False,
                ),
            ],
            metadata=(
                self._schema_metadata(
                    source=source,
                    batch_id=batch_id,
                )
            ),
        )

    @staticmethod
    def _build_quarantine_rows(
        records: Sequence[QuarantinedRecord],
    ) -> list[dict[str, object]]:
        return [
            {
                "record_index": (record.record_index),
                "reasons": [reason.value for reason in record.reasons],
                "raw_payload": (_serialize_json(record.raw_record)),
            }
            for record in records
        ]

    def _build_quarantine_schema(
        self,
        *,
        source: str,
        batch_id: str,
    ) -> pa.Schema:
        return pa.schema(
            [
                pa.field(
                    "record_index",
                    pa.int64(),
                    nullable=False,
                ),
                pa.field(
                    "reasons",
                    pa.list_(
                        pa.field(
                            "element",
                            pa.string(),
                            nullable=True,
                        )
                    ),
                    nullable=False,
                ),
                pa.field(
                    "raw_payload",
                    pa.string(),
                    nullable=False,
                ),
            ],
            metadata=(
                self._schema_metadata(
                    source=source,
                    batch_id=batch_id,
                )
            ),
        )

    def _quality_payload(
        self,
        *,
        source: str,
        batch_id: str,
        summary: DataQualitySummary,
    ) -> dict[str, object]:
        return {
            "source": source,
            "batch_id": batch_id,
            "normalization_version": (self._normalization_version),
            "input_count": (summary.input_count),
            "valid_count": (summary.valid_count),
            "invalid_count": (summary.invalid_count),
            "duplicate_count": (summary.duplicate_count),
            "quarantine_count": (summary.quarantine_count),
            "reason_counts": (summary.reason_counts_by_code),
        }

    def _schema_metadata(
        self,
        *,
        source: str,
        batch_id: str,
    ) -> dict[str, str]:
        return {
            "source": source,
            "batch_id": batch_id,
            "normalization_version": (self._normalization_version),
        }


def _serialize_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
