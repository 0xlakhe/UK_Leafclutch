---
task: 0007
title: Landing page sections
status: in-progress
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

- [ ] `0005_page_sections` creates, with every column, default, constraint and index from
      `DATABASE.md`:
      - `page_section` (§Section items, `:586-609`): the four checks, both composite
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
- [ ] The three functions and every trigger above are copied verbatim, including the
      exception messages `page section item % needs a page_section row`, `row belongs to
      section %, not %`, `a section reference cannot move between versions or items`,
      `references belong to a page section version`, `published section version is
      immutable`, `section item has no page_section row` and
      `section % cannot reference a %`.
- [ ] `content_item_page_section_row` is a **constraint trigger**, `after insert` on
      `content_item`, `deferrable initially deferred`, for each row.
- [ ] `assert_section_version_item` is attached `before insert or update or delete` on
      `section_version_item`; `assert_section_child` triggers are `before insert or
      update` on their five tables.
- [ ] The seven immutability attachments match §Publication and immutability
      (`:2147-2173`). No later revision's trigger (services, projects, settings, legal)
      appears.
- [ ] A test inserts ten `content_item` rows of kind `page_section` with `page_section`
      rows in PRD §5 order — `hero, proof, services, not-sure, work, process, about,
      testimonials, faqs, contact` at `sort_order` 0–9 — and reads them back in that
      order. This is the M5 exit check.
- [ ] Database tests cover, and fail when the guard is dropped:
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
- [ ] `alembic check` is clean at `0005_page_sections`; `app/models.py` models all eight
      tables including the partial index predicate; `downgrade base` → `upgrade head`
      succeeds.
- [ ] `uv run ruff check .`, `uv run mypy app`, `uv run pytest` (and
      `--import-mode=importlib`) pass; output quoted.
- [ ] Only `Backend/` changes.

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

## Decisions made

## Files changed

## Migrations

## Tests

## Review

## Docs updated

## Remaining

## Next

## Open questions

## Not verified
