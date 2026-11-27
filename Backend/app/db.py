"""Database base class, engine and session construction, and the request dependency."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


def build_engine(settings: Settings) -> Engine:
    """Build the engine for this process.

    Creating an engine opens no connection; the pool connects on first use. The engine is
    owned by the application lifespan, never by a module global.
    """
    return create_engine(settings.database_url)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build the session factory bound to ``engine``."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session(request: Request) -> Iterator[Session]:
    """Yield a session from the factory the lifespan stored on the application."""
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
