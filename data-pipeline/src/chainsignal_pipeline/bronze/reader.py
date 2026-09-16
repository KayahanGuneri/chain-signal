from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pyarrow as pa
import pyarrow.parquet as pq

from chainsignal_pipeline.bronze.models import (
    BronzeBatchMetadata,
    calculate_batch_id,
    calculate_raw_content_hash,
)


@dataclass(frozen=True, slots=True)
class BronzeBatch:
    """One verified immutable Bronze batch loaded from Parquet."""

    path: Path
    metadata: BronzeBatchMetadata
    raw_records: tuple[dict[str, Any], ...]


class BronzeReader:
    """Read and verify immutable Bronze Parquet batches."""

    def read(
        self,
        path: Path,
    ) -> BronzeBatch:
        if not path.is_file():
            raise FileNotFoundError(f"Bronze Parquet file does not exist: {path}")

        schema = pq.read_schema(path)

        self._validate_schema(
            path=path,
            schema=schema,
        )

        metadata = self._read_metadata(
            path=path,
            schema=schema,
        )

        table = pq.read_table(
            path,
            columns=[
                "record_index",
                "raw_payload",
            ],
        )

        if table.num_rows != metadata.record_count:
            raise ValueError(
                f"Bronze Parquet row count does not match metadata record_count: {path}"
            )

        record_indexes = cast(
            list[int],
            table.column("record_index").to_pylist(),
        )

        raw_payloads = cast(
            list[str],
            table.column("raw_payload").to_pylist(),
        )

        self._validate_record_indexes(
            path=path,
            record_indexes=record_indexes,
            expected_count=metadata.record_count,
        )

        raw_records = self._deserialize_records(
            path=path,
            raw_payloads=raw_payloads,
        )

        self._validate_content_identity(
            path=path,
            metadata=metadata,
            raw_records=raw_records,
        )

        self._validate_partition_path(
            path=path,
            metadata=metadata,
        )

        return BronzeBatch(
            path=path,
            metadata=metadata,
            raw_records=tuple(raw_records),
        )

    @staticmethod
    def _validate_schema(
        *,
        path: Path,
        schema: pa.Schema,
    ) -> None:
        required_fields = {
            "record_index",
            "raw_payload",
        }

        if not required_fields.issubset(set(schema.names)):
            raise ValueError(f"Bronze Parquet schema is invalid: {path}")

        if schema.field("record_index").type != pa.int64():
            raise ValueError(f"Bronze record_index must be int64: {path}")

        if schema.field("raw_payload").type != pa.string():
            raise ValueError(f"Bronze raw_payload must be string: {path}")

    @staticmethod
    def _read_metadata(
        *,
        path: Path,
        schema: pa.Schema,
    ) -> BronzeBatchMetadata:
        raw_metadata = cast(
            dict[bytes, bytes] | None,
            schema.metadata,
        )

        if raw_metadata is None:
            raise ValueError(f"Bronze Parquet file has no metadata: {path}")

        def read_text(key: str) -> str:
            raw_value = raw_metadata.get(key.encode("utf-8"))

            if raw_value is None:
                raise ValueError(f"Bronze Parquet metadata is missing {key}: {path}")

            return raw_value.decode("utf-8")

        try:
            ingested_at = datetime.fromisoformat(read_text("ingested_at"))

            record_count = int(read_text("record_count"))
        except ValueError as exc:
            raise ValueError(f"Bronze Parquet metadata is malformed: {path}") from exc

        return BronzeBatchMetadata(
            source=read_text("source"),
            request_identity=read_text("request_identity"),
            raw_content_hash=read_text("raw_content_hash"),
            batch_id=read_text("batch_id"),
            ingested_at=ingested_at,
            record_count=record_count,
        )

    @staticmethod
    def _validate_record_indexes(
        *,
        path: Path,
        record_indexes: list[int],
        expected_count: int,
    ) -> None:
        expected_indexes = list(range(expected_count))

        if record_indexes != expected_indexes:
            raise ValueError(f"Bronze record_index sequence is invalid: {path}")

    @staticmethod
    def _deserialize_records(
        *,
        path: Path,
        raw_payloads: list[str],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for record_index, raw_payload in enumerate(raw_payloads):
            if not isinstance(raw_payload, str):
                raise ValueError(
                    f"Bronze raw_payload is not a string at record_index={record_index}: {path}"
                )

            try:
                parsed = json.loads(raw_payload)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Bronze raw_payload contains invalid JSON at "
                    f"record_index={record_index}: {path}"
                ) from exc

            if not isinstance(parsed, dict):
                raise ValueError(
                    "Bronze raw_payload must contain a JSON object at "
                    f"record_index={record_index}: {path}"
                )

            records.append(cast(dict[str, Any], parsed))

        return records

    @staticmethod
    def _validate_content_identity(
        *,
        path: Path,
        metadata: BronzeBatchMetadata,
        raw_records: list[dict[str, Any]],
    ) -> None:
        actual_raw_content_hash = calculate_raw_content_hash(raw_records)

        if actual_raw_content_hash != metadata.raw_content_hash:
            raise ValueError(f"Bronze raw content hash does not match metadata: {path}")

        actual_batch_id = calculate_batch_id(
            request_identity=metadata.request_identity,
            raw_content_hash=actual_raw_content_hash,
        )

        if actual_batch_id != metadata.batch_id:
            raise ValueError(f"Bronze batch_id does not match content identity: {path}")

    @staticmethod
    def _validate_partition_path(
        *,
        path: Path,
        metadata: BronzeBatchMetadata,
    ) -> None:
        expected_parts = {
            f"source={metadata.source}",
            (f"ingestion_date={metadata.partition_date.isoformat()}"),
            f"batch_id={metadata.batch_id}",
        }

        path_parts = set(path.parts)

        if not expected_parts.issubset(path_parts):
            raise ValueError(f"Bronze partition path does not match Parquet metadata: {path}")

        if path.name != "part-00000.parquet":
            raise ValueError(f"Unexpected Bronze Parquet filename: {path}")
