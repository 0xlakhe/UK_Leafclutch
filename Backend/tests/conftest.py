"""Test configuration.

The environment is set before any application module is imported so that settings and the
engine are built for the test database, never for local or production data. These tests
construct an engine but open no connection.
"""

import os
from collections.abc import Iterator

import pytest

from app.config import get_settings

TEST_DATABASE_URL = "postgresql+psycopg://leafclutch:leafclutch@localhost:5432/leafclutch_test"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Keep the lru_cache from leaking settings between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
