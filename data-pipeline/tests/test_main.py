import argparse
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any
from unittest.mock import MagicMock

import pyarrow.parquet as pq
import pytest

from chainsignal_pipeline import __main__ as app
from chainsignal_pipeline.bronze.writer import BronzeWriteResult
from chainsignal_pipeline.config import DatabaseSettings, Settings
from chainsignal_pipeline.database.event_writer import EventPersistenceResult
from chainsignal_pipeline.sources.base import SourceWindow


def test_parse_datetime_accepts_timezone_aware_value() -> None:
    parsed = app.parse_datetime("2026-09-15T12:30:00+03:00")

    assert parsed == datetime(
        2026,
        9,
        15,
        12,
        30,
        tzinfo=parsed.tzinfo,
    )
    assert parsed.utcoffset() is not None


def test_parse_datetime_rejects_naive_value() -> None:
    with pytest.raises(
        argparse.ArgumentTypeError,
        match="timezone offset",
    ):
        app.parse_datetime("2026-09-15T12:30:00")


def test_run_gdacs_fetch_wires_settings_to_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            return None

    class FakeAdapter:
        source_name = "GDACS"

        def __init__(self, client: object) -> None:
            captured["client"] = client

        def fetch(
            self,
            window: SourceWindow,
        ) -> list[dict[str, Any]]:
            captured["window"] = window

            return [
                {
                    "type": "Feature",
                }
            ]

    def fake_create_gdacs_client(
        *,
        timeout_seconds: float,
    ) -> FakeClient:
        captured["timeout_seconds"] = timeout_seconds
        return FakeClient()

    monkeypatch.setattr(
        app,
        "create_gdacs_client",
        fake_create_gdacs_client,
    )
    monkeypatch.setattr(
        app,
        "GdacsAdapter",
        FakeAdapter,
    )

    settings = Settings(
        http_timeout_seconds=23.0,
    )

    start = datetime(
        2026,
        9,
        14,
        tzinfo=UTC,
    )
    end = datetime(
        2026,
        9,
        15,
        tzinfo=UTC,
    )

    app.run_gdacs_fetch(
        settings=settings,
        start=start,
        end=end,
    )

    assert captured["timeout_seconds"] == 23.0

    window = captured["window"]

    assert isinstance(window, SourceWindow)
    assert window.start == start
    assert window.end == end


def test_normalize_parser_accepts_bronze_file(tmp_path: Path) -> None:
    path = tmp_path / "part-00000.parquet"
    args = app.build_parser().parse_args(["normalize-gdacs", "--bronze-file", str(path)])
    assert args.command == "normalize-gdacs"
    assert args.bronze_file == path


def test_normalization_command_uses_configured_normalized_path(
    tmp_path: Path,
    bronze_output: BronzeWriteResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "custom"
    monkeypatch.setenv("CHAIN_SIGNAL_NORMALIZED_PATH", str(root))
    # Logging configuration is process-global; preserve pytest's capture handlers.
    monkeypatch.setattr(app, "configure_logging", lambda level: None)
    for key, value in {
        "HOST": "localhost",
        "PORT": "5432",
        "NAME": "unit_test",
        "USER": "unit_test",
        "PASSWORD": "unit_test",
    }.items():
        monkeypatch.setenv("CHAIN_SIGNAL_DB_" + key, value)
    persistence = MagicMock()
    persistence.write.return_value = EventPersistenceResult(1, 1)
    factory = MagicMock(return_value=persistence)
    monkeypatch.setattr(app, "EventPersistenceWriter", factory)
    app.main(["normalize-gdacs", "--bronze-file", str(bronze_output.path)])
    factory.assert_called_once()
    persistence.write.assert_called_once()
    assert persistence.write.call_args.args[0][0].identity == ("GDACS", "EQ:123")
    path = (
        root
        / "source=GDACS"
        / "normalization_version=v1"
        / f"batch_id={bronze_output.metadata.batch_id}"
    )
    assert {output.name for output in path.iterdir()} == {
        "events.parquet",
        "quarantine.parquet",
        "quality.json",
    }
    assert pq.ParquetFile(path / "events.parquet").read().column("sourceEventId").to_pylist() == [
        "EQ:123"
    ]


def test_cli_propagates_database_failure_without_completion_log(
    tmp_path: Path,
    bronze_output: BronzeWriteResult,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("CHAIN_SIGNAL_NORMALIZED_PATH", str(tmp_path / "normalized"))
    monkeypatch.setattr(app, "configure_logging", lambda level: None)
    configured = DatabaseSettings.model_validate(
        {
            "host": "localhost",
            "port": 5432,
            "name": "unit_test",
            "user": "unit_test",
            "password": "unit_test",
        }
    )
    monkeypatch.setattr(app, "DatabaseSettings", lambda: configured)
    persistence = MagicMock()
    persistence.write.side_effect = RuntimeError("Database unavailable")
    monkeypatch.setattr(app, "EventPersistenceWriter", MagicMock(return_value=persistence))
    with caplog.at_level("INFO"), pytest.raises(RuntimeError, match="Database unavailable"):
        app.main(["normalize-gdacs", "--bronze-file", str(bronze_output.path)])
    assert not any(
        getattr(record, "event", "") == "gdacs_normalization_completed" for record in caplog.records
    )
