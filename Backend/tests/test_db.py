from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request

from app.config import Settings
from app.db import build_engine, build_session_factory, get_session
from app.main import app

DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/example"


def test_lifespan_stores_the_engine_and_session_factory() -> None:
    with TestClient(app):
        assert isinstance(app.state.engine, Engine)
        assert isinstance(app.state.session_factory, sessionmaker)


def test_build_engine_uses_the_configured_url() -> None:
    engine = build_engine(Settings(_env_file=None, database_url=DATABASE_URL))
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.url.username == "user"
        assert engine.url.database == "example"
    finally:
        engine.dispose()


def test_session_factory_is_bound_to_the_engine() -> None:
    engine = build_engine(Settings(_env_file=None, database_url=DATABASE_URL))
    try:
        factory = build_session_factory(engine)
        with factory() as session:
            assert session.get_bind() is engine
    finally:
        engine.dispose()


def test_get_session_uses_the_application_factory() -> None:
    engine = build_engine(Settings(_env_file=None, database_url=DATABASE_URL))
    try:
        factory = build_session_factory(engine)
        application = Starlette()
        application.state.session_factory = factory
        request = Request({"type": "http", "app": application})

        sessions = get_session(request)
        session = next(sessions)
        try:
            assert session.get_bind() is engine
        finally:
            sessions.close()
    finally:
        engine.dispose()
