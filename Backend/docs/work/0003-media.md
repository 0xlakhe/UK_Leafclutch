---
task: 0003
title: Media table and immutability
status: done
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Add revision `0003_media` exactly as `Backend/docs/DATABASE.md` defines it: the `media`
table with its seventeen constraints and the `media_immutable` trigger that keeps a row
immutable except for one promotion and one frozen `deleted_at`.

This is M3 in `PLAN.md`. Storage buckets, grants and RLS are M12; the upload endpoint is
M17.

## Acceptance criteria

- [x] `0003_media` creates `media` with every column, default and constraint in
      `DATABASE.md` §Media, including `media_object_unique`, `media_visibility_bucket`,
      `media_promotion`, `media_deleted_after_upload`, `media_promoted_after_upload`,
      `media_object_path`, `media_size` (4 MB), `media_checksum` (32 bytes),
      `media_alt_required`, `media_alt_length` (not empty), `media_types` (PDF only in
      `evidence`) and `media_image_dimensions`.
- [x] `prevent_media_mutation()` and the `media_immutable` trigger are copied verbatim,
      including every exception message.
- [x] Downgrade drops the trigger, the function and the table.
- [x] `media` is modelled in `app/models.py`; `alembic check` stays clean.
- [x] Database tests cover, each failing if the protection is removed:
      - a `public` row must be in `site-media`; a private row must be `media-staging` or
        `evidence`;
      - `promoted_at` is set exactly when the row is public;
      - `alt` is required outside `evidence`, optional in it;
      - PDF is accepted in `evidence` and refused elsewhere; an unknown MIME is refused;
      - zero or over-4 MB size, a checksum that is not 32 bytes, an absolute object path,
        and an image without dimensions are refused;
      - editing any pinned column raises `media rows are immutable; create a new row`;
      - a staged row can be promoted once (bucket to `site-media`, public, `promoted_at`);
      - a soft-deleted staged row cannot be promoted, including when `deleted_at` is set in
        the promotion statement itself;
      - a public row cannot return to private or change bucket, and an evidence row
        cannot become public;
      - `deleted_at` is the only change a public row accepts, a set `deleted_at` is frozen,
        and neither timestamp may precede `uploaded_at`;
      - an empty `alt` is refused outside `evidence`;
      - a structural test pins the trigger and the function body.
- [x] `uv run ruff check .`, `uv run mypy app` and `uv run pytest` pass; `alembic check`
      is clean; `downgrade base` then `upgrade head` succeeds. Output quoted.
- [x] Only `Backend/` changes.

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
  restrict`, `uploaded_at default now()`, `promoted_at`, `deleted_at`. The seventeen
  constraints are the primary key, `media_object_unique` and the fifteen
  `sa.CheckConstraint` entries with the document's expressions. The table has no index,
  as `DATABASE.md` specifies. `prevent_media_mutation()` and `media_immutable` are
  `op.execute` copies of the document, verbatim, and the trigger is `before update` only.
  Downgrade drops the trigger, then the function, then the table.
- **2026-11-27 — Tests.** Added `Backend/tests/test_media_schema.py`: the empty table; a
  staged image and an evidence PDF happy path; the unique `(bucket, object_path)` pair;
  the visibility, promotion, path, size, checksum, alt and image-dimension checks refused
  with their named constraints (`media_bucket` and `media_mime_length` are catalog-only);
  the 120-character and relative-path bounds; 1/4194304-byte size acceptance and
  0/negative/over-4 MB refusal; 31/33-byte checksums; all ten pinned columns; one
  successful promotion and a refused second one; a public row refused private or a bucket
  change; an evidence row refused promotion; a private row refused a bucket change;
  `deleted_at` accepted on a public row with undelete and alt edits refused; a catalog
  test pinning the installed constraint set; and a structural test pinning the trigger
  (`before update`, row level, not insert or delete) and every pinned column, branch and
  exception message in the installed function.
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
- **2026-11-27 — Review fixes: Medium 1–3, L2 and L5.** The promotion branch now refuses
  a row whose current or incoming `deleted_at` is set, and a test covers a soft-deleted
  staged row and a promotion that deletes in the same statement. A set `deleted_at` is
  frozen with `media deletion cannot be changed`; `media_deleted_after_upload` and
  `media_promoted_after_upload` refuse a timestamp before `uploaded_at`, and a test
  accepts equal timestamps. `media_alt_length` now refuses the empty string. The catalog
  test compares normalised `pg_get_constraintdef` for every documented constraint and
  `pg_enum` labels for all thirteen enums, not just `(conname, contype)`. `DATABASE.md`
  §Media gained the new condition, the two checks, the frozen deletion and the L3/L4
  sentences; the model, revision and this log now say seventeen constraints (the README
  names the tables but carries no count). The earlier claim that every check has a
  behavioural test is corrected:
  `media_bucket` and `media_mime_length` are catalog-only. The suite is 114 tests; the
  boundary change was proven on a scratch copy and every command is quoted under
  `## Tests`.

## Decisions made

- **The document wins over the brief on the exception messages.** The brief and the work
  file said "three exception messages"; `DATABASE.md` has three refusal branches but six
  distinct `raise exception` messages after the review fix (immutable row, undelete,
  frozen deletion, public-row change, promotion shape, non-promotion visibility change).
  All six are copied verbatim and pinned by the structural test; none is reworded.
  Recorded under `## Open questions`.
- **"Seventeen constraints" is the primary key, the unique pair and the fifteen checks.**
  That is 17 objects in the document's `create table media` block. The `uploaded_by`
  foreign key is the eighteenth constraint in `pg_constraint`; it is left unnamed so
  PostgreSQL generates `media_uploaded_by_fkey`, matching the 0002 decision for foreign
  keys. The catalog test pins all eighteen installed names and definitions, including the
  foreign key.
- **Check constraints live in metadata, but `alembic check` cannot compare them.**
  Alembic 1.20's autogenerate has no check-constraint comparison (the same limitation
  task 0002 recorded as L2). The fifteen expressions are copied verbatim into both
  `app/models.py` and the revision, and
  `test_every_documented_constraint_matches_its_definition` compares the normalised
  `pg_get_constraintdef` of every documented constraint, so a changed bound or operator
  fails the suite. `media_bucket` and `media_mime_length` are covered by that test only;
  the other checks also have a behavioural test.
- **A soft-deleted row cannot be promoted.** The promotion branch refuses a row whose
  current or incoming `deleted_at` is set, so a row cannot be deleted and promoted in one
  statement or promoted after deletion.
- **Deletion is frozen and timestamps are ordered.** After the first `deleted_at`, any
  other value (including null, caught earlier as undelete) raises
  `media deletion cannot be changed`. `media_deleted_after_upload` and
  `media_promoted_after_upload` require each timestamp to be at or after `uploaded_at`;
  equality is accepted.
- **Alt is non-empty when present.** `media_alt_length` now requires 1 to 120 characters
  for a non-null `alt`; `evidence` may still omit it entirely.
- **L3 and L4 are documented, not coded.** The database still accepts a direct public
  insert and does not inspect `object_path` for `..`; the upload path and the M12 grants
  carry those guarantees, and `DATABASE.md` §Media now says so.
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

- `Backend/docs/DATABASE.md` — §Media gained the new function condition, the two
  timestamp checks, the non-empty alt bound, frozen deletion and the L3/L4 sentences
- `Backend/app/models.py` — the `media` table and `media_visibility` enum
- `Backend/tests/test_staff_schema.py` — cleanup truncates `media, staff`
- `Backend/README.md` — layout rows for the model and test contents
- `Backend/docs/work/README.md` — the orchestrator's 0003 index row, included as it stood

No runbook, `CONTRACT.md`, `ADMIN.md`, `Frontend/` or `Admin/` change; no dependency
change (`uv.lock` untouched).

## Migrations

- `0003_media` (parent `0002_staff`) — creates `media` with its primary key,
  `media_object_unique`, the fifteen checks (including `media_deleted_after_upload` and
  `media_promoted_after_upload`) and the `uploaded_by` foreign key, then
  `prevent_media_mutation()` and `media_immutable`. No index is created. Downgrade drops
  `media_immutable`, then `prevent_media_mutation()`, then the table.
- The revision was applied to the development database (`0002_staff` → `0003_media`),
  checked with `alembic check`, then round-tripped `downgrade base` → `upgrade head`;
  the output is quoted under `## Tests`.
- The test database was migrated once by the session fixture when the suite ran
  (`0002_staff` → `0003_media`).

## Tests

The block below is the actual run for this slice after the review fixes (PostgreSQL
18.7, `.env` target `leafclutch` at port 5434).

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest -q
........................................................................ [ 63%]
..........................................                               [100%]
114 passed, 4 warnings in 0.86s

$ uv run pytest -q --import-mode=importlib
........................................................................ [ 63%]
..........................................                               [100%]
114 passed, 4 warnings in 0.70s

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
`path_separator` deprecation carried from task 0002. `test_media_schema.py` alone is 55
tests.

Constraint-drift proof: a scratch copy of `leafclutch_test` had `media_object_path`
replaced with the same check bounded at 299 instead of 300. The new catalog test fails on
the definition even though `alembic check` cannot see CHECK constraints:

```
$ TEST_DATABASE_URL=<scratch> uv run pytest -q \
    tests/test_media_schema.py::test_every_documented_constraint_matches_its_definition
E       Differing items:
E       {'media_object_path': ('c', "... <= 299 ...")} !=
E       {'media_object_path': ('c', "... <= 300 ...")}
FAILED tests/test_media_schema.py::test_every_documented_constraint_matches_its_definition
1 failed, 1 warning in 0.23s
```

The scratch database was dropped; the real test database was not altered. The earlier
trigger-drop mutation check (16 failed) was run before the review fixes and is
**superseded** by the current behavioural tests.

## Review

Two rounds with one independent reviewer session, plus the fix round. Every Critical, High
and Medium is closed; four Low findings are deferred with reasons.

Round 1: no Critical or High. Three Medium — a soft-deleted staged row could be promoted;
`deleted_at` could be rewritten and neither timestamp was checked against `uploaded_at`;
and changing a constraint expression left the suite green because the catalog test compared
only names. Six Low. Fixed in `018111d`: the promotion branch refuses a deleted row, the
deletion is frozen and bounded, `media_deleted_after_upload` and
`media_promoted_after_upload` were added, the catalog test compares normalised definitions,
`media_alt_length` requires 1–120, and the enum labels are pinned.

Round 2: the three Mediums are closed, with probes for legitimate promotion, equal
timestamps, a changed constraint expression and added or renamed enum labels. Four Low
remain, deferred:

1. The catalog normaliser strips every parenthesis, so a pure regrouping can pass it alone;
   the behavioural suite caught the current grouping change (28 failures). Recorded rather
   than made semantic, because the check is a backstop, not the only test.
2. The two timestamp checks are exercised on insert, not on the promotion or update path;
   the reviewer verified both update paths manually and they refuse correctly.
3. `alt=''` in `evidence` is refused by the length check but has no dedicated test; only
   `null` is the evidence omission.
4. The normalisation wording in `## Open questions` calls all parentheses decorative; the
   reviewer showed grouping can matter.

Verified by the orchestrator: 114 tests, `alembic check` clean at `0003_media`, and both new
constraints present in the migration, the model and the document.

Outcome: **accepted**. No open Critical or High.

## Next

M4 — content spine (revision `0004`): `content_item`, `content_version`,
`content_publication`, `content_seo` and the immutable-content function.

## Docs updated

- `Backend/README.md` — the layout rows that name tables now list the `staff` and `media`
  tables and the media schema in the tests.
- `Backend/docs/DATABASE.md` — §Media now carries the deleted-row promotion guard, the
  frozen `deleted_at` and its message, `media_deleted_after_upload`,
  `media_promoted_after_upload`, the non-empty alt bound, and the L3/L4 notes on direct
  inserts and object-path traversal. The matching function body is updated in place.
- `Backend/docs/ADMIN.md` and `CONTRACT.md` do not change: no role, screen, payload or
  endpoint changed.
- No OpenAPI change: no endpoint was added or changed.
- No ADR: `Backend/docs/` has no ADR directory.
- `Backend/docs/work/0003-media.md` — this log.

## Open questions

- The brief and acceptance criteria originally said "three exception messages", but
  `DATABASE.md` §Media's function now has six distinct `raise exception` messages in
  three branches. All six were copied verbatim because the source document is the
  authority. If "three" meant something else, the document and the brief disagree and
  that needs an orchestrator decision.
- Alembic 1.20 does not compare CHECK constraints, so `alembic check` cannot prove them.
  `test_every_documented_constraint_matches_its_definition` now compares the normalised
  `pg_get_constraintdef` of every documented constraint, so a changed bound or operator
  fails the suite; the normalisation strips PostgreSQL's decorative parentheses and
  whitespace, which is the trade-off for stability.
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
- Not every constraint has a behavioural test: `media_bucket` and `media_mime_length` are
  covered by the catalog definition test only. The other checks also have a behavioural
  test that asserts the named constraint.
- The constraint-drift mutation proof changed `media_object_path` from 300 to 299 on a
  scratch copy; the other definitions are guarded by the same catalog comparison, not by
  a per-constraint mutation run.
- `media_mime_length` cannot be exercised with an allowed MIME type (all are under 100
  characters); its installed definition is pinned by the catalog test, and an unknown MIME
  is proved refused by `media_types`.
- L3 (a direct public insert is not prevented) and L4 (`..` in `object_path` is not
  rejected) are documented for the M12/M17 work, not fixed in the database here.
