import os
from pathlib import Path

import pytest
from database_target import resolve_test_database_url

VALID_TEST_URL = "postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:5432/leafclutch_test"


def test_explicit_test_database_url_is_accepted(tmp_path: Path) -> None:
    assert (
        resolve_test_database_url({"TEST_DATABASE_URL": VALID_TEST_URL}, tmp_path / ".env")
        == VALID_TEST_URL
    )


def test_explicit_non_test_database_is_refused(tmp_path: Path) -> None:
    url = "postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:5432/leafclutch"

    with pytest.raises(RuntimeError, match="_test"):
        resolve_test_database_url({"TEST_DATABASE_URL": url}, tmp_path / ".env")


def test_non_loopback_host_is_refused(tmp_path: Path) -> None:
    url = "postgresql+psycopg://prod:prod@db.production.example:5432/leafclutch_test"

    with pytest.raises(RuntimeError, match="loopback"):
        resolve_test_database_url({"TEST_DATABASE_URL": url}, tmp_path / ".env")


def test_ambient_non_test_database_url_is_refused(tmp_path: Path) -> None:
    url = "postgresql+psycopg://prod:prod@db.production.example:5432/leafclutch"

    with pytest.raises(RuntimeError, match="_test") as excinfo:
        resolve_test_database_url({"DATABASE_URL": url}, tmp_path / ".env")

    message = str(excinfo.value)
    assert "db.production.example" in message
    assert "prod:prod" not in message


def test_ambient_test_database_url_is_not_used_as_the_target(tmp_path: Path) -> None:
    environ = {
        "DATABASE_URL": "postgresql+psycopg://ci:ci@127.0.0.1:5432/other_test",
        "POSTGRES_PORT": "5434",
    }

    url = resolve_test_database_url(environ, tmp_path / ".env")

    assert url == "postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:5434/leafclutch_test"


def test_postgres_port_is_read_from_the_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_PORT=5434\n"
        "DATABASE_URL=postgresql+psycopg://prod:prod@db.production.example:5432/leafclutch\n"
    )

    url = resolve_test_database_url({}, env_file)

    assert url == "postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:5434/leafclutch_test"


def test_environment_port_wins_over_the_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("POSTGRES_PORT=5434\n")

    url = resolve_test_database_url({"POSTGRES_PORT": "5433"}, env_file)

    assert url == "postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:5433/leafclutch_test"


def test_conftest_forces_a_test_environment() -> None:
    assert os.environ["ENVIRONMENT"] == "test"
    assert os.environ["DATABASE_URL"].endswith("/leafclutch_test")
