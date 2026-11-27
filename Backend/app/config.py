"""Application settings, loaded once from the environment."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    ``DATABASE_URL`` has no default on purpose: a missing database URL is a deployment
    error, not something to paper over with a localhost connection.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "staging", "production", "test"] = "development"
    database_url: str
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"


@lru_cache
def get_settings() -> Settings:
    """Return the one settings instance for this process.

    ``database_url`` is a required field, but mypy cannot see pydantic-settings fields
    as constructor arguments, so the call is silenced rather than given a default.
    """
    return Settings()  # type: ignore[call-arg]
