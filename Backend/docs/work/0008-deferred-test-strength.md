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
  is 59 tests; the suite is 326.
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

## Files changed

- `Backend/tests/test_media_schema.py` — parenthesis-preserving `normalise_constraint`,
  corrected comments, the empty-evidence-alt test, the two timestamp update-path refusals
  and the equal-timestamp update/promotion acceptance test
- `Backend/tests/test_content_spine.py` — the L1 behavioural pins: published-version
  deletion with SEO and after unpublishing, the live-pointer item cascade, restore and
  half-clear archive flags, and the staff/media restrict foreign keys, plus the local
  `media_values`/`add_media` helper
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

## Review

## Docs updated

## Remaining

- Step 3 of the plan — the page-section real-commit and exact-body pins — is a later
  commit of task 0008.
- The M4 `## Remaining` item L1 is closed by the Step 2 pins. The 0004 work file is not
  edited, per the brief.
- `media_bucket` and `media_mime_length` still have no behavioural test; their installed
  definitions are pinned by the catalog test, as recorded in task 0003's `## Not verified`.
- The deferred Low about the 0003 `## Open questions` wording is superseded here, not
  edited in the 0003 file.

## Next

## Open questions

## Not verified
