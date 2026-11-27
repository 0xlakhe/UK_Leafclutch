"""Test configuration.

The environment is populated before any application module is imported, so settings and
the engine target the test database. A caller-supplied ``DATABASE_URL`` (CI) wins over the
local default. These tests construct an engine but open no connection.
"""

import os
from collections.abc import Iterator

import pytest


def local_test_database_url() -> str:
    """The test database on the Compose host port, 5432 unless overridden."""
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg://leafclutch:leafclutch@localhost:{port}/leafclutch_test"


os.environ.setdefault("DATABASE_URL", local_test_database_url())
os.environ.setdefault("ENVIRONMENT", "test")

from app.config import get_settings  # noqa: E402  (the environment must be set first)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Keep the lru_cache from leaking settings between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
