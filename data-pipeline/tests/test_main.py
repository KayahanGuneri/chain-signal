import argparse
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

import pytest

from chainsignal_pipeline import __main__ as app
from chainsignal_pipeline.config import Settings
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
