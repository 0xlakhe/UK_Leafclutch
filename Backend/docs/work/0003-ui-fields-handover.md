---
task: 0003
title: UI field handover — safety fixes and endpoint regroup
status: in-progress
branch: handover/ui-fields
started: 2026-11-27
updated: 2026-11-27
---

## Goal

Make `Backend/docs/handover/ui-fields.md` safe to hand to a frontend developer, then
regroup it by the endpoint the frontend calls. The first draft (1117 lines at
`4a6b01c`) was reviewed independently and returned five High findings: Editors appeared
able to publish, admin forms used public payload names, the Turnstile token was missing,
C3 gave wrong advice, and the BFF privacy rule was absent. The restructure re-cuts the
same material into four public endpoints and the 48 admin endpoints in `ADMIN.md` §4,
so a reader looking up a call does not have to reconstruct it from screens.

## Acceptance criteria

- [x] H1–H5 fixed exactly as briefed, committed before any restructuring
      (`708368a`).
- [x] The file is ordered by endpoint: conventions, four public endpoints, 48 admin
      endpoints, screen index, build order, limits, shared behaviour, do-not-build,
      open decisions, conflicts/gaps, database-only, source map.
- [x] Every admin endpoint names its request and response fields, auth and role.
- [x] M1–M9 applied: database-only columns moved out, † marks and the testimonial `name`
      field corrected, revoke body and `revocation_note`, header/footer split, C2
      recast, version/pagination/media-role/staff/page-pointer fields added, admin error
      contract, conflicts relabelled, this work file added.
- [x] Lows applied: `seo.noindex` default, no `not_found` on the enquiry form, corrected
      limits sourcing, `hours.summary` 120, C1 advice softened, `replace` an action,
      `uploaded_by` †, enquiry `service` 60 †, `approved_by_email` nullable.
- [x] Every field traces to CONTRACT or ADMIN, or to DATABASE with † and a citation.
- [x] No source document is edited and no other file in the worktree is staged.

## Non-goals

- No code, test, migration or OpenAPI change; the FastAPI service does not exist yet.
- Do not resolve C1, C3, C4 or C7; record both citations and the effect on the UI.
- Do not invent a sort allowlist, a staff-removal route, an invite landing page, a
  working-hours row shape, a multipart part name or a dashboard key.
- Do not edit `Backend/docs/handover/mentor-update.md`, `Frontend/` or `Admin/`.
- Do not push, and do not touch the main checkout at `UK_Leafclutch`.

## Plan

1. Fix the five High findings in the existing 1117-line file and commit
   `fix(handover): correct roles, request fields and the enquiry form`.
2. Rewrite the file in endpoint order, carrying the fixed content, applying M1–M9 and
   the cheap Lows, and adding this work file in the same commit.
3. Verify citations against `ADMIN.md`, `CONTRACT.md` and `DATABASE.md` at `4a6b01c`.

## Work log

### 2026-11-27

- Read `Backend/docs/ADMIN.md` §1–§14, `CONTRACT.md` "The calls" through "Field limits",
  and the `DATABASE.md` tables named by the admin typed bodies.
- **Stage 1.** Added `turnstile_token`, the Turnstile widget states and the no-JavaScript
  fallback; added the BFF boundary block (`X-Client-IP`, no `X-Forwarded-For`, logging
  only id/outcome/hash); added a public-to-admin field mapping table and the flat-column
  rule; added "publish, unpublish and archive are Admin only" to the five affected role
  sentences; changed C3's advice to cap at 40/160. Committed as `708368a`.
- **Stage 2.** Re-cut the file: §2 conventions (shapes, pagination/sort, public and admin
  error envelopes, ETag/412, request-name mapping, cache tags, roles); §3 four public
  endpoints with the ten landing-section tables kept under `/public/page`; §4 the 48
  admin endpoints in twelve groups; §5 screen index; §6 build order; §7 field limits;
  §8 shared behaviour; §9 do-not-build; §10 open decisions; §11 conflicts, drift and
  unspecified; §12 database-only; §13 source map.
- Moved `long_description`, `category` and `working_hours` out of forms into §12.
  Marked `sort_order`, `created_by`, `image_id` and `technologies[].name` with † and
  citations, and used `name` for the testimonial field.
- Split the header/footer sentence: five `nav_label` values are on the section items;
  `footer_links` is a settings child list seeded from them.
- Recast C2 as the `settings_location.phone_hours text` column (the location half of
  C1) and moved C2, C5 and C6 to "drift and gaps"; C1, C3, C4 and C7 remain conflicts.
- Added U15 (sort allowlist), U16 (staff removal) and U17 (invite landing/set-password).
- Corrected source-line citations found while checking: success-body shape
  `ADMIN.md:253-254`, shared item chrome `ADMIN.md:214-216`.

## Decisions made

- **Mapping table, not provisional names.** H2 offered either a mapping table or marking
  every admin form name provisional. The table was chosen because it is directly usable
  and states the flat-column rule once; a provisional mark would leave the developer to
  guess the request key.
- **Child-row names are database tables, marked †.** ADMIN names the typed table and its
  children but not the child array keys. The tables use the DATABASE table name with †
  and say the array key is OpenAPI's (U9), rather than inventing `paragraphs[]` or
  `stages[]` as wire names.
- **C2 is drift, folded under C1.** The brief asks both for the C2 recast and for C2 to
  be relabelled drift; §11.2 states it is the location half of C1 and cites the text
  column, while §11.1 C1 covers both columns.
- **C3 advice is 40/160, not "the Pydantic limit".** The Pydantic limit is built from
  the CONTRACT row, so it would still be 80/200 and the database would refuse the text.
- **Build order is delivery advice, not a requirement.** It depends on the publish and
  media surfaces landing before enquiries and approvals; the source documents do not fix
  an order.
- **Work-file status left `in-progress`.** The orchestrator owns the final status and
  closure; the Review section records the review that was received.

## Files changed

- `Backend/docs/handover/ui-fields.md` — modified (stage 1, then rewritten in stage 2).
- `Backend/docs/work/0002-ui-fields-handover.md` — new.
- `Backend/docs/work/README.md` — index row added.

## Migrations

None. Documentation only.

## Tests

Documentation task; no test suite applies.

- **actual run** `git status --short`, `git diff --stat`, `git log --oneline -3` —
  confirmed only `Backend/docs/handover/ui-fields.md` was modified before stage 1, and
  the stage 1 commit contains one file.
- **actual run** `wc -l Backend/docs/handover/ui-fields.md` — 1117 before stage 1,
  1447 after stage 2.
- **actual run** `grep -n` for the named fields and drift terms — checked `limits.py`,
  `long_description`, `category`, `working_hours`, `client_name`, `not_found` and
  `replace`; all remaining hits are scoped citations or the database-only table.
- **actual run** source-line checks with `awk`/`sed` against `ADMIN.md`, `CONTRACT.md`
  and `DATABASE.md` — corrected two admin line ranges (see Work log).
- **not run** `uv run pytest`, lint and typecheck — no Python or frontend code changed;
  the repository has no documentation linter. The orchestrator's definition of done
  still requires the reviewer; see Remaining.

## Review

### Round 1 — independent review of the first draft (`4a6b01c`, 1117 lines)

No Critical. Five High, all fixed in `708368a`:

| ID | Finding | Fix |
| --- | --- | --- |
| H1 | Editors appeared able to publish on five screens (§3.8, §3.10, §3.13–§3.15) | Added "publish, unpublish and archive are Admin only" to each role sentence. |
| H2 | Admin forms used public names (`primary_cta.label`, `company.legal_name`), which `422` against the flat typed table | Added the mapping table and the flat-column rule; the endpoint rewrite carries them in §2.5. |
| H3 | `turnstile_token` absent from the form, with no load-failure fallback | Added the field, widget states and the site-email fallback. |
| H4 | C3 told the developer to use the Pydantic limit, which is also 80/200 | Changed the advice to cap at 40/160 until reconciled. |
| H5 | BFF privacy rules absent: `X-Client-IP`, no `X-Forwarded-For`, no message/email/raw-address logs | Added the BFF boundary block. |

Outcome: **failed** the first pass on the five High findings; the fixes are the first
commit, so they survive the rewrite.

### Round 2 — the endpoint restructure (this commit)

Applied the M1–M9 and Low findings from the same review. No independent review of the
restructured file has been run yet; the orchestrator dispatches the reviewer after this
commit. **Not run.**

## Docs updated

`Backend/docs/handover/ui-fields.md` only. `ADMIN.md`, `CONTRACT.md`, `DATABASE.md`,
the OpenAPI schema and the ADRs are unchanged, because this task resolves no source
conflict and adds no endpoint.

## Remaining

- Independent review of the restructured file, and a decision on C1, C3, C4 and C7.
- The orchestrator owns the work-file status and `Next`.

## Next

Dispatch the reviewer with this file, the diff `4a6b01c..HEAD` and the cited source
sections. Then decide C1 (phone-hours shape), C3 (40/160 vs 80/200), C4 (create
optionality) and C7 (sign-in route) before any frontend build starts.

## Open questions

- C1: is `phone_hours` one text column (`ADMIN.md:718`, `DATABASE.md:1304-1305`) or the
  object `{summary, timezone}` (`CONTRACT.md:721-728`)? The same question covers
  `settings_location.phone_hours`.
- C3: which pair wins, 80/200 or 40/160?
- C4: are `path` and `slug` optional on create for every kind?
- C7: one `/admin/audit` screen or a separate `/admin/sign-ins`?
- U15–U17: sort allowlist, staff removal, invite landing/set-password.

## Not verified

- No independent review of the restructured document.
- No line-by-line rendering check in a Markdown viewer; table pipe counts were checked by
  script, not by eye in the target CMS/editor.
- The FastAPI service and its generated OpenAPI schema do not exist, so no field name
  could be validated against a live contract.
