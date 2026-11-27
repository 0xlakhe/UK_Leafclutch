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
- **2026-11-27 — Compose port fix, end to end.** The first attempt could not bind host
  port 5432 (native PostgreSQL 18). Added `name: leafclutch` and the `POSTGRES_PORT`
  substitution, documented the override, created the git-ignored local `.env` with 5434,
  removed the old `backend` project (`docker compose -p backend down -v`: container,
  network and volume), and started the new project. `docker compose up -d --wait db`
  reached `Healthy`; `uv run alembic current` exits 0; `psql -lqt` lists `leafclutch` and
  `leafclutch_test`; `GET /health` returns 200.
- **2026-11-27 — Review fixes (M1–M3, L4–L10).** Bound Compose to `127.0.0.1`, moved the
  healthcheck to the TCP listener, and recreated the container. The test bootstrap now
  derives `POSTGRES_PORT` (default 5432), uses `setdefault` so a caller-supplied
  `DATABASE_URL` wins, and imports `app.config` after the environment is populated.
  Removed the unused `log_level` setting and the framework-only 404 test, corrected the
  README wording and command, added conftest and engine-disposal tests, and confirmed the
  data layer in `DATABASE.md`. 14 tests pass. (`## Plan` step 2 still mentions a log-level
  literal; it is superseded by L8 and left unchanged because `Plan` is orchestrator-owned.)
- **2026-11-27 — Evidence correction (L10).** The first-iteration `## Tests` block, which
  held the failed Compose output, was replaced by the successful block in commit 79d68f3.
  The failure summary remains in the "Checks" entry above; the deleted output is not
  reproduced. The review-fix block in `## Tests` supersedes the 79d68f3 output in turn.

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
- The Compose host port is configurable: `POSTGRES_PORT` (default 5432) substitutes into
  the `db` port mapping, and the project is named `leafclutch` so its containers and
  volume do not depend on the checkout folder. Reason: host port 5432 is owned by a native
  PostgreSQL 18 on this machine and 5433 by another project's container, so this checkout
  uses 5434. `DATABASE_URL` must use the same port; `.env.example` keeps 5432 and
  documents the pairing, while the local `.env` holds the 5434 override and is never
  committed.
- Compose publishes PostgreSQL on the loopback interface only
  (`127.0.0.1:${POSTGRES_PORT:-5432}:5432`). The credentials are a fixed local throwaway
  in the repository, so binding every interface would expose a known-password database to
  the local network; the password stays a Compose-local default, not a deployed secret.
- The test bootstrap derives the URL port from `POSTGRES_PORT` (default 5432) and uses
  `os.environ.setdefault`, so a CI-supplied `DATABASE_URL` wins. `app.config` is imported
  only after the environment is populated. M1 tests still open no connection.
- `log_level` is removed from `Settings` and `.env.example`: nothing consumed it. Logging
  configuration arrives with M20, when there is a real consumer. `environment` stays.
- `test_unknown_route_returns_404` is deleted: it asserts Starlette's routing, not this
  application, and would pass for any FastAPI app.

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

Follow-up (Compose port fix):

- `Backend/compose.yaml` — project name and `POSTGRES_PORT` substitution
- `Backend/.env.example` — `POSTGRES_PORT` and its comment
- `Backend/README.md` — port override paragraph; `alembic current` reads `.env`
- `Backend/docs/work/0001-skeleton.md` — this record
- `Backend/.env` — created locally for the 5434 override, git-ignored, not committed

Review fixes:

- `Backend/compose.yaml` — loopback-only publish; loopback healthcheck
- `Backend/.env.example` — removed `LOG_LEVEL`
- `Backend/README.md` — loopback/throwaway wording; `docker compose up -d --wait db`
- `Backend/app/config.py` — removed the unused `log_level`
- `Backend/tests/conftest.py` — `POSTGRES_PORT` derivation, `setdefault`, import order
- `Backend/tests/test_conftest.py` — new external-URL and port tests
- `Backend/tests/test_config.py` — dropped the `log_level` default assertion
- `Backend/tests/test_health.py` — dropped the framework-only 404 test
- `Backend/tests/test_db.py` — added the engine-disposal test
- `Backend/docs/DATABASE.md` — open question 1 records the confirmed data layer
- `Backend/docs/work/0001-skeleton.md` — this record

`Backend/.gitignore` already contained the Python ignores and was left as it was.

## Migrations

None. This milestone is the Alembic baseline: `alembic.ini`, `migrations/env.py`,
`migrations/script.py.mako` and an empty `migrations/versions/` (`.gitkeep`). No revision
exists and no table is created; `Base.metadata` stays empty until M2.

## Tests

The block below is an **actual run** from the review-fix round. The 12-test block from
commit 79d68f3 is **superseded**; the first-iteration failure output was removed by that
commit and its summary remains in the "Checks" work-log entry.

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 5 source files

$ uv run pytest
tests/test_config.py .....                                               [ 35%]
tests/test_conftest.py ..                                                [ 50%]
tests/test_db.py .....                                                   [ 85%]
tests/test_health.py ..                                                  [100%]
======================== 14 passed, 1 warning in 0.24s =========================
```

The warning is the known one:

```
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning:
Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

Recorded, not chased.

Coverage: health 200 and payload; health still 200 with a deliberately unreachable
database URL (proves liveness does not touch the database); required `DATABASE_URL`;
unknown environment rejected; defaults; cached settings; settings read from the
environment; engine URL; session factory binding; `get_session` using the factory on
`app.state`; lifespan storing and disposing the engine; conftest keeping a caller-supplied
`DATABASE_URL` and deriving the URL port from `POSTGRES_PORT`. The framework-only 404 test
and the `log_level` default assertion are removed per review. Role and empty-state tests
are not applicable: M1 has no auth, collections or tables.

Database checks. The local `.env` is git-ignored and not committed; it sets
`POSTGRES_PORT=5434`.

```
$ docker compose config
    ports:
      - mode: ingress
        host_ip: 127.0.0.1
        target: 5432
        published: "5434"
        protocol: tcp
...
    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -h 127.0.0.1 -U leafclutch -d leafclutch

$ docker compose up -d --wait --force-recreate db
 Container leafclutch-db-1 Recreate
 Container leafclutch-db-1 Recreated
 Container leafclutch-db-1 Starting
 Container leafclutch-db-1 Started
 Container leafclutch-db-1 Waiting
 Container leafclutch-db-1 Healthy

$ docker compose ps
NAME              IMAGE         COMMAND                  SERVICE   CREATED         STATUS                   PORTS
leafclutch-db-1   postgres:16   "docker-entrypoint.s…"   db        5 seconds ago   Up 5 seconds (healthy)   127.0.0.1:5434->5432/tcp

$ docker compose port db 5432
127.0.0.1:5434

$ uv run alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
exit=0

$ docker compose --env-file /dev/null config   # with no .env, the default is 5432
    ports:
      - mode: ingress
        host_ip: 127.0.0.1
        target: 5432
        published: "5432"
        protocol: tcp
```

The initdb databases (`leafclutch`, `leafclutch_test`) still exist; the volume was not
recreated, so the init script did not rerun. Alembic exits 0 with no revision applied and
no error.

## Review

## Docs updated

- `Backend/README.md`: setup, run, checks, database (loopback-only service, configurable
  host port and `up -d --wait db`), layout and documentation table; renamed from the empty
  `Backend/README.MD` with `git mv`.
- `Backend/docs/DATABASE.md`: open question 1 now records the confirmed sync SQLAlchemy
  2.0 + psycopg 3 / Python 3.12 data layer and why async was rejected. Nothing else in
  that document changed.
- `Backend/docs/work/0001-skeleton.md`: this record.
- `Backend/docs/work/README.md`: task index entry (orchestrator).
- No `CONTRACT.md` or `ADMIN.md` change: M1 adds no payload, role or admin screen. The
  OpenAPI schema is generated from the app (`/openapi.json`, `/docs`); there is no static
  spec to edit. There is no ADR directory under `Backend/docs/`.

## Remaining

none. Every acceptance criterion is met and demonstrated; all three Medium and seven Low
findings are fixed, and no check from the review brief is outstanding. Environment limits
are recorded under `## Not verified`.

## Next

## Open questions

- `StarletteDeprecationWarning` recommends `httpx2` for `TestClient`. Not changed here; it
  is a dependency decision outside this review round.

## Not verified

- Migration `upgrade`/`downgrade` — there are no revisions yet.
- `uv sync` from a literal clean checkout — it ran in this working tree and resolved
  `uv.lock`; no second clone was made.
- The default Compose port 5432 — this machine cannot bind it (native PostgreSQL 18), so
  only the `POSTGRES_PORT=5434` override was verified end to end. `docker compose config`
  confirms the default still resolves to 5432.
- Database-backed tests — M1 has none; the suite constructs an engine but opens no
  connection. The `POSTGRES_PORT`-derived test URL is unit-tested, not used to connect.
