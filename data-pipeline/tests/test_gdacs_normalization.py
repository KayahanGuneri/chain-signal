from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest

from chainsignal_pipeline.models.event import (
    EventType,
    Severity,
)
from chainsignal_pipeline.normalization.gdacs import (
    normalize_gdacs_records,
)
from chainsignal_pipeline.quality.models import (
    QuarantineReason,
)


def make_gdacs_record() -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
                80.6401,
                7.2143,
            ],
        },
        "properties": {
            "eventtype": "FL",
            "eventid": 1104160,
            "fromdate": "2026-09-14T01:00:00",
            "alertlevel": "Green",
            "country": "Sri Lanka",
            "episodeid": 1,
            "source": "GLOFAS",
            "alertscore": 1,
            "episodealertlevel": "Green",
            "episodealertscore": 0.5,
            "iso3": "LKA",
            "iscurrent": "true",
            "istemporary": "false",
            "todate": "2026-09-16T01:00:00",
            "datemodified": "2026-09-16T05:56:43",
        },
    }


def test_normalizes_valid_gdacs_record() -> None:
    result = normalize_gdacs_records([make_gdacs_record()])

    assert result.summary.input_count == 1
    assert result.summary.valid_count == 1
    assert result.summary.invalid_count == 0
    assert result.summary.duplicate_count == 0
    assert result.summary.quarantine_count == 0

    assert len(result.events) == 1
    assert result.quarantined_records == ()

    event = result.events[0]

    assert event.source == "GDACS"
    assert event.source_event_id == "FL:1104160"
    assert event.event_type == EventType.FLOOD
    assert event.occurred_at == datetime(
        2026,
        9,
        14,
        1,
        0,
        tzinfo=UTC,
    )
    assert event.latitude == 7.2143
    assert event.longitude == 80.6401
    assert event.severity == Severity.LOW
    assert event.country == "Sri Lanka"
    assert event.schema_version == "v1"

    assert event.metadata["gdacs_episode_id"] == 1
    assert event.metadata["gdacs_source"] == "GLOFAS"


def test_quarantines_missing_occurrence_time() -> None:
    record = make_gdacs_record()
    record["properties"].pop("fromdate")

    result = normalize_gdacs_records([record])

    assert result.events == ()
    assert result.summary.input_count == 1
    assert result.summary.valid_count == 0
    assert result.summary.invalid_count == 1
    assert result.summary.duplicate_count == 0
    assert result.summary.quarantine_count == 1

    quarantine = result.quarantined_records[0]

    assert quarantine.reasons == (QuarantineReason.INVALID_OCCURRENCE_TIME,)


def test_quarantines_invalid_coordinates() -> None:
    record = make_gdacs_record()
    record["geometry"]["coordinates"] = [
        80.6401,
        120.0,
    ]

    result = normalize_gdacs_records([record])

    assert result.events == ()
    assert result.summary.invalid_count == 1
    assert result.summary.quarantine_count == 1

    assert result.quarantined_records[0].reasons == (QuarantineReason.INVALID_COORDINATES,)


def test_collects_multiple_quarantine_reasons() -> None:
    record = make_gdacs_record()

    record["properties"]["fromdate"] = "not-a-date"
    record["properties"]["alertlevel"] = "Unknown"
    record["geometry"]["coordinates"] = [
        500.0,
        120.0,
    ]

    result = normalize_gdacs_records([record])

    quarantine = result.quarantined_records[0]

    assert quarantine.reasons == (
        QuarantineReason.INVALID_OCCURRENCE_TIME,
        QuarantineReason.INVALID_COORDINATES,
        QuarantineReason.INVALID_SEVERITY,
    )

    assert result.summary.input_count == 1
    assert result.summary.valid_count == 0
    assert result.summary.invalid_count == 1
    assert result.summary.duplicate_count == 0
    assert result.summary.quarantine_count == 1

    assert result.summary.reason_counts_by_code == {
        "INVALID_OCCURRENCE_TIME": 1,
        "INVALID_COORDINATES": 1,
        "INVALID_SEVERITY": 1,
    }


def test_quarantines_duplicate_canonical_identity() -> None:
    first = make_gdacs_record()
    duplicate = deepcopy(first)

    duplicate["properties"]["country"] = "Different mutable provider value"

    result = normalize_gdacs_records(
        [
            first,
            duplicate,
        ]
    )

    assert len(result.events) == 1
    assert len(result.quarantined_records) == 1

    assert result.summary.input_count == 2
    assert result.summary.valid_count == 1
    assert result.summary.invalid_count == 0
    assert result.summary.duplicate_count == 1
    assert result.summary.quarantine_count == 1

    assert result.quarantined_records[0].reasons == (QuarantineReason.DUPLICATE_CANONICAL_IDENTITY,)

    assert result.summary.reason_counts_by_code == {
        "DUPLICATE_CANONICAL_IDENTITY": 1,
    }


@pytest.mark.parametrize(
    "provider,canonical",
    [
        ("Green", Severity.LOW),
        ("Orange", Severity.MEDIUM),
        ("Red", Severity.HIGH),
    ],
)
def test_earthquake_severity_mapping(
    gdacs_record: dict[str, Any],
    provider: str,
    canonical: Severity,
) -> None:
    gdacs_record["properties"]["alertlevel"] = provider
    result = normalize_gdacs_records([gdacs_record])
    event = result.events[0]
    assert event.event_type == EventType.EARTHQUAKE
    assert event.identity == ("GDACS", "EQ:123")
    assert event.severity == canonical
    assert event.severity != Severity.CRITICAL
    assert (event.longitude, event.latitude) == (30.5, 40.25)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("eventid", None, QuarantineReason.MISSING_SOURCE_EVENT_ID),
        ("eventid", True, QuarantineReason.MISSING_SOURCE_EVENT_ID),
        ("eventid", "  ", QuarantineReason.MISSING_SOURCE_EVENT_ID),
        ("eventtype", "TC", QuarantineReason.UNSUPPORTED_EVENT_TYPE),
        ("fromdate", None, QuarantineReason.INVALID_OCCURRENCE_TIME),
        ("fromdate", "not-a-date", QuarantineReason.INVALID_OCCURRENCE_TIME),
        ("alertlevel", "Critical", QuarantineReason.INVALID_SEVERITY),
        ("alertlevel", None, QuarantineReason.INVALID_SEVERITY),
    ],
)
def test_invalid_provider_properties_reach_quarantine(
    gdacs_record: dict[str, Any],
    field: str,
    value: object,
    reason: QuarantineReason,
) -> None:
    if value is None:
        gdacs_record["properties"].pop(field)
    else:
        gdacs_record["properties"][field] = value
    result = normalize_gdacs_records([gdacs_record])
    assert result.events == ()
    assert result.summary.invalid_count == 1
    assert result.summary.duplicate_count == 0
    assert result.quarantined_records[0].reasons == (reason,)
    assert result.quarantined_records[0].raw_record == gdacs_record


@pytest.mark.parametrize(
    "geometry",
    [
        None,
        {},
        {"type": "LineString", "coordinates": [30, 40]},
        {"type": "Point", "coordinates": None},
        {"type": "Point", "coordinates": []},
        {"type": "Point", "coordinates": [30]},
        {"type": "Point", "coordinates": "30,40"},
        {"type": "Point", "coordinates": [30, 91]},
        {"type": "Point", "coordinates": [181, 40]},
        {"type": "Point", "coordinates": [30, -91]},
        {"type": "Point", "coordinates": [-181, 40]},
        {"type": "Point", "coordinates": [True, 40]},
        {"type": "Point", "coordinates": [30, False]},
        {"type": "Point", "coordinates": ["30", 40]},
        {"type": "Point", "coordinates": [30, "40"]},
        {"type": "Point", "coordinates": [float("nan"), 40]},
        {"type": "Point", "coordinates": [30, float("nan")]},
        {"type": "Point", "coordinates": [float("inf"), 40]},
        {"type": "Point", "coordinates": [30, -float("inf")]},
    ],
)
def test_invalid_geometry_reaches_quarantine(
    gdacs_record: dict[str, Any],
    geometry: object,
) -> None:
    if geometry is None:
        gdacs_record.pop("geometry")
    else:
        gdacs_record["geometry"] = geometry
    result = normalize_gdacs_records([gdacs_record])
    assert result.events == ()
    assert result.summary.invalid_count == result.summary.quarantine_count == 1
    assert result.quarantined_records[0].reasons == (QuarantineReason.INVALID_COORDINATES,)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-09-14T01:00:00",
        "2026-09-14T04:00:00+03:00",
        "2026-09-14T01:00:00Z",
        "2026-09-13T21:00:00-04:00",
    ],
)
def test_occurrence_normalizes_to_utc(gdacs_record: dict[str, Any], timestamp: str) -> None:
    gdacs_record["properties"]["fromdate"] = timestamp
    event = normalize_gdacs_records([gdacs_record]).events[0]
    assert event.occurred_at == datetime(2026, 9, 14, 1, tzinfo=UTC)
    assert event.occurred_at.tzinfo is UTC


@pytest.mark.parametrize("country", [None, "", "  "])
def test_optional_country_normalizes_to_null(gdacs_record: dict[str, Any], country: object) -> None:
    if country is None:
        gdacs_record["properties"].pop("country")
    else:
        gdacs_record["properties"]["country"] = country
    result = normalize_gdacs_records([gdacs_record])
    assert result.events[0].country is None
    assert result.summary.quarantine_count == 0


def test_metadata_contains_only_selected_supplementary_fields(gdacs_record: dict[str, Any]) -> None:
    event = normalize_gdacs_records([gdacs_record]).events[0]
    assert event.metadata == {
        "gdacs_episode_id": 2,
        "gdacs_source": "provider",
        "gdacs_alert_level": "Orange",
        "gdacs_alert_score": 1.5,
        "gdacs_episode_alert_level": "Green",
        "gdacs_episode_alert_score": 0.5,
        "gdacs_severity_data": {"magnitude": 5.5},
        "gdacs_iso3": "TUR",
        "gdacs_affected_countries": ["Türkiye"],
        "gdacs_is_current": True,
        "gdacs_is_temporary": False,
        "gdacs_to_date": "2026-09-15T01:00:00",
        "gdacs_modified_at": "2026-09-16T02:00:00",
    }
    gdacs_record["properties"]["severitydata"]["magnitude"] = 99
    assert event.metadata["gdacs_severity_data"] == {"magnitude": 5.5}


@pytest.mark.parametrize("record", [{}, {"type": "Feature", "properties": []}])
def test_malformed_records_are_quarantined(record: dict[str, Any]) -> None:
    result = normalize_gdacs_records([record])
    assert result.summary.invalid_count == 1
    assert result.quarantined_records[0].reasons == (QuarantineReason.MALFORMED_RECORD,)


def test_batch_ordering_and_first_valid_identity_are_deterministic(
    gdacs_record: dict[str, Any],
) -> None:
    invalid = deepcopy(gdacs_record)
    invalid["properties"].pop("fromdate")
    duplicate = deepcopy(gdacs_record)
    duplicate["properties"].update(country="Changed", alertscore=99)
    second = deepcopy(gdacs_record)
    second["properties"]["eventid"] = 456
    records = [invalid, gdacs_record, second, duplicate, invalid]
    first = normalize_gdacs_records(records)
    assert normalize_gdacs_records(records) == first
    assert [event.source_event_id for event in first.events] == ["EQ:123", "EQ:456"]
    assert first.events[0].country == "Türkiye"
    assert [record.record_index for record in first.quarantined_records] == [0, 3, 4]
    assert first.summary.input_count == 5
    assert first.summary.valid_count == 2
    assert first.summary.invalid_count == 2
    assert first.summary.duplicate_count == 1
    assert first.summary.quarantine_count == 3


def test_empty_normalization_batch() -> None:
    result = normalize_gdacs_records([])
    assert result.events == ()
    assert result.quarantined_records == ()
    assert result.summary.input_count == result.summary.quarantine_count == 0
    assert result.summary.reason_counts_by_code == {}
