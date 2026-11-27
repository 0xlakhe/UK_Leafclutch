---
task: 0006
title: Archive a landing page whose sections are still live
status: done
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Correct the documented `archive_content` so a landing page can be archived when its own
publication pointer is already gone but one or more of its sections is still live.

Discovered by the task 0004 recheck. The M4 `content_item_archive_guard` refuses any
update that archives an item while a `content_publication` row names it. `archive_content`
archives the page's sections in the same transaction, so a live section pointer makes the
whole archive fail. The guard is right; the function's precondition is wrong: it calls
`_unpublish_internal` only when the **page** itself has a pointer, and `_unpublish_internal`
is what deletes the section pointers.

`archive_content` is documented, not installed: it arrives in M11. This task changes the
authoritative SQL before it is implemented, not the database.

## Acceptance criteria

- [x] In `DATABASE.md`, `archive_content`'s condition is true when the item has its own
      pointer **or** the item is a `landing_page` and any `page_section` row for it has a
      pointer. The call remains `_unpublish_internal(p_item_id, p_actor, false)`.
- [x] The rest of the body is unchanged: the locking read, both existing refusals, the
      single `archive` audit row, and the section archive update.
- [x] The two `DATABASE.md` prose passages — the delete-paths paragraph and the archive
      guard paragraph — say that archiving a landing page unpublishes a live section even
      when the page itself is not live.
- [x] `ADMIN.md`'s **Archive** bullet says the same in one clause, without changing any
      other rule.
- [x] No table, constraint, index, other function or migration changes; no application
      code changes, and the runbook harness is the only test change.
- [x] `uv run ruff check .`, `uv run mypy app`, `uv run pytest -q` and
      `uv run alembic check` are unchanged and quoted; `git diff --check` is silent.
- [x] The runbook harness (`docs/runbooks/database-validation.sql`) gains a phase that
      proves the fix: publish only the hero so the page pointer is absent and the hero
      pointer present, archive the page, and assert 11 archived, no pointers, one page
      `unpublish` audit row, one `{page:/,routes}` revalidation row and no new draft. The phase
      fails against the pre-fix body from `208188a^` and passes against the corrected one;
      both runs are quoted.
- [x] Only `Backend/` changes.

## Non-goals

- Installing `archive_content` in the application database: it is M11. The runbook harness
  exercises the documented body now; installation and the application-database test are
  M11.
- Changing `_unpublish_internal`, `content_item_archive_guard` or any M4 object.
- The M11 test in the application database. It repeats the runbook case and is required
  by `PLAN.md` M11.
- Patching `~/Work/website-build`; the design workspace syncs from this repository.

## Plan

| File | Purpose |
| --- | --- |
| `Backend/docs/DATABASE.md` | The `archive_content` condition and two prose passages |
| `Backend/docs/ADMIN.md` | One clause in the Archive bullet |
| `Backend/docs/runbooks/database-validation.sql` | The regression phase for the page-pointer-absent case |
| `Backend/docs/runbooks/database-validation.md` | The recorded run and its counts |
| `Backend/docs/work/0006-archive-content-pointers.md` | This file |
| `Backend/docs/work/README.md` | Index row |

The condition to install:

```sql
  if exists (select 1 from content_publication where item_id = p_item_id)
     or (
       v_kind = 'landing_page'
       and exists (
         select 1
         from page_section ps
         join content_publication cp on cp.item_id = ps.item_id
         where ps.page_id = p_item_id
       )
     ) then
    perform _unpublish_internal(p_item_id, p_actor, false);
  end if;
```

`_unpublish_internal` already deletes every section pointer for a landing page and
computes the page tags from `content_item.path`, so it behaves correctly when the page
itself has no pointer.

## Work log

### 2026-11-27

- Read `Backend/docs/DATABASE.md` `_unpublish_internal` (`:3287-3378`) and
  `archive_content` (`:3396-3445`), plus the delete-paths and archive-guard prose.
  Confirmed that `_unpublish_internal` deletes every section pointer for a landing page
  and computes the page tags from `content_item.path`, so it works when the page has no
  pointer of its own.
- Replaced the `archive_content` condition in `Backend/docs/DATABASE.md` with the
  pointer-or-live-section test from the brief. The locking read, both refusals,
  `p_create_draft` false, the single `archive` audit row and the section archive update
  are unchanged.
- Added the landing-page qualification to the delete-paths paragraph and the
  archive-guard paragraph in `Backend/docs/DATABASE.md`, and one clause to the
  **Archive** bullet in `Backend/docs/ADMIN.md`.
- No application code, test, table, constraint, index, other function or migration
  changed. `archive_content` is documented only: it is installed in M11, and
  `page_section` arrives in M5, so the branch cannot be tested yet.
- `cmp` showed `Backend/docs/DATABASE.md` and `Backend/docs/ADMIN.md` byte-identical to
  `~/Work/website-build/docs/` before this change (both returned `0`). They are now ahead
  of that workspace until it syncs.

### 2026-11-27 review round

- Added a new DO phase to `Backend/docs/runbooks/database-validation.sql` after the
  archive/restore block. It publishes only the hero, archives the page, asserts 11 items
  archived, every pointer gone, one new page-named `unpublish` audit row, one new
  `archive` audit row, one new `{page:/,routes}` revalidation row and no new open draft,
  then restores the page and checks all 11 flags.
- Updated `Backend/docs/runbooks/database-validation.md` with the counts the extraction
  actually prints (`58 SQL blocks`, 46 public tables), block 57 as the skipped
  `cron.schedule`, the 18 PASS/5 DO output with the new psql line numbers, and the third
  27 November 2026 run.
- Corrected the audit and revalidation wording in `Backend/docs/DATABASE.md` and
  `Backend/docs/ADMIN.md`: archive writes the rows when it removes a live pointer, the
  item's own or a landing page's section's, and the `unpublish` row names the archived
  item. Widened the ADMIN **Archive** bullet, added the harness case to the
  migration-test list, and noted the concurrent-section-publish caveat by the archive
  guard.
- Correction to the first entry: the claim that `archive_content` "cannot be tested yet"
  was wrong. The runbook harness applies every fenced `sql` block from `DATABASE.md`,
  except the skipped `cron.schedule` block, to a scratch PostgreSQL and executes the
  documented function; the new phase is the regression test. M11 still installs it in the
  application database.
- Correction: the work index row was not at HEAD when the first commit was made; the
  orchestrator committed it in `cc891c3`.

### 2026-11-27 final correction

- Changed the new phase's PASS wording from "no draft" to "no new draft" in
  `Backend/docs/runbooks/database-validation.sql`, its recorded output in
  `Backend/docs/runbooks/database-validation.md`, and the quote in this file. The
  delete-refusal phase leaves an open draft on the `work` section (`:302-303`), so the
  pre-archive open-draft count is one; the assertion at `:485-489` compares before and
  after and proves no new draft. No assertion or other line changed.
- Corrected the two sentences that said the harness applies "every fenced SQL block" to
  note the skipped `cron.schedule` block.
- Re-ran the harness on a fresh `postgres:18` container: `psql` exited `0`, with 18
  `PASS` notices and five `DO` blocks; the new line is
  `PASS archive page with a live section and no page pointer: 11 archived, pointers
  gone, one page unpublish audit row, page:/ and routes cache tag, no new draft`.

## Decisions made

- Corrected the documented function's precondition rather than `_unpublish_internal` or
  `content_item_archive_guard`: the guard's rule is right, and `_unpublish_internal`
  already deletes every section pointer. Only the call condition was wrong.
- Kept the M11 test requirement in `Backend/docs/work/PLAN.md` M11 (`:108-112`). It is
  the milestone that installs the function; the runbook harness now exercises the
  documented body, and M11 repeats the case in the application database.
- Proved the fix with the existing documented-SQL harness rather than a new migration
  test: it already applies every fenced `sql` block in `DATABASE.md`, except the skipped
  `cron.schedule` block, and calls `archive_content`, so the new phase fails on the
  pre-fix body and passes on the fix.
- Left the work index row to the orchestrator; it was committed in `cc891c3`, after this
  task's first commit, so it was not at HEAD then.

## Files changed

- Modified: `Backend/docs/DATABASE.md` — `archive_content` condition, delete-paths
  paragraph, archive-guard paragraph, revalidation and archive prose, migration-test list.
- Modified: `Backend/docs/ADMIN.md` — **Archive** bullet and the two audit/revalidation
  passages.
- Modified: `Backend/docs/runbooks/database-validation.sql` — new regression phase.
- Modified: `Backend/docs/runbooks/database-validation.md` — counts, expected output and
  run number.
- Added: `Backend/docs/work/0006-archive-content-pointers.md` — this work file.

## Migrations

None.

## Tests

All commands run from `Backend/`, actual output quoted:

- `uv run ruff check .` → `All checks passed!`
- `uv run mypy app` → `Success: no issues found in 6 source files`
- `uv run pytest -q` → `210 passed, 4 warnings in 1.22s`
- `uv run alembic check` → `No new upgrade operations detected.`
- `uv run alembic current` → `0004_content_core (head)`
- `git diff --check` → silent, exit `0`.
- `git status --short` → `M docs/ADMIN.md`, `M docs/DATABASE.md`,
  `M docs/work/README.md`, `?? docs/work/0006-archive-content-pointers.md` before the
  commit; `README.md` belongs to the orchestrator and is not staged.

### 2026-11-27 review round

The runbook harness in `Backend/docs/runbooks/database-validation.sql` now exercises the
documented function; the two runs below are the regression proof.

Pre-fix run on a fresh `postgres:18` container (`lc-pg18-validate`), with the
`create or replace function archive_content` block from `208188a^` replacing block 47:

- Applied the auth/storage stubs and all 58 extracted blocks with the runbook's loop;
  block 57 (`cron.schedule`) skipped.
- `docker exec lc-pg18-validate psql -U postgres -d lc -f /tmp/database-validation.sql`
  exited `3`:

```
## archive page with a live section and no page pointer
psql:/tmp/database-validation.sql:500: ERROR:  archive removes the publication pointer first
CONTEXT:  PL/pgSQL function prevent_archived_with_publication() line 8 at RAISE
```

Corrected run on a fresh `postgres:18` container:

- Extraction printed `58 SQL blocks`; the apply step skipped
  `skip /tmp/lc-blocks/57.sql (no pg_cron)`; `pg_tables` count printed `46`.
- The same psql command exited `0`:

```
## archive page with a live section and no page pointer
psql:/tmp/database-validation.sql:500: NOTICE:  PASS archive page with a live section and no page pointer: 11 archived, pointers gone, one page unpublish audit row, page:/ and routes cache tag, no new draft
DO
```

The corrected run prints 18 `PASS` notices, two `INSERT 0 1` lines and five `DO` blocks.
The scratch container `lc-pg18-validate` was removed afterwards. A final corrected run
after the documentation and assertion edits reproduced `58 SQL blocks`, `46` tables,
18 `PASS`/5 `DO` and exit `0`.

Final application checks before the commit:

- `uv run ruff check .` → `All checks passed!`
- `uv run mypy app` → `Success: no issues found in 6 source files`
- `uv run pytest -q` → `210 passed, 4 warnings in 1.13s`
- `uv run alembic check` → `No new upgrade operations detected.`
- `uv run alembic current` → `0004_content_core (head)`
- `git diff --check` → silent, exit `0`.

## Review

Two rounds with one independent reviewer session; the second round re-ran the harness on
fresh PostgreSQL 18 databases.

Round 1: one High — the fix had no regression test, and the work file falsely claimed the
documented body could not be exercised before M11, when the runbook harness applies every
`DATABASE.md` SQL block and calls `archive_content`. One Medium — the audit and
revalidation wording read as if the `unpublish` row named the live section, while it names
the archived page. Three Low: the ADMIN archive bullet was too narrow, the migration-test
list omitted the case, and a concurrent section publish can still trip the guard.

Fixed in `c48cb81` and `725ec54`. The harness now publishes only the hero, asserts the page
pointer is absent and the hero pointer present, archives the page and asserts 11 archived,
no pointers, one new page-named `unpublish` row, one new `archive` row, one
`{page:/, routes}` revalidation row and no new draft. The reviewer reproduced both
directions: the pre-fix body fails the phase with
`archive removes the publication pointer first`; the corrected body passes with exit 0.
The audit wording, the migration-test list and the concurrency caveat are in `DATABASE.md`
and `ADMIN.md`.

Round 2: the High and the Medium are closed; the Lows are fixed or recorded. Two accuracy
items from the recheck — "no draft" where the assertion proves "no new draft", and the
work file's remaining non-goals claim — are fixed.

Verified by the orchestrator: 210 tests, ruff, mypy, `alembic check` clean at
`0004_content_core`, and the harness PASS line quoted in the work file.

Outcome: **accepted**. No open Critical, High or Medium.

## Docs updated

- `Backend/docs/DATABASE.md` — documented `archive_content` condition and the two prose
  passages.
- `Backend/docs/ADMIN.md` — **Archive** bullet and audit/revalidation wording.
- `Backend/docs/runbooks/database-validation.sql` — new regression phase.
- `Backend/docs/runbooks/database-validation.md` — extraction counts, expected output,
  PASS/DO counts and run number.
- `Backend/docs/work/PLAN.md` — no change; the M11 test requirement was already recorded.
- `Backend/docs/work/README.md` — no change in this task; the index row was committed by
  the orchestrator in `cc891c3`.

## Remaining

- M11 installs `archive_content`; its test with the page pointer absent and one section
  pointer present remains required by `Backend/docs/work/PLAN.md` M11. The runbook harness
  is the pre-install regression proof.
- A concurrent section publish can still trip the archive guard, because the condition
  reads `page_section` and `content_publication` without locking the section rows. The
  archive rolls back cleanly and is safe to retry; the harness does not exercise this
  race.
- The new phase's draft assertion is a delta, not zero: the delete-refusal phase leaves
  an open draft on the `work` section, so the pre-archive count is one. The PASS wording
  now says "no new draft"; no assertion changed.
- `~/Work/website-build` needs to sync `DATABASE.md` and `ADMIN.md`; this repository is
  now ahead. The design workspace is out of bounds for this task.

## Next

M5 — task 0007, revision `0005_page_sections`: the landing page section tables, split into
two green commits; part one builds `page_section` and `section_version`.
## Open questions

## Not verified

- The function is not installed in the application database until M11. The runbook
  harness executed the documented body against scratch PostgreSQL 18 and proved the
  pre-fix failure and the corrected pass; M11's installation is still untested.
- The concurrent section publish race is documented but not exercised; the harness is
  sequential.
- The design workspace was compared read-only with `cmp` before the first edit but was not
  updated.
