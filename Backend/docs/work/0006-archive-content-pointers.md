---
task: 0006
title: Archive a landing page whose sections are still live
status: in-progress
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

- [ ] In `DATABASE.md`, `archive_content`'s condition is true when the item has its own
      pointer **or** the item is a `landing_page` and any `page_section` row for it has a
      pointer. The call remains `_unpublish_internal(p_item_id, p_actor, false)`.
- [ ] The rest of the body is unchanged: the locking read, both existing refusals, the
      single `archive` audit row, and the section archive update.
- [ ] The two `DATABASE.md` prose passages — the delete-paths paragraph and the archive
      guard paragraph — say that archiving a landing page unpublishes a live section even
      when the page itself is not live.
- [ ] `ADMIN.md`'s **Archive** bullet says the same in one clause, without changing any
      other rule.
- [ ] No table, constraint, index, other function or migration changes; no application or
      test code changes.
- [ ] `uv run ruff check .`, `uv run mypy app`, `uv run pytest -q` and
      `uv run alembic check` are unchanged and quoted; `git diff --check` is silent.
- [ ] Only `Backend/` changes.

## Non-goals

- Installing or testing `archive_content`: it is M11. `page_section` does not exist until
  M5, so the branch cannot be exercised yet.
- Changing `_unpublish_internal`, `content_item_archive_guard` or any M4 object.
- The M11 test itself. It is already required in `PLAN.md` M11.
- Patching `~/Work/website-build`; the design workspace syncs from this repository.

## Plan

| File | Purpose |
| --- | --- |
| `Backend/docs/DATABASE.md` | The `archive_content` condition and two prose passages |
| `Backend/docs/ADMIN.md` | One clause in the Archive bullet |
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

## Decisions made

- Corrected the documented function's precondition rather than `_unpublish_internal` or
  `content_item_archive_guard`: the guard's rule is right, and `_unpublish_internal`
  already deletes every section pointer. Only the call condition was wrong.
- Kept the M11 test requirement in `Backend/docs/work/PLAN.md` M11 (`:108-112`). It is
  the milestone that installs the function; no test can exercise it on this branch yet.
- Left the work index row unchanged; it already names task 0006.

## Files changed

- Modified: `Backend/docs/DATABASE.md` — `archive_content` condition, delete-paths
  paragraph, archive-guard paragraph.
- Modified: `Backend/docs/ADMIN.md` — **Archive** bullet.
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

No SQL test exercises the documented `archive_content` body: this task changes the
authoritative documentation only.

## Review

## Docs updated

- `Backend/docs/DATABASE.md` — documented `archive_content` condition and the two prose
  passages.
- `Backend/docs/ADMIN.md` — **Archive** bullet.
- `Backend/docs/work/PLAN.md` — no change; the M11 test requirement was already recorded.
- `Backend/docs/work/README.md` — no change; the index row already existed.

## Remaining

- M11 installs `archive_content`; its test with the page pointer absent and one section
  pointer present remains required by `Backend/docs/work/PLAN.md` M11.
- `~/Work/website-build` needs to sync `DATABASE.md` and `ADMIN.md`; this repository is
  now ahead. The design workspace is out of bounds for this task.

## Next

## Open questions

## Not verified

- The corrected `archive_content` has not been executed against PostgreSQL. The function
  is not installed until M11 and `page_section` does not exist until M5, so neither the
  guard bypass nor the section archive update can be demonstrated on this branch.
- The design workspace was compared read-only with `cmp` before the edit but was not
  updated.
