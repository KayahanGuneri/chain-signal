from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

CANONICAL_EVENT_SCHEMA_VERSION = "v1"


class EventType(StrEnum):
    """Canonical event types understood by ChainSignal."""

    EARTHQUAKE = "EARTHQUAKE"
    FLOOD = "FLOOD"
    CONFLICT = "CONFLICT"
    PROTEST = "PROTEST"
    STRIKE = "STRIKE"


class Severity(StrEnum):
    """Canonical severity levels understood by ChainSignal."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class CanonicalEvent:
    """Provider-independent canonical Event v1."""

    source: str
    source_event_id: str
    event_type: EventType
    occurred_at: datetime
    latitude: float
    longitude: float
    severity: Severity
    country: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = CANONICAL_EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("Canonical event source must not be blank")

        if not self.source_event_id.strip():
            raise ValueError("Canonical event source_event_id must not be blank")

        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("Canonical event occurred_at must be timezone-aware")

        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("Canonical event latitude must be between -90 and 90")

        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("Canonical event longitude must be between -180 and 180")

        if self.country is not None and not self.country.strip():
            raise ValueError("Canonical event country must be null or non-blank")

        if not self.schema_version.strip():
            raise ValueError("Canonical event schema_version must not be blank")

    @property
    def identity(self) -> tuple[str, str]:
        """Return the canonical source identity."""

        return (
            self.source,
            self.source_event_id,
        )
