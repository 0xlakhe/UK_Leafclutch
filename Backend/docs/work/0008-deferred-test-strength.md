---
task: 0008
title: Close the deferred test-strength items
status: in-progress
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Close the deferred test-strength Lows from tasks 0003 (media), 0004 (content spine) and
0007 (landing page sections) that need no schema change: the parenthesis-preserving catalog
comparison for media, the two media timestamp checks on the update and promotion paths, the
empty-evidence alt case, the content-spine behavioural pins, and real-commit plus exact-body
pins for the page-section guards.

This is test work. No application, migration, model or schema-document change: the
`DATABASE.md` schema stays as it is.

## Acceptance criteria

- [ ] `test_media_schema.py` compares `pg_get_constraintdef` with parentheses retained; a
      pure regrouping fails, and the existing bound and column mutations still fail.
- [ ] `alt=''` in `evidence` is refused, and `alt=null` in `evidence` is still allowed.
- [ ] `media_deleted_after_upload` and `media_promoted_after_upload` are exercised on the
      public-row update and staged-promotion paths, not only on insert.
- [ ] `test_content_spine.py` pins: deleting a published version with SEO, deleting a
      published version after the pointer was removed, deleting an item with a live
      pointer, clearing the archive flags, and the staff/media restrict violations
      (`created_by`, `updated_by`, `published_by` on both rows, `og_image_id`).
- [ ] `test_page_sections.py` has a real-commit test on a separate connection for the
      changed reinsert, identical reinsert, create-and-delete, sections-then-page and
      version-move paths, with cleanup in `finally`.
- [ ] The seven M5 guard functions are compared by exact normalised body against the
      migration's `ASSERT_..._SQL` constants. M3/M4 body pins stay as fragments, with the
      reason recorded: their source is inline in pushed revisions and duplicating the
      bodies adds no branch coverage beyond the existing mutation proofs.
- [ ] `uv run ruff check .`, `uv run mypy app`, `uv run pytest` in both import modes and
      `uv run alembic check` pass; 322 or more tests.
- [ ] Only `Backend/` changes.

## Non-goals

- The M2 `TRUNCATE` guard (a schema change, recorded), M3 L3/L4 (M12/M17), M4's in-place
  revision note, the M11 functions and their application-database tests, Supabase and
  staging.
- A shared test-helper module; each test file keeps its local helper.

## Plan

| Step | Files | Commit |
| --- | --- | --- |
| 1. Media: parenthesis-preserving normaliser, empty-evidence alt, both timestamp update paths | `tests/test_media_schema.py` | `test(db): pin the media catalog and timestamp paths` |
| 2. Content spine: the L1 behavioural pins | `tests/test_content_spine.py` | `test(db): pin the content spine refusals` |
| 3. Page sections: real-commit tests and exact function bodies | `tests/test_page_sections.py` | `test(db): commit the page section guards` |

No migration content changes. The suite still applies `alembic upgrade head` once; run
`alembic check` after each commit.

## Work log

- **2026-11-28 — Step 1: media test strength.** `normalise_constraint` in
  `Backend/tests/test_media_schema.py` now lower-cases and collapses whitespace only;
  PostgreSQL's parentheses are kept and compared exactly. The two comments that called the
  parentheses decorative are corrected. All eighteen expected definitions already matched
  PostgreSQL 18.7's `pg_get_constraintdef` output after the change, so no expected
  definition needed a pin correction; the catalog test passes unmodified. Added
  `test_an_empty_alt_is_refused_in_evidence` (`alt = ''` refused by `media_alt_length`);
  `alt = null` in `evidence` remains allowed and is proved by the existing happy-path test.
  Added `test_deleted_at_cannot_precede_uploaded_at_on_a_public_row` and
  `test_promoted_at_cannot_precede_uploaded_at_on_promotion` (both refuse inside
  `db.begin_nested()` and assert the row keeps its old value or stays private), plus
  `test_equal_timestamps_are_accepted_on_update_and_promotion` for the legitimate update
  and promotion paths. Both mutation proofs ran on scratch copies of `leafclutch_test`
  (`leafclutch_scratch_regroup_test`, `leafclutch_scratch_bound_test`) and both were
  dropped afterwards; the real test database was not altered. `tests/test_media_schema.py`
  is 59 tests; the suite is 326. Correction (review Low): the recorded regrouping SQL
  changes meaning, not only grouping; see Mutation 1 under Tests.
- **2026-11-28 — Step 2: content-spine behavioural pins.** `Backend/tests/test_content_spine.py`
  now pins the five L1 gaps: a published version with a `content_seo` row cannot be
  deleted and the SEO row survives; a published version stays undeletable after its
  publication pointer is removed (history kept); deleting an item with a live pointer
  refuses through the version cascade with the published-version message; restoring an
  archived item clears both flags while clearing only one is still refused; and every
  restrict foreign key named in the brief is exercised by deleting the referenced row
  (`content_item.created_by`, `content_version.created_by`/`.updated_by`/`.published_by`,
  `content_publication.published_by`, `content_seo.og_image_id`). Each refusal matches the
  named constraint or message and asserts the child row keeps its reference. A local
  `media_values`/`add_media` helper copies the shape `tests/test_media_schema.py` inserts;
  every staff row is an Editor and each FK uses its own row, so `enforce_last_admin` never
  fires first. All twelve new cases passed on the first run: no probe contradicted
  `DATABASE.md`. `tests/test_content_spine.py` is 108 tests; the suite is 338.
- **2026-11-28 — Step 3: page-section real commits and exact function bodies.**
  `Backend/tests/test_page_sections.py` gains `committed_connection`, a context manager on
  a connection from `database_engine`: it commits an Editor for `created_by` (an Editor
  never trips `enforce_last_admin`) and, in `finally`, deletes the content items the case
  registered — the cascades clear the versions and section rows — then the staff row, then
  the auth row. Seven real-commit cases: a changed `page_id`, `section_key` or
  `sort_order` reinsert fails at `COMMIT` with `page section item .* changed its
  page_section row` and the rollback leaves the original row; an identical
  delete-and-reinsert commits; a section item inserted with its row and deleted in the
  same transaction commits without `needs a page_section_row`; two sections with draft
  versions deleted and then their landing page deleted commits; and a committed draft
  `content_version` moved to a project item is refused with `a version cannot move between
  items` (that trigger is immediate, so on the real connection the refusal is at the
  UPDATE). The cleanup leaves no row: `content_item`, `content_version`, `page_section`,
  `section_version` and `staff` counted 0 after the run, and the empty-state test passes
  again on the next run. The six-case fragment parametrisation of
  `test_the_installed_section_functions_pin_their_bodies` became one test comparing the
  exact `pg_proc.prosrc` of the seven M5 functions with the migration's `ASSERT_..._SQL`
  constants, loaded through `importlib.util.spec_from_file_location`. The body is the text
  between the first `as $$` and the closing `$$`; whitespace is collapsed and case is
  kept. The test asserts the map holds seven functions and that the installed set equals
  the map. The older standalone fragment pin for `assert_page_section_row()` stays: it is
  a separate message-level check and the brief scoped the replacement to the parametrised
  loop. `tests/test_page_sections.py` is 114 tests; the suite is 340. Review Low: the
  expected function set is now derived from the migration, so an eighth guard fails the
  pin; see the review-Low entry below.
- **2026-11-28 — Review Lows: the body pin derives its function list.** Closing the review
  Lows on step 3. `Backend/tests/test_page_sections.py`'s module docstring now separates
  the two pins: the installed constraint, index and trigger definitions are compared with
  `Backend/docs/DATABASE.md`, while the seven function bodies are compared with the
  `0005_page_sections.py` constants, which carry the same SQL today.
  `migration_function_names` derives the expected names from the revision — every
  module-level string matching `create or replace function (\w+)` — and the pin asserts the
  seven-entry map equals that set before comparing `prosrc`. The seven entries are
  unchanged. The recorded media mutation is corrected under Mutation 1: it changes
  meaning, and the reviewer's semantically equivalent clause reorder is the evidence that
  the parenthesis-preserving normaliser rejects a regrouping.

## Decisions made

- **Parentheses are significant.** The catalog comparison keeps PostgreSQL's parentheses
  and compares exact definitions after case folding and whitespace collapse. A regrouping
  that preserves the stripped token order is now a failure, which is the behaviour the
  review asked for. No expected definition was relaxed to make this pass.
- **The 0003 work file is not rewritten.** Its `## Open questions` sentence calling the
  parentheses decorative is superseded by the code and this entry; the orchestrator records
  the review closure in `0003-media.md`.
- **Content-spine refusals are pinned by behaviour, not by re-pinning SQL.** The Step 2
  tests use the existing helpers and `db.begin_nested()`, and match the constraint name or
  trigger message the database actually raised. The M4 function bodies stay as fragment
  pins: as `## Plan` records, the exact normalised-body comparison is reserved for the
  seven M5 guard functions, because the M3/M4 bodies live inline in already-pushed
  revisions and duplicating them adds no branch coverage beyond the existing mutation
  proofs.
- **Staff FK probes use Editors.** Every referenced staff row is an Editor, and the
  `content_item` and `content_version` cases use a separate row per foreign key, so the
  delete reaches the named restrict FK rather than `enforce_last_admin`.
- **The seven M5 bodies are pinned against the migration, not `DATABASE.md`.** The
  migration's `ASSERT_..._SQL` constants are what `alembic upgrade head` installs, so they
  are the executable source; `DATABASE.md` §Section items and §Section copy carry the same
  SQL. Comparing `pg_proc.prosrc` with the constant catches a change to either the
  installed function or the migration text, and collapsing whitespace only keeps case,
  punctuation and clause order in the comparison. `prosrc` is read for the function in the
  `public` schema, so a function in another schema cannot satisfy the pin.
- **The real-commit cases clean up by content item, not by TRUNCATE.** Each case registers
  every content item id it creates; `committed_connection` deletes those items first (the
  version, section and child rows cascade), then the staff row, then the auth row. Deleting
  the page item alone would orphan its section items and fail the deferred
  `page_section_row_kept` check, which is why the section items are registered and deleted
  in the same statement.
- **The older `assert_page_section_row()` fragment test stays.** The exact-body pin
  subsumes it, but the brief replaced the parametrised fragment loop only; removing a
  passing test was outside the slice.

## Files changed

- `Backend/tests/test_media_schema.py` — parenthesis-preserving `normalise_constraint`,
  corrected comments, the empty-evidence-alt test, the two timestamp update-path refusals
  and the equal-timestamp update/promotion acceptance test
- `Backend/tests/test_content_spine.py` — the L1 behavioural pins: published-version
  deletion with SEO and after unpublishing, the live-pointer item cascade, restore and
  half-clear archive flags, and the staff/media restrict foreign keys, plus the local
  `media_values`/`add_media` helper
- `Backend/tests/test_page_sections.py` — the seven real-commit cases through
  `committed_connection`, and the exact `pg_proc.prosrc` comparison for the seven M5
  functions against `0005_page_sections.py`'s SQL constants, replacing the six-case
  fragment parametrisation
- `Backend/docs/work/0008-deferred-test-strength.md` — this log

## Migrations

None.

## Tests

Actual runs for this slice (PostgreSQL 18.7, `.env` target `leafclutch` at port 5434):

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files

$ uv run pytest -q
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 66%]
........................................................................ [ 88%]
......................................                                   [100%]
326 passed, 4 warnings in 1.59s

$ uv run pytest -q --import-mode=importlib
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 66%]
........................................................................ [ 88%]
......................................                                   [100%]
326 passed, 4 warnings in 1.43s

$ uv run alembic check
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
No new upgrade operations detected.
```

`tests/test_media_schema.py` alone after the change:

```
$ uv run pytest -q tests/test_media_schema.py
...........................................................              [100%]
59 passed, 1 warning in 0.68s
```

The four warnings are the known Starlette `httpx` deprecation and the Alembic
`path_separator` deprecation carried from earlier tasks.

**Mutation 1 — regrouping `media_visibility_bucket`.** On `leafclutch_scratch_regroup_test`
the constraint was dropped and re-added as
`visibility = 'public' and (bucket = 'site-media' or visibility = 'private') and bucket in ('media-staging', 'evidence')`,
which PostgreSQL renders as a different grouping. The catalog test fails:

```
$ TEST_DATABASE_URL=<scratch> uv run pytest -q \
    tests/test_media_schema.py::test_every_documented_constraint_matches_its_definition
E       Differing items:
E       {'media_visibility_bucket': ('c', "check (((visibility = 'public'::media_visibility) and ((bucket = 'site-media'::text) or (visibility = 'private'::media_visibility)) and (bucket = any (array['media-staging'::text, 'evidence'::text]))))")} !=
E       {'media_visibility_bucket': ('c', "check ((((visibility = 'public'::media_visibility) and (bucket = 'site-media'::text...r ((visibility = 'private'::media_visibility) and (bucket = any (array['media-staging'::text, 'evidence'::text])))))")}
FAILED tests/test_media_schema.py::test_every_documented_constraint_matches_its_definition
1 failed, 1 warning in 0.27s
```

The regrouping is the one the review showed can preserve the stripped token order; the
old normaliser still considers the two definitions equal, the new one does not:

```
old normaliser equal: True
new normaliser equal: False
```

**Correction (review Low).** The mutation above is not a pure regrouping. Under
`visibility = 'public' and (bucket = 'site-media' or visibility = 'private') and bucket in
('media-staging', 'evidence')` a public row cannot satisfy every conjunct, so no public row
can be stored: the statement changes meaning as well as grouping. It still proves the
normaliser keeps PostgreSQL's parentheses, but the equivalence evidence is the reviewer's
second probe — the two OR branches swapped, which is semantically equivalent — and the
parenthesis-preserving normaliser rejected that as well. Neither probe was re-run in this
commit.

**Mutation 2 — `media_object_path` bound 300 → 299.** On
`leafclutch_scratch_bound_test` the bound was lowered; the catalog test still fails:

```
$ TEST_DATABASE_URL=<scratch> uv run pytest -q \
    tests/test_media_schema.py::test_every_documented_constraint_matches_its_definition
E       Differing items:
E       {'media_object_path': ('c', "check ((((char_length(object_path) >= 1) and (char_length(object_path) <= 299)) and (object_path !~ '^/'::text)))")} !=
E       {'media_object_path': ('c', "check ((((char_length(object_path) >= 1) and (char_length(object_path) <= 300)) and (object_path !~ '^/'::text)))")}
FAILED tests/test_media_schema.py::test_every_documented_constraint_matches_its_definition
1 failed, 1 warning in 0.22s
```

Both scratch databases were dropped; the real `leafclutch_test` and `leafclutch`
databases were not altered.

Step 2 runs on 2026-11-28 (same PostgreSQL 18.7 target):

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files
```

```
$ uv run pytest -q
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
...................................................                      [100%]
338 passed, 4 warnings in 1.52s

$ uv run pytest -q --import-mode=importlib
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
...................................................                      [100%]
338 passed, 4 warnings in 1.47s

$ uv run alembic check
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.types
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.constraints
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.defaults
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments
No new upgrade operations detected.
```

`tests/test_content_spine.py` alone after the change:

```
$ uv run pytest -q tests/test_content_spine.py
........................................................................ [ 66%]
....................................                                     [100%]
108 passed, 1 warning in 0.65s
```

The twelve new cases (ten single-case functions plus one parametrised over the two
half-cleared flags) ran:

```
$ uv run pytest -q tests/test_content_spine.py -k "with_seo_cannot or live_pointer \
    or survives_unpublishing or restoring_an_archived or clearing_only_one \
    or item_creator or version_creator or version_editor or version_publisher \
    or publication_publisher or og_image"
12 passed, 96 deselected, 1 warning in 0.32s
```

All passed; no probe failed or contradicted the document.

Step 3 runs on 2026-11-28 (same PostgreSQL 18.7 target):

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files
```

```
$ uv run pytest -q
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
....................................................                     [100%]
340 passed, 4 warnings in 1.57s

$ uv run pytest -q --import-mode=importlib
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
....................................................                     [100%]
340 passed, 4 warnings in 1.51s

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
```

`tests/test_page_sections.py` alone after the change:

```
$ uv run pytest -q tests/test_page_sections.py
........................................................................ [ 63%]
..........................................                               [100%]
114 passed, 1 warning in 0.74s
```

The new cases (seven real-commit plus the single exact-body pin) ran:

```
$ uv run pytest tests/test_page_sections.py -v -k "at_commit or identical_page_section \
    or created_and_deleted or both_sections or project_item or pin_their_bodies"
tests/test_page_sections.py::test_a_page_section_item_created_and_deleted_in_one_transaction_passes PASSED [ 11%]
tests/test_page_sections.py::test_the_installed_section_functions_pin_their_bodies PASSED [ 22%]
tests/test_page_sections.py::test_a_changed_page_section_reinsert_fails_at_commit[page_id] PASSED [ 33%]
tests/test_page_sections.py::test_a_changed_page_section_reinsert_fails_at_commit[section_key] PASSED [ 44%]
tests/test_page_sections.py::test_a_changed_page_section_reinsert_fails_at_commit[sort_order] PASSED [ 55%]
tests/test_page_sections.py::test_an_identical_page_section_reinsert_commits PASSED [ 66%]
tests/test_page_sections.py::test_a_page_section_created_and_deleted_in_one_commit_passes PASSED [ 77%]
tests/test_page_sections.py::test_deleting_both_sections_then_their_page_commits PASSED [ 88%]
tests/test_page_sections.py::test_a_draft_version_cannot_move_to_a_project_item PASSED [100%]
9 passed, 105 deselected, 1 warning in 0.24s
```

The `-k` pattern also matches the older savepoint create-and-delete case, which is why
the run reports nine.

After the suite, no committed row was left behind (`select count(*)` on each table):

```
content_item: 0
content_version: 0
page_section: 0
section_version: 0
staff: 0
```

**Mutation 3 — regrouped `assert_page_section_position` body.** On a fresh scratch
database (`leafclutch_scratch_body_test`, created empty and then upgraded by the suite's
own `alembic upgrade head`), the installed function was replaced by a semantically
equivalent body that swaps the four `or` clauses. The exact pin fails while all four
behavioural cases still pass, which is the gap the exact pin closes:

```
$ TEST_DATABASE_URL=<scratch> uv run pytest -q \
    tests/test_page_sections.py::test_the_installed_section_functions_pin_their_bodies
E           AssertionError: the installed assert_page_section_position() body differs from
ASSERT_PAGE_SECTION_POSITION_SQL in 0005
E           assert 'begin if new...urn new; end;' == 'begin if new...urn new; end;'
E             Skipping 89 identical trailing characters in diff, use -v to show
E             - begin if new.item_id is distinct from old.item_id or new.page_id is
distinct from old.page_id or new.section_key is distinct from old.section_key or
new.sort_order is distinct from old.sort_order then rai
E             + begin if new.sort_order is distinct from old.sort_order or new.section_key
is distinct from old.section_key or new.page_id is distinct from old.page_id or
new.item_id is distinct from old.item_id then rai
FAILED tests/test_page_sections.py::test_the_installed_section_functions_pin_their_bodies
1 failed, 1 warning in 0.20s

$ TEST_DATABASE_URL=<scratch> uv run pytest -q \
    tests/test_page_sections.py::test_a_page_section_identity_or_position_cannot_change
4 passed, 1 warning in 0.19s
```

The correct body was restored from `ASSERT_PAGE_SECTION_POSITION_SQL` (the pin passes
again) and the scratch database was dropped. The real `leafclutch_test` and `leafclutch`
databases were not altered.

Review-Low runs on 2026-11-28 (same PostgreSQL 18.7 target):

```
$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 6 source files
```

```
$ uv run pytest -q
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
....................................................                     [100%]
340 passed, 4 warnings in 1.74s

$ uv run pytest -q --import-mode=importlib
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
....................................................                     [100%]
340 passed, 4 warnings in 1.49s

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
```

The totals stay 340: the pin test was strengthened, not added. The eighth-function probe
appended a `FUTURE_GUARD_SQL` constant defining `future_guard()` to
`0005_page_sections.py`, ran the pin, and restored the file with
`git checkout -- migrations/versions/0005_page_sections.py`; `git status` then showed only
`tests/test_page_sections.py`. The suite's own `alembic upgrade head` had already run, so
the probe needed no schema change.

```
$ uv run pytest -q tests/test_page_sections.py::test_the_installed_section_functions_pin_their_bodies
>       assert set(SECTION_FUNCTION_BODIES) == migration_function_names(migration)
E       AssertionError: assert {'assert_page...ion_key', ...} == {'assert_page...ion_key', ...}
E         Extra items in the right set:
E         'future_guard'
FAILED tests/test_page_sections.py::test_the_installed_section_functions_pin_their_bodies
1 failed, 1 warning in 0.29s
```

After the restore the same test passed: `1 passed, 1 warning in 0.18s`.

## Review

## Docs updated

- No document is invalidated: this is test-only work, and `DATABASE.md` §Section items and
  §Section copy already describe the committed behaviour and the seven guard functions.
  `DATABASE.md`, `CONTRACT.md`, `ADMIN.md` and OpenAPI are unchanged.
- `Backend/tests/test_page_sections.py`'s module docstring now says which cases commit
  through `database_engine` and why, and it separates the two pins: constraint, index and
  trigger definitions against `DATABASE.md`, function bodies against the migration
  constants.

## Remaining

- Step 3 of the plan is closed: `tests/test_page_sections.py` commits its guard probes and
  pins the seven M5 function bodies exactly.
- The M3/M4 function bodies stay fragment-pinned, as `## Plan` records: their SQL is
  inline in revisions that were already pushed, and duplicating the bodies would add no
  branch coverage beyond the existing mutation proofs.
- The M4 `## Remaining` item L1 is closed by the Step 2 pins. The 0004 work file is not
  edited, per the brief.
- `media_bucket` and `media_mime_length` still have no behavioural test; their installed
  definitions are pinned by the catalog test, as recorded in task 0003's `## Not verified`.
- The deferred Low about the 0003 `## Open questions` wording is superseded here, not
  edited in the 0003 file.

## Next

## Open questions

## Not verified

- The real-commit and exact-body proofs ran on the local PostgreSQL 18.7 container only;
  nothing was run against Supabase or staging.
