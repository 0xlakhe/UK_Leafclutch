"""Test configuration.

The database target is resolved and validated before any application module is imported:
the suite refuses a non-test database or a non-loopback host, never uses an exported
``DATABASE_URL`` as its target, and always runs with ``ENVIRONMENT=test``.

Database-backed tests share one engine. A session fixture applies the local ``auth``
stand-in and ``alembic upgrade head`` once; each test then runs inside its own transaction,
which is always rolled back, so rows never leak between tests.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from database_target import resolve_test_database_url
from sqlalchemy import Connection, Engine

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
BACKEND_DIR = Path(__file__).resolve().parent.parent
BOOTSTRAP_SQL = BACKEND_DIR / "scripts" / "bootstrap_local.sql"

os.environ["DATABASE_URL"] = resolve_test_database_url(os.environ, ENV_FILE)
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Keep the lru_cache from leaking settings between tests."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def build_alembic_config() -> Config:
    """Return the project configuration, independent of the working directory."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    return build_alembic_config()


@pytest.fixture(scope="session")
def database_engine(alembic_config: Config) -> Iterator[Engine]:
    """Ensure the Supabase stand-in exists and bring the test database to head once."""
    from app.config import get_settings
    from app.db import build_engine

    engine = build_engine(get_settings())
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(BOOTSTRAP_SQL.read_text(encoding="utf-8"))
        command.upgrade(alembic_config, "head")
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(database_engine: Engine) -> Iterator[Connection]:
    """A transaction per test, rolled back so the database keeps no test rows."""
    with database_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()
