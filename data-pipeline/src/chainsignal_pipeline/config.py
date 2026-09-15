from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHAIN_SIGNAL_",
        extra="ignore",
    )

    environment: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    http_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=120,
    )

    bronze_path: Path = Path("data/bronze")
