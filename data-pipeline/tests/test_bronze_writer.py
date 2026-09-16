import json
import shutil
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from chainsignal_pipeline.bronze.models import BronzeRequest
from chainsignal_pipeline.bronze.writer import BronzeWriter, BronzeWriteResult


def test_bronze_persistence_contract(
    tmp_path: Path,
    bronze_output: BronzeWriteResult,
    gdacs_record: dict[str, Any],
) -> None:
    metadata = bronze_output.metadata
    assert bronze_output.created is True
    assert bronze_output.path == (
        tmp_path
        / "bronze"
        / "source=GDACS"
        / "ingestion_date=2026-09-16"
        / f"batch_id={metadata.batch_id}"
        / "part-00000.parquet"
    )
    table = pq.ParquetFile(bronze_output.path).read()
    assert table.schema.names == ["record_index", "raw_payload"]
    assert table.schema.field("record_index") == pa.field(
        "record_index", pa.int64(), nullable=False
    )
    assert table.schema.field("raw_payload") == pa.field("raw_payload", pa.string(), nullable=False)
    assert table.schema.metadata == {
        b"source": b"GDACS",
        b"request_identity": metadata.request_identity.encode(),
        b"raw_content_hash": metadata.raw_content_hash.encode(),
        b"batch_id": metadata.batch_id.encode(),
        b"ingested_at": metadata.ingested_at.isoformat().encode(),
        b"record_count": b"1",
    }
    assert table.column("record_index").to_pylist() == [0]
    assert json.loads(table.column("raw_payload")[0].as_py()) == gdacs_record
    assert list(bronze_output.path.parent.iterdir()) == [bronze_output.path]


@pytest.mark.parametrize("record_count", [0, 3])
def test_zero_and_multiple_record_batches_preserve_order(
    tmp_path: Path,
    bronze_request: BronzeRequest,
    ingested_at: datetime,
    record_count: int,
) -> None:
    records = [{"type": "Feature", "id": index} for index in range(record_count)]
    result = BronzeWriter(tmp_path).write(
        request=bronze_request,
        raw_records=records,
        ingested_at=ingested_at,
    )
    table = pq.ParquetFile(result.path).read()
    assert table.schema.names == ["record_index", "raw_payload"]
    assert table.num_rows == record_count == result.metadata.record_count
    assert table.column("record_index").to_pylist() == list(range(record_count))
    assert [json.loads(payload) for payload in table.column("raw_payload").to_pylist()] == records


def test_identical_logical_batch_is_idempotent_across_ingestion_dates(
    tmp_path: Path,
    bronze_output: BronzeWriteResult,
    bronze_request: BronzeRequest,
    gdacs_record: dict[str, Any],
    ingested_at: datetime,
) -> None:
    original_bytes = bronze_output.path.read_bytes()
    repeat = BronzeWriter(tmp_path / "bronze").write(
        request=bronze_request,
        raw_records=deepcopy([gdacs_record]),
        ingested_at=ingested_at + timedelta(days=1),
    )
    assert repeat.created is False
    assert repeat.path == bronze_output.path
    assert repeat.metadata == bronze_output.metadata
    assert repeat.path.read_bytes() == original_bytes
    assert list((tmp_path / "bronze").rglob("*.parquet")) == [bronze_output.path]


def test_changed_provider_content_creates_distinct_batch(
    tmp_path: Path,
    bronze_output: BronzeWriteResult,
    bronze_request: BronzeRequest,
    gdacs_record: dict[str, Any],
    ingested_at: datetime,
) -> None:
    gdacs_record["properties"]["country"] = "Changed"
    changed = BronzeWriter(tmp_path / "bronze").write(
        request=bronze_request,
        raw_records=[gdacs_record],
        ingested_at=ingested_at,
    )
    assert changed.created is True
    assert changed.metadata.request_identity == bronze_output.metadata.request_identity
    assert changed.metadata.batch_id != bronze_output.metadata.batch_id
    assert changed.path != bronze_output.path
    assert len(list((tmp_path / "bronze").rglob("*.parquet"))) == 2


def test_duplicate_physical_batches_fail_loudly(
    tmp_path: Path,
    bronze_output: BronzeWriteResult,
    bronze_request: BronzeRequest,
    gdacs_record: dict[str, Any],
    ingested_at: datetime,
) -> None:
    duplicate = (
        tmp_path
        / "bronze"
        / "source=GDACS"
        / "ingestion_date=2026-09-17"
        / bronze_output.path.parent.name
        / bronze_output.path.name
    )
    duplicate.parent.mkdir(parents=True)
    shutil.copyfile(bronze_output.path, duplicate)
    with pytest.raises(RuntimeError, match="Multiple Bronze files"):
        BronzeWriter(tmp_path / "bronze").write(
            request=bronze_request,
            raw_records=[gdacs_record],
            ingested_at=ingested_at,
        )
