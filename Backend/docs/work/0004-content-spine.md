---
task: 0004
title: Content spine
status: done
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

- [x] `0004_content_core` creates the four tables with every column, default, constraint
      and index in `DATABASE.md` §Content items and versions and §Page SEO:
      `content_item_next_version`, the path/slug formats and required-by-kind rules, the
      settings and section shapes, the archive rule, `unique (id, kind)`;
      `content_version_published`/`_publisher`/`_review`, `unique (item_id, version_number)`,
      `unique (item_id, id)`; `content_publication_version_fk`;
      `content_seo_title_length`/`_description_length`; and the six indexes including
      `content_version_one_open`.
- [x] Functions and triggers, copied verbatim: `bump_next_version` +
      `content_version_bump_next`, `prevent_published_version_mutation` +
      `content_version_immutable`, `assert_publication_version` +
      `content_publication_assert`, and `prevent_published_content_mutation` +
      `content_seo_immutable`.
- [x] `prevent_published_content_mutation` is created here, but it is attached **only** to
      `content_seo`: the typed tables it also guards arrive in M5 onwards and attach it in
      their own revisions.
- [x] Downgrade drops every trigger, then the functions, then the tables, in an order that
      works with the composite foreign keys.
- [x] The four tables are modelled in `app/models.py`; `alembic check` stays clean.
- [x] Database tests cover, each failing if the protection is removed:
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
- [x] `uv run ruff check .`, `uv run mypy app` and `uv run pytest` pass; `alembic check`
      is clean; `downgrade base` then `upgrade head` succeeds. Output quoted.
- [x] Only `Backend/` changes.

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
- **2026-11-27 — Review fixes (High 1–3, Medium, Lows).** Extended
  `prevent_published_version_mutation` to `before update or delete` with a `return old`
  delete branch, so a published version and any item cascade through it are refused;
  added the `old.version_id is distinct from new.version_id` guard to
  `prevent_published_content_mutation`; changed `content_item.archived_by` to
  `on delete restrict`; added `prevent_archived_with_publication()` and
  `content_item_archive_guard`; tightened `content_item_path_format` to
  `^/([a-z0-9-]+(/[a-z0-9-]+)*)?$`; made `content_item_archive` symmetric; fixed the
  publication item on update in `assert_publication_version`; and made the index
  catalogue test compare the exact set of indexes on the four tables. Added the matching
  behavioural tests, including the published delete, the item cascade, the typed-row
  move, the archiver delete, the archive-with-pointer refusal, the publication pointer
  updates, the `v5`-then-`v2` gap and the real publish-timestamp call. Updated
  `Backend/docs/DATABASE.md` §Content items and versions, §Publication and immutability,
  the publish-invariant table and the `0004_content_core` migration row. Because
  `0004_content_core` had already been applied to both local databases and is unreleased,
  their `public` schemas (both empty) were recreated and `upgrade head` re-ran; the
  reviewer's leftover `leafclutch_m4_review` and `leafclutch_m4_review_test` databases
  were dropped. The suite is now 210 tests.

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
- **`content_version_immutable` covers update and delete.** The publish update must
  pass; the trigger checks `old.status`, so moving a draft or in-review row to published
  is allowed and any later update or delete is refused. The delete branch returns `old`;
  the trigger-type test pins the bits. Deleting an item whose version is published is
  therefore refused too, which is intended: `delete_content` only deletes
  never-published items.
- **A typed row cannot move between versions.** The guard is in the shared
  `prevent_published_content_mutation` function, not a per-table trigger, because every
  later typed table has the same rule. It fires before the status check, so a published
  version's `content_seo` row cannot be reassigned to a draft.
- **`archived_by` is `on delete restrict`, not `set null`.** The `content_item_archive`
  check requires the flag pair, so `set null` would make deleting the archiver fail on
  the check instead of the reference. Staff are deactivated rather than deleted, and the
  archive record is audit evidence, so the reference stays and the check stays; the two
  now agree.
- **Archiving refuses a live item until its pointer is gone.** `archive_content` (M11)
  deletes the publication pointer first, so the normal path passes; a direct archive that
  left the item live is refused with `archive removes the publication pointer first`.
- **The path regex requires a non-empty first segment.** `^/([a-z0-9-]+(/[a-z0-9-]+)*)?$`
  keeps `/` for the landing page and rejects `//a`, which the previous expression
  accepted.
- **The publication item is fixed on update.** `assert_publication_version` refuses
  `new.item_id <> old.item_id`; repointing to another published version of the same item
  remains allowed, which is how a republish moves the pointer.
- **The index catalogue is exhaustive.** The test now compares every index on the four
  tables, including the primary-key and unique-constraint backers, so an unplanned extra
  index fails as well as a changed expression or predicate.
- **The publication foreign key is now a backstop, not the first refusal.** A publication
  can only name a published version, and deleting a published version is refused by the
  immutability trigger before `content_publication_version_fk` is reached. The FK keeps
  its `on delete restrict` definition and the catalogue test pins it.
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

- `Backend/migrations/versions/0004_content_core.py` — the four tables, six indexes, five
  functions and six triggers
- `Backend/tests/test_content_spine.py` — 96 behavioural and catalog tests
- `Backend/docs/work/0004-content-spine.md` — this log

Modified:

- `Backend/app/models.py` — `content_item`, `content_version`, `content_publication`,
  `content_seo`, `content_kind` and `version_status`
- `Backend/tests/test_staff_schema.py` — `cleanup_committed_staff` truncates the content
  tables before `staff`
- `Backend/README.md` — the two layout rows that name tables
- `Backend/docs/DATABASE.md` — the review round's table checks, foreign key, functions,
  triggers, invariant table and migration row
- `Backend/docs/work/README.md` — the orchestrator's 0004 index row, committed as it stood

No `Frontend/`, `Admin/`, runbook, `CONTRACT.md`, `ADMIN.md` or dependency change;
`uv.lock` is untouched. `DATABASE.md` was untouched in the first round and changed by the
review fixes above.

## Migrations

- `0004_content_core` (parent `0003_media`) creates `content_item`, `content_version`,
  `content_publication` and `content_seo` in that order, then the six documented indexes,
  then `bump_next_version`, `prevent_archived_with_publication`,
  `prevent_published_version_mutation`, `assert_publication_version` and
  `prevent_published_content_mutation`, their six triggers (including
  `content_version_set_updated_at`) via `op.execute`. `archived_by` references staff
  `on delete restrict`; the archive check is symmetric; the path format rejects an empty
  first segment.
- `upgrade` was applied to the test database by the suite fixture and to the development
  database by hand; `alembic check` reports no new operations at `0004_content_core`.
- `downgrade base` → `upgrade head` succeeded on the development database. The downgrade
  drops every trigger, then the four functions, then the tables in reverse dependency
  order; the indexes and their predicates go with the tables.

## Tests

First-round green runs (PostgreSQL 18, `.env` target `leafclutch` at port 5434;
**superseded** by the review-fix round at the end of this section):

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
was 198 tests; the four warnings are the known `httpx`/Starlette and Alembic
`path_separator` deprecations carried from earlier tasks.

Review-fix round (actual run). Both local `public` schemas were empty and were recreated
before these commands because `0004_content_core` had already been applied with the
first-round code:

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest -q
210 passed, 4 warnings in 1.00s

$ uv run pytest -q --import-mode=importlib
210 passed, 4 warnings in 0.92s

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

`tests/test_content_spine.py` alone is now 96 tests:

```
$ uv run pytest -q tests/test_content_spine.py
96 passed, 1 warning in 0.79s
```

Every new or changed case, run as one selection:

```
$ uv run pytest -q \
    tests/test_content_spine.py::test_a_published_version_cannot_be_deleted \
    tests/test_content_spine.py::test_deleting_an_item_with_a_published_version_is_refused \
    tests/test_content_spine.py::test_bump_next_version_keeps_the_high_water_mark \
    tests/test_content_spine.py::test_the_publish_update_sets_updated_at \
    tests/test_content_spine.py::test_the_archive_flags_move_together \
    tests/test_content_spine.py::test_deleting_the_archiver_is_refused \
    tests/test_content_spine.py::test_archiving_a_live_item_is_refused_until_unpublished \
    tests/test_content_spine.py::test_a_valid_path_is_accepted \
    tests/test_content_spine.py::test_an_invalid_path_is_refused \
    tests/test_content_spine.py::test_a_publication_can_point_to_another_published_version \
    tests/test_content_spine.py::test_a_publication_update_refuses_a_draft_version \
    tests/test_content_spine.py::test_a_publication_cannot_change_its_item \
    tests/test_content_spine.py::test_a_typed_row_cannot_move_off_a_published_version \
    tests/test_content_spine.py::test_a_version_named_by_a_publication_cannot_be_deleted \
    tests/test_content_spine.py::test_the_installed_functions_pin_their_messages \
    tests/test_content_spine.py::test_the_installed_triggers_fire_on_the_documented_events \
    tests/test_content_spine.py::test_the_documented_indexes_and_predicates_are_installed \
    tests/test_content_spine.py::test_every_documented_constraint_matches_its_definition
33 passed, 1 warning in 0.37s
```

Mutation proof for High 1, on `leafclutch_m4_scratch_test` (a copy of the current
`leafclutch_test`) with `content_version_immutable` dropped:

```
$ uv run pytest -q \
    tests/test_content_spine.py::test_a_published_version_cannot_be_deleted \
    tests/test_content_spine.py::test_deleting_an_item_with_a_published_version_is_refused
E       Failed: DID NOT RAISE DBAPIError
E       Failed: DID NOT RAISE DBAPIError
FAILED tests/test_content_spine.py::test_a_published_version_cannot_be_deleted
FAILED tests/test_content_spine.py::test_deleting_an_item_with_a_published_version_is_refused
2 failed, 1 warning in 0.22s
```

The scratch database was dropped. `leafclutch_m4_review` and
`leafclutch_m4_review_test` were dropped; only `leafclutch` and `leafclutch_test` remain.

## Review

Two rounds with one independent reviewer session. Every Critical, High and listed Medium is
closed; the one Medium that survives belongs to M11, and it is recorded in `PLAN.md` M11.

Round 1: three High — a published version could be deleted directly and through the item
cascade; a typed row could move off a published version because only the new `version_id`
was checked; `archived_by ON DELETE SET NULL` contradicted the archive check. One Medium —
archiving a live item left its publication pointer. Six Low. Fixed in `709146`.

Round 2: the three Highs are closed with mutation proofs — dropping
`content_version_immutable` fails the delete tests, removing the `version_id` guard fails the
move test, and deleting an archiver now raises `RestrictViolation`. The archive guard passes
the normal order (delete the pointer, then set the flags). The surviving Medium is the M11
page/section edge; the Lows are deferred with reasons under `## Remaining`.

One correction recorded: the H1 proof is dropping the trigger. Removing only the delete
branch leaves the status check in place, so the published-delete tests still pass; that
mutation only proves the branch is needed for draft deletes.

Verified by the orchestrator: 210 tests in both modes, `alembic check` clean at
`0004_content_core`, and the scratch round trip.

Outcome: **accepted**. No open Critical or High.

## Docs updated

- `Backend/README.md` — the `app/models.py` and `tests/` layout rows now name the
  content-spine tables and schema.
- `Backend/docs/DATABASE.md` — updated in the review round: §Content items and versions
  (foreign key, path regex, symmetric archive check, archive guard), §Publication and
  immutability (delete branch, typed-row move guard, fixed publication item), the
  publish-invariant table and the `0004_content_core` migration row. It was not edited in
  the first round; the review made the document and the migration diverge.
- `Backend/docs/ADMIN.md`, `Backend/docs/CONTRACT.md` — none: no role, screen, payload or
  endpoint changed.
- OpenAPI — none: no endpoint was added or changed.
- ADR — none: there is no `Backend/docs/adr/` directory in this checkout.
- Runbook — not edited, per the brief.
- `Backend/docs/work/0004-content-spine.md` — this log.

## Remaining

Deferred with reasons after the round-2 recheck:

- **The `archive_content` page/section edge is M11 work, not M4.** A page with no pointer
  but a live section pointer would fail the archive guard when M11 archives the section.
  The guard is correct; the M11 function must delete every section pointer first. Recorded
  in `PLAN.md` M11 with the required test.
- **L1 — test precision.** Published-with-SEO, pointer-removed and restore cases, and the
  other staff FK deletions, were verified by probe but are not all pinned as tests.
- **L2 — catalog normalisation.** Parentheses are stripped, so a pure regrouping can pass
  the constraint catalog test; the function tests pin fragments, not whole bodies.
- **L4 — the revision was edited in place.** Safe because no database outside this checkout
  applied `307c96d`; if one did, a new revision is required rather than a schema recreation.

- **Closed in task 0008:** L1's cases — published with SEO, pointer removed, the item
  cascade, archive clearing and the six restrict violations — are pinned in
  `tests/test_content_spine.py`. The normalisation half of L2 was closed in task 0007; its
  function-body half remains deferred, as recorded in task 0008.

## Next

M5 — landing page sections (revision `0005`): the ten sections, their child tables and the
typed-table triggers that attach `prevent_published_content_mutation`.

## Open questions

- **Resolved by the review instruction:** `content_version_set_updated_at` stays in
  `0004`. `DATABASE.md` §Timestamps and the last Admin attaches it to `content_version`,
  and the review confirmed the table arrives here. The revision now has six triggers
  (five guards plus the timestamp trigger).
- **The review cites a `DATABASE.md` §Page validity that does not exist in this
  checkout.** The changes were applied to §Content items and versions and §Publication
  and immutability, which describe the affected objects, plus the publish-invariant table
  and the migration row. Confirm that is where the review intended them.
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
  the formats and required-by-kind rules, both directions of the archive rule, the
  version status checks, the SEO lengths, the one-open index, the singleton/path/slug
  uniqueness, the two cascade rules, `content_item_archived_by_fkey`'s restrict and the
  archive guard do. The foreign keys `content_item.created_by`,
  `content_version.created_by`/`updated_by`/`published_by`,
  `content_publication.published_by` and `content_seo.og_image_id` are pinned by the
  catalog definition test only.
- `content_item_kind_idx` and `content_version_item_status_idx` are pinned by the index
  definition test; no test asserts a query plan or that PostgreSQL uses them.
- The mutation proofs dropped `content_version_one_open` and, in the review round,
  `content_version_immutable` only. The other guards are covered by behavioural tests and
  by the trigger/function catalog tests, not by a per-guard mutation run.
- The migration round trip ran on the development database, as task 0003 did; the test
  database was brought to head by the suite fixture and was not downgraded in this run.
- The archive guard was exercised by a direct update, not by M11's `archive_content`.
  The normal order (delete the pointer, then set the flags) passes, but the page/section
  edge described under `## Remaining` cannot be exercised until `page_section` (M5) and
  `archive_content` (M11) exist.
- The publish/unpublish functions, grants, RLS and views are M11/M12, so the spine was
  exercised with direct SQL inside one transaction, not through the application.
