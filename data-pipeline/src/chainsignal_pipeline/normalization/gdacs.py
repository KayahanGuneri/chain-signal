from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from chainsignal_pipeline.models.event import (
    CanonicalEvent,
    EventType,
    Severity,
)
from chainsignal_pipeline.quality.models import (
    DataQualitySummary,
    QuarantinedRecord,
    QuarantineReason,
)

GDACS_SOURCE_NAME = "GDACS"

EVENT_TYPE_MAPPING = {
    "EQ": EventType.EARTHQUAKE,
    "FL": EventType.FLOOD,
}

SEVERITY_MAPPING = {
    "Green": Severity.LOW,
    "Orange": Severity.MEDIUM,
    "Red": Severity.HIGH,
}


@dataclass(frozen=True, slots=True)
class GdacsNormalizationResult:
    """Canonical output and data-quality results for one GDACS batch."""

    events: tuple[CanonicalEvent, ...]
    quarantined_records: tuple[QuarantinedRecord, ...]
    summary: DataQualitySummary


def normalize_gdacs_records(
    raw_records: Sequence[dict[str, Any]],
) -> GdacsNormalizationResult:
    """Normalize raw GDACS Features into canonical Event v1 records."""

    events: list[CanonicalEvent] = []
    quarantined_records: list[QuarantinedRecord] = []

    seen_identities: set[tuple[str, str]] = set()

    reason_counts: Counter[QuarantineReason] = Counter()

    invalid_count = 0
    duplicate_count = 0

    for record_index, raw_record in enumerate(raw_records):
        event, reasons = _normalize_record(raw_record)

        if reasons:
            invalid_count += 1

            quarantined_record = QuarantinedRecord(
                record_index=record_index,
                raw_record=deepcopy(raw_record),
                reasons=reasons,
            )

            quarantined_records.append(quarantined_record)
            reason_counts.update(reasons)

            continue

        if event is None:
            raise RuntimeError("GDACS normalization produced neither event nor reasons")

        if event.identity in seen_identities:
            duplicate_count += 1

            duplicate_reason = QuarantineReason.DUPLICATE_CANONICAL_IDENTITY

            quarantined_records.append(
                QuarantinedRecord(
                    record_index=record_index,
                    raw_record=deepcopy(raw_record),
                    reasons=(duplicate_reason,),
                )
            )

            reason_counts[duplicate_reason] += 1
            continue

        seen_identities.add(event.identity)
        events.append(event)

    summary = DataQualitySummary(
        input_count=len(raw_records),
        valid_count=len(events),
        invalid_count=invalid_count,
        duplicate_count=duplicate_count,
        quarantine_count=len(quarantined_records),
        reason_counts=dict(reason_counts),
    )

    return GdacsNormalizationResult(
        events=tuple(events),
        quarantined_records=tuple(quarantined_records),
        summary=summary,
    )


def _normalize_record(
    raw_record: dict[str, Any],
) -> tuple[
    CanonicalEvent | None,
    tuple[QuarantineReason, ...],
]:
    if raw_record.get("type") != "Feature":
        return (
            None,
            (QuarantineReason.MALFORMED_RECORD,),
        )

    properties = raw_record.get("properties")

    if not isinstance(properties, dict):
        return (
            None,
            (QuarantineReason.MALFORMED_RECORD,),
        )

    reasons: list[QuarantineReason] = []

    raw_event_type = _read_non_blank_string(properties.get("eventtype"))

    canonical_event_type = _map_event_type(raw_event_type)

    if canonical_event_type is None:
        reasons.append(QuarantineReason.UNSUPPORTED_EVENT_TYPE)

    source_event_id = _build_source_event_id(
        event_type=raw_event_type,
        event_id=properties.get("eventid"),
    )

    if source_event_id is None:
        reasons.append(QuarantineReason.MISSING_SOURCE_EVENT_ID)

    occurred_at = _parse_occurrence_time(properties.get("fromdate"))

    if occurred_at is None:
        reasons.append(QuarantineReason.INVALID_OCCURRENCE_TIME)

    coordinates = _parse_coordinates(raw_record.get("geometry"))

    if coordinates is None:
        reasons.append(QuarantineReason.INVALID_COORDINATES)

    severity = _map_severity(properties.get("alertlevel"))

    if severity is None:
        reasons.append(QuarantineReason.INVALID_SEVERITY)

    if reasons:
        return (
            None,
            tuple(reasons),
        )

    if (
        canonical_event_type is None
        or source_event_id is None
        or occurred_at is None
        or coordinates is None
        or severity is None
    ):
        raise RuntimeError("GDACS validation succeeded with incomplete canonical fields")

    latitude, longitude = coordinates

    event = CanonicalEvent(
        source=GDACS_SOURCE_NAME,
        source_event_id=source_event_id,
        event_type=canonical_event_type,
        occurred_at=occurred_at,
        latitude=latitude,
        longitude=longitude,
        severity=severity,
        country=_normalize_country(properties.get("country")),
        metadata=_build_metadata(properties),
    )

    return event, ()


def _map_event_type(
    value: str | None,
) -> EventType | None:
    if value is None:
        return None

    return EVENT_TYPE_MAPPING.get(value.upper())


def _build_source_event_id(
    *,
    event_type: str | None,
    event_id: object,
) -> str | None:
    if event_type is None:
        return None

    normalized_event_id = _normalize_event_id(event_id)

    if normalized_event_id is None:
        return None

    return f"{event_type.upper()}:{normalized_event_id}"


def _normalize_event_id(
    value: object,
) -> str | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return str(value)

    if isinstance(value, str):
        stripped = value.strip()

        if stripped:
            return stripped

    return None


def _parse_occurrence_time(
    value: object,
) -> datetime | None:
    text = _read_non_blank_string(value)

    if text is None:
        return None

    normalized_text = text

    if normalized_text.endswith("Z"):
        normalized_text = normalized_text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized_text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _parse_coordinates(
    geometry: object,
) -> tuple[float, float] | None:
    if not isinstance(geometry, dict):
        return None

    if geometry.get("type") != "Point":
        return None

    coordinates = geometry.get("coordinates")

    if not isinstance(coordinates, list):
        return None

    if len(coordinates) < 2:
        return None

    longitude = _finite_number(coordinates[0])
    latitude = _finite_number(coordinates[1])

    if longitude is None or latitude is None:
        return None

    if not -180.0 <= longitude <= 180.0:
        return None

    if not -90.0 <= latitude <= 90.0:
        return None

    return latitude, longitude


def _finite_number(
    value: object,
) -> float | None:
    if isinstance(value, bool):
        return None

    if not isinstance(value, int | float):
        return None

    number = float(value)

    if not math.isfinite(number):
        return None

    return number


def _map_severity(
    value: object,
) -> Severity | None:
    text = _read_non_blank_string(value)

    if text is None:
        return None

    normalized = text.casefold()

    for gdacs_value, severity in SEVERITY_MAPPING.items():
        if gdacs_value.casefold() == normalized:
            return severity

    return None


def _normalize_country(
    value: object,
) -> str | None:
    return _read_non_blank_string(value)


def _read_non_blank_string(
    value: object,
) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()

    if not stripped:
        return None

    return stripped


def _build_metadata(
    properties: dict[str, Any],
) -> dict[str, Any]:
    mappings = {
        "gdacs_episode_id": "episodeid",
        "gdacs_source": "source",
        "gdacs_alert_level": "alertlevel",
        "gdacs_alert_score": "alertscore",
        "gdacs_episode_alert_level": "episodealertlevel",
        "gdacs_episode_alert_score": "episodealertscore",
        "gdacs_severity_data": "severitydata",
        "gdacs_iso3": "iso3",
        "gdacs_affected_countries": "affectedcountries",
        "gdacs_is_current": "iscurrent",
        "gdacs_is_temporary": "istemporary",
        "gdacs_to_date": "todate",
        "gdacs_modified_at": "datemodified",
    }

    metadata: dict[str, Any] = {}

    for metadata_key, provider_key in mappings.items():
        value = properties.get(provider_key)

        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        metadata[metadata_key] = deepcopy(value)

    return metadata
