---
task: 0004
title: Content spine
status: in-progress
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Add revision `0004_content_core`: `content_item`, `content_version`, `content_publication`
and `content_seo`, with their indexes and the three guards that make the spine safe — one
open version per item, a published version that cannot change, and a publication pointer
that can only name a published version of the same, unarchived item.

This is M4 in `PLAN.md`. Sections, services, projects and everything typed hang off these
four tables; no typed table is created here.

## Acceptance criteria

- [ ] `0004_content_core` creates the four tables with every column, default, constraint
      and index in `DATABASE.md` §Content items and versions and §Page SEO:
      `content_item_next_version`, the path/slug formats and required-by-kind rules, the
      settings and section shapes, the archive rule, `unique (id, kind)`;
      `content_version_published`/`_publisher`/`_review`, `unique (item_id, version_number)`,
      `unique (item_id, id)`; `content_publication_version_fk`;
      `content_seo_title_length`/`_description_length`; and the six indexes including
      `content_version_one_open`.
- [ ] Functions and triggers, copied verbatim: `bump_next_version` +
      `content_version_bump_next`, `prevent_published_version_mutation` +
      `content_version_immutable`, `assert_publication_version` +
      `content_publication_assert`, and `prevent_published_content_mutation` +
      `content_seo_immutable`.
- [ ] `prevent_published_content_mutation` is created here, but it is attached **only** to
      `content_seo`: the typed tables it also guards arrive in M5 onwards and attach it in
      their own revisions.
- [ ] Downgrade drops every trigger, then the functions, then the tables, in an order that
      works with the composite foreign keys.
- [ ] The four tables are modelled in `app/models.py`; `alembic check` stays clean.
- [ ] Database tests cover, each failing if the protection is removed:
      - a second open version for one item is refused; a new version after the first is
        published is allowed;
      - updating a published version is refused, while the publish update itself
        (draft → published with `published_at`/`published_by`) succeeds;
      - `content_version_published` refuses a published row without `published_at`, and a
        draft with it; `_publisher` refuses the same for `published_by`; `_review` refuses
        `in_review` without `submitted_at`;
      - `content_publication` refuses a draft version, a version belonging to another item,
        and an archived item;
      - `bump_next_version` raises `next_version` past an inserted version;
      - `content_seo` is refused once its version is published, and its lengths are 1–60
        and 1–160;
      - path and slug formats are enforced; `landing_page`/`legal_page` require a path,
        `service`/`project` require a slug, `settings` and `page_section` carry neither;
      - `archived_at` without `archived_by` is refused; the settings singleton and the path
        index refuse a duplicate;
      - deleting an item cascades versions and SEO; deleting a version named by
        `content_publication` is refused.
- [ ] `uv run ruff check .`, `uv run mypy app` and `uv run pytest` pass; `alembic check`
      is clean; `downgrade base` then `upgrade head` succeeds. Output quoted.
- [ ] Only `Backend/` changes.

## Non-goals

- Typed content tables, section records and their triggers (M5 onwards).
- Publish/draft/unpublish functions (M11); this revision only installs the guards.
- RLS, grants, views, storage and any endpoint.

## Plan

| File | Purpose |
| --- | --- |
| `migrations/versions/0004_content_core.py` | Four tables and indexes via SQLAlchemy operations; functions and triggers via `op.execute` |
| `app/models.py` | The four tables for `alembic check` |
| `tests/test_content_spine.py` | The constraints, guards and cascade rules |
| `README.md` | Layout row only if it names tables |

Order: models, tables, functions, tests, checks. Copy constraint expressions, function
bodies and exception messages verbatim. The composite foreign keys require
`content_item (id, kind)` and `content_version (item_id, id)` to exist first; keep that
order.

## Work log

- **2026-11-27 — Models and revision.** Added the four Core tables to
  `Backend/app/models.py` and revision `Backend/migrations/versions/0004_content_core.py`
  (parent `0003_media`). Columns, defaults, every check, `unique (id, kind)`,
  `unique (item_id, version_number)`, `unique (item_id, id)`, the composite
  `content_publication_version_fk` and the six indexes with their `postgresql_where`
  predicates are copied from `DATABASE.md` §Content items and versions and §Page SEO.
  The composite uniques are explicitly named with the names PostgreSQL would generate
  (`content_item_id_kind_key`, `content_version_item_id_version_number_key`,
  `content_version_item_id_id_key`) because the document leaves them unnamed. The four
  functions and their triggers are copied verbatim; `prevent_published_content_mutation`
  is attached only to `content_seo`. `content_version_set_updated_at` is also created,
  reusing `set_updated_at()` from `0002_staff` (`DATABASE.md` §Timestamps and the last
  Admin); the brief lists only the four guard pairs, so this is recorded under
  `## Open questions`. Downgrade drops the triggers, then the functions, then the tables
  in reverse dependency order.
- **2026-11-27 — Tests.** Added `Backend/tests/test_content_spine.py` (84 tests): the
  empty tables; item and version defaults; `bump_next_version`; the one-open index; the
  publish update succeeding and every later update to a published version refused; the
  status checks; publication refusals and the happy path; path, slug and per-kind shape
  rules; the archive rule; the settings singleton and unique path/slug; SEO bounds and
  immutability; the two cascade/restrict rules; and catalog tests pinning every
  constraint definition, the six index definitions and predicates, the five triggers and
  the installed function bodies and messages.
- **2026-11-27 — Test-harness correction.** The first full-suite run failed five staff
  concurrency tests because `cleanup_committed_staff` in
  `Backend/tests/test_staff_schema.py` still ran `truncate table media, staff`; the new
  content foreign keys make PostgreSQL refuse that even with empty content tables. It now
  truncates `content_seo, content_publication, content_version, content_item, media,
  staff`. A second run failed 17 because the refused cleanup had left committed admin rows
  in the test database; after truncating the test database, the suite passed 198. Both
  failing runs are quoted under `## Tests` and are superseded.
- **2026-11-27 — Checks and mutation proof.** Ran ruff, mypy, pytest in default and
  importlib modes, `alembic check`, and `downgrade base` → `upgrade head` → `current` on
  the local development database. On a `leafclutch_scratch_test` copy, dropped
  `content_version_one_open`: the one-open behavioural test failed with
  `DID NOT RAISE IntegrityError` and the index definition test failed on the missing
  index. The scratch database was dropped; the real test database was not altered.

## Decisions made

- **The timestamp trigger is included even though the brief lists four guard pairs.**
  `DATABASE.md` §Timestamps and the last Admin attaches `content_version_set_updated_at`
  (using the existing `set_updated_at()`) to the table this revision creates, and the
  document is the authority on detail. Leaving it out would ship a `content_version` whose
  documented `updated_at` never moves. The guard triggers stay exactly as briefed, and no
  later table gains a trigger here.
- **The composite uniques carry explicit names.** `DATABASE.md` writes
  `unique (id, kind)`, `unique (item_id, version_number)` and `unique (item_id, id)`
  without names. The model and revision name them with PostgreSQL's default names so
  `alembic check` compares like with like and the catalog test can pin them; the installed
  names match what the document's SQL would create.
- **Index predicates are copied verbatim into `postgresql_where`.** Alembic 1.20 compares
  index expressions but not the `WHERE` predicate, so a changed predicate can pass
  `alembic check`. `test_the_documented_indexes_and_predicates_are_installed` compares
  `pg_get_indexdef` for the six indexes instead.
- **`content_version_immutable` is `before update` only.** The publish update must pass;
  the trigger checks `old.status`, so moving a draft or in-review row to published is
  allowed and any later update is refused. The trigger-type test pins the bits.
- **`prevent_published_content_mutation` is attached only to `content_seo`.** The typed
  tables it also guards do not exist yet; their revisions attach the same function in
  M5 onwards.
- **No check constraint is duplicated in Pydantic here.** These are database rules for
  this slice; the FastAPI boundary layers arrive with the endpoints and will cite the same
  section rather than re-implement a regex in four places.
- **The media suite's pattern is reused.** Every test runs inside the `db` transaction,
  uses `begin_nested()` for an expected refusal, and inserts its auth user and staff row
  rather than committing fixtures.
- **The README layout rows are updated because they name tables.** `app/models.py` now
  lists the content-spine tables and `tests/` names the content-spine schema. No other
  README change was made.

## Files changed

New:

- `Backend/migrations/versions/0004_content_core.py` — the four tables, six indexes, four
  functions and five triggers
- `Backend/tests/test_content_spine.py` — 84 behavioural and catalog tests
- `Backend/docs/work/0004-content-spine.md` — this log

Modified:

- `Backend/app/models.py` — `content_item`, `content_version`, `content_publication`,
  `content_seo`, `content_kind` and `version_status`
- `Backend/tests/test_staff_schema.py` — `cleanup_committed_staff` truncates the content
  tables before `staff`
- `Backend/README.md` — the two layout rows that name tables
- `Backend/docs/work/README.md` — the orchestrator's 0004 index row, committed as it stood

No `Frontend/`, `Admin/`, `DATABASE.md`, runbook, `CONTRACT.md`, `ADMIN.md` or dependency
change; `uv.lock` is untouched.

## Migrations

- `0004_content_core` (parent `0003_media`) creates `content_item`, `content_version`,
  `content_publication` and `content_seo` in that order, then the six indexes, then
  `bump_next_version`, `prevent_published_version_mutation`, `assert_publication_version`
  and `prevent_published_content_mutation`, their five triggers (including
  `content_version_set_updated_at`) via `op.execute`.
- `upgrade` was applied to the test database by the suite fixture and to the development
  database by hand; `alembic check` reports no new operations at `0004_content_core`.
- `downgrade base` → `upgrade head` succeeded on the development database. The downgrade
  drops every trigger, then the four functions, then the tables in reverse dependency
  order; the indexes and their predicates go with the tables.

## Tests

Final green runs (PostgreSQL 18, `.env` target `leafclutch` at port 5434):

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest -q
198 passed, 4 warnings in 1.09s

$ uv run pytest -q --import-mode=importlib
198 passed, 4 warnings in 0.89s

$ uv run alembic check
No new upgrade operations detected.

$ uv run alembic downgrade base
INFO  [alembic.runtime.migration] Running downgrade 0004_content_core -> 0003_media, The content spine: items, versions, publication pointers, page SEO and their guards.
INFO  [alembic.runtime.migration] Running downgrade 0003_media -> 0002_staff, The media table and the immutability trigger.
INFO  [alembic.runtime.migration] Running downgrade 0002_staff -> 0001_extensions_enums, The staff table, the last-Admin guard and the timestamp trigger.
INFO  [alembic.runtime.migration] Running downgrade 0001_extensions_enums -> , Extensions and every enum type.

$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_extensions_enums, Extensions and every enum type.
INFO  [alembic.runtime.migration] Running upgrade 0001_extensions_enums -> 0002_staff, The staff table, the last-Admin guard and the timestamp trigger.
INFO  [alembic.runtime.migration] Running upgrade 0002_staff -> 0003_media, The media table and the immutability trigger.
INFO  [alembic.runtime.migration] Running upgrade 0003_media -> 0004_content_core, The content spine: items, versions, publication pointers, page SEO and their guards.

$ uv run alembic current
0004_content_core (head)
```

`tests/test_content_spine.py` alone:

```
$ uv run pytest -q tests/test_content_spine.py
84 passed, 1 warning in 0.47s
```

Failed run 1, fixed by the harness correction above (**superseded**):

```
$ uv run pytest -q
FAILED tests/test_staff_schema.py::test_concurrent_deletes_cannot_remove_both_active_admins
FAILED tests/test_staff_schema.py::test_two_concurrent_deletes_serialise_without_a_deadlock
FAILED tests/test_staff_schema.py::test_an_insert_with_created_by_does_not_deadlock_with_a_delete
FAILED tests/test_staff_schema.py::test_the_guard_holds_at_stronger_isolation[REPEATABLE READ]
FAILED tests/test_staff_schema.py::test_the_guard_holds_at_stronger_isolation[SERIALIZABLE]
5 failed, 193 passed, 4 warnings in 1.20s
```

Failed run 2, the stale committed rows from run 1 (**superseded**):

```
$ uv run pytest -q
17 failed, 181 passed, 4 warnings in 1.20s
```

Mutation proof on `leafclutch_scratch_test` (a copy of `leafclutch_test`) with
`content_version_one_open` dropped:

```
$ uv run pytest -q tests/test_content_spine.py::test_a_second_open_version_is_refused
E       Failed: DID NOT RAISE IntegrityError
FAILED tests/test_content_spine.py::test_a_second_open_version_is_refused

$ uv run pytest -q tests/test_content_spine.py::test_the_documented_indexes_and_predicates_are_installed
E       Right contains 1 more item:
E       {'content_version_one_open': 'create unique index content_version_one_open on '
E                                    'public.content_version using btree (item_id) '
E                                    'where (status = any '
E                                    "(array['draft'::version_status, "
E                                    "'in_review'::version_status]))"}
FAILED tests/test_content_spine.py::test_the_documented_indexes_and_predicates_are_installed
2 failed, 1 warning in 0.30s
```

The scratch database was dropped; the real test database was not altered. The full suite
is 198 tests; the four warnings are the known `httpx`/Starlette and Alembic
`path_separator` deprecations carried from earlier tasks.

## Review

## Docs updated

- `Backend/README.md` — the `app/models.py` and `tests/` layout rows now name the
  content-spine tables and schema.
- `Backend/docs/DATABASE.md` — not edited, per the brief. It already defines the four
  tables and every function and trigger this revision installs; nothing in it was
  invalidated.
- `Backend/docs/ADMIN.md`, `Backend/docs/CONTRACT.md` — none: no role, screen, payload or
  endpoint changed.
- OpenAPI — none: no endpoint was added or changed.
- ADR — none: there is no `Backend/docs/adr/` directory in this checkout.
- Runbook — not edited, per the brief.
- `Backend/docs/work/0004-content-spine.md` — this log.

## Remaining

none

## Open questions

- **`content_version_set_updated_at` is not in the brief's four trigger pairs.**
  `DATABASE.md` §Timestamps and the last Admin attaches it to `content_version`, a table
  this revision creates, so it was installed using the existing `set_updated_at()`.
  Confirm that is wanted here rather than deferred; removing it would leave a documented
  trigger missing, keeping it makes this revision create five triggers rather than the
  four listed in the acceptance criteria.
- Alembic 1.20 does not compare CHECK constraints or an index's `WHERE` predicate, so
  `alembic check` cannot prove either. The catalog tests compare the normalised
  `pg_get_constraintdef` and `pg_get_indexdef` instead. The normalisation drops
  PostgreSQL's decorative parentheses, so a pure regrouping could pass the constraint
  test even though the behavioural tests would usually catch it.
- `PLAN.md` M5 onwards attaches `prevent_published_content_mutation` to the typed tables
  and adds the publish functions. This revision deliberately installs neither.

## Not verified

- Supabase itself: the revision and triggers ran against the plain PostgreSQL 18
  container, not a Supabase project; the `eu-west-2` behaviour and extension versions
  there are unconfirmed.
- Not every constraint has a dedicated behavioural test. `content_item_next_version`,
  the formats and required-by-kind rules, the archive rule, the version status checks, the
  SEO lengths, the one-open index, the singleton/path/slug uniqueness and the two cascade
  and one restrict rules do. The foreign keys `content_item.created_by`,
  `content_item.archived_by`, `content_version.created_by`/`updated_by`/`published_by`,
  `content_publication.published_by` and `content_seo.og_image_id` are pinned by the
  catalog definition test only; `archived_by`'s `SET NULL` and `og_image_id`'s
  `RESTRICT` are not exercised.
- `content_item_kind_idx` and `content_version_item_status_idx` are pinned by the index
  definition test; no test asserts a query plan or that PostgreSQL uses them.
- The mutation proof dropped `content_version_one_open` only. The other guards are
  covered by behavioural tests and by the trigger/function catalog tests, not by a
  per-guard mutation run.
- The migration round trip ran on the development database, as task 0003 did; the test
  database was brought to head by the suite fixture and was not downgraded in this run.
- The publish/unpublish functions, grants, RLS and views are M11/M12, so the spine was
  exercised with direct SQL inside one transaction, not through the application.
