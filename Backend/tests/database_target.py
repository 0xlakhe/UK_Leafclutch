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


def _validated_port(port: str | None) -> str:
    """Return the Compose port only when it is a plain decimal port number."""
    if port is None or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise RuntimeError(
            "Refusing POSTGRES_PORT: it must be a decimal integer between 1 and 65535."
        )
    return port


def validate_test_database_url(url: str) -> str:
    """Return ``url`` only if it is a disposable, local test target.

    Errors never include the raw URL. Parsed refusals print it with the password hidden.
    """
    try:
        parsed = make_url(url)
    except (ArgumentError, ValueError):
        raise RuntimeError(
            "Refusing test database URL: it is not a valid SQLAlchemy URL."
        ) from None

    if parsed.query:
        raise RuntimeError(
            "Refusing test database URL: query parameters can override the connection "
            "target and are not allowed."
        )

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
    only that key from ``env_file`` (without interpolation), then 5432. An exported
    ``DATABASE_URL`` is never the target; it is validated solely so a production or
    otherwise unsafe value stops the run instead of being silently replaced.
    """
    explicit = environ.get("TEST_DATABASE_URL")
    if explicit is not None:
        return validate_test_database_url(explicit)

    ambient = environ.get("DATABASE_URL")
    if ambient is not None:
        validate_test_database_url(ambient)

    if "POSTGRES_PORT" in environ:
        port = _validated_port(environ["POSTGRES_PORT"])
    else:
        env_values = (
            dotenv_values(env_file, interpolate=False) if env_file.is_file() else {}
        )
        if "POSTGRES_PORT" in env_values:
            port = _validated_port(env_values["POSTGRES_PORT"])
        else:
            port = "5432"

    return validate_test_database_url(
        f"postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:{port}/leafclutch_test"
    )
