"""Alembic environment. The database URL comes from application settings, not the ini."""

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  # registers every table on Base.metadata
from app.config import get_settings
from app.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ConfigParser interpolates "%(name)s", so a literal percent (a password may contain
# one) has to be escaped before it is stored.
config.set_main_option(
    "sqlalchemy.url",
    get_settings().database_url.replace("%", "%%"),
)

target_metadata = Base.metadata


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    """Keep schemas Supabase owns out of autogenerate.

    A plain PostgreSQL database has an `auth` schema only because the local bootstrap
    created it; Supabase owns the real one. The stub in app/models.py exists so the staff
    foreign key resolves. Without this filter autogenerate proposes creating the stub, and
    with `include_schemas` it would compare or drop Supabase's real table.
    """
    schema = getattr(obj, "schema", None)
    if schema is None and type_ != "table":
        schema = getattr(getattr(obj, "table", None), "schema", None)
    return schema != "auth"


def run_migrations_offline() -> None:
    """Run migrations without a live connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
