from dataclasses import replace
from datetime import UTC, datetime

import pytest

from chainsignal_pipeline.models.event import CanonicalEvent, EventType, Severity


@pytest.fixture
def event() -> CanonicalEvent:
    return CanonicalEvent(
        source="GDACS",
        source_event_id="EQ:123",
        event_type=EventType.EARTHQUAKE,
        occurred_at=datetime(2026, 9, 14, tzinfo=UTC),
        latitude=40.0,
        longitude=30.0,
        severity=Severity.MEDIUM,
        country=None,
    )


def test_valid_event_has_canonical_identity_and_nullable_country(event: CanonicalEvent) -> None:
    assert event.identity == ("GDACS", "EQ:123")
    assert event.country is None
    assert event.schema_version == "v1"
    assert replace(event, country="Türkiye", severity=Severity.HIGH).identity == event.identity
    assert replace(event, source="OTHER").identity != event.identity


@pytest.mark.parametrize("field", ["source", "source_event_id", "country", "schema_version"])
def test_blank_event_fields_are_rejected(event: CanonicalEvent, field: str) -> None:
    with pytest.raises(ValueError, match=field):
        replace(
            event,
            source="  " if field == "source" else event.source,
            source_event_id="  " if field == "source_event_id" else event.source_event_id,
            country="  " if field == "country" else event.country,
            schema_version="  " if field == "schema_version" else event.schema_version,
        )


def test_naive_occurrence_is_rejected(event: CanonicalEvent) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(event, occurred_at=datetime(2026, 9, 14))


@pytest.mark.parametrize("latitude", [-90.0, 90.0])
@pytest.mark.parametrize("longitude", [-180.0, 180.0])
def test_coordinate_boundaries_are_inclusive(
    event: CanonicalEvent,
    latitude: float,
    longitude: float,
) -> None:
    bounded = replace(event, latitude=latitude, longitude=longitude)
    assert bounded.latitude == latitude
    assert bounded.longitude == longitude


@pytest.mark.parametrize(
    "field,value",
    [
        ("latitude", -90.01),
        ("latitude", 90.01),
        ("longitude", -180.01),
        ("longitude", 180.01),
        ("latitude", float("nan")),
        ("longitude", float("inf")),
    ],
)
def test_invalid_coordinates_are_rejected(event: CanonicalEvent, field: str, value: float) -> None:
    with pytest.raises(ValueError, match=field):
        replace(
            event,
            latitude=value if field == "latitude" else event.latitude,
            longitude=value if field == "longitude" else event.longitude,
        )
