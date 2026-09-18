import os
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from chainsignal_pipeline.config import DatabaseSettings
from chainsignal_pipeline.database.event_writer import EventPersistenceWriter
from chainsignal_pipeline.models.event import CanonicalEvent, EventType, Severity

pytestmark = pytest.mark.skipif(
    os.environ.get("CHAIN_SIGNAL_TEST_DATABASE") != "1",
    reason="Run scripts/phase2-smoke.ps1 -RunTests for disposable PostGIS",
)


@pytest.fixture
def database() -> Iterator[
    tuple[psycopg.Connection[tuple[Any, ...]], EventPersistenceWriter, CanonicalEvent]
]:
    settings = DatabaseSettings()
    source = "PYTEST_" + uuid4().hex
    with psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.name,
        user=settings.user,
        password=settings.password.get_secret_value(),
        autocommit=True,
    ) as connection:
        assert connection.execute(
            "SELECT count(*) FROM flyway_schema_history WHERE success"
        ).fetchone() == (3,)
        event = CanonicalEvent(
            source,
            "one",
            EventType.FLOOD,
            datetime(2026, 9, 1, tzinfo=UTC),
            41,
            29,
            Severity.HIGH,
            None,
            {"nested": {"null": None, "text": "Türkiye"}, "list": [1, True]},
        )
        try:
            yield connection, EventPersistenceWriter(settings), event
        finally:
            connection.execute("DELETE FROM event WHERE source=%s", (source,))


def test_insert_rerun_update_identity_jsonb_and_generated_geography(
    database: tuple[psycopg.Connection[tuple[Any, ...]], EventPersistenceWriter, CanonicalEvent],
) -> None:
    connection, writer, event = database
    assert writer.write([event]).changed_count == 1
    query = """SELECT id, xmin::text, country, metadata, ST_X(location::geometry),
               ST_Y(location::geometry), ST_SRID(location::geometry) FROM event WHERE source=%s"""
    first = connection.execute(query, (event.source,)).fetchone()
    assert first is not None
    assert first[2:] == (None, event.metadata, 29.0, 41.0, 4326)
    result = writer.write([event])
    assert (result.changed_count, result.unchanged_count) == (0, 1)
    assert connection.execute(query, (event.source,)).fetchone() == first
    changed = replace(
        event,
        event_type=EventType.STRIKE,
        severity=Severity.CRITICAL,
        country=" Provider text ",
        latitude=42,
        longitude=30,
        occurred_at=datetime(2026, 9, 2, tzinfo=UTC),
        metadata={"changed": True},
    )
    assert writer.write([changed]).changed_count == 1
    updated = connection.execute(query, (event.source,)).fetchone()
    assert updated is not None and updated[0] == first[0] and updated[1] != first[1]
    assert updated[2:] == (" Provider text ", {"changed": True}, 30.0, 42.0, 4326)
    assert connection.execute(
        "SELECT event_type, severity, occurred_at FROM event WHERE source=%s", (event.source,)
    ).fetchone() == ("STRIKE", "CRITICAL", changed.occurred_at)
    assert writer.write([changed]).changed_count == 0


def test_atomic_batch_rolls_back_inserts_and_updates_on_database_failure(
    database: tuple[psycopg.Connection[tuple[Any, ...]], EventPersistenceWriter, CanonicalEvent],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection, writer, event = database
    writer.write([event])
    original = writer._to_database_parameters

    def parameters(item: CanonicalEvent) -> tuple[Any, ...]:
        values = original(item)
        return (None, *values[1:]) if item.source_event_id == "fail" else values

    monkeypatch.setattr(writer, "_to_database_parameters", parameters)
    with pytest.raises(psycopg.errors.NotNullViolation):
        writer.write(
            [
                replace(event, severity=Severity.LOW),
                replace(event, source_event_id="new"),
                replace(event, source_event_id="fail"),
            ]
        )
    assert connection.execute(
        "SELECT source_event_id, severity FROM event WHERE source=%s", (event.source,)
    ).fetchall() == [("one", "HIGH")]


def test_duplicate_and_unsupported_batches_leave_database_unchanged(
    database: tuple[psycopg.Connection[tuple[Any, ...]], EventPersistenceWriter, CanonicalEvent],
) -> None:
    connection, writer, event = database
    for batch in [
        [event, replace(event, severity=Severity.LOW)],
        [event, replace(event, source_event_id="two", schema_version="v2")],
    ]:
        with pytest.raises(ValueError):
            writer.write(batch)
        assert connection.execute(
            "SELECT count(*) FROM event WHERE source=%s", (event.source,)
        ).fetchone() == (0,)
