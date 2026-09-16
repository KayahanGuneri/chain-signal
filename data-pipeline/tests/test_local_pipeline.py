import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from chainsignal_pipeline.bronze.models import BronzeRequest
from chainsignal_pipeline.bronze.reader import BronzeReader
from chainsignal_pipeline.bronze.writer import BronzeWriter
from chainsignal_pipeline.normalization.gdacs import normalize_gdacs_records
from chainsignal_pipeline.normalization.writer import NormalizationWriter


def test_local_pipeline_preserves_raw_records_quality_and_idempotency(
    tmp_path: Path,
    bronze_request: BronzeRequest,
    gdacs_record: dict[str, Any],
    ingested_at: datetime,
) -> None:
    flood = deepcopy(gdacs_record)
    flood["properties"].update(eventtype="FL", eventid=456, alertlevel="Red")
    invalid = deepcopy(gdacs_record)
    invalid["properties"].pop("fromdate")
    invalid["geometry"]["coordinates"] = [30, 120]
    duplicate = deepcopy(gdacs_record)
    duplicate["properties"]["country"] = "Changed"
    records = [gdacs_record, invalid, flood, duplicate]
    bronze_writer = BronzeWriter(tmp_path / "bronze")
    normalized_writer = NormalizationWriter(tmp_path / "normalized")
    snapshot: dict[str, bytes] = {}
    for run in range(2):
        bronze = bronze_writer.write(
            request=bronze_request,
            raw_records=records,
            ingested_at=ingested_at + timedelta(days=run),
        )
        assert bronze.created is (run == 0)
        verified = BronzeReader().read(bronze.path)
        assert verified.raw_records == tuple(records)
        assert verified.metadata == bronze.metadata
        result = normalize_gdacs_records(verified.raw_records)
        assert [event.identity for event in result.events] == [
            ("GDACS", "EQ:123"),
            ("GDACS", "FL:456"),
        ]
        assert result.events[0].occurred_at == datetime(2026, 9, 14, 1, tzinfo=UTC)
        assert [record.record_index for record in result.quarantined_records] == [1, 3]
        assert result.quarantined_records[0].raw_record == invalid
        assert result.summary.reason_counts_by_code == {
            "INVALID_OCCURRENCE_TIME": 1,
            "INVALID_COORDINATES": 1,
            "DUPLICATE_CANONICAL_IDENTITY": 1,
        }
        output = normalized_writer.write(
            source=verified.metadata.source,
            batch_id=verified.metadata.batch_id,
            events=result.events,
            quarantined_records=result.quarantined_records,
            summary=result.summary,
        )
        assert output.created is (run == 0)
        rows = pq.ParquetFile(output.events_path).read().to_pylist()
        assert [(row["sourceEventId"], row["eventType"], row["severity"]) for row in rows] == [
            ("EQ:123", "EARTHQUAKE", "MEDIUM"),
            ("FL:456", "FLOOD", "HIGH"),
        ]
        quarantine = pq.ParquetFile(output.quarantine_path).read().to_pylist()
        assert [json.loads(row["raw_payload"]) for row in quarantine] == [invalid, duplicate]
        quality = json.loads(output.quality_path.read_text(encoding="utf-8"))
        assert {
            key: quality[key]
            for key in [
                "input_count",
                "valid_count",
                "invalid_count",
                "duplicate_count",
                "quarantine_count",
            ]
        } == {
            "input_count": 4,
            "valid_count": 2,
            "invalid_count": 1,
            "duplicate_count": 1,
            "quarantine_count": 2,
        }
        current = {
            str(path.relative_to(tmp_path)): path.read_bytes()
            for path in tmp_path.rglob("*")
            if path.is_file()
        }
        if run == 0:
            snapshot = current
        else:
            assert current == snapshot
