import shutil
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from chainsignal_pipeline.bronze.reader import BronzeReader
from chainsignal_pipeline.bronze.writer import BronzeWriteResult


def test_verified_bronze_round_trip(
    bronze_output: BronzeWriteResult,
    gdacs_record: dict[str, Any],
) -> None:
    batch = BronzeReader().read(bronze_output.path)
    assert batch.path == bronze_output.path
    assert batch.metadata == bronze_output.metadata
    assert batch.raw_records == (gdacs_record,)


def test_missing_bronze_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        BronzeReader().read(tmp_path / "missing.parquet")


@pytest.mark.parametrize(
    "column,data_type,message",
    [
        ("record_index", None, "schema is invalid"),
        ("raw_payload", None, "schema is invalid"),
        ("record_index", pa.int32(), "record_index must be int64"),
        ("raw_payload", pa.binary(), "raw_payload must be string"),
    ],
)
def test_bronze_schema_corruption(
    bronze_output: BronzeWriteResult,
    column: str,
    data_type: Any,
    message: str,
) -> None:
    table = pq.ParquetFile(bronze_output.path).read()
    if data_type is None:
        table = table.drop([column])
    else:
        index = table.schema.get_field_index(column)
        table = table.set_column(index, column, table.column(column).cast(data_type))
    pq.write_table(table, bronze_output.path)
    with pytest.raises(ValueError, match=message):
        BronzeReader().read(bronze_output.path)


@pytest.mark.parametrize(
    "key,value,message",
    [
        (None, None, "has no metadata"),
        (b"source", None, "missing source"),
        (b"request_identity", None, "missing request_identity"),
        (b"raw_content_hash", None, "missing raw_content_hash"),
        (b"batch_id", None, "missing batch_id"),
        (b"ingested_at", None, "metadata is malformed"),
        (b"record_count", None, "metadata is malformed"),
        (b"record_count", b"2", "row count does not match"),
        (b"record_count", b"not-an-integer", "metadata is malformed"),
        (b"ingested_at", b"not-a-date", "metadata is malformed"),
        (b"raw_content_hash", b"corrupt", "raw content hash does not match"),
        (b"batch_id", b"corrupt", "batch_id does not match content identity"),
    ],
)
def test_bronze_metadata_corruption(
    bronze_output: BronzeWriteResult,
    key: bytes | None,
    value: bytes | None,
    message: str,
) -> None:
    table = pq.ParquetFile(bronze_output.path).read()
    metadata = dict(table.schema.metadata or {})
    if key is not None:
        if value is None:
            metadata.pop(key)
        else:
            metadata[key] = value
    table = table.replace_schema_metadata(None if key is None else metadata)
    pq.write_table(table, bronze_output.path)
    with pytest.raises(ValueError, match=message):
        BronzeReader().read(bronze_output.path)


@pytest.mark.parametrize(
    "column,value,message",
    [
        ("record_index", 1, "record_index sequence is invalid"),
        ("raw_payload", "{broken", "invalid JSON"),
        ("raw_payload", "[]", "JSON object"),
        ("raw_payload", "null", "JSON object"),
        ("raw_payload", '{"changed":true}', "raw content hash does not match"),
    ],
)
def test_bronze_row_corruption(
    bronze_output: BronzeWriteResult,
    column: str,
    value: object,
    message: str,
) -> None:
    table = pq.ParquetFile(bronze_output.path).read()
    rows = table.to_pylist()
    rows[0][column] = value
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), bronze_output.path)
    with pytest.raises(ValueError, match=message):
        BronzeReader().read(bronze_output.path)


@pytest.mark.parametrize(
    "component,replacement",
    [
        ("source", "source=OTHER"),
        ("ingestion_date", "ingestion_date=2026-09-17"),
        ("batch_id", "batch_id=wrong"),
        ("filename", "unexpected.parquet"),
    ],
)
def test_bronze_partition_and_filename_corruption(
    tmp_path: Path,
    bronze_output: BronzeWriteResult,
    component: str,
    replacement: str,
) -> None:
    parts = list(bronze_output.path.relative_to(tmp_path / "bronze").parts)
    index = {"source": 0, "ingestion_date": 1, "batch_id": 2, "filename": 3}[component]
    parts[index] = replacement
    corrupt_path = (tmp_path / "corrupt").joinpath(*parts)
    corrupt_path.parent.mkdir(parents=True)
    shutil.copyfile(bronze_output.path, corrupt_path)
    message = "filename" if component == "filename" else "partition path"
    with pytest.raises(ValueError, match=message):
        BronzeReader().read(corrupt_path)
