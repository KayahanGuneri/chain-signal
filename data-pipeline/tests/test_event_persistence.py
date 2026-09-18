from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import MagicMock

import psycopg
import pytest
from psycopg.types.json import Jsonb
from pydantic import SecretStr

from chainsignal_pipeline.config import DatabaseSettings
from chainsignal_pipeline.database.event_writer import EventPersistenceWriter
from chainsignal_pipeline.models.event import CanonicalEvent, EventType, Severity


@pytest.fixture
def canonical() -> CanonicalEvent:
    return CanonicalEvent(
        "TEST",
        "one",
        EventType.FLOOD,
        datetime(2026, 9, 1, tzinfo=UTC),
        41,
        29,
        Severity.HIGH,
        None,
        {"nested": [True, None, "Türkiye"]},
    )


@pytest.fixture
def writer() -> EventPersistenceWriter:
    return EventPersistenceWriter(
        DatabaseSettings(
            host="localhost",
            port=5432,
            name="test",
            user="test",
            password=SecretStr("unit-test-secret"),
        )
    )


def test_empty_batch_never_connects(
    writer: EventPersistenceWriter, monkeypatch: pytest.MonkeyPatch
) -> None:
    connect = MagicMock()
    monkeypatch.setattr(psycopg, "connect", connect)
    result = writer.write([])
    assert (result.input_count, result.changed_count, result.unchanged_count) == (0, 0, 0)
    connect.assert_not_called()


@pytest.mark.parametrize("invalid", ["version", "duplicate"])
def test_invalid_batches_rejected_before_connecting(
    writer: EventPersistenceWriter,
    canonical: CanonicalEvent,
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
) -> None:
    connect = MagicMock()
    monkeypatch.setattr(psycopg, "connect", connect)
    events = (
        [replace(canonical, schema_version="v2")]
        if invalid == "version"
        else [canonical, canonical]
    )
    with pytest.raises(ValueError, match="Unsupported" if invalid == "version" else "Duplicate"):
        writer.write(events)
    connect.assert_not_called()


def test_batch_uses_explicit_transaction_jsonb_and_never_location(
    writer: EventPersistenceWriter, canonical: CanonicalEvent, monkeypatch: pytest.MonkeyPatch
) -> None:
    connect = MagicMock()
    connection = connect.return_value.__enter__.return_value
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.rowcount = 1
    monkeypatch.setattr(psycopg, "connect", connect)
    result = writer.write([canonical])
    assert result.changed_count == 1
    connection.transaction.assert_called_once_with()
    sql, rows = cursor.executemany.call_args.args
    assert "location" not in sql
    assert "ON CONFLICT (source, source_event_id)" in sql
    assert isinstance(rows[0][8], Jsonb)
    assert rows[0][8].obj == canonical.metadata
    assert connect.call_args.kwargs["password"] == "unit-test-secret"
    assert connect.call_args.kwargs["autocommit"] is True
