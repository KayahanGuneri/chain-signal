from pathlib import Path

import pytest
from pydantic import ValidationError

from chainsignal_pipeline.config import Settings


def test_settings_use_expected_defaults() -> None:
    settings = Settings()

    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.http_timeout_seconds == 10.0
    assert settings.bronze_path == Path("data/bronze")


def test_http_timeout_can_be_overridden_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAIN_SIGNAL_HTTP_TIMEOUT_SECONDS", "25.5")

    settings = Settings()

    assert settings.http_timeout_seconds == 25.5


def test_invalid_http_timeout_fails_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAIN_SIGNAL_HTTP_TIMEOUT_SECONDS", "-1")

    with pytest.raises(ValidationError):
        Settings()
