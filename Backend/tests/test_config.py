import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings

DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/example"


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_unknown_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("ENVIRONMENT", "preview")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.database_url == DATABASE_URL
    assert settings.environment == "development"
    assert settings.log_level == "info"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_get_settings_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("ENVIRONMENT", "staging")

    assert get_settings().environment == "staging"
