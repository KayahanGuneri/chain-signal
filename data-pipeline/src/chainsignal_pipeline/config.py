from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHAIN_SIGNAL_",
        extra="ignore",
    )

    environment: Literal[
        "local",
        "test",
        "production",
    ] = "local"

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    http_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=120,
    )

    bronze_path: Path = Path("data/bronze")
    normalized_path: Path = Path("data/normalized")


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHAIN_SIGNAL_DB_",
        extra="ignore",
    )

    host: str
    port: int = Field(
        ge=1,
        le=65535,
    )
    name: str
    user: str
    password: SecretStr

    connect_timeout_seconds: int = Field(
        default=10,
        gt=0,
        le=60,
    )

    @field_validator("host", "name", "user")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Database setting must not be blank")

        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("Database password must not be empty")

        return value
