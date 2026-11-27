---
task: 0003
title: Media table and immutability
status: in-progress
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Add revision `0003_media` exactly as `Backend/docs/DATABASE.md` defines it: the `media`
table with its fifteen constraints and the `media_immutable` trigger that keeps a row
immutable except for one promotion and `deleted_at`.

This is M3 in `PLAN.md`. Storage buckets, grants and RLS are M12; the upload endpoint is
M17.

## Acceptance criteria

- [ ] `0003_media` creates `media` with every column, default and constraint in
      `DATABASE.md` §Media, including `media_object_unique`, `media_visibility_bucket`,
      `media_promotion`, `media_object_path`, `media_size` (4 MB), `media_checksum`
      (32 bytes), `media_alt_required`, `media_types` (PDF only in `evidence`) and
      `media_image_dimensions`.
- [ ] `prevent_media_mutation()` and the `media_immutable` trigger are copied verbatim,
      including the three exception messages.
- [ ] Downgrade drops the trigger, the function and the table.
- [ ] `media` is modelled in `app/models.py`; `alembic check` stays clean.
- [ ] Database tests cover, each failing if the protection is removed:
      - a `public` row must be in `site-media`; a private row must be `media-staging` or
        `evidence`;
      - `promoted_at` is set exactly when the row is public;
      - `alt` is required outside `evidence`, optional in it;
      - PDF is accepted in `evidence` and refused elsewhere; an unknown MIME is refused;
      - zero or over-4 MB size, a checksum that is not 32 bytes, an absolute object path,
        and an image without dimensions are refused;
      - editing any pinned column raises `media rows are immutable; create a new row`;
      - a staged row can be promoted once (bucket to `site-media`, public, `promoted_at`);
      - a public row cannot return to private or change bucket, and an evidence row
        cannot become public;
      - `deleted_at` is the only change a public row accepts, and undelete is refused;
      - a structural test pins the trigger and the function body.
- [ ] `uv run ruff check .`, `uv run mypy app` and `uv run pytest` pass; `alembic check`
      is clean; `downgrade base` then `upgrade head` succeeds. Output quoted.
- [ ] Only `Backend/` changes.

## Non-goals

- Storage buckets, RLS, grants, signed URLs and promotion in FastAPI (M12, M17).
- Content tables and their media references (M4 onwards).
- Any endpoint or admin screen.

## Plan

| File | Purpose |
| --- | --- |
| `migrations/versions/0003_media.py` | Table via SQLAlchemy operations; function and trigger via `op.execute` |
| `app/models.py` | `media` table for `alembic check` |
| `tests/test_media_schema.py` | Constraints, promotion rules and immutability |
| `README.md` | Layout row only if it lists tables (otherwise none) |

Order: model, revision, tests, checks. Copy the constraint and function text verbatim; do
not reorder or reword the exception messages.

## Work log

- **2026-11-27 — Model and revision.** Added the `media` Core table to
  `Backend/app/models.py` and revision `Backend/migrations/versions/0003_media.py`
  (parent `0002_staff`). The columns keep the document's order: `id uuid primary key
  default gen_random_uuid()`, `visibility media_visibility`, `bucket`, `object_path`,
  `mime_type`, `size_bytes bigint`, `width integer`, `height integer`, `alt`,
  `checksum_sha256 bytea`, `uploaded_by uuid references staff (user_id) on delete
  restrict`, `uploaded_at default now()`, `promoted_at`, `deleted_at`. The fifteen
  constraints are the primary key, `media_object_unique` and the thirteen
  `sa.CheckConstraint` entries with the document's expressions. The table has no index,
  as `DATABASE.md` specifies. `prevent_media_mutation()` and `media_immutable` are
  `op.execute` copies of the document, verbatim, and the trigger is `before update` only.
  Downgrade drops the trigger, then the function, then the table.
- **2026-11-27 — Tests.** Added `Backend/tests/test_media_schema.py`: the empty table; a
  staged image and an evidence PDF happy path; the unique `(bucket, object_path)` pair;
  every check constraint refused with its named constraint; the 120-character and
  relative-path bounds; 1/4194304-byte size acceptance and 0/negative/over-4 MB refusal;
  31/33-byte checksums; all ten pinned columns; one successful promotion and a refused
  second one; a public row refused private or a bucket change; an evidence row refused
  promotion; a private row refused a bucket change; `deleted_at` accepted on a public row
  with undelete and alt edits refused; a catalog test pinning the installed constraint
  set; and a structural test pinning the trigger (`before update`, row level, not insert
  or delete) and every pinned column, branch and exception message in the installed
  function.
- **2026-11-27 — Test-harness correction caused by the new foreign key.** The staff
  helper `cleanup_committed_staff` truncated `staff` alone; the new
  `media.uploaded_by` reference makes PostgreSQL refuse that with
  `FeatureNotSupported`, even when `media` is empty. It now runs
  `truncate table media, staff`. The first full suite run after the migration failed the
  five multi-connection staff tests for this reason (the refused cleanup left committed
  rows, then `commit_two_admins` collided on `staff_email_unique`); the stale rows were
  removed and the corrected run is quoted under `## Tests`.
- **2026-11-27 — Mutation checks on a scratch copy.** Created
  `leafclutch_scratch_test` from `leafclutch_test`, dropped `media_immutable`, and ran
  the trigger-dependent tests: 16 failed, 3 passed (the two public/`media_visibility_bucket`
  cases and the insert-time `media_promotion` test still fail on their checks, not the
  trigger).
  In a fresh copy, dropping `media_visibility_bucket` made its three tests fail. Both
  scratch databases were dropped; the real test database was not altered.
- **2026-11-27 — Checks and round trip.** Ran ruff, mypy, pytest in default and importlib
  modes, `alembic check`, and `downgrade base` → `upgrade head` → `current` on the local
  development database; every command is quoted under `## Tests`.

## Decisions made

- **The document wins over the brief on the exception messages.** The brief and the work
  file say "three exception messages"; `DATABASE.md` has three refusal branches but five
  distinct `raise exception` messages (immutable row, undelete, public-row change,
  promotion shape, non-promotion visibility change). All five are copied verbatim and
  pinned by the structural test; none is reworded. Recorded under `## Open questions`.
- **"Fifteen constraints" is the primary key, the unique pair and the thirteen checks.**
  That is 15 objects in the document's `create table media` block. The `uploaded_by`
  foreign key is the sixteenth constraint in `pg_constraint`; it is left unnamed so
  PostgreSQL generates `media_uploaded_by_fkey`, matching the 0002 decision for foreign
  keys. The catalog test pins all sixteen installed names and kinds, including the
  foreign key.
- **Check constraints live in metadata, but `alembic check` cannot compare them.**
  Alembic 1.20's autogenerate has no check-constraint comparison (the same limitation
  task 0002 recorded as L2). The thirteen expressions are copied verbatim into both
  `app/models.py` and the revision, and `test_every_documented_constraint_is_installed`
  pins the installed set by name and kind so a missing constraint is not silent drift;
  every check also has a behavioural test that asserts its constraint name.
- **`media` is a Core `sa.Table`, not an ORM class.** No repository reads it yet; this is
  the same choice as `staff` in 0002 and keeps the unused ORM layer out.
- **The trigger is `before update` only.** Insert is governed by the table constraints
  and must accept a staged row; delete is left to the publish gate and reference checks.
  A structural test asserts the trigger's type bits.
- **The README layout rows are updated because they name tables.** `app/models.py` now
  lists the `staff` and `media` tables and their enums, and `tests/` names the media
  schema. No other README change was made.
- **The staff test cleanup truncates both tables.** `truncate table media, staff` keeps
  the multi-connection staff tests working with the new foreign key; `media` is never
  committed by the suite, so no committed media row is lost.

## Files changed

New:

- `Backend/migrations/versions/0003_media.py` — `media`, `prevent_media_mutation()` and
  the `media_immutable` trigger
- `Backend/tests/test_media_schema.py` — constraints, promotion, immutability, catalog
  and structural tests
- `Backend/docs/work/0003-media.md` — this log

Modified:

- `Backend/app/models.py` — the `media` table and `media_visibility` enum
- `Backend/tests/test_staff_schema.py` — cleanup truncates `media, staff`
- `Backend/README.md` — layout rows for the model and test contents
- `Backend/docs/work/README.md` — the orchestrator's 0003 index row, included as it stood

No `Backend/docs/DATABASE.md`, runbook, `CONTRACT.md`, `ADMIN.md`, `Frontend/` or
`Admin/` change; no dependency change (`uv.lock` untouched).

## Migrations

- `0003_media` (parent `0002_staff`) — creates `media` with its primary key,
  `media_object_unique`, the thirteen checks and the `uploaded_by` foreign key, then
  `prevent_media_mutation()` and `media_immutable`. No index is created. Downgrade drops
  `media_immutable`, then `prevent_media_mutation()`, then the table.
- The revision was applied to the development database (`0002_staff` → `0003_media`),
  checked with `alembic check`, then round-tripped `downgrade base` → `upgrade head`;
  the output is quoted under `## Tests`.
- The test database was migrated once by the session fixture when the suite ran
  (`0002_staff` → `0003_media`).

## Tests

The block below is the actual run for this slice (PostgreSQL 18.7, `.env` target
`leafclutch` at port 5434).

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest -q
........................................................................ [ 67%]
..................................                                       [100%]
106 passed, 4 warnings in 0.78s

$ uv run pytest -q --import-mode=importlib
........................................................................ [ 67%]
..................................                                       [100%]
106 passed, 4 warnings in 0.69s

$ uv run alembic check
No new upgrade operations detected.

$ uv run alembic downgrade base
INFO  [alembic.runtime.migration] Running downgrade 0003_media -> 0002_staff, The media table and the immutability trigger.
INFO  [alembic.runtime.migration] Running downgrade 0002_staff -> 0001_extensions_enums, The staff table, the last-Admin guard and the timestamp trigger.
INFO  [alembic.runtime.migration] Running downgrade 0001_extensions_enums -> , Extensions and every enum type.

$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_extensions_enums, Extensions and every enum type.
INFO  [alembic.runtime.migration] Running upgrade 0001_extensions_enums -> 0002_staff, The staff table, the last-Admin guard and the timestamp trigger.
INFO  [alembic.runtime.migration] Running upgrade 0002_staff -> 0003_media, The media table and the immutability trigger.

$ uv run alembic current
0003_media (head)
```

The four warnings are the known `httpx`/Starlette deprecation and the Alembic
`path_separator` deprecation carried from task 0002.

Mutation check, scratch copy of `leafclutch_test` with `media_immutable` dropped:

```
$ TEST_DATABASE_URL=<scratch> uv run pytest -q tests/test_media_schema.py \
    -k "pinned or promoted or public_row or evidence_row or private_row_cannot or deleted_at or staged_row_can or installed_trigger"
16 failed, 3 passed, 28 deselected, 1 warning in 0.37s
```

The same check with `media_visibility_bucket` dropped instead:

```
$ TEST_DATABASE_URL=<scratch> uv run pytest -q tests/test_media_schema.py \
    -k "public_row_must or private_row_must"
3 failed, 44 deselected, 1 warning in 0.20s
```

Both scratch databases were dropped. `test_media_schema.py` alone is 47 tests; the
installed function and trigger were also read directly with `pg_get_functiondef` and
`pg_get_triggerdef` and match `DATABASE.md`.

## Review

## Docs updated

- `Backend/README.md` — the layout rows that name tables now list the `staff` and `media`
  tables and the media schema in the tests.
- No `Backend/docs/DATABASE.md` change: this revision implements §Media as written, and
  the brief forbids editing it.
- No `Backend/docs/ADMIN.md` or `CONTRACT.md` change: no role, screen, payload or
  endpoint changed.
- No OpenAPI change: no endpoint was added or changed.
- No ADR: `Backend/docs/` has no ADR directory.
- `Backend/docs/work/0003-media.md` — this log.

## Open questions

- The brief and acceptance criteria say "three exception messages", but
  `DATABASE.md` §Media's function has five distinct `raise exception` messages in three
  branches. All five were copied verbatim because the source document is the authority.
  If "three" means something else (for example, a different function version), the
  document and the brief disagree and that needs an orchestrator decision.
- Alembic 1.20 does not compare CHECK constraints, so `alembic check` cannot prove the
  thirteen checks. They are pinned by name and kind in a catalog test and exercised one
  by one behaviourally, but a future edit to a check expression alone would not be
  detected automatically. This is the same limitation recorded for `staff` in task 0002.
- Promotion, signed URLs, storage buckets, grants and RLS remain M12/M17. This slice only
  installs the table and the database guard.

## Not verified

- Supabase itself: the revision and the trigger were run against the plain PostgreSQL 18
  container, not a Supabase project.
- Storage objects and the bucket policies: there is no `storage.buckets`/`storage.objects`
  stub in this checkout's harness, and no object is copied or removed.
- The promotion workflow in FastAPI (M17): only the database transition was exercised.
- The full validation runbook (`docs/runbooks/database-validation.sql`), which needs the
  content tables from M4 onwards.
- Mutation proof covers the trigger and `media_visibility_bucket`; the other twelve
  constraints are proven by their tests asserting the named constraint, not by dropping
  each one on a scratch copy.
- `media_mime_length` cannot be exercised with an allowed MIME type (all are under 100
  characters); its installed name is pinned by the catalog test, and an unknown MIME is
  proved refused by `media_types`. No behaviour test isolates the length check itself.
