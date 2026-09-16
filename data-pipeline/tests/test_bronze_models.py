from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from chainsignal_pipeline.bronze.models import (
    BronzeBatchMetadata,
    BronzeRequest,
    calculate_raw_content_hash,
)


def test_request_identity_uses_utc_and_request_contract(bronze_request: BronzeRequest) -> None:
    offset = timezone(timedelta(hours=3))
    equivalent = replace(
        bronze_request,
        window_start=bronze_request.window_start.astimezone(offset),
        window_end=bronze_request.window_end.astimezone(offset),
    )
    assert equivalent.request_identity == bronze_request.request_identity
    assert replace(bronze_request).request_identity == bronze_request.request_identity
    for changed in [
        replace(bronze_request, source="OTHER"),
        replace(bronze_request, request_contract_version="v2"),
        replace(bronze_request, window_start=bronze_request.window_start - timedelta(hours=1)),
        replace(bronze_request, window_end=bronze_request.window_end + timedelta(hours=1)),
    ]:
        assert changed.request_identity != bronze_request.request_identity


def test_content_hash_ignores_object_key_order_but_preserves_record_order() -> None:
    records = [{"a": 1, "b": 2}, {"id": 3}]
    assert calculate_raw_content_hash(records) == calculate_raw_content_hash(
        [
            {"b": 2, "a": 1},
            {"id": 3},
        ]
    )
    assert calculate_raw_content_hash(records) != calculate_raw_content_hash(records[::-1])
    assert calculate_raw_content_hash([]) == calculate_raw_content_hash([])


def test_batch_identity_tracks_content_and_utc_partition(
    bronze_request: BronzeRequest,
    gdacs_record: dict[str, Any],
) -> None:
    ingestion = datetime(2026, 9, 16, 1, tzinfo=timezone(timedelta(hours=3)))
    original = BronzeBatchMetadata.create(
        request=bronze_request,
        raw_records=[gdacs_record],
        ingested_at=ingestion,
    )
    repeat = BronzeBatchMetadata.create(
        request=bronze_request,
        raw_records=[deepcopy(gdacs_record)],
        ingested_at=ingestion + timedelta(days=1),
    )
    assert original.batch_id == repeat.batch_id
    assert original.partition_date.isoformat() == "2026-09-15"
    gdacs_record["properties"]["country"] = "Changed"
    changed = BronzeBatchMetadata.create(
        request=bronze_request,
        raw_records=[gdacs_record],
        ingested_at=ingestion,
    )
    assert changed.request_identity == original.request_identity
    assert changed.raw_content_hash != original.raw_content_hash
    assert changed.batch_id != original.batch_id


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("source", " ", "source"),
        ("request_contract_version", " ", "request_contract_version"),
        ("window_start", datetime(2026, 9, 14), "window_start must be timezone-aware"),
        ("window_end", datetime(2026, 9, 16), "window_end must be timezone-aware"),
        ("window_start", datetime(2026, 9, 17, tzinfo=UTC), "must not be after"),
    ],
)
def test_invalid_request_invariants(
    bronze_request: BronzeRequest,
    field: str,
    value: Any,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(bronze_request, **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", " "),
        ("request_identity", " "),
        ("raw_content_hash", " "),
        ("batch_id", " "),
        ("ingested_at", datetime(2026, 9, 16)),
        ("record_count", -1),
    ],
)
def test_invalid_batch_metadata_invariants(
    bronze_request: BronzeRequest,
    ingested_at: datetime,
    field: str,
    value: Any,
) -> None:
    metadata = BronzeBatchMetadata.create(
        request=bronze_request,
        raw_records=[],
        ingested_at=ingested_at,
    )
    with pytest.raises(ValueError, match=field):
        replace(metadata, **{field: value})
