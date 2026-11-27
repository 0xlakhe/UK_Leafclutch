---
task: 0001
title: FastAPI skeleton and local database
status: in-progress
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Stand up the runnable backend skeleton: configuration, application assembly, a liveness
endpoint, the SQLAlchemy/Alembic baseline and a PostgreSQL service for local work. No
domain tables or feature endpoints. This is M1 in `PLAN.md`.

Stack is fixed: Python 3.12, FastAPI, sync SQLAlchemy 2.0 + psycopg 3, Alembic,
pydantic-settings.

## Acceptance criteria

- [ ] `cd Backend && uv sync` installs from a clean checkout.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run mypy app` passes.
- [ ] `uv run pytest` passes, and the output is quoted in `## Tests`.
- [ ] `uv run uvicorn app.main:app` serves `GET /health` → 200 `{"status":"ok"}`.
- [ ] `docker compose up -d db` reaches `healthy`, and `uv run alembic current` runs
      against it without error.
- [ ] No secret is committed; `.env.example` lists every required variable.

## Non-goals

- ORM models, tables, RLS, roles, publish functions (M2 onwards).
- Auth, content, enquiries, media, email, revalidation.
- CI, deployment, `Frontend/`, `Admin/`.

## Plan

1. `pyproject.toml`, `.gitignore`, `.env.example`.
2. `app/config.py` — pydantic-settings; `DATABASE_URL` required, no default; environment
   and log level as literals.
3. `app/db.py` — `Base`, `build_engine`, `build_session_factory`, `get_session`; the engine
   is built in the lifespan and stored on `app.state`, never as a module global.
4. `app/health.py` — liveness only, no database dependency.
5. `app/main.py` — `create_app()` and the lifespan.
6. Alembic baseline: `alembic.ini`, `migrations/env.py` reading the URL from settings,
   empty `versions/`.
7. `compose.yaml` with PostgreSQL 16, a healthcheck and a `leafclutch_test` database.
8. Tests: health, configuration validation, engine/session construction.
9. `README.md` — setup, commands, layout. Replace the empty `README.MD` with `git mv`.

## Work log

- **2026-11-27 — Skeleton built.** Added `pyproject.toml` (Python 3.12; FastAPI, sync
  SQLAlchemy 2.0 + psycopg 3, Alembic, pydantic-settings; ruff, mypy and pytest
  configured), `.env.example`, `compose.yaml` with PostgreSQL 16 and the
  `leafclutch_test` init script, `app/config.py`, `app/db.py`, `app/health.py`,
  `app/main.py`, the Alembic baseline and 12 tests. Renamed the empty `README.MD` to
  `README.md` with `git mv` and wrote the setup, run, checks, database, layout and docs
  sections.
- **2026-11-27 — Checks.** `uv sync`, `ruff`, `mypy` and `pytest` pass; `/health` returns
  200 under uvicorn. `docker compose up -d db` is blocked by a native PostgreSQL 18
  already listening on host port 5432, so the container cannot bind. Per the brief the
  port and `.env.example` were left unchanged. `alembic current` therefore reaches the
  wrong server and fails authentication; `alembic upgrade head --sql` (offline) succeeds,
  proving `migrations/env.py` loads the URL from settings.

## Decisions made

- `DATABASE_URL` is required and has no default. The single `# type: ignore[call-arg]` on
  `Settings()` exists only because mypy cannot see pydantic-settings fields as
  constructor arguments; the field still has no default.
- `.env` is read when present and is git-ignored; `.env.example` lists every variable.
- `create_app()` reads no settings. `get_settings()` runs in the lifespan, so importing
  `app.main` (including OpenAPI generation) does not need a database URL. The engine and
  session factory live on `app.state`, and the engine is disposed on shutdown.
- `sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)`: request-scoped
  sessions should not flush implicitly, and objects should stay usable after commit.
- Alembic takes the URL from `get_settings()`, not `alembic.ini`. A literal `%` (possible
  in a password) is escaped before being stored in the ConfigParser option.
- Tests set `DATABASE_URL` (the `leafclutch_test` database created by the init script) and
  `ENVIRONMENT=test` in `conftest.py` before importing the app, and clear the settings
  cache around every test. They construct an engine but open no connection.
- `[tool.uv] package = false` because the service is an application, not an installable
  package. `uv.lock` is committed.
- The health response is a Pydantic model with `status: Literal["ok"]`. It is liveness
  only; readiness/database checks are out of scope for M1.

## Files changed

New:

- `Backend/pyproject.toml`
- `Backend/uv.lock`
- `Backend/.env.example`
- `Backend/compose.yaml`
- `Backend/docker/initdb/01-create-test-db.sql`
- `Backend/app/__init__.py`
- `Backend/app/config.py`
- `Backend/app/db.py`
- `Backend/app/health.py`
- `Backend/app/main.py`
- `Backend/alembic.ini`
- `Backend/migrations/env.py`
- `Backend/migrations/script.py.mako`
- `Backend/migrations/versions/.gitkeep`
- `Backend/tests/conftest.py`
- `Backend/tests/test_health.py`
- `Backend/tests/test_config.py`
- `Backend/tests/test_db.py`
- `Backend/docs/work/0001-skeleton.md` (brief plus this log)

Modified:

- `Backend/README.MD` → `Backend/README.md` (renamed with `git mv`, then filled)
- `Backend/docs/work/README.md` (index entry, written by the orchestrator)

`Backend/.gitignore` already contained the Python ignores and was left as it was.

## Migrations

None. This milestone is the Alembic baseline: `alembic.ini`, `migrations/env.py`,
`migrations/script.py.mako` and an empty `migrations/versions/` (`.gitkeep`). No revision
exists and no table is created; `Base.metadata` stays empty until M2.

## Tests

```
$ uv sync
Resolved 44 packages in 9ms
Checked 41 packages in 8ms

$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 5 source files

$ uv run pytest -q
............                                                             [100%]
12 passed, 1 warning in 0.24s
```

The warning is the known one:

```
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning:
Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

Recorded, not chased, per the brief.

Coverage: health 200 and payload; unknown route 404; health still 200 with a deliberately
unreachable database URL (proves liveness does not touch the database); required
`DATABASE_URL`; unknown environment rejected; defaults; cached settings; settings read
from the environment; engine URL; session factory binding; `get_session` using the
factory on `app.state`; lifespan storing the engine and session factory. Role and
empty-state tests are not applicable: M1 has no auth, collections or tables.

Database checks:

```
$ docker compose up -d db
Container backend-db-1 Created
Container backend-db-1 Starting
Error response from daemon: ports are not available: exposing port TCP 0.0.0.0:5432 -> 127.0.0.1:0: listen tcp 0.0.0.0:5432: bind: address already in use
```

Diagnosis: host port 5432 is occupied by a native PostgreSQL 18
(`/Library/PostgreSQL/18/bin/postgres`, user `postgres`); `pg_isready` reports
`127.0.0.1:5432 - accepting connections` and `nc` succeeds, while the container stays
`Created` and never starts. The port and `.env.example` were not changed.

```
$ DATABASE_URL=postgresql+psycopg://leafclutch:leafclutch@localhost:5432/leafclutch uv run alembic current
...
psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 5432
failed: FATAL:  password authentication failed for user "leafclutch"
(Background on this error at: https://sqlalche.me/e/21/e3q8)
```

Alembic does load `migrations/env.py` and the settings URL — it reaches the host's
server — but that server is not the compose database.

```
$ DATABASE_URL=postgresql+psycopg://leafclutch:leafclutch@localhost:5432/leafclutch uv run alembic upgrade head --sql
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Generating static SQL
INFO  [alembic.runtime.migration] Will assume transactional DDL.
BEGIN;

COMMIT;
```

The offline path exercises `env.py` and the URL wiring without a connection.

```
$ DATABASE_URL=postgresql+psycopg://leafclutch:leafclutch@localhost:5432/leafclutch uv run uvicorn app.main:app --port 8000
GET /health -> 200 {"status":"ok"}
INFO:     Application startup complete.
INFO:     127.0.0.1:52651 - "GET /health HTTP/1.1" 200 OK
INFO:     Application shutdown complete.
```

## Review

## Docs updated

- `Backend/README.md`: setup, run, checks, database, layout and documentation table;
  renamed from the empty `Backend/README.MD` with `git mv`.
- `Backend/docs/work/0001-skeleton.md`: this record.
- `Backend/docs/work/README.md`: task index entry (orchestrator).
- No `DATABASE.md`, `CONTRACT.md` or `ADMIN.md` change: M1 adds no table, payload, role or
  admin screen. The OpenAPI schema is generated from the app (`/openapi.json`, `/docs`);
  there is no static spec to edit. There is no ADR directory under `Backend/docs/`.

## Open questions

- Host port 5432 is occupied by a native PostgreSQL 18. The compose service cannot bind
  and `alembic current` authenticates against the wrong server. Possible resolutions are
  to stop that server, move the compose host port (which also changes `.env.example`), or
  use the native server. The brief forbids changing the port here, so this needs an
  orchestrator decision.
- `DATABASE.md` "Open questions" item 1 still says "Confirm before scaffolding". This task
  settles it as sync SQLAlchemy 2.0 + psycopg 3 on Python 3.12, but the source document
  was left untouched because the brief lists the expected files and says nothing else.
  A follow-up docs edit may be wanted.
- `StarletteDeprecationWarning` recommends `httpx2` for `TestClient`. Not changed here.

## Not verified

- `docker compose up -d db` reaching `healthy`, and the `leafclutch_test` init script
  running — the container never started because the host port is taken.
- `uv run alembic current` against the compose database — it connects to the host's
  PostgreSQL 18 and fails authentication.
- Migration `upgrade`/`downgrade` — there are no revisions yet.
- `uv sync` from a literal clean checkout — it ran in this working tree and resolved
  `uv.lock`; no second clone was made.
