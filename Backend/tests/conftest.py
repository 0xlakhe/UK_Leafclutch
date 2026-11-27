"""Test configuration.

The database target is resolved and validated before any application module is imported:
the suite refuses a non-test database or a non-loopback host, never uses an exported
``DATABASE_URL`` as its target, and always runs with ``ENVIRONMENT=test``. These tests
construct an engine but open no connection.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from database_target import resolve_test_database_url

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

os.environ["DATABASE_URL"] = resolve_test_database_url(os.environ, ENV_FILE)
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Keep the lru_cache from leaking settings between tests."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
