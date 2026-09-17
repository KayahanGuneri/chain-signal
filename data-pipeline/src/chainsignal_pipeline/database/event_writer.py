from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from chainsignal_pipeline.config import DatabaseSettings
from chainsignal_pipeline.models.event import (
    CANONICAL_EVENT_SCHEMA_VERSION,
    CanonicalEvent,
)

_UPSERT_EVENTS_SQL = """
INSERT INTO event (
    source,
    source_event_id,
    event_type,
    occurred_at,
    latitude,
    longitude,
    severity,
    country,
    metadata,
    schema_version
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s
)
ON CONFLICT (source, source_event_id)
DO UPDATE SET
    event_type = EXCLUDED.event_type,
    occurred_at = EXCLUDED.occurred_at,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    severity = EXCLUDED.severity,
    country = EXCLUDED.country,
    metadata = EXCLUDED.metadata,
    schema_version = EXCLUDED.schema_version
WHERE (
    event.event_type,
    event.occurred_at,
    event.latitude,
    event.longitude,
    event.severity,
    event.country,
    event.metadata,
    event.schema_version
) IS DISTINCT FROM (
    EXCLUDED.event_type,
    EXCLUDED.occurred_at,
    EXCLUDED.latitude,
    EXCLUDED.longitude,
    EXCLUDED.severity,
    EXCLUDED.country,
    EXCLUDED.metadata,
    EXCLUDED.schema_version
)
"""


@dataclass(frozen=True, slots=True)
class EventPersistenceResult:
    input_count: int
    changed_count: int

    @property
    def unchanged_count(self) -> int:
        return self.input_count - self.changed_count


class EventPersistenceWriter:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings

    def write(
        self,
        events: Sequence[CanonicalEvent],
    ) -> EventPersistenceResult:
        self._validate_events(events)

        if not events:
            return EventPersistenceResult(
                input_count=0,
                changed_count=0,
            )

        parameters = [self._to_database_parameters(event) for event in events]

        with psycopg.connect(
            host=self._settings.host,
            port=self._settings.port,
            dbname=self._settings.name,
            user=self._settings.user,
            password=self._settings.password.get_secret_value(),
            connect_timeout=self._settings.connect_timeout_seconds,
            autocommit=True,
        ) as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.executemany(
                        _UPSERT_EVENTS_SQL,
                        parameters,
                        returning=False,
                    )
                    changed_count = cursor.rowcount

        return EventPersistenceResult(
            input_count=len(events),
            changed_count=changed_count,
        )

    @staticmethod
    def _validate_events(
        events: Sequence[CanonicalEvent],
    ) -> None:
        seen_identities: set[tuple[str, str]] = set()

        for event in events:
            if event.schema_version != CANONICAL_EVENT_SCHEMA_VERSION:
                raise ValueError(
                    "Unsupported canonical event schema version: "
                    f"{event.schema_version!r}; "
                    f"expected {CANONICAL_EVENT_SCHEMA_VERSION!r}"
                )

            if event.identity in seen_identities:
                raise ValueError(
                    f"Duplicate canonical event identity in persistence batch: {event.identity!r}"
                )

            seen_identities.add(event.identity)

    @staticmethod
    def _to_database_parameters(
        event: CanonicalEvent,
    ) -> tuple[Any, ...]:
        return (
            event.source,
            event.source_event_id,
            event.event_type.value,
            event.occurred_at,
            event.latitude,
            event.longitude,
            event.severity.value,
            event.country,
            Jsonb(dict(event.metadata)),
            event.schema_version,
        )
