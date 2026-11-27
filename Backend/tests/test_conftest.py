import importlib
import os

import conftest
import pytest


def test_external_database_url_is_not_overwritten(monkeypatch: pytest.MonkeyPatch) -> None:
    external = "postgresql+psycopg://ci:ci@database.internal:5432/leafclutch"
    monkeypatch.setenv("DATABASE_URL", external)

    importlib.reload(conftest)

    assert os.environ["DATABASE_URL"] == external


def test_local_test_database_url_uses_the_postgres_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_PORT", "5434")

    assert conftest.local_test_database_url() == (
        "postgresql+psycopg://leafclutch:leafclutch@localhost:5434/leafclutch_test"
    )
