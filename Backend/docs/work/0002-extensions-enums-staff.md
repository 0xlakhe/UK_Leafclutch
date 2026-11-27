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
- **2026-11-27 — Review fixes: High, Mediums 1–2 and Lows 3, 5, 6, 7.** Added
  `perform pg_advisory_xact_lock(hashtext('staff_last_admin'))` at the start of
  `enforce_last_admin()` and a two-connection test that proves the second delete waits and
  is refused. `0001`'s downgrade now drops the enum types only; `migrations/env.py` sets
  `compare_server_default=True` on both configure calls and accepts an injected
  connection; `tests/test_migrations.py` alters `staff.active`'s default and expects
  drift. Added the combined demotion/deactivation and second-inactive-Admin tests, made
  the empty-state test name stale rows, removed `path_separator = os`, and widened the
  `auth.users` stub to `(id, email, last_sign_in_at)`. Updated `Backend/README.md` with the
  extension behaviour and the required round trip.
- **2026-11-27 — Concurrency test first run and correction.** The first run failed with
  `assert 0 == 1` at `remaining == 1`: the assertion sat after the `finally` that truncates
  the committed rows. The assertions moved inside the `try`, before the cleanup; the run
  quoted in `## Tests` supersedes it.
- **2026-11-27 — Databases rebuilt for the edited revision.** The function and the
  downgrade live in already-applied revisions, so the local Compose volume was recreated
  and the test database round-tripped before the quoted run. Both now report
  `0002_staff (head)`, and `pg_get_functiondef` shows the advisory lock.
- **2026-11-27 — L6 correction.** The `path_separator` entry above is superseded: the
  review found the setting has no effect with a single path, so it was removed and the
  Alembic deprecation warning is accepted in the test output.
- **2026-11-27 — Round-3 review fixes (High, deadlock Medium, two Lows).** Moved the
  advisory lock out of the row trigger into a statement-level `staff_lock_writes` trigger
  and its `lock_staff_writes()` function, so the lock precedes every row lock. The row
  guard now counts through `select ... for update`, which under REPEATABLE READ and
  SERIALIZABLE raises `40001` instead of reading a stale snapshot. Added the deadlock
  regression test (delete one Admin, another writer updates the second, the first updates
  the second), a structural test for the function bodies and trigger levels, and RR and
  SERIALIZABLE isolation tests. Scoped the `pg_locks` wait to the current database. Made
  the bootstrap stub upgrade-safe with a guarded `DO` block. Updated `DATABASE.md`.
- **2026-11-27 — Round-3 observed outcome.** Both RR and SERIALIZABLE runs end with
  `(psycopg.errors.SerializationFailure) could not serialize access due to concurrent
  update` and exactly one active Admin; the test accepts either that or the refusal.
- **2026-11-27 — Round-3 lint fix.** The first ruff run rejected a 101-character
  `pg_locks` string; it was split across lines. No behaviour change.
- **2026-11-27 — Databases rebuilt again.** `0002` was edited in place before release, so
  the volume was recreated and the test database round-tripped. The installed definitions
  were checked with `pg_get_functiondef` and `pg_trigger`.
- **2026-11-27 — Round-4 review fixes (Mediums 1–2, three Lows).** Added INSERT to
  `staff_lock_writes`: a `created_by` foreign key takes a key-share lock on an Admin before
  the statement takes the advisory lock, so the trigger must cover INSERT. Documented in
  `DATABASE.md` and the `0002` docstring that the trigger orders only the locks its own
  statement takes: a service must take `pg_advisory_xact_lock(hashtext('staff_last_admin'))`
  before its first staff row lock or retry `40P01` with a bounded backoff, now recorded
  under M15 in `PLAN.md`. Added the sentence that the lock is held to commit, so staff write
  transactions stay short. Removed the delete-then-update test, which passed with the
  statement trigger dropped; added a barrier-driven two-delete test that fails with `40P01`
  without the trigger, and made the orchestrated two-delete test assert the sqlstate is
  `P0001`/`40001`, never `40P01`. Added the insert-with-`created_by` deadlock regression
  test. Extended the structural test to pin the trigger's INSERT, UPDATE and DELETE bits.
  Replaced `information_schema.columns` with `pg_catalog` in the bootstrap guard.
- **2026-11-27 — Scratch check.** Copied `leafclutch_test` to `leafclutch_scratch_test`,
  dropped `staff_lock_writes`, and the new two-delete test failed with
  `AssertionError: unexpected sqlstate: 40P01`; restoring the trigger made it pass and the
  copy was dropped. The real test database was never altered.
- **2026-11-27 — Bootstrap guard checked.** Dropped `email` and `last_sign_in_at` from the
  local stub, reran the script (both columns returned), and reran it again (the `DO` block
  was a no-op). The script printed no `ALTER` on the second run.

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
- **The local `auth.users` stub.** It started as `(id uuid primary key)` per the brief; the
  review widened it to `(id, email, last_sign_in_at)` so the validation runbook's admin
  fixture can run (L7). `staff_account` still needs `auth.mfa_factors`; that is a harness
  change at M15, not a revision. Noted under `## Open questions`.
- **The bootstrap is run by the test fixture, not by Alembic.** A session fixture executes
  `scripts/bootstrap_local.sql` against the test database before `upgrade head`; the
  script is idempotent, so repeated runs are no-ops. The README documents the same command
  for the development database. This keeps `auth` out of the migration history.
- **Downgrades reverse the document's revision table, with one deviation.** `0001` drops
  the enums in reverse creation order; it does not drop `citext` or `pgcrypto`, for the
  shared-object reason recorded under the review fix below. `0002` drops `staff` (which
  removes the index, constraints and triggers) and then both functions.
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
- **Round 2: the last-Admin guard took a transaction-scoped advisory lock inside the row
  trigger (superseded in round 3).** The reviewer reproduced the race with two connections:
  both deleted a different active Admin, both triggers counted the other row as active, and
  both committed, leaving zero active Admins. The row trigger was given
  `perform pg_advisory_xact_lock(hashtext('staff_last_admin'))`. That closed READ COMMITTED
  but not REPEATABLE READ or SERIALIZABLE, where the statement snapshot predates the lock,
  and it introduced an advisory-versus-row-lock deadlock; round 3 moved the lock to a
  statement trigger and made the count a locking read.
- **The advisory lock is statement-level and the row guard reads with `for update`
  (round 3).** `staff_lock_writes` takes the lock before any row lock, so two writers
  cannot each hold a row the other needs, and `enforce_last_admin` counts through a
  `for update` subquery. Under READ COMMITTED the statement lock serialises the writers;
  under REPEATABLE READ and SERIALIZABLE a concurrent committed change raises `40001`,
  which is the correct outcome for this invariant. The alternative, documenting READ
  COMMITTED as the only supported level, was rejected.
- **`DATABASE.md` now carries the change.** §Timestamps and the last Admin has the
  statement trigger, the locking-read row body and the isolation note, and its migration
  table says the `0001` downgrade drops enums only. The design workspace still needs the
  same patch; until it lands, the two copies differ and this note stays.
- **The structural test pins the installed definitions.** `pg_get_functiondef` must
  contain `for update` for `enforce_last_admin` and `pg_advisory_xact_lock` for
  `lock_staff_writes`, and `pg_trigger` must show `staff_lock_writes` at statement level
  firing on INSERT, UPDATE and DELETE, with `staff_last_admin` at row level, so a database
  that still has an older definition cannot pass silently.
- **The bootstrap stub upgrades in place.** A guarded `DO` block adds `email` and
  `last_sign_in_at` only when `pg_catalog` says they are missing; a fresh stub has them and
  Supabase has them, so both are no-ops. The first version read `information_schema`, which
  hides columns from a non-owner; round 4 replaced it.
- **The `pg_locks` wait is scoped to the current database.** Advisory locks are
  database-scoped; matching on `database = (select oid from pg_database where datname =
  current_database())` prevents a waiter in another database from satisfying the poll.
- **The downgrade leaves `pgcrypto` and `citext` installed (deviation from `DATABASE.md`'s
  "Drop enums and extensions (dev only)").** Extensions are shared objects that may predate
  this revision or belong to another schema; dropping them can fail or remove support other
  code needs. `0001` drops the enum types only, and its `create extension if not exists`
  re-applies the extensions on upgrade. The README states that `alembic downgrade base` is a
  development command that does not remove them.
- **`alembic check` compares server defaults.** `compare_server_default=True` is set on
  both configure paths; the existing `true` and `now()` defaults compare clean. The new test
  injects the fixture connection through `config.attributes["connection"]` (env.py accepts
  it) and proves that `alter table staff alter column active set default false` inside the
  rolled-back transaction is reported as drift.
- **The revisions were edited before release instead of adding a third revision.** No
  database outside this checkout had run `0002_staff`, so fixing the function in `0002` and
  the downgrade in `0001` keeps M2 to the two revisions the task defines. Local databases
  were recreated and round-tripped; once a revision has run outside development, the same
  change must be a new revision.
- **L5 does not delete stale rows.** The empty-state test names any committed row in its
  failure message instead of deleting it, because the guard refuses to remove the last
  active Admin and a test should not bypass the invariant it verifies.
- **L7 widens the local `auth.users` stub.** `(id, email, last_sign_in_at)` lets the
  validation runbook's admin fixture run; the statements remain `if not exists`, so Supabase
  is unaffected. `auth.mfa_factors` is still absent until M15 needs it.
- **The statement trigger covers INSERT (round 4).** The reviewer reproduced a deadlock the
  UPDATE/DELETE trigger cannot prevent: T1 inserts a staff row whose `created_by` takes a
  key-share lock on Admin A and then updates Admin B; T2 deletes A, takes the advisory lock
  and waits for A; T1 waits for the advisory lock. Firing the trigger on INSERT makes T1
  take the advisory lock before the foreign key does. The insert-with-`created_by` test
  covers that interleaving.
- **A trigger cannot order locks the caller already holds.** The statement trigger orders
  the locks its own statement takes. A staff service that holds a `SELECT ... FOR UPDATE`
  on a staff row before the statement can still form a `40P01` cycle with the trigger.
  `PLAN.md` M15 now requires every staff write to take
  `pg_advisory_xact_lock(hashtext('staff_last_admin'))` before its first staff row lock or
  retry `40P01` with a bounded backoff. This is an M15 obligation, not an M2 defect.
- **The advisory lock is held to commit.** It serialises every staff writer for the life of
  the transaction, so staff write transactions must stay short. Stated in `DATABASE.md`.
- **The delete-then-update test was removed, not repaired.** It passed with
  `staff_lock_writes` dropped because the `for update` count already ordered the rows; it
  proved nothing. Its replacement is a barrier-driven two-delete test: both transactions
  delete their own active Admin, one commits, the other must be `P0001` or `40001` and never
  `40P01`, and one active Admin remains. The orchestrated two-delete test stays because it
  proves the second writer waits on the advisory lock, and it now asserts the sqlstate.
- **The bootstrap guard reads `pg_catalog`.** `information_schema.columns` hides columns
  from a role without privileges on the table, which made the guard try to `ALTER` a table
  it does not own. `pg_attribute`/`pg_class`/`pg_namespace` see the columns regardless, so
  the block no-ops whenever they exist, including on Supabase.
- **The RR test is what pins the locking read.** The SERIALIZABLE case would catch the
  conflict through SSI without `for update`; the REPEATABLE READ case is the one that
  requires it. A comment records that in the test.

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
- `Backend/alembic.ini` — `path_separator = os` (removed again in the review fixes, L6)
- `Backend/README.md` — bootstrap step, database-backed tests, `alembic check`, layout

`Backend/docs/work/README.md` already held the orchestrator's 0002 index row and is
included as it stood. No `Frontend/`, `Admin/`, `compose.yaml`, `.env` or `.env.example`
change; no dependency change (`uv.lock` untouched).

Review fixes (second commit):

- `Backend/migrations/versions/0001_extensions_enums.py` — downgrade drops the enums only
- `Backend/migrations/versions/0002_staff.py` — advisory lock in `enforce_last_admin()`
- `Backend/migrations/env.py` — `compare_server_default=True`; injected-connection support
- `Backend/alembic.ini` — removed `path_separator = os`
- `Backend/scripts/bootstrap_local.sql` — `email` and `last_sign_in_at` in the stub
- `Backend/tests/test_staff_schema.py` — concurrency, L3 and L5 tests
- `Backend/tests/test_migrations.py` — changed-server-default drift test
- `Backend/README.md` — extension behaviour, required round trip, stub shape
- `Backend/docs/work/0002-extensions-enums-staff.md` — this log

Review fixes (third commit):

- `Backend/docs/DATABASE.md` — statement trigger, locking-read body, isolation note,
  `0001` downgrade wording
- `Backend/migrations/versions/0002_staff.py` — statement-level lock, locking read, downgrade
  drops both triggers and both functions
- `Backend/scripts/bootstrap_local.sql` — guarded `DO` block for an existing stub
- `Backend/tests/test_staff_schema.py` — deadlock, isolation and structural tests; scoped wait
- `Backend/docs/work/0002-extensions-enums-staff.md` — this log

Review fixes (fourth commit):

- `Backend/docs/DATABASE.md` — INSERT in the statement trigger, ordering caveat and
  long-transaction note
- `Backend/docs/work/PLAN.md` — M15 requirement: take the advisory lock first or retry
  `40P01`
- `Backend/migrations/versions/0002_staff.py` — INSERT in the trigger; docstring records the
  ordering limit
- `Backend/scripts/bootstrap_local.sql` — `pg_catalog` guard instead of
  `information_schema`
- `Backend/tests/test_staff_schema.py` — insert/FK and barrier two-delete tests, sqlstate
  assertions and the INSERT pin
- `Backend/docs/work/0002-extensions-enums-staff.md` — this log

## Migrations

- `0001_extensions_enums` (no parent) — `create extension if not exists pgcrypto` and
  `citext`, then the thirteen enum types from `DATABASE.md` §Enums, copied verbatim.
  Downgrade drops the enums in reverse creation order and **leaves the extensions in
  place**, because they are shared objects; the upgrade's `if not exists` makes re-applying
  them safe. Upgrade, downgrade and a second upgrade were run on a fresh Compose volume,
  and the test database's downgrade was checked to leave `citext`, `pgcrypto` and `plpgsql`
  installed.
- `0002_staff` (parent `0001_extensions_enums`) — `staff` with its primary key,
  `staff_email_unique`, `staff_display_name_length`, the `auth.users` and self-referencing
  foreign keys, `staff_active_role_idx`; then `set_updated_at()` and its trigger,
  `lock_staff_writes()` and the statement trigger `staff_lock_writes` on INSERT, UPDATE and
  DELETE, and `enforce_last_admin()` with the `for update` count and the row trigger
  `staff_last_admin`. Downgrade drops both last-Admin triggers, the table (with the
  timestamp trigger and the index) and all three functions. Upgrade, downgrade and a second
  upgrade were run on the test database.
- The review fixes edited already-applied revisions three times. No database outside this
  checkout had run them, so the local volume was recreated and both local databases
  round-tripped; the live definitions were checked with `pg_get_functiondef` and
  `pg_trigger` (statement trigger on INSERT/UPDATE/DELETE, row trigger on UPDATE/DELETE).
- `content_version_set_updated_at` and `enquiry_set_updated_at` are not created here;
  the revisions that create `content_version` and `enquiry` will attach them.
- `auth.users` is not a migration. `scripts/bootstrap_local.sql` creates it idempotently
  for local and test databases; Supabase owns the real table.
- `alembic check` against the migrated development database reported
  `No new upgrade operations detected.` with server-default comparison enabled. The
  in-process tests in `tests/test_migrations.py` repeat it against `leafclutch_test` and
  prove a changed default is reported.

## Tests

The block below is the **actual run** for round 4 (PostgreSQL 18.7). Round 3's 58-test
block, the 54-test round-2 block and the 50-test first-round block further down are
**superseded**; their failure entries are kept as history.

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest -q
59 passed, 4 warnings in 0.73s

$ uv run pytest -q --import-mode=importlib
59 passed, 4 warnings in 0.58s

$ uv run alembic check
No new upgrade operations detected.

$ uv run alembic current
0002_staff (head)

$ DATABASE_URL=<test> uv run alembic downgrade base
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0002_staff -> 0001_extensions_enums, The staff table, the last-Admin guard and the timestamp trigger.
INFO  [alembic.runtime.migration] Running downgrade 0001_extensions_enums -> , Extensions and every enum type.

$ docker compose exec -T db psql -U leafclutch -d leafclutch_test -c "select extname from pg_extension order by extname;"
 extname
----------
 citext
 pgcrypto
 plpgsql
(3 rows)

$ DATABASE_URL=<test> uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_extensions_enums, Extensions and every enum type.
INFO  [alembic.runtime.migration] Running upgrade 0001_extensions_enums -> 0002_staff, The staff table, the last-Admin guard and the timestamp trigger.

$ DATABASE_URL=<test> uv run alembic current
0002_staff (head)
```

The concurrency tests:

```
$ uv run pytest tests/test_staff_schema.py -k "concurrent or created_by or stronger_isolation or installed_guard" -vv
collecting ... collected 28 items / 22 deselected / 6 selected
tests/test_staff_schema.py::test_the_installed_guard_is_the_locking_read_version PASSED [ 16%]
tests/test_staff_schema.py::test_concurrent_deletes_cannot_remove_both_active_admins PASSED [ 33%]
tests/test_staff_schema.py::test_two_concurrent_deletes_serialise_without_a_deadlock PASSED [ 50%]
tests/test_staff_schema.py::test_an_insert_with_created_by_does_not_deadlock_with_a_delete PASSED [ 66%]
tests/test_staff_schema.py::test_the_guard_holds_at_stronger_isolation[REPEATABLE READ] PASSED [ 83%]
tests/test_staff_schema.py::test_the_guard_holds_at_stronger_isolation[SERIALIZABLE] PASSED [100%]
================= 6 passed, 22 deselected, 1 warning in 0.27s ==================
```

The installed trigger definition:

```
$ docker compose exec -T db psql -U leafclutch -d leafclutch -Atc "select pg_get_triggerdef(oid) from pg_trigger where tgrelid = 'staff'::regclass and tgname = 'staff_lock_writes';"
CREATE TRIGGER staff_lock_writes BEFORE INSERT OR DELETE OR UPDATE ON public.staff FOR EACH STATEMENT EXECUTE FUNCTION lock_staff_writes()
```

The scratch check, on a template copy of `leafclutch_test` with `staff_lock_writes`
dropped:

```
$ create database leafclutch_scratch_test template leafclutch_test;
CREATE DATABASE
$ drop trigger staff_lock_writes on staff;
DROP TRIGGER
$ TEST_DATABASE_URL=<scratch> uv run pytest tests/test_staff_schema.py::test_two_concurrent_deletes_serialise_without_a_deadlock -q
...
>           assert sqlstate in {"P0001", "40001"}, f"unexpected sqlstate: {sqlstate}"
E           AssertionError: unexpected sqlstate: 40P01
E           assert '40P01' in {'40001', 'P0001'}
FAILED tests/test_staff_schema.py::test_two_concurrent_deletes_serialise_without_a_deadlock
1 failed, 1 warning in 1.31s
```

With the trigger restored, the same test passed (`1 passed`), and the scratch database was
dropped. The real test database was not altered.

The bootstrap guard, simulated on the local stub:

```
$ alter table auth.users drop column email, drop column last_sign_in_at;
ALTER TABLE
# columns before: id
$ docker compose exec -T db psql ... -v ON_ERROR_STOP=1 < scripts/bootstrap_local.sql
CREATE SCHEMA
CREATE TABLE
DO
# columns after: id, email, last_sign_in_at
$ docker compose exec -T db psql ... -v ON_ERROR_STOP=1 < scripts/bootstrap_local.sql
CREATE SCHEMA
CREATE TABLE
DO
```

The second run printed no `ALTER TABLE`: the `DO` block is a no-op when the columns exist.

`DATABASE_URL=<test>` is the disposable test target,
`postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:5434/leafclutch_test`. The downgrade
leaves `citext` and `pgcrypto` installed, as Medium 1 requires.

Superseded — the round-3 run, before the round-4 fixes. Every command ran from `Backend/`;
Docker Compose's progress lines are shown once each. The failing runs of that round are
quoted after the coverage notes.

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest -q
58 passed, 4 warnings in 0.70s

$ uv run pytest -q --import-mode=importlib
58 passed, 4 warnings in 0.56s

$ uv run alembic check
No new upgrade operations detected.

$ uv run alembic current
0002_staff (head)

$ DATABASE_URL=<test> uv run alembic downgrade base
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0002_staff -> 0001_extensions_enums, The staff table, the last-Admin guard and the timestamp trigger.
INFO  [alembic.runtime.migration] Running downgrade 0001_extensions_enums -> , Extensions and every enum type.

$ docker compose exec -T db psql -U leafclutch -d leafclutch_test -c "select extname from pg_extension order by extname;"
 extname
----------
 citext
 pgcrypto
 plpgsql
(3 rows)

$ DATABASE_URL=<test> uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_extensions_enums, Extensions and every enum type.
INFO  [alembic.runtime.migration] Running upgrade 0001_extensions_enums -> 0002_staff, The staff table, the last-Admin guard and the timestamp trigger.

$ DATABASE_URL=<test> uv run alembic current
0002_staff (head)
```

The specific concurrency tests:

```
$ uv run pytest tests/test_staff_schema.py -k "concurrent or deadlock or stronger_isolation or installed_guard" -vv
collecting ... collected 27 items / 22 deselected / 5 selected
tests/test_staff_schema.py::test_the_installed_guard_is_the_locking_read_version PASSED [ 20%]
tests/test_staff_schema.py::test_concurrent_deletes_cannot_remove_both_active_admins PASSED [ 40%]
tests/test_staff_schema.py::test_a_delete_then_an_update_of_the_other_admin_does_not_deadlock PASSED [ 60%]
tests/test_staff_schema.py::test_the_guard_holds_at_stronger_isolation[REPEATABLE READ] PASSED [ 80%]
tests/test_staff_schema.py::test_the_guard_holds_at_stronger_isolation[SERIALIZABLE] PASSED [100%]
================= 5 passed, 22 deselected, 1 warning in 0.27s ==================
```

What the isolation test observes, from a direct run of the same interleaving with the
exception printed:

```
REPEATABLE READ -> OperationalError (psycopg.errors.SerializationFailure) could not serialize access due to concurrent update | active admins: 1
SERIALIZABLE -> OperationalError (psycopg.errors.SerializationFailure) could not serialize access due to concurrent update | active admins: 1
```

`DATABASE_URL=<test>` is the disposable test target,
`postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:5434/leafclutch_test`. The downgrade
leaves `citext` and `pgcrypto` installed, as Medium 1 requires.

Superseded — the round-2 run, after the first review fixes. Every command ran from
`Backend/`; Docker Compose's progress lines are shown once each. The failing runs of that
round are quoted after the coverage notes.

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest -q
54 passed, 4 warnings in 0.62s

$ uv run pytest -q --import-mode=importlib
54 passed, 4 warnings in 0.49s

$ uv run alembic check
No new upgrade operations detected.

$ uv run alembic current
0002_staff (head)

$ DATABASE_URL=<test> uv run alembic downgrade base
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0002_staff -> 0001_extensions_enums, The staff table, the timestamp trigger and the last-Admin guard.
INFO  [alembic.runtime.migration] Running downgrade 0001_extensions_enums -> , Extensions and every enum type.

$ docker compose exec -T db psql -U leafclutch -d leafclutch_test -c "select extname from pg_extension order by extname;"
 extname
----------
 citext
 pgcrypto
 plpgsql
(3 rows)

$ DATABASE_URL=<test> uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_extensions_enums, Extensions and every enum type.
INFO  [alembic.runtime.migration] Running upgrade 0001_extensions_enums -> 0002_staff, The staff table, the timestamp trigger and the last-Admin guard.

$ DATABASE_URL=<test> uv run alembic current
0002_staff (head)
```

`DATABASE_URL=<test>` is the disposable test target,
`postgresql+psycopg://leafclutch:leafclutch@127.0.0.1:5434/leafclutch_test`. The downgrade
leaves `citext` and `pgcrypto` installed, as Medium 1 requires.

The concurrency test on its own:

```
$ uv run pytest tests/test_staff_schema.py::test_concurrent_deletes_cannot_remove_both_active_admins -vv
tests/test_staff_schema.py::test_concurrent_deletes_cannot_remove_both_active_admins PASSED [100%]
1 passed, 1 warning in 0.25s
```

The four warnings are the known `httpx`/Starlette deprecation and Alembic's `path_separator`
deprecation, which L6 left in place: with a single `prepend_sys_path` entry the setting has
no effect.

Superseded — the first-round run, before the review fixes. Every command ran from
`Backend/`; Docker Compose's progress lines are shown once each. The failing runs of that
round are quoted after the coverage notes.

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

Coverage of `tests/test_staff_schema.py` (28 tests; the multi-connection tests commit
outside the `db` fixture, the rest run inside a rolled-back transaction): the empty table at
the start, with a message naming any stale committed row; a staff row requires an existing
`auth.users` row, and deleting a staffed auth user is refused; deleting, demoting to
`editor`, setting `active = false`, and demoting and deactivating in one update each raise
`the last active Admin cannot be removed` and leave the row as it was; a second active
Admin makes the three single changes succeed; an editor and an inactive admin are not
protected, and a second inactive Admin does not protect the only active one; a duplicate
`staff.email` is refused in the same case and in a different case (`citext`);
`display_name` of 1 and 100 characters is accepted while `''` and 101 are refused by
`staff_display_name_length`; the server defaults apply; deleting a missing id is a no-op;
and an update moves `updated_at` forward while `created_at` is unchanged. A structural test
reads `pg_get_functiondef` for both functions and `pg_trigger` for both trigger levels and
event bits, so a stale definition cannot pass. The multi-connection tests commit two active
Admins and clean up in a `finally`: the orchestrated delete test waits on `pg_locks`
(scoped to the current database) until the second writer blocks, then asserts the refusal
message, `P0001`/`40001` and one active Admin; the barrier delete test starts both deletes
together and asserts one commit, one `P0001`/`40001` and never `40P01`, with one active
Admin left; the insert/`created_by` test asserts both writers commit, the foreign key's
`ON DELETE SET NULL` runs and one active Admin remains; the RR/SERIALIZABLE tests assert a
refusal or `could not serialize access` and never zero active Admins.
`tests/test_migrations.py` runs `alembic check` against `leafclutch_test` (no drift) and
alters `staff.active`'s default inside the test transaction to prove that a changed server
default is reported, then rolls it back.

## Review

## Docs updated

- `Backend/README.md` — the `auth` bootstrap command and why it is not a migration; the
  database-backed test fixture; `alembic check` and the `auth` exclusion; layout rows for
  `app/models.py` and `scripts/bootstrap_local.sql`. The review round added the stub's
  columns, the statement that `alembic downgrade base` does not remove the extensions, and
  the required round trip against the test database.
- `Backend/docs/work/0002-extensions-enums-staff.md` — this log.
- `Backend/docs/DATABASE.md` — §Timestamps and the last Admin now has
  `lock_staff_writes()` with the statement trigger `staff_lock_writes` on INSERT, UPDATE and
  DELETE, the `for update` count in `enforce_last_admin()`, the ordering caveat, the
  long-transaction note and the isolation note; the migration table says the `0001`
  downgrade drops enums only and the `0002` contents name both triggers. The design
  workspace still needs the same patch; the divergence note in `## Decisions made` stays
  until it lands.
- `Backend/docs/work/PLAN.md` — M15 now requires every staff write to take the advisory
  lock before its first staff row lock or retry `40P01` with a bounded backoff, and records
  that the lock is held to commit.
- No `Backend/docs/ADMIN.md` or `CONTRACT.md` change: no role, screen or payload changed.
- No OpenAPI change: no endpoint was added or changed.
- No ADR: `Backend/docs/` has no ADR directory.

## Remaining

Accepted limitations from the review, deferred with their reasons:

- **L1 — TRUNCATE bypasses the row triggers.** `truncate table staff` removes every row
  without firing `staff_last_admin`. No TRUNCATE trigger is added: M12's grants deny
  `TRUNCATE` to `api_runner`, only the database owner can run it, and the concurrency test's
  cleanup relies on it.
- **L2 — `alembic check` does not inspect CHECK constraints or enum labels.** The check
  constraint and the `staff_role` labels are covered by database tests instead; a model
  change to either must ship with a revision and is caught in review, not by autogenerate.
- **L4 — the downgrade/upgrade round trip is manual.** It is a required README command
  against the disposable test database, run for this round and quoted in `## Tests`, but it
  is not automated because it drops every table in the target database.

## Open questions

- The design workspace still holds the unguarded `enforce_last_admin` body and the old
  "drop extensions" downgrade wording; this checkout's `DATABASE.md` is patched, so the two
  copies differ until the design workspace receives the same patch.
- The RR/SERIALIZABLE guard raises `40001`, and a staff service that pre-holds a row lock
  can still hit `40P01` with the trigger. `PLAN.md` M15 records the obligation: take
  `pg_advisory_xact_lock(hashtext('staff_last_admin'))` before the first staff row lock or
  retry `40P01` with a bounded backoff, and translate `40001`.
- The validation runbook's admin fixture now has the `auth.users` columns it needs, but the
  full runbook still needs `auth.mfa_factors` (for `staff_account`) and the tables from
  M3–M15. That wider stub is a harness change at M15, not a revision.
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
- The orchestrated, barrier and insert/foreign-key concurrency tests, and the
  RR/SERIALIZABLE tests, use two or three connections on PostgreSQL 18; a higher connection
  count and a production write load were not exercised.
- The bootstrap upgrade path was verified by dropping `email` and `last_sign_in_at` from the
  local stub and rerunning the script; it was not run against Supabase, where the columns
  already exist.
- The scratch `40P01` comparison (template copy with the trigger dropped) is a manual check,
  not a CI step; the barrier test is stochastic without the trigger and passed on some runs
  even with it dropped.
- The round trip is manual (L4); nothing enforces it in CI, because the repository has no
  CI yet.
