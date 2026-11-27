# Leafclutch UK backend

The FastAPI service behind the Leafclutch UK website and admin panel. It is the only part
of the system that holds database credentials and talks to PostgreSQL.

M1 is the runnable skeleton: configuration, application assembly, a liveness endpoint, the
SQLAlchemy/Alembic baseline and a local PostgreSQL service. There are no domain tables or
feature endpoints yet.

## Setup

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (for the local
database).

```bash
cd Backend
uv sync
cp .env.example .env
```

`.env` is ignored by git. `DATABASE_URL` is required and has no default; the other
variables have defaults. Do not commit `.env` or put real credentials in
`.env.example`.

## Run

```bash
uv run uvicorn app.main:app --reload
```

The liveness endpoint is `GET /health`, which answers `{"status":"ok"}`. It does not touch
the database. Interactive API docs are at `/docs`; the generated OpenAPI schema is the
API contract.

## Checks

```bash
uv run ruff check .
uv run mypy app
uv run pytest
```

Tests construct the engine but open no connection, so they do not need a running
database.

## Database

Start the local PostgreSQL 16 service and wait for it to become healthy:

```bash
docker compose up -d --wait db
docker compose ps
```

The container creates the `leafclutch` database and, on first initialisation, the
`leafclutch_test` database used by the test suite. It publishes the database on the
loopback interface only (`127.0.0.1`) and uses the throwaway `leafclutch`/`leafclutch`
credentials from `compose.yaml`; these are for local development and must not be reused
anywhere else.

The Compose host port is configurable. `POSTGRES_PORT` defaults to 5432; when that port is
already in use, set it in `.env` to a free port (5434 in this checkout) and change the port
in `DATABASE_URL` to match. The container always listens on 5432 internally.

Alembic reads the URL from application settings (`.env` or the environment), never from
`alembic.ini`:

```bash
uv run alembic current
```

Create and apply migrations:

```bash
uv run alembic revision -m "describe the change"
uv run alembic upgrade head
```

The init scripts only run when the volume is first created. To rebuild a broken local
database from scratch, `docker compose down -v` and start it again; this deletes all local
data.

## Layout

| Path | Contents |
| --- | --- |
| `app/config.py` | Pydantic settings; `DATABASE_URL` is required |
| `app/db.py` | `Base`, engine and session factory builders, `get_session` dependency |
| `app/health.py` | `GET /health`, liveness only |
| `app/main.py` | `create_app()` and the lifespan that owns the engine |
| `migrations/` | Alembic environment and revisions |
| `tests/` | Health, configuration and database-construction tests |
| `compose.yaml`, `docker/initdb/` | Local PostgreSQL 16 and the test database |

The engine and session factory live on `app.state`, created in the lifespan and disposed
on shutdown. They are never module globals.

## Documentation

| Question | Read |
| --- | --- |
| What are we building, and what is legally required? | [`docs/PRD.md`](docs/PRD.md) |
| What is the public payload and what has been decided? | [`docs/CONTRACT.md`](docs/CONTRACT.md) |
| What tables, functions, publish gates and grants exist? | [`docs/DATABASE.md`](docs/DATABASE.md) |
| What are the admin screens, endpoints, roles and tests? | [`docs/ADMIN.md`](docs/ADMIN.md) |
| What is the build plan? | [`docs/work/PLAN.md`](docs/work/PLAN.md) |
| What was done in each task? | [`docs/work/`](docs/work/) |
