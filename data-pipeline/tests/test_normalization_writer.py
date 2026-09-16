import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from chainsignal_pipeline.normalization.gdacs import (
    GdacsNormalizationResult,
    normalize_gdacs_records,
)
from chainsignal_pipeline.normalization.writer import NormalizationWriter, NormalizationWriteResult


@pytest.fixture
def normalization_result(gdacs_record: dict[str, Any]) -> GdacsNormalizationResult:
    gdacs_record["properties"].pop("country")
    invalid = deepcopy(gdacs_record)
    invalid["properties"]["fromdate"] = "invalid"
    invalid["properties"]["alertlevel"] = "invalid"
    return normalize_gdacs_records([gdacs_record, invalid, deepcopy(gdacs_record)])


def persist(
    writer: NormalizationWriter, result: GdacsNormalizationResult
) -> NormalizationWriteResult:
    return writer.write(
        source="GDACS",
        batch_id="synthetic-batch",
        events=result.events,
        quarantined_records=result.quarantined_records,
        summary=result.summary,
    )


def test_normalized_persistence_contract(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
) -> None:
    output = persist(NormalizationWriter(tmp_path), normalization_result)
    assert output.created is True
    assert output.output_directory == (
        tmp_path / "source=GDACS" / "normalization_version=v1" / "batch_id=synthetic-batch"
    )
    assert {path.name for path in output.output_directory.iterdir()} == {
        "events.parquet",
        "quarantine.parquet",
        "quality.json",
    }
    metadata = {
        b"source": b"GDACS",
        b"batch_id": b"synthetic-batch",
        b"normalization_version": b"v1",
    }
    events = pq.ParquetFile(output.events_path).read()
    expected_schema = pa.schema(
        [
            pa.field("source", pa.string(), nullable=False),
            pa.field("sourceEventId", pa.string(), nullable=False),
            pa.field("eventType", pa.string(), nullable=False),
            pa.field("occurredAt", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("latitude", pa.float64(), nullable=False),
            pa.field("longitude", pa.float64(), nullable=False),
            pa.field("severity", pa.string(), nullable=False),
            pa.field("country", pa.string(), nullable=True),
            pa.field("metadata", pa.string(), nullable=False),
            pa.field("schemaVersion", pa.string(), nullable=False),
        ],
        metadata=metadata,
    )
    assert events.schema.equals(expected_schema, check_metadata=True)
    event = normalization_result.events[0]
    serialized_metadata = json.dumps(
        event.metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert events.to_pylist() == [
        {
            "source": "GDACS",
            "sourceEventId": "EQ:123",
            "eventType": "EARTHQUAKE",
            "occurredAt": event.occurred_at,
            "latitude": 40.25,
            "longitude": 30.5,
            "severity": "MEDIUM",
            "country": None,
            "metadata": serialized_metadata,
            "schemaVersion": "v1",
        }
    ]
    quarantine = pq.ParquetFile(output.quarantine_path).read()
    expected_quarantine_schema = pa.schema(
        [
            pa.field("record_index", pa.int64(), nullable=False),
            pa.field(
                "reasons", pa.list_(pa.field("element", pa.string(), nullable=True)), nullable=False
            ),
            pa.field("raw_payload", pa.string(), nullable=False),
        ],
        metadata=metadata,
    )
    assert quarantine.schema.equals(expected_quarantine_schema, check_metadata=True)
    assert quarantine.to_pylist() == [
        {
            "record_index": record.record_index,
            "reasons": [reason.value for reason in record.reasons],
            "raw_payload": json.dumps(
                record.raw_record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ),
        }
        for record in normalization_result.quarantined_records
    ]
    assert json.loads(output.quality_path.read_text(encoding="utf-8")) == {
        "source": "GDACS",
        "batch_id": "synthetic-batch",
        "normalization_version": "v1",
        "input_count": 3,
        "valid_count": 1,
        "invalid_count": 1,
        "duplicate_count": 1,
        "quarantine_count": 2,
        "reason_counts": {
            "INVALID_OCCURRENCE_TIME": 1,
            "INVALID_SEVERITY": 1,
            "DUPLICATE_CANONICAL_IDENTITY": 1,
        },
    }


@pytest.mark.parametrize("records_kind", ["mixed", "valid", "empty", "invalid"])
def test_strict_idempotency_including_empty_quarantine_schema(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
    gdacs_record: dict[str, Any],
    records_kind: str,
) -> None:
    result = normalization_result
    if records_kind == "valid":
        result = normalize_gdacs_records([gdacs_record])
    elif records_kind == "empty":
        result = normalize_gdacs_records([])
    elif records_kind == "invalid":
        result = normalize_gdacs_records([{}])
    writer = NormalizationWriter(tmp_path)
    first = persist(writer, result)
    original = {path.name: path.read_bytes() for path in first.output_directory.iterdir()}
    quarantine = pq.ParquetFile(first.quarantine_path).read()
    assert quarantine.num_rows == result.summary.quarantine_count
    assert quarantine.schema.field("reasons").type.value_field.name == "element"
    second = persist(writer, result)
    assert first.created is True
    assert second.created is False
    assert second.output_directory == first.output_directory
    assert {path.name: path.read_bytes() for path in second.output_directory.iterdir()} == original
    assert len(list(tmp_path.rglob("quality.json"))) == 1


@pytest.mark.parametrize("missing_file", ["events.parquet", "quarantine.parquet", "quality.json"])
def test_incomplete_existing_output_fails_loudly(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
    missing_file: str,
) -> None:
    writer = NormalizationWriter(tmp_path)
    first = persist(writer, normalization_result)
    (first.output_directory / missing_file).unlink()
    with pytest.raises(RuntimeError, match="incomplete"):
        persist(writer, normalization_result)
    assert not (first.output_directory / missing_file).exists()


@pytest.mark.parametrize(
    "file_name,column,value",
    [
        ("events.parquet", "sourceEventId", "EQ:changed"),
        ("quarantine.parquet", "raw_payload", '{"tampered":true}'),
        ("quarantine.parquet", "reasons", ["INVALID_COORDINATES"]),
    ],
)
def test_tampered_parquet_content_fails_loudly(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
    file_name: str,
    column: str,
    value: object,
) -> None:
    writer = NormalizationWriter(tmp_path)
    first = persist(writer, normalization_result)
    path = first.output_directory / file_name
    table = pq.ParquetFile(path).read()
    rows = table.to_pylist()
    rows[0][column] = value
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
    tampered = path.read_bytes()
    with pytest.raises(RuntimeError, match="output does not match"):
        persist(writer, normalization_result)
    assert path.read_bytes() == tampered


@pytest.mark.parametrize("file_name", ["events.parquet", "quarantine.parquet"])
@pytest.mark.parametrize("corruption", ["schema", "metadata"])
def test_tampered_parquet_schema_fails_loudly(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
    file_name: str,
    corruption: str,
) -> None:
    writer = NormalizationWriter(tmp_path)
    first = persist(writer, normalization_result)
    path = first.output_directory / file_name
    table = pq.ParquetFile(path).read()
    if corruption == "schema":
        table = table.drop([table.schema.names[0]])
    else:
        table = table.replace_schema_metadata({b"source": b"OTHER"})
    pq.write_table(table, path)
    with pytest.raises(RuntimeError, match="schema does not match"):
        persist(writer, normalization_result)


@pytest.mark.parametrize("content", ['{"valid_count":99}', "{invalid-json"])
def test_tampered_quality_fails_loudly(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
    content: str,
) -> None:
    writer = NormalizationWriter(tmp_path)
    first = persist(writer, normalization_result)
    first.quality_path.write_text(content, encoding="utf-8")
    with pytest.raises(RuntimeError, match="quality output"):
        persist(writer, normalization_result)
    assert first.quality_path.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("mismatch", ["events", "quarantine"])
def test_summary_output_count_mismatch_rejected(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
    mismatch: str,
) -> None:
    with pytest.raises(ValueError, match="does not match"):
        NormalizationWriter(tmp_path).write(
            source="GDACS",
            batch_id="batch",
            summary=normalization_result.summary,
            events=() if mismatch == "events" else normalization_result.events,
            quarantined_records=()
            if mismatch == "quarantine"
            else normalization_result.quarantined_records,
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("field", ["source", "batch_id", "normalization_version"])
def test_blank_persistence_identifiers_rejected(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
    field: str,
) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        writer = NormalizationWriter(
            tmp_path, normalization_version=" " if field == "normalization_version" else "v1"
        )
        writer.write(
            source=" " if field == "source" else "GDACS",
            batch_id=" " if field == "batch_id" else "batch",
            events=normalization_result.events,
            quarantined_records=normalization_result.quarantined_records,
            summary=normalization_result.summary,
        )
    assert list(tmp_path.iterdir()) == []


def test_normalization_versions_have_separate_persisted_state(
    tmp_path: Path,
    normalization_result: GdacsNormalizationResult,
) -> None:
    first = persist(NormalizationWriter(tmp_path), normalization_result)
    second = persist(
        NormalizationWriter(tmp_path, normalization_version="v2"), normalization_result
    )
    assert first.created is second.created is True
    assert first.output_directory != second.output_directory
    assert pq.read_schema(second.events_path).metadata[b"normalization_version"] == b"v2"
