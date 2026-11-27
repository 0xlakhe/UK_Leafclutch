import os
import subprocess
import sys
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


def test_query_override_is_refused(tmp_path: Path) -> None:
    url = (
        "postgresql+psycopg://leafclutch:supersecret@127.0.0.1:1/leafclutch_test"
        "?host=db.production.example&dbname=leafclutch"
    )

    with pytest.raises(RuntimeError, match="query") as excinfo:
        resolve_test_database_url({"TEST_DATABASE_URL": url}, tmp_path / ".env")

    message = str(excinfo.value)
    assert "supersecret" not in message
    assert "db.production.example" not in message


def test_malformed_url_does_not_leak_the_password(tmp_path: Path) -> None:
    url = "postgresql+psycopg://user:supersecret@127.0.0.1:notaport/leafclutch_test"

    with pytest.raises(RuntimeError, match="not a valid") as excinfo:
        resolve_test_database_url({"TEST_DATABASE_URL": url}, tmp_path / ".env")

    message = str(excinfo.value)
    assert "supersecret" not in message
    assert excinfo.value.__cause__ is None


@pytest.mark.parametrize(
    "port",
    [
        "0",
        "65536",
        "abc",
        "5432/leafclutch",
        "5432?host=db.production.example",
        "${DATABASE_URL}",
    ],
)
def test_invalid_postgres_port_is_refused(tmp_path: Path, port: str) -> None:
    with pytest.raises(RuntimeError) as excinfo:
        resolve_test_database_url({"POSTGRES_PORT": port}, tmp_path / ".env")

    message = str(excinfo.value)
    assert "POSTGRES_PORT" in message
    assert port not in message
    assert "db.production.example" not in message


def test_env_file_port_cannot_interpolate_another_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_PORT=${DATABASE_URL}\n"
        "DATABASE_URL=postgresql+psycopg://prod:prod@db.production.example:5432/leafclutch\n"
    )

    with pytest.raises(RuntimeError) as excinfo:
        resolve_test_database_url({}, env_file)

    message = str(excinfo.value)
    assert "POSTGRES_PORT" in message
    assert "db.production.example" not in message
    assert "prod:prod" not in message


def test_conftest_forces_a_test_environment_in_a_subprocess() -> None:
    backend = Path(__file__).resolve().parent.parent
    conftest_path = backend / "tests" / "conftest.py"
    script = (
        "import importlib.util, os\n"
        f"spec = importlib.util.spec_from_file_location('conftest_force', {str(conftest_path)!r})\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "print(os.environ['ENVIRONMENT'])\n"
    )
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "PYTHONPATH": str(backend / "tests"),
    }
    for key in ("DATABASE_URL", "POSTGRES_PORT", "TEST_DATABASE_URL"):
        env.pop(key, None)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "test"
