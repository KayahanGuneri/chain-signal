from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pyarrow as pa
import pyarrow.parquet as pq

from chainsignal_pipeline.bronze.models import (
    BronzeBatchMetadata,
    BronzeRequest,
)


@dataclass(frozen=True, slots=True)
class BronzeWriteResult:
    """Result of persisting one immutable Bronze batch."""

    path: Path
    metadata: BronzeBatchMetadata
    created: bool


class BronzeWriter:
    """Persist raw source records as immutable partitioned Parquet batches."""

    def __init__(
        self,
        root_path: Path,
    ) -> None:
        self._root_path = root_path

    def write(
        self,
        *,
        request: BronzeRequest,
        raw_records: list[dict[str, Any]],
        ingested_at: datetime,
    ) -> BronzeWriteResult:
        metadata = BronzeBatchMetadata.create(
            request=request,
            raw_records=raw_records,
            ingested_at=ingested_at,
        )

        existing_path = self._find_existing_batch(
            source=metadata.source,
            batch_id=metadata.batch_id,
        )

        if existing_path is not None:
            existing_metadata = self._read_batch_metadata(existing_path)

            return BronzeWriteResult(
                path=existing_path,
                metadata=existing_metadata,
                created=False,
            )

        destination = self._build_destination(metadata)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        table = self._build_table(
            raw_records=raw_records,
            metadata=metadata,
        )

        temporary_path = destination.with_suffix(".parquet.tmp")

        try:
            pq.write_table(
                table,
                temporary_path,
                compression="zstd",
            )

            os.replace(
                temporary_path,
                destination,
            )
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return BronzeWriteResult(
            path=destination,
            metadata=metadata,
            created=True,
        )

    def _find_existing_batch(
        self,
        *,
        source: str,
        batch_id: str,
    ) -> Path | None:
        source_root = self._root_path / f"source={source}"

        if not source_root.exists():
            return None

        matches = list(source_root.glob(f"ingestion_date=*/batch_id={batch_id}/part-00000.parquet"))

        if not matches:
            return None

        if len(matches) > 1:
            raise RuntimeError("Multiple Bronze files exist for the same batch_id")

        return matches[0]

    def _build_destination(
        self,
        metadata: BronzeBatchMetadata,
    ) -> Path:
        return (
            self._root_path
            / f"source={metadata.source}"
            / f"ingestion_date={metadata.partition_date.isoformat()}"
            / f"batch_id={metadata.batch_id}"
            / "part-00000.parquet"
        )

    @staticmethod
    def _build_table(
        *,
        raw_records: list[dict[str, Any]],
        metadata: BronzeBatchMetadata,
    ) -> pa.Table:
        rows = [
            {
                "record_index": index,
                "raw_payload": _serialize_raw_record(record),
            }
            for index, record in enumerate(raw_records)
        ]

        schema = pa.schema(
            [
                pa.field(
                    "record_index",
                    pa.int64(),
                    nullable=False,
                ),
                pa.field(
                    "raw_payload",
                    pa.string(),
                    nullable=False,
                ),
            ],
            metadata={
                "source": metadata.source,
                "request_identity": metadata.request_identity,
                "raw_content_hash": metadata.raw_content_hash,
                "batch_id": metadata.batch_id,
                "ingested_at": metadata.ingested_at.isoformat(),
                "record_count": str(metadata.record_count),
            },
        )

        return pa.Table.from_pylist(
            rows,
            schema=schema,
        )

    @staticmethod
    def _read_batch_metadata(
        path: Path,
    ) -> BronzeBatchMetadata:
        schema = pq.read_schema(path)

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

        return BronzeBatchMetadata(
            source=read_text("source"),
            request_identity=read_text("request_identity"),
            raw_content_hash=read_text("raw_content_hash"),
            batch_id=read_text("batch_id"),
            ingested_at=datetime.fromisoformat(read_text("ingested_at")),
            record_count=int(read_text("record_count")),
        )


def _serialize_raw_record(
    record: dict[str, Any],
) -> str:
    return json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
