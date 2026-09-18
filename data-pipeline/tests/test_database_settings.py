import pytest
from pydantic import SecretStr, ValidationError

from chainsignal_pipeline.config import DatabaseSettings


def settings(**overrides: object) -> DatabaseSettings:
    values: dict[str, object] = {
        "host": "localhost",
        "port": 5432,
        "name": "test",
        "user": "test",
        "password": SecretStr("unit-test-secret"),
        "connect_timeout_seconds": 10,
    }
    values.update(overrides)
    return DatabaseSettings.model_validate(values)


@pytest.mark.parametrize("field", ["host", "name", "user"])
@pytest.mark.parametrize("value", ["", " \t"])
def test_blank_database_settings_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        settings(**{field: value})


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_database_port_bounded(port: int) -> None:
    with pytest.raises(ValidationError):
        settings(port=port)


@pytest.mark.parametrize("timeout", [0, 61])
def test_connect_timeout_bounded(timeout: int) -> None:
    with pytest.raises(ValidationError):
        settings(connect_timeout_seconds=timeout)


def test_secret_never_appears_in_settings_repr_or_json() -> None:
    configured = settings()
    assert "unit-test-secret" not in repr(configured)
    assert "unit-test-secret" not in configured.model_dump_json()
    assert configured.password.get_secret_value() == "unit-test-secret"
    with pytest.raises(ValidationError):
        settings(password=SecretStr(""))


def test_settings_load_explicit_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "HOST": "localhost",
        "PORT": "55433",
        "NAME": "test",
        "USER": "test",
        "PASSWORD": "unit-test-secret",
    }.items():
        monkeypatch.setenv("CHAIN_SIGNAL_DB_" + key, value)
    configured = DatabaseSettings()
    assert configured.port == 55433
    assert configured.password.get_secret_value() == "unit-test-secret"


def test_required_settings_do_not_silently_default(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ["HOST", "PORT", "NAME", "USER", "PASSWORD"]:
        monkeypatch.delenv("CHAIN_SIGNAL_DB_" + key, raising=False)
    with pytest.raises(ValidationError):
        DatabaseSettings()
