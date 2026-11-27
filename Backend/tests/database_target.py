"""Resolve and validate the only database the test suite may use.

The resolution is pure: it takes the environment mapping and the path to ``Backend/.env``
so the guard can be tested without importing the application or mutating the process.
"""

from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import make_url
from sqlalchemy.exc import ArgumentError

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def validate_test_database_url(url: str) -> str:
    """Return ``url`` only if it is a disposable, local test target.

    The password is redacted in errors so a rejected production URL cannot leak its
    credentials into test logs.
    """
    try:
        parsed = make_url(url)
    except (ArgumentError, ValueError) as exc:
        raise RuntimeError(f"Refusing database URL {url!r}: it does not parse.") from exc

    display = parsed.render_as_string(hide_password=True)
    database = parsed.database or ""

    if not database.endswith("_test"):
        raise RuntimeError(
            f"Refusing database URL {display!r}: the database name must end in '_test'."
        )

    host = (parsed.host or "").lower()
    if host not in LOOPBACK_HOSTS:
        raise RuntimeError(
            f"Refusing database URL {display!r}: the host must be loopback "
            "(127.0.0.1, localhost or ::1)."
        )

    return url


def resolve_test_database_url(environ: Mapping[str, str], env_file: Path) -> str:
    """Resolve the test target and reject anything that is not obviously disposable.

    ``TEST_DATABASE_URL`` is the deliberate CI override. Otherwise the URL is derived on
    loopback with the Compose port from ``POSTGRES_PORT``: the environment first, then
    only that key from ``env_file``, then 5432. An exported ``DATABASE_URL`` is never the
    target; it is validated solely so a production or otherwise unsafe value stops the
    run instead of being silently replaced.
    """
    explicit = environ.get("TEST_DATABASE_URL")
    if explicit is not None:
        return validate_test_database_url(explicit)

    ambient = environ.get("DATABASE_URL")
    if ambient is not None:
        validate_test_database_url(ambient)

    port = environ.get("POSTGRES_PORT") or None
    if port is None and env_file.is_file():
        port = dotenv_values(env_file).get("POSTGRES_PORT") or None
    port = port or "5432"

    return validate_test_database_url(
        f"postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:{port}/leafclutch_test"
    )
