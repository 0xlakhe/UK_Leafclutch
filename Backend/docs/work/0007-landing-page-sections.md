---
task: 0007
title: Landing page sections
status: done
branch: prabesh
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Add revision `0005_page_sections`: the eight tables behind the landing page — its ten
`page_section` records, the `section_version` copy row, the five child tables
(`section_paragraph`, `process_stage`, `process_assurance`, `faq_item`,
`contact_next_step`) and `section_version_item` — with their indexes and guards.

This is milestone M5 in `PLAN.md`. The migration revision is `0005_page_sections`; the
work-file number is 0007 because task 0005 was the documents sync and task 0006 the
`archive_content` correction.

The guards installed here:

- `assert_page_section_row` + `content_item_page_section_row`, a deferred constraint
  trigger that fails the commit when a `page_section` item has no `page_section` row.
- `assert_section_child` + five triggers, so a paragraph, stage, assurance, FAQ or next
  step can only attach to the section key that owns it.
- `assert_section_version_item` + `section_version_item_assert`, so a reference can only
  name the item kind its section renders, cannot move, and cannot change under a
  published version.
- `prevent_published_content_mutation` attached to all seven version-keyed tables of this
  revision: `section_version`, the five child tables and `section_version_item`.

`page_section` is item-keyed, not version-keyed, and gets no immutability trigger.

## Acceptance criteria

- [x] `0005_page_sections` creates, with every column, default, constraint and index from
      `DATABASE.md`:
      - `page_section` (§Section items): the three checks, both composite
        foreign keys, both uniques, the primary key and `page_section_page_idx`;
      - `section_version` (§Section copy, `:649-712`): all twelve checks, the primary key
        and the `content_version` cascade;
      - `section_paragraph` (`:733-743`), `process_stage` (`:745-759`),
        `process_assurance` (`:761-775`), `faq_item` (`:777-791`) and
        `contact_next_step` (`:793-807`), each with its sort bound, length checks and
        `(version_id, sort_order)` primary key;
      - `section_version_item` (§Section references, `:856-880`): `section_version_item_pk`,
        all four checks, the composite `(item_id, item_kind)` foreign key, the partial
        unique `section_version_item_order_key` and `section_version_item_lookup_idx`.
- [x] The three functions and every trigger above are copied verbatim, including the
      exception messages `page section item % needs a page_section row`, `row belongs to
      section %, not %`, `a section reference cannot move between versions or items`,
      `references belong to a page section version`, `published section version is
      immutable`, `section item has no page_section row` and
      `section % cannot reference a %`.
- [x] `content_item_page_section_row` is a **constraint trigger**, `after insert` on
      `content_item`, `deferrable initially deferred`, for each row.
- [x] `assert_section_version_item` is attached `before insert or update or delete` on
      `section_version_item`; `assert_section_child` triggers are `before insert or
      update` on their five tables.
- [x] The seven immutability attachments match §Publication and immutability
      (`:2147-2173`). No later revision's trigger (services, projects, settings, legal)
      appears.
- [x] A test inserts ten `content_item` rows of kind `page_section` with `page_section`
      rows in PRD §5 order — `hero, proof, services, not-sure, work, process, about,
      testimonials, faqs, contact` at `sort_order` 0–9 — and reads them back in that
      order. This is the M5 exit check.
- [x] Database tests cover, and fail when the guard is dropped:
      - the deferred constraint trigger: a `page_section` item with no `page_section` row
        fails at commit, and one inserted in the same transaction succeeds;
      - a duplicate `(page_id, section_key)` and a duplicate `(page_id, sort_order)`;
      - each `section_version` key check: a `proof` row with a heading, a `hero` row with
        a `nav_label`, an `about` row with a CTA, a `contact` row with an eyebrow, a
        non-`about` row with an image, and a non-`contact` row with privacy fields are
        refused; valid hero, about and contact rows insert;
      - each `assert_section_child` trigger: an `about` paragraph on a `contact` version,
        a stage on an `about` version, an assurance on `services`, an FAQ on `process`
        and a next step on `faqs` are refused, and the owning key is accepted;
      - `assert_section_version_item`: `services`+`project`, `work`+`service_group`,
        `proof`+`testimonial` and `testimonials`+`proof_figure` are refused; the four
        valid pairings insert; a reference on a published version is refused; moving a
        reference between versions or items is refused; a reference on a
        non-`page_section` version is refused;
      - `section_version_item_order`: a project reference carries a null `sort_order`, and
        a non-project reference carries a non-null one; the partial unique index refuses a
        duplicate order in one version and allows nulls to repeat;
      - editing or deleting a row of each of the seven tables once its version is
        published is refused; the same edit while the version is draft succeeds;
      - cascade: deleting a draft version removes its `section_version`, paragraphs,
        stages, assurances, FAQs, next steps and references; a reference naming an item
        with a live reply is `on delete restrict` as documented;
      - `archived_at`/`archived_by` and `page_section` cascade: deleting a landing-page
        item removes its `page_section` rows.
- [x] `alembic check` is clean at `0005_page_sections`; `app/models.py` models all eight
      tables including the partial index predicate; `downgrade base` → `upgrade head`
      succeeds.
- [x] `uv run ruff check .`, `uv run mypy app`, `uv run pytest` (and
      `--import-mode=importlib`) pass; output quoted.
- [x] Only `Backend/` changes.

## Non-goals

- `assert_section_counts`, `assert_publishable_version` and the publish/unpublish
  functions (`:2258-2322`, `:2324-...`): M11.
- The ten real sections' copy, images and references as data: seeding is M10/M11.
- Services, projects, proof, testimonials, legal pages and settings: M6–M8.
- Views, grants, RLS, storage and endpoints: M12 onwards.

## Plan

Two commits under this one task file, each green, each touching the same revision because
it is unpushed. The split exists to keep the agent inside its step budget; it is not a
schema split.

| Step | Files | Commit |
| --- | --- | --- |
| 1. `page_section` and `section_version` with their index, the deferred constraint trigger and `section_version_immutable`; constraints and trigger tests | `app/models.py`, `migrations/versions/0005_page_sections.py`, `tests/test_page_sections.py`, `README.md` | `feat(db): add the page section tables` |
| 2. The five child tables, `section_version_item`, `assert_section_child`, `assert_section_version_item` and the remaining immutability attachments; the ten-section order test and the guard tests | same files | `feat(db): add the section children and references` |

The revision's down revision is `0004_content_core`. Downgrade drops the triggers, then
the three functions, then the eight tables in reverse dependency order.

## Work log

### 2026-11-27 — part 1: `page_section` and `section_version`

Implemented the first of the two commits planned for this task. `Backend/app/models.py` now
defines `PAGE_SECTION_KEY`, `page_section` and `section_version`.
`Backend/migrations/versions/0005_page_sections.py` creates them with the three
`page_section` checks, both composite foreign keys, both uniques,
`page_section_page_idx`, all twelve `section_version` checks, `assert_page_section_row()`
and its deferred constraint trigger, and `section_version_immutable` reusing
`prevent_published_content_mutation()` from 0004.

`Backend/tests/test_page_sections.py` covers the deferred trigger in both directions, the
page-section constraints and cascades, every `section_version` check with a refusal and a
valid row for each of the ten keys, the image restrict, the draft/published immutability
and the catalog definitions.

Two existing tests had to learn the new schema. `Backend/tests/test_content_spine.py`
compares every trigger on the content tables, and `content_item_page_section_row` is now
one of them. `Backend/tests/test_staff_schema.py` truncates the committed rows its
concurrency tests create, and the new foreign keys make `page_section` and
`section_version` part of that truncate. Both changes are consequences of this slice, not
weakened assertions.

### 2026-11-27 — part 2: the section children and references

Extended revision `0005_page_sections` in place. It is unpushed and nothing outside this
checkout has applied it: `2999fab` holds the part-1 version, and no other database has run
it. `Backend/app/models.py` now also defines `FAQ_STATUS`, `section_paragraph`,
`process_stage`, `process_assurance`, `faq_item`, `contact_next_step` and
`section_version_item`. `Backend/migrations/versions/0005_page_sections.py` creates the six
tables in dependency order, the partial unique `section_version_item_order_key` and
`section_version_item_lookup_idx`, `assert_section_child()` with its five triggers,
`assert_section_version_item()` with `section_version_item_assert`, and the six remaining
`prevent_published_content_mutation()` attachments. Its downgrade drops every new trigger
and function before the six tables, in reverse dependency order, and drops `section_version`
and `page_section` last as before.

`Backend/tests/test_page_sections.py` grows by 39 cases, 295 in the suite. The new tests
cover the M5 exit check (ten `page_section` rows in PRD §5 order read back in that order),
each `assert_section_child` wrong key with the owning key accepted, all four invalid and all
four valid `section_version_item` pairings, the published-version insert refusal, a
reference moving between versions or between items, a reference on a non-`page_section`
version and on a `page_section` version without its `page_section` row, the
project/non-project order rule, the partial unique index and its repeated nulls, the
composite `on delete restrict`, draft-editable/published-frozen on all six tables, the
draft-version cascade, and the catalogue pinning of every constraint, both indexes, all
fourteen trigger event-bit tuples and both new function bodies including every message.

`Backend/tests/test_staff_schema.py`'s cleanup `TRUNCATE` list gains the six tables.
`TRUNCATE` refuses while any table references `content_version` or `content_item`,
regardless of rows. That is a consequence of the new foreign keys, and it is load-bearing:
applying the revision to the test database before the list changed left the concurrency
tests' committed rows behind, and five staff tests failed until the list was extended and
the stale rows were removed.

Mutation proofs, on a scratch copy `leafclutch_scratch_test` created from
`leafclutch_test` and dropped afterwards:

1. Dropping `section_paragraph_section` made the wrong-key test fail with `Failed: DID NOT
   RAISE DBAPIError`; recreating the trigger made it pass (`1 passed`).
2. Dropping `section_version_item_assert` made the wrong-pairing test fail with `Failed:
   DID NOT RAISE DBAPIError`; recreating it made it pass (`1 passed`).
3. The brief's literal "drop `content_item_page_section_row` and weaken
   `assert_page_section_row()`" combination fails first on the missing constraint name
   (`constraint "content_item_page_section_row" does not exist` from `set constraints`), so
   the proof that the rule matters, not the name, keeps the trigger and replaces the
   function body with `return new;`: the deferred test then failed with `Failed: DID NOT
   RAISE DBAPIError`. The migration's function and trigger were restored and the whole file
   passed on the scratch database (`85 passed`).

### 2026-11-27 — review round: hold the page section identity

Applied the review findings to the same revision, still in place: it is unpushed, and
`9cad54d` is the last commit that touches it; no database outside this checkout has applied
it. `app/models.py` is unchanged because the fix is triggers and functions only.

High 1, the "a `page_section` item has its row" invariant held on insert only:
`content_item_page_section_row` now fires `after insert or update of kind`, so an item
cannot become a `page_section` without a row. `assert_page_section_item_kept()` and the
deferred constraint trigger `page_section_row_kept` (`after delete on page_section`) close
the other side with the invariant, not the event: a delete is refused only when the item is
still a `page_section` and no replacement row exists, so a delete-and-reinsert in one
transaction passes. `assert_page_section_position()` and `page_section_immutable`
(`before update on page_section`) freeze `item_id`, `page_id`, `section_key` and
`sort_order`; a no-op update passes. The review's correction added the versions condition
to `assert_page_section_row()`: a `page_section` item that still has a `section_version`
cannot leave the kind, even after its row is deleted in the same transaction.

High 2, the duplicated, mutable, unguarded section key: `assert_section_version_key()` and
`section_version_key_guard` (`before insert or update of section_key`) refuse a version for
a non-`page_section` item, a version without its page row, a key that differs from the
owning row, and any key change. That also closes Medium 2 at the root: a `section_version`
can only exist for a `page_section` item, so `assert_section_child` needs no kind check. A
project version can no longer gain a `section_version`.

Medium 3: `normalise_constraint` in `tests/test_page_sections.py` now keeps PostgreSQL's
parentheses and only lower-cases and collapses whitespace, so a regrouped expression cannot
pass. Every expected definition was copied from PostgreSQL and still matches. The same
change was safe in `tests/test_content_spine.py`, whose expected strings also carry the
parentheses, so it was applied there too.

Lows: an `about` row with a CTA joins the `section_version_hero_ctas` cases; the
landing-page delete test now expects the refusal while its sections exist, and deletes the
section items first before the page; the function-body pins stay fragment checks, recorded
under Remaining with the reason.

Mutation proofs, on a scratch copy `leafclutch_scratch_test` created from
`leafclutch_test` and dropped afterwards:

1. Dropped `section_version_key_guard`: `test_a_section_version_key_must_match_its_section`
   failed with `Failed: DID NOT RAISE DBAPIError`; the restored trigger passed.
2. Replaced `assert_page_section_item_kept()` with `return null;`:
   `test_a_live_page_section_row_cannot_be_deleted` failed with `Failed: DID NOT RAISE
   DBAPIError`; the restored body passed.
3. Regrouped `section_version_hero_ctas` as `(section_key = 'hero' or primary_label is
   null) and ...`: `test_every_documented_constraint_matches_its_definition` failed with
   the two definitions side by side; the restored constraint passed.
4. Removed the versions condition from `assert_page_section_row()`:
   `test_a_section_item_with_versions_cannot_change_kind` failed with `Failed: DID NOT
   RAISE DBAPIError`; the restored function passed, and the whole file passed on the
   scratch database (`105 passed`).

The part-2 open question about `section_version.section_key` is closed by High 2:
`section_version_key_guard` now ties the key to the owning `page_section` row.

### 2026-11-27 — recheck: the row must stay identical

Fixed the first half of the recheck findings in the same revision, still in place and
unpushed (`62fec05` is the last commit). `assert_page_section_item_kept()` now requires the
replacement row to match the deleted row's `page_id`, `section_key` and `sort_order` with
`is not distinct from`; a difference raises `page section item % changed its page_section
row`, while a missing row keeps `page section item % lost its page_section row`. A
delete-and-reinsert is therefore allowed only when the row is identical. In
`assert_page_section_row()`, the needs-row check now reads the item's current state
(`exists (select 1 from content_item where id = new.id and kind = 'page_section')`) rather
than the queued event's `new.kind`, so an item created and deleted in one transaction
passes its deferred insert check; the versions branch is unchanged.

The tests add three changed-reinsert cases (`page_id`, `section_key`, `sort_order`), keep
the identical reinsert, add a create-and-delete transaction, and change the
sections-then-page test to delete both section items and the page before forcing
`content_item_page_section_row, page_section_row_kept immediate`; the page-delete refusal
test stays. The two function-body catalogue pins were updated.

Mutation proofs on `leafclutch_scratch_test` (created from `leafclutch_test`, dropped
afterwards):

1. Presence-only `assert_page_section_item_kept()`: the changed-reinsert test failed with
   `Failed: DID NOT RAISE DBAPIError` (`test_page_sections.py:1078`); the restored function
   passed.
2. The old `new.kind` check in `assert_page_section_row()`: the create-and-delete test
   failed with `page section item <id> needs a page_section row`; the restored function
   passed, and the whole file passed on the scratch database (`109 passed`).

### 2026-11-27 — recheck, second half: a version keeps its item

Fixed the second half of the recheck findings in the same revision, still unpushed
(`f8d74c1` is the last commit). `content_version.item_id` is now frozen for every status:
`prevent_version_item_move()` and `content_version_item_frozen` (`before update of item_id
on content_version`) raise `a version cannot move between items`. A draft version can no
longer move from its `page_section` item to a project, so the reviewer's sequence cannot
reach the paragraph insert, and the §Section copy claim that a version may exist only for a
`page_section` item now holds for drafts too. The guard is a new object in the unpushed
`0005` revision, not an edit to the pushed `0004`; the downgrade drops the trigger and the
function.

The tests add the refused move and the reviewer's sequence (the version still belongs to
the page-section item, its key is unchanged, and a paragraph inserts on it).
`test_content_spine.py`'s trigger inventory gains `content_version_item_frozen`; the
page-sections catalogue also pins its event bits, its `item_id` column and its body.

Mutation proof on `leafclutch_scratch_test` (created from `leafclutch_test`, dropped
afterwards): dropping `content_version_item_frozen` made the move test fail with `Failed:
DID NOT RAISE DBAPIError` (`test_page_sections.py:1399`); recreating it made both new tests
pass.

## Decisions made

- The deferred trigger's `tgdeferrable`/`tginitdeferred` flags and its function body are
  pinned in `tests/test_page_sections.py`; `tests/test_content_spine.py` only gains the
  expected entry so its per-table comparison stays exact.
- The `test_staff_schema.py` cleanup truncates the two new tables explicitly rather than
  using `CASCADE`, so the tables it clears stay visible.
- The brief says "fourteen text columns" but lists thirteen names, and `DATABASE.md`
  §Section copy has the same thirteen; the thirteen are implemented.
- `section_version.section_key` is not tied to `page_section.section_key`: `DATABASE.md`
  defines no such constraint and the brief says not to add one. Recorded under Open
  questions. Superseded by the review round: `section_version_key_guard` now enforces it.
- A published `section_version_item` refuses an edit or delete with `published section
  version is immutable`, from `assert_section_version_item`, not the generic `published
  version content is immutable`: PostgreSQL fires `before` row triggers in name order, and
  `section_version_item_assert` sorts before `section_version_item_immutable`. The tests
  pin the message that actually fires.
- Part-2 mutation proof 3 keeps `content_item_page_section_row` and weakens only
  `assert_page_section_row()`, because dropping the trigger fails on the missing constraint
  name before the function is reached; the kept-trigger run is the one that proves the
  rule.
- The brief's part-1 text says "the four page_section checks"; the table has three, and the
  work log now says three.
- The review round's delete guard tests the invariant, not the delete event: the condition
  also requires that no replacement `page_section` row exists, so a delete-and-reinsert in
  one transaction is allowed while a direct delete and a landing-page cascade are refused.
- `section_version_key_guard` is the root fix for the child guard: since a version can only
  exist for a `page_section` item with a matching key, `assert_section_child` keeps reading
  the version key alone and needs no kind check (Medium 2).
- A `page_section` item with versions cannot leave the kind even after its row is deleted,
  because those versions would be orphaned; `assert_page_section_row()` carries that rule.
- `normalise_constraint` keeps PostgreSQL's parentheses in both catalog test files, so a
  regrouped expression fails; both files' expected definitions already matched the
  parenthesised output.
- The function-body pins remain fragment checks, as in tasks 0003/0004; deferred with the
  review's agreement because the behavioural tests and the mutation proofs cover the
  branches.

## Files changed

- `Backend/app/models.py` — `PAGE_SECTION_KEY`, `page_section`, `section_version`.
- `Backend/migrations/versions/0005_page_sections.py` — new revision.
- `Backend/tests/test_page_sections.py` — new tests, 46 cases.
- `Backend/tests/test_content_spine.py` — expected trigger entry for
  `content_item_page_section_row`.
- `Backend/tests/test_staff_schema.py` — cleanup truncate list gains the two new tables.
- `Backend/README.md` — the two Layout rows name the page-section tables.
- `Backend/docs/work/0007-landing-page-sections.md` — this update.
- Part 2: `Backend/app/models.py` also gains `FAQ_STATUS` and the six child/reference
  tables, `section_paragraph`, `process_stage`, `process_assurance`, `faq_item`,
  `contact_next_step` and `section_version_item`.
- Part 2: `Backend/migrations/versions/0005_page_sections.py` gains the six tables, the two
  indexes, the two functions, the twelve new trigger attachments and the extended
  downgrade.
- Part 2: `Backend/tests/test_page_sections.py` gains 39 cases, 85 in the file.
- Part 2: `Backend/tests/test_staff_schema.py` gains the six child tables in the cleanup
  truncate list.
- Part 2: `Backend/docs/work/0007-landing-page-sections.md` — this update.
- Review round: `Backend/migrations/versions/0005_page_sections.py` gains the update-of-kind
  event, `assert_page_section_item_kept`/`page_section_row_kept`,
  `assert_page_section_position`/`page_section_immutable`,
  `assert_section_version_key`/`section_version_key_guard`, the versions condition in
  `assert_page_section_row` and the extended downgrade.
- Review round: `Backend/tests/test_page_sections.py` gains the guard tests, the
  parenthesis-preserving normaliser, the `about` CTA case, the rewritten landing-page
  delete tests, the new trigger and `tgattr` pins and the three new function-body pins;
  105 cases in the file.
- Review round: `Backend/tests/test_content_spine.py` gains the update bit for
  `content_item_page_section_row` and the parenthesis-preserving normaliser.
- Review round: `Backend/docs/DATABASE.md` documents the new trigger events, the three
  functions, their messages and the corrected invariant wording.
- Review round: `Backend/docs/work/0007-landing-page-sections.md` — this update.
- Recheck: `Backend/migrations/versions/0005_page_sections.py` changes the two function
  bodies (`assert_page_section_row` reads the current item; `assert_page_section_item_kept`
  compares the replacement row); `Backend/docs/DATABASE.md` §Section items follows;
  `Backend/tests/test_page_sections.py` gains the changed-reinsert and create-and-delete
  cases, changes the sections-then-page test and updates the two body pins.
- Recheck: `Backend/docs/work/0007-landing-page-sections.md` — this update.
- Recheck, second half: `Backend/migrations/versions/0005_page_sections.py` gains
  `prevent_version_item_move()` and `content_version_item_frozen`, and its downgrade drops
  them; `Backend/docs/DATABASE.md` §Publication and immutability documents them;
  `Backend/tests/test_page_sections.py` gains the move tests and the catalogue pins;
  `Backend/tests/test_content_spine.py` gains the trigger inventory entry.
- Recheck, second half: `Backend/docs/work/0007-landing-page-sections.md` — this update.

## Migrations

- `0005_page_sections` (`down_revision = '0004_content_core'`) creates `page_section`,
  `section_version`, `page_section_page_idx`, `assert_page_section_row()`,
  `content_item_page_section_row` (constraint trigger, `after insert`, `deferrable
  initially deferred`) and `section_version_immutable` (`before insert or update or
  delete`, reusing `prevent_published_content_mutation()`).
- Downgrade drops both triggers, then the function, then `section_version`, then
  `page_section`. Verified with `alembic downgrade base` → `alembic upgrade head` →
  `alembic current`.
- Part 2 extends the same revision with `section_paragraph`, `process_stage`,
  `process_assurance`, `faq_item`, `contact_next_step` and `section_version_item`, the
  partial unique `section_version_item_order_key`
  (`where sort_order is not null`), `section_version_item_lookup_idx`,
  `assert_section_child()`, `assert_section_version_item()`, the five `*_section`
  triggers, `section_version_item_assert` and the six `*_immutable` triggers.
- The extended downgrade drops the twelve new triggers, then the two functions, then the
  six new tables, then the part-1 objects. The round trip was re-run after the extension:
  `alembic downgrade base` downgraded all five revisions, `alembic upgrade head` upgraded
  all five, and `alembic current` reported `0005_page_sections (head)`.
- The review round extends the same revision further: `content_item_page_section_row` now
  fires `after insert or update of kind`; `page_section_row_kept` is a deferred constraint
  trigger `after delete on page_section`; `page_section_immutable` is `before update`; and
  `section_version_key_guard` is `before insert or update of section_key`. Its downgrade
  drops those three triggers and `assert_page_section_item_kept`,
  `assert_page_section_position` and `assert_section_version_key` before the tables, then
  follows the part-2 order. The round trip was re-run: `alembic downgrade base` downgraded
  all five revisions, `alembic upgrade head` upgraded all five, and `alembic current`
  reported `0005_page_sections (head)`.
- The recheck changes two function bodies only: `assert_page_section_row` checks the item's
  current state, and `assert_page_section_item_kept` compares the replacement row's
  `page_id`, `section_key` and `sort_order`. The triggers, tables and downgrade are
  unchanged. The round trip was re-run with the same result.
- The recheck's second half adds `prevent_version_item_move()` and
  `content_version_item_frozen` (`before update of item_id on content_version`); the
  downgrade drops both before the tables. The round trip was re-run with the same result.

## Tests

Run from `Backend/` on 2026-11-27 against PostgreSQL 18 in Docker (port 5434).

| Command | Result |
| --- | --- |
| `uv run ruff check .` | `All checks passed!` |
| `uv run mypy app` | `Success: no issues found in 6 source files` |
| `uv run pytest -q` | `256 passed, 4 warnings in 1.29s` |
| `uv run pytest -q --import-mode=importlib` | `256 passed, 4 warnings in 1.08s` |
| `uv run alembic check` | `No new upgrade operations detected.` |
| `uv run alembic downgrade base` | all five revisions downgraded |
| `uv run alembic upgrade head` | all five revisions upgraded |
| `uv run alembic current` | `0005_page_sections (head)` |

Mutation check: a scratch copy, `leafclutch_scratch_test`, was created with
`create database leafclutch_scratch_test template leafclutch_test`, and
`content_item_page_section_row` was dropped there. The deferred test then failed:

```
AssertionError: Regex pattern did not match.
  Actual message: '(psycopg.errors.UndefinedObject) constraint
  "content_item_page_section_row" does not exist\n[SQL: set constraints
  content_item_page_section_row immediate]'
```

Restoring the trigger with the migration's `create constraint trigger` made the same test
pass (`1 passed`). The scratch database was dropped; the test database has no committed
rows.

Part 2, run from `Backend/` on 2026-11-27 against PostgreSQL 18 in Docker (port 5434):

| Command | Result |
| --- | --- |
| `uv run ruff check .` | `All checks passed!` |
| `uv run mypy app` | `Success: no issues found in 6 source files` |
| `uv run pytest -q` | `295 passed, 4 warnings in 1.47s` |
| `uv run pytest -q --import-mode=importlib` | `295 passed, 4 warnings in 1.29s` |
| `uv run alembic check` | `No new upgrade operations detected.` |
| `uv run alembic downgrade base` | all five revisions downgraded |
| `uv run alembic upgrade head` | all five revisions upgraded |
| `uv run alembic current` | `0005_page_sections (head)` |

Part-2 mutation proofs on `leafclutch_scratch_test`:

```
tests/test_page_sections.py:1151: Failed: DID NOT RAISE DBAPIError
1 failed, 1 warning in 0.17s
```

after dropping `section_paragraph_section`; the restored trigger gave `1 passed`.

```
tests/test_page_sections.py:1225: Failed: DID NOT RAISE DBAPIError
1 failed, 1 warning in 0.18s
```

after dropping `section_version_item_assert`; the restored trigger gave `1 passed`.

```
tests/test_page_sections.py:788: Failed: DID NOT RAISE DBAPIError
1 failed, 1 warning in 0.18s
```

with `content_item_page_section_row` kept and `assert_page_section_row()` replaced by
`return new;`. Dropping the trigger as well fails earlier with `constraint
"content_item_page_section_row" does not exist` from `set constraints`, which proves the
attachment but not the rule. The restored function and trigger gave `1 passed`, and the
whole file passed on the scratch database (`85 passed`). The scratch database was dropped.

The review round, run from `Backend/` on 2026-11-27 against PostgreSQL 18 in Docker (port
5434):

| Command | Result |
| --- | --- |
| `uv run ruff check .` | `All checks passed!` |
| `uv run mypy app` | `Success: no issues found in 6 source files` |
| `uv run pytest -q` | `315 passed, 4 warnings in 1.52s` |
| `uv run pytest -q --import-mode=importlib` | `315 passed, 4 warnings in 1.38s` |
| `uv run alembic check` | `No new upgrade operations detected.` |
| `uv run alembic downgrade base` | all five revisions downgraded |
| `uv run alembic upgrade head` | all five revisions upgraded |
| `uv run alembic current` | `0005_page_sections (head)` |

Review-round mutation proofs on `leafclutch_scratch_test`:

```
tests/test_page_sections.py:1269: Failed: DID NOT RAISE DBAPIError
1 failed, 1 warning in 0.26s
```

after dropping `section_version_key_guard`; the restored trigger gave `1 passed`.

```
tests/test_page_sections.py:1004: Failed: DID NOT RAISE DBAPIError
1 failed, 1 warning in 0.17s
```

after replacing `assert_page_section_item_kept()` with `return null;`; the restored body
gave `1 passed`.

```
E     {'section_version_hero_ctas': ('c', "check ((((section_key = 'hero'::page_section_key) or (primary_label is null)) and (primary_href is null) and (secondary_label is null) and (secondary_href is null)))")} != {'section_version_hero_ctas': ('c', "check (((section_key = 'hero'::page_section_key) or ((primary_label is null) and (primary_href is null) and (secondary_label is null) and (secondary_href is null))))")}
FAILED tests/test_page_sections.py::test_every_documented_constraint_matches_its_definition
1 failed, 1 warning in 0.27s
```

after regrouping `section_version_hero_ctas`; the restored constraint gave `1 passed`.

```
tests/test_page_sections.py:1332: Failed: DID NOT RAISE DBAPIError
1 failed, 1 warning in 0.19s
```

after removing the versions condition from `assert_page_section_row()`; the restored
function passed and the whole file passed on the scratch database (`105 passed`). The
scratch database was dropped.

The recheck, run from `Backend/` on 2026-11-27 against PostgreSQL 18 in Docker (port 5434):

| Command | Result |
| --- | --- |
| `uv run ruff check .` | `All checks passed!` |
| `uv run mypy app` | `Success: no issues found in 6 source files` |
| `uv run pytest -q` | `319 passed, 4 warnings in 1.43s` |
| `uv run pytest -q --import-mode=importlib` | `319 passed, 4 warnings in 1.40s` |
| `uv run alembic check` | `No new upgrade operations detected.` |
| `uv run alembic downgrade base` | all five revisions downgraded |
| `uv run alembic upgrade head` | all five revisions upgraded |
| `uv run alembic current` | `0005_page_sections (head)` |

Recheck mutation proofs on `leafclutch_scratch_test`:

```
E   Failed: DID NOT RAISE DBAPIError
tests/test_page_sections.py:1078: Failed: DID NOT RAISE DBAPIError
1 failed, 1 warning in 0.18s
```

after replacing `assert_page_section_item_kept()` with the presence-only body; the restored
function gave `3 passed`.

```
E   psycopg.errors.RaiseException: page section item <id> needs a page_section row
FAILED tests/test_page_sections.py::test_a_page_section_item_created_and_deleted_in_one_transaction_passes
1 failed, 1 warning in 0.24s
```

after restoring the old `new.kind` check in `assert_page_section_row()`; the restored
function passed and the whole file passed on the scratch database (`109 passed`). The
scratch database was dropped.

The recheck's second half, run from `Backend/` on 2026-11-27 against PostgreSQL 18 in
Docker (port 5434):

| Command | Result |
| --- | --- |
| `uv run ruff check .` | `All checks passed!` |
| `uv run mypy app` | `Success: no issues found in 6 source files` |
| `uv run pytest -q` | `322 passed, 4 warnings in 1.50s` |
| `uv run pytest -q --import-mode=importlib` | `322 passed, 4 warnings in 1.40s` |
| `uv run alembic check` | `No new upgrade operations detected.` |
| `uv run alembic downgrade base` | all five revisions downgraded |
| `uv run alembic upgrade head` | all five revisions upgraded |
| `uv run alembic current` | `0005_page_sections (head)` |

Mutation proof: dropping `content_version_item_frozen` on `leafclutch_scratch_test` made
the move test fail:

```
E   Failed: DID NOT RAISE DBAPIError
tests/test_page_sections.py:1399: Failed: DID NOT RAISE DBAPIError
1 failed, 1 warning in 0.18s
```

Recreating the trigger made both new tests pass (`2 passed`). The scratch database was
dropped.

Real-commit evidence. The final recheck ran these against a real `BEGIN … COMMIT` on a
scratch copy at `0005_page_sections`, and the orchestrator independently ran the validation
harness:

- delete a `hero` row and reinsert with a changed `page_id`, `section_key` or `sort_order`:
  each failed at `COMMIT` with `page section item … changed its page_section row`; the old
  `hero|0` row remained;
- identical delete-and-reinsert committed, one row;
- insert a section item plus its row, delete the item, commit: no error, zero rows;
- two section items with rows, versions, section copies and a paragraph; delete the items,
  then the landing page, commit: all rows gone;
- a draft version moved to a project is refused with `a version cannot move between
  items`; after rollback the version still belongs to the page-section item and its key is
  unchanged, and a paragraph inserts;
- the validation harness on a fresh `postgres:18`: 58 SQL blocks applied, block 57 skipped
  for `cron.schedule`, 46 public tables, 18 PASS, exit 0, including the
  archive-with-live-section phase.

The suite itself still exercises deferred failures through `set constraints … immediate`
and rolls back; these real-commit runs are recorded evidence, not suite tests.

## Review

Three review rounds with one independent reviewer session, plus a final delta recheck.

Round 1: two High and three Medium. High 1 — the "a `page_section` item has its row"
invariant was insert-only, so a kind update, a direct row delete or a landing-page cascade
left a section rowless. High 2 — `section_version.section_key` was duplicated and
unguarded, so a version's key could disagree with its section; the child and reference
guards read different copies. Medium 1 — `page_section` had no position guard. Medium 2 —
`assert_section_child` did not check the owning item kind. Medium 3 — the catalog
normaliser stripped parentheses, so a regrouping could pass. Fixed in `62fec05`.

Round 2: one High and two Medium. High — delete-and-reinsert only proved that *a* row
existed, so the key, order or page could change. Medium — the deferred insert event
rejected a valid same-transaction create-and-delete, and the sections-then-page test did
not prove the commit path. Medium — a draft `content_version` could move to another item,
carrying its typed rows. Fixed in `f8d74c1` and `f458a4f`.

Round 3: no Critical, High or Medium. Three Lows: force both constraints in the
create-and-delete test, record the real-commit evidence, and qualify the version-item
wording. Fixed in `970eccd`.

Evidence: 322 tests in both modes, ruff, mypy, `alembic check` clean at
`0005_page_sections`, the migration round trip, and the validation harness on a fresh
PostgreSQL 18 — 58 SQL blocks, 46 public tables, 18 PASS, exit 0. The reviewer reproduced
every mutation proof: dropping the key guard, the row-kept function, the versions
condition or the version-item trigger each fails its test with `DID NOT RAISE`; the
regrouped constraint fails the catalog test.

Outcome: **accepted**. No open Critical, High or Medium. Two Lows are deferred with
reasons: the function-body pins remain fragment checks, and the suite exercises deferred
failures through `set constraints … immediate` while the real-commit runs are recorded
evidence.

## Docs updated

- `Backend/README.md`: the `app/models.py` and `tests/` Layout rows now name the
  page-section tables and schema.
- No change to `DATABASE.md`, `CONTRACT.md`, `ADMIN.md` or OpenAPI: the schema was already
  documented in `DATABASE.md` §Section items, §Section copy and §Publication and
  immutability, and this slice exposes no endpoint.
- Part 2 needs no further documentation change: `DATABASE.md` §Lists inside a section,
  §Section references and §Publication and immutability already specify the six tables and
  their guards, and the slice still exposes no endpoint, so `CONTRACT.md`, `ADMIN.md` and
  OpenAPI do not move.
- Correction (review round): the two "no documentation change" lines above are superseded.
  `DATABASE.md` §Section items now documents `content_item_page_section_row` on
  `insert or update of kind`, `page_section_row_kept`, `page_section_immutable` and the
  versions condition in `assert_page_section_row`; §Section copy documents
  `section_version_key_guard` and the key rule; the Migrations table row for
  `0005_page_sections` names the five child tables and the guards. `CONTRACT.md`,
  `ADMIN.md` and OpenAPI still do not move: no endpoint is exposed.
- The recheck rounds leave that documentation current: §Section items describes the
  identity and current-state checks, and §Publication and immutability gains
  `prevent_version_item_move` and `content_version_item_frozen`.

## Remaining

- One review Low is deferred as instructed: the function-body catalogue checks remain
  fragment checks rather than exact `pg_get_functiondef` comparisons, as in tasks
  0003/0004. The reason is recorded with the review: the behavioural tests and the four
  mutation proofs cover each branch.
- The first half of the recheck findings is fixed in this commit; nothing else is open for
  that half. The independent re-review and the orchestrator's decision are the next gate.
- The second half is fixed too: `content_version_item_frozen` closes the draft-version
  move. No code, test or migration work is open for task 0007.

## Next

M6 — the catalogue, revisions `0006_services` to `0008_proof`: service groups and services,
projects with images and technologies, proof figures, testimonials and client logos, their
triggers and indexes, and the ten-section references they feed.
## Open questions

- None open. The earlier question about `section_version.section_key` is resolved: the
  review round added `section_version_key_guard`, so the key is tied to the owning
  `page_section` row and cannot change.

## Not verified

- The suite itself does not commit: it still exercises deferred failures through
  `set constraints … immediate` inside a transaction that rolls back. The real-commit
  behaviour is covered by the recorded runs under Tests, not by a suite test.
- `alembic downgrade base` was run only on the local development database; there is no
  staging or production database in this environment.
- The part-2 guards were exercised through SQL only: no application code reads or writes
  the six tables yet, so there is no service-level path to verify, and the part-2 runs were
  against the local PostgreSQL 18 container only.
- The review-round mutation proofs and the round trip ran on this checkout's local
  PostgreSQL 18 container; nothing was run against staging or production.

