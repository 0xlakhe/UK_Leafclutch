from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_health_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/not-a-route")

    assert response.status_code == 404


def test_health_does_not_touch_the_database(monkeypatch) -> None:
    # Port 1 refuses immediately, so the test fails fast if liveness ever queries the DB.
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://nobody:nobody@127.0.0.1:1/missing",
    )
    get_settings.cache_clear()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
