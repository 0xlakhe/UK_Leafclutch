---
task: 0002
title: Extensions, enums and staff
status: in-progress
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Create the first two Alembic revisions exactly as `Backend/docs/DATABASE.md` defines them,
and with them the database test harness that every later schema milestone reuses.

`0001_extensions_enums` adds the extensions and every enum type. `0002_staff` adds the
`staff` table, its index and the last-Admin guard: demoting, deactivating or deleting the
last active Admin must fail. This is M2 in `PLAN.md`; no RLS, grants, views or publish
functions yet.

## Acceptance criteria

- [ ] `0001_extensions_enums` creates `pgcrypto`, `citext` and every enum in
      `DATABASE.md` §Enums verbatim (`staff_role`, `content_kind`, `page_section_key`,
      `version_status`, `approval_scope`, `media_visibility`, `media_role`,
      `enquiry_status`, `faq_status`, `legal_block_kind`, `email_kind`, `email_status`,
      `revalidation_status`). Downgrade drops them.
- [ ] `0002_staff` creates `staff`, `staff_email_unique`, `staff_display_name_length`,
      `staff_active_role_idx`, `set_updated_at()`, `staff_set_updated_at`,
      `enforce_last_admin()` and `staff_last_admin` exactly as `DATABASE.md` defines them.
      Downgrade removes them.
- [ ] `content_version_set_updated_at` and `enquiry_set_updated_at` are **not** created
      in 0002: those tables do not exist yet and their revisions attach them.
- [ ] The `auth.users` foreign key is satisfied by a documented local bootstrap, not by a
      migration. `DATABASE.md` open question 2 leaves this to the harness: a plain
      PostgreSQL has no `auth` schema. Supabase already has the real table, so the
      bootstrap must be a no-op there and must not be part of the migration path.
- [ ] From a fresh bootstrapped database: `alembic upgrade head` and `alembic downgrade
      base` both succeed, and `alembic check` reports no difference. The `auth` schema is
      excluded from autogenerate, or modelled so it does not appear as drift.
- [ ] The `staff` table and its enum are represented as SQLAlchemy models in
      `app/models.py`, so `alembic check` is meaningful from this revision onwards.
- [ ] Database-backed tests run against `leafclutch_test` with the target guard from task
      0001 intact, covering: the last active Admin cannot be deleted; the last active
      Admin cannot be demoted or deactivated; a second active Admin makes both allowed;
      `staff_email_unique` refuses a duplicate; `staff_display_name_length` refuses empty
      and 101 characters; `set_updated_at` moves `updated_at` on update.
- [ ] `uv run ruff check .`, `uv run mypy app` and `uv run pytest` pass, and the output is
      quoted in `## Tests`.
- [ ] Only `Backend/` changes; no `Frontend/`, `Admin/`, or application endpoint.

## Non-goals

- Media, content, sections, settings, approvals, enquiries, audit, RLS, grants, views and
  publish functions (M3–M13).
- Any FastAPI route, auth flow or admin screen.
- Supabase local, `pg_cron`, storage objects and real `auth.users`.
- Editing `DATABASE.md`; this task implements it, and any disagreement is reported, not
  resolved by changing the document.

## Plan

### Files expected

| File | Purpose |
| --- | --- |
| `migrations/versions/0001_extensions_enums.py` | Extensions and enums, `op.execute` for the types |
| `migrations/versions/0002_staff.py` | `staff` via SQLAlchemy operations, functions and triggers via `op.execute` |
| `app/models.py` | `Base` metadata: `staff` table and the `staff_role` enum |
| `migrations/env.py` | Exclude the `auth` schema from autogenerate if that is what keeps `alembic check` clean |
| `scripts/bootstrap_local.sql` | Minimal `auth` schema and `auth.users(id)` stub; idempotent |
| `tests/conftest.py` | Database fixture: ensure the stub, apply migrations once, isolate each test |
| `tests/test_staff_schema.py` | The constraints and the last-Admin guard |
| `README.md` | Bootstrap step in the database section |

### Order

1. Models and the bootstrap stub.
2. Revision 0001; upgrade and downgrade on a fresh database.
3. Revision 0002; upgrade, downgrade and `alembic check`.
4. Database fixture and tests.
5. README; run every check; commit.

### Notes

- The enum SQL is copied verbatim, including `site_logo` in `media_role`; do not
  alphabetise or "tidy" it.
- `staff.email` is `citext`, so 0001 must run first.
- The last-Admin trigger counts active Admins excluding the row being changed; keep the
  message text `the last active Admin cannot be removed`.
- The test fixture must not weaken the task-0001 target guard; if it needs a different
  URL, it goes through `TEST_DATABASE_URL` and the guard still applies.
- If the `auth.users` model makes `alembic check` noisy, prefer excluding that schema over
  adding a stub table to the migration metadata; record the choice.

## Work log

- **2026-11-27 — Model, bootstrap and environment.** Added `Backend/app/models.py`: the
  `staff` Core table, the `staff_role` enum with `create_type=False`, and an `auth.users`
  stub. Added `Backend/scripts/bootstrap_local.sql`, an idempotent `auth` schema and
  `auth.users (id)` for local and test databases. `Backend/migrations/env.py` imports the
  models so `Base.metadata` is populated and excludes the `auth` schema from autogenerate
  with `include_object`.
- **2026-11-27 — Revisions.** Added `Backend/migrations/versions/0001_extensions_enums.py`
  (the `Enums` block copied verbatim, including `site_logo`) and
  `Backend/migrations/versions/0002_staff.py` (`staff`, its two constraints and its index
  through `op.create_table`/`op.create_index`; `set_updated_at`,
  `staff_set_updated_at`, `enforce_last_admin` and `staff_last_admin` copied verbatim
  through `op.execute`). `content_version_set_updated_at` and `enquiry_set_updated_at`
  were deliberately not created: their tables do not exist yet.
- **2026-11-27 — Harness and tests.** `Backend/tests/conftest.py` gained a session fixture
  that applies the bootstrap to `leafclutch_test` and runs `alembic upgrade head` once, and
  a `db` fixture that gives each test a connection inside a transaction rolled back at the
  end. Added `Backend/tests/test_staff_schema.py` (the constraints and the last-Admin
  guard) and `Backend/tests/test_migrations.py` (in-process `alembic check`). Updated
  `Backend/README.md`.
- **2026-11-27 — First failure and correction: autogenerate could not sort the metadata.**
  The first `alembic check` failed with `NoReferencedTableError: Foreign key associated
  with column 'staff.user_id' could not find table 'auth.users'` because autogenerate
  calls `Base.metadata.sorted_tables`. The `auth.users` stub was added to `Base.metadata`
  and the `auth` schema excluded with `include_object`; `alembic check` then reported no
  differences. Superseded by the green run in `## Tests`.
- **2026-11-27 — First test run and correction.** 13 staff tests failed with
  `ForeignKeyViolation ... staff_user_id_fkey`: staff rows were inserted without the
  referenced `auth.users` row. The `add_staff` helper now inserts the auth row first, and
  two explicit tests cover the FK and its `on delete restrict`. Superseded by the 50-test
  run in `## Tests`.
- **2026-11-27 — Timestamp test constraint.** PostgreSQL `now()` is the transaction start
  and constant for the whole test transaction, so an insert-then-update using the server
  defaults would leave `updated_at` equal to `created_at`. The test seeds both timestamps
  an hour in the past and supplies an older `updated_at` in the UPDATE; only the trigger
  can move it forward.
- **2026-11-27 — Fresh-volume run.** Removed the local Compose volume (`docker compose down
  -v`; it held only this schema), started it again, ran the bootstrap, then upgrade →
  downgrade base → upgrade → check, then ruff, mypy and pytest. All green; the output is
  quoted in `## Tests`.
- **2026-11-27 — Alembic deprecation warning.** Added `path_separator = os` to
  `Backend/alembic.ini` to silence Alembic 1.20's warning about splitting
  `prepend_sys_path`. It changes no migration behaviour.

## Decisions made

- **`staff` is a Core `sa.Table`, not an ORM class.** The model is in `app/models.py` and
  populates `Base.metadata`; `alembic check` compares it. No repository reads the table
  yet, so a mapped class would be unused code: the rule is no abstraction until the second
  real use. A mapped class arrives with the first staff repository (M15).
- **The `auth.users` stub is modelled in `Base.metadata` and excluded from autogenerate.**
  Autogenerate calls `Base.metadata.sorted_tables`, which must resolve
  `staff.user_id -> auth.users.id`; so the metadata needs the table. Alembic's
  `include_object` returns `False` for every object in schema `auth`, so autogenerate never
  proposes creating the stub and never proposes dropping the real table. No migration
  creates it: `DATABASE.md` §Migrations leaves `auth` to the harness, and open question 2
  says a plain PostgreSQL needs a minimal `auth.users`.
- **The local stub has only `id`.** The brief specifies `auth.users (id uuid primary key)`.
  The validation runbook's admin fixture also inserts `email` and `last_sign_in_at`, and
  `staff_account` needs `auth.mfa_factors`; extending the stub is a harness change for
  those milestones, not a revision. Noted under `## Open questions`.
- **The bootstrap is run by the test fixture, not by Alembic.** A session fixture executes
  `scripts/bootstrap_local.sql` against the test database before `upgrade head`; the
  script is idempotent, so repeated runs are no-ops. The README documents the same command
  for the development database. This keeps `auth` out of the migration history.
- **Downgrades reverse the document's revision table.** `0001` drops the enums in reverse
  creation order and then `citext` and `pgcrypto` with `if exists`; `DATABASE.md` marks
  "Drop enums and extensions" as dev-only. `0002` drops `staff` (which removes the index,
  constraints and triggers) and then both functions.
- **The two other timestamp triggers are deferred.** `DATABASE.md` attaches
  `content_version_set_updated_at` and `enquiry_set_updated_at` to tables created in 0004
  and 0012; those revisions attach them. `0002` creates `set_updated_at()`,
  `staff_set_updated_at` and the last-Admin pair only.
- **Foreign-key names are left to PostgreSQL.** The document names the unique and check
  constraints and the index, but not the two foreign keys; the migration and model leave
  them unnamed, so the database generates `staff_user_id_fkey` and
  `staff_created_by_fkey`, and `on delete restrict` / `on delete set null` are modelled.
- **`sa.Enum` in the model, `postgresql.ENUM` in the migration.** The brief specifies
  `sa.Enum(..., name="staff_role", create_type=False)` for the model; the migration uses
  the dialect type, which documents the `create_type` argument explicitly. Both render the
  type as `staff_role`, and `alembic check` compares them as equal.
- **Tests isolate with transactions, not truncation.** The `db` fixture begins one
  transaction on a shared session engine and always rolls it back; expected failures run
  inside `SAVEPOINT`s (`Connection.begin_nested()`), so the outer transaction and the
  fixture survive a trigger or constraint error. The empty-state test asserts the table is
  empty, proving no row leaked between tests.
- **The test Alembic config uses an absolute `script_location`.** The fixture builds
  `Config(<Backend>/alembic.ini)` and overrides the script location so `uv run pytest`
  works from another working directory; the URL still comes from application settings.

## Files changed

New:

- `Backend/app/models.py` — `staff`, the `staff_role` enum and the `auth.users` metadata stub
- `Backend/migrations/versions/0001_extensions_enums.py`
- `Backend/migrations/versions/0002_staff.py`
- `Backend/scripts/bootstrap_local.sql`
- `Backend/tests/test_staff_schema.py`
- `Backend/tests/test_migrations.py`
- `Backend/docs/work/0002-extensions-enums-staff.md` (this log)

Modified:

- `Backend/migrations/env.py` — imports `app.models`; `include_object` excludes schema `auth`
- `Backend/tests/conftest.py` — session bootstrap and migration; per-test rolled-back connection
- `Backend/alembic.ini` — `path_separator = os`
- `Backend/README.md` — bootstrap step, database-backed tests, `alembic check`, layout

`Backend/docs/work/README.md` already held the orchestrator's 0002 index row and is
included as it stood. No `Frontend/`, `Admin/`, `compose.yaml`, `.env` or `.env.example`
change; no dependency change (`uv.lock` untouched).

## Migrations

- `0001_extensions_enums` (no parent) — `create extension if not exists pgcrypto` and
  `citext`, then the thirteen enum types from `DATABASE.md` §Enums, copied verbatim.
  Downgrade drops the enums in reverse creation order and then the two extensions with
  `if exists`. Upgrade, downgrade and a second upgrade were run on a fresh Compose volume.
- `0002_staff` (parent `0001_extensions_enums`) — `staff` with its primary key,
  `staff_email_unique`, `staff_display_name_length`, the `auth.users` and self-referencing
  foreign keys, `staff_active_role_idx`; then `set_updated_at()`,
  `staff_set_updated_at`, `enforce_last_admin()` and `staff_last_admin`. Downgrade drops
  the table (with its index, constraints and triggers) and both functions. Upgrade,
  downgrade and a second upgrade were run on a fresh Compose volume.
- `content_version_set_updated_at` and `enquiry_set_updated_at` are not created here;
  the revisions that create `content_version` and `enquiry` will attach them.
- `auth.users` is not a migration. `scripts/bootstrap_local.sql` creates it idempotently
  for local and test databases; Supabase owns the real table.
- `alembic check` against the migrated development database reported
  `No new upgrade operations detected.` The in-process test in
  `tests/test_migrations.py` repeats it against `leafclutch_test`.

## Tests

The block below is an **actual run** from a freshly created Compose volume (PostgreSQL
18.7). Every command ran from `Backend/`; Docker Compose's progress lines are shown once
each. The earlier failing runs are quoted afterwards.

```
$ docker compose down -v
 Container leafclutch-db-1 Stopping
 Container leafclutch-db-1 Stopped
 Container leafclutch-db-1 Removing
 Container leafclutch-db-1 Removed
 Volume leafclutch_postgres-data Removing
 Network leafclutch_default Removing
 Volume leafclutch_postgres-data Removed
 Network leafclutch_default Removed

$ docker compose up -d --wait db
 Network leafclutch_default Creating
 Volume leafclutch_postgres-data Creating
 Network leafclutch_default Created
 Volume leafclutch_postgres-data Created
 Container leafclutch-db-1 Creating
 Container leafclutch-db-1 Created
 Container leafclutch-db-1 Starting
 Container leafclutch-db-1 Started
 Container leafclutch-db-1 Waiting
 Container leafclutch-db-1 Healthy

$ docker compose exec -T db psql -U leafclutch -d leafclutch -v ON_ERROR_STOP=1 < scripts/bootstrap_local.sql
CREATE SCHEMA
CREATE TABLE

$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_extensions_enums, Extensions and every enum type.
INFO  [alembic.runtime.migration] Running upgrade 0001_extensions_enums -> 0002_staff, The staff table, the timestamp trigger and the last-Admin guard.

$ uv run alembic downgrade base
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0002_staff -> 0001_extensions_enums, The staff table, the timestamp trigger and the last-Admin guard.
INFO  [alembic.runtime.migration] Running downgrade 0001_extensions_enums -> , Extensions and every enum type.

$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_extensions_enums, Extensions and every enum type.
INFO  [alembic.runtime.migration] Running upgrade 0001_extensions_enums -> 0002_staff, The staff table, the timestamp trigger and the last-Admin guard.

$ uv run alembic check
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.schemas
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.tables
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.types
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.constraints
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.defaults
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments
No new upgrade operations detected.

$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest
rootdir: /Users/prabeshshrestha/Work/UK_Leafclutch/Backend
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0
collected 50 items

tests/test_config.py .....                                               [ 10%]
tests/test_conftest.py .................                                 [ 44%]
tests/test_db.py .....                                                   [ 54%]
tests/test_health.py ..                                                  [ 58%]
tests/test_migrations.py .                                               [ 60%]
tests/test_staff_schema.py ....................                          [100%]

=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /Users/prabeshshrestha/Work/UK_Leafclutch/Backend/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 50 passed, 1 warning in 0.49s =========================

$ uv run pytest -q --import-mode=importlib
50 passed, 1 warning in 0.44s
```

The warning is the known `httpx`/Starlette deprecation carried over from task 0001;
recorded, not chased.

First failing run, before the `auth.users` metadata stub (superseded):

```
$ uv run alembic check
...
sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column 'staff.user_id'
could not find table 'auth.users' with which to generate a foreign key to target column 'id'
exit=1
```

First failing pytest run, before the test helper seeded `auth.users` (superseded):

```
$ uv run pytest -q
...
E   sqlalchemy.exc.IntegrityError: (psycopg.errors.ForeignKeyViolation) insert or update on
table "staff" violates foreign key constraint "staff_user_id_fkey"
...
13 failed, 33 passed, 3 warnings in 1.01s
```

Coverage of `tests/test_staff_schema.py` (20 tests, every one inside a rolled-back
transaction): the empty table at the start; a staff row requires an existing
`auth.users` row, and deleting a staffed auth user is refused; deleting, demoting to
`editor` and setting `active = false` on the last active Admin each raise
`the last active Admin cannot be removed` and leave the row as it was; a second active
Admin makes all three changes succeed; an editor and an inactive admin are not protected;
a duplicate `staff.email` is refused in the same case and in a different case (`citext`);
`display_name` of 1 and 100 characters is accepted while `''` and 101 are refused by
`staff_display_name_length`; the server defaults apply; deleting a missing id is a no-op;
and an update moves `updated_at` forward while `created_at` is unchanged.
`tests/test_migrations.py` runs `alembic check` against `leafclutch_test` and finds no
model drift.

## Review

## Docs updated

- `Backend/README.md` — the `auth` bootstrap command and why it is not a migration; the
  database-backed test fixture; `alembic check` and the `auth` exclusion; layout rows for
  `app/models.py` and `scripts/bootstrap_local.sql`.
- `Backend/docs/work/0002-extensions-enums-staff.md` — this log.
- No `Backend/docs/DATABASE.md`, `ADMIN.md` or `CONTRACT.md` change: this task implements
  those documents, their decisions are unchanged, and the brief forbids editing them.
- No OpenAPI change: no endpoint was added or changed.
- No ADR: `Backend/docs/` has no ADR directory.

## Open questions

- The validation runbook's admin fixture inserts `auth.users (id, email, last_sign_in_at)`,
  and `staff_account` reads `auth.mfa_factors`, while the local stub has only `id` as the
  brief specifies. The stub must grow those objects for the runbook and for
  `staff_account` in M15; that is a harness change at that milestone, not a revision. No
  runbook execution is possible before then anyway, because its other tables arrive in
  M3–M15.
- `alembic check` compares the enum's name, not its labels. Adding a value to
  `staff_role` must therefore be a deliberate `alter type ... add value` revision per
  `DATABASE.md` §Migrations; no automated check would catch a forgotten one.

## Not verified

- Supabase itself: the extensions, the `if not exists` idempotency and the `auth` no-op
  were run only against the plain PostgreSQL 18 container, not a Supabase project.
- The full validation runbook (`docs/runbooks/database-validation.sql`) was not run; it
  needs tables from M3–M15 and a wider `auth` stub.
- The default Compose port 5432 was not exercised; a native PostgreSQL 18 holds it, so the
  local `.env` uses 5434, as recorded in task 0001.
- `mypy` covers `app` only, as configured in `pyproject.toml`; the migrations and tests are
  not type-checked.
- Datasets: no production or staging data was involved; the volume was created from
  scratch.
