---
task: 0003
title: UI field handover — safety fixes and endpoint regroup
status: done
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

### 2026-11-27 — round 2 review

The independent review of `f2f5bcc` returned no Critical and no High: four Medium and
twelve Low findings. All are fixed in this commit. The outcome is logged here because
`## Review` belongs to the orchestrator.

- **M1** — the §2.5 mapping table presented `section_paragraph[]`,
  `settings_address_line[]`, `settings_location[]`, `settings_location_address_line[]`
  and `settings_footer_link[]` as admin request keys. They are database tables: each row
  now says "rows †", and a note states that the array key is OpenAPI's (U9), as §4.3.1
  already said.
- **M2** — §3.1 promised "landing or legal" and documented only the landing shell. Added
  §3.1.12 with the legal payload (`type`, `path`, `revision`, `published_at`, `seo`,
  `title`, `updated_on`, `effective_on`, `blocks[]`), including `updated_on`, which was
  absent from the whole document; §4.3.1 cross-refers for the derived fields.
- **M3** — the Files changed list named `0002-ui-fields-handover.md`; corrected to
  `0003`, matching `README.md`.
- **M4** — `GET /approvals` was missing from §5. It is now on the `/admin/proof` row,
  with a note that there is no `/admin/approvals` route and that `POST /auth/sign-out`
  is a header action.
- **L5** — three `DATABASE.md` citations corrected: `service_version.sort_order`
  884→883, `project_version.sort_order` 970→963, `project_image` 1003-1015→995-1003.
  A fourth in the same block, `project_technology` 990-1000→983-993, was found while
  checking.
- **L6** — `GET /preview?path=` became `GET /preview` with `path` in the request column,
  in §4.12 and §5.
- **L7** — unpublish now leaves the existing in-review version as well as a draft copy
  (`ADMIN.md:522`), corrected in §4.4 and §8.
- **L8** — the revoke `note` is a field row capped at `500 †` (`DATABASE.md:1548`).
- **L9** — the media text now says ADMIN lists `replace` as a state and explains that it
  is an action creating a new row; recorded as C8 drift in §11.2.
- **L10** — U7 now says ADMIN names no row fields and DATABASE names the columns (§12).
- **L11** — §4.11 and U14 separate the §3 screen route (undefined) from
  `GET /revalidation` (defined in §4, `ADMIN.md:363`).
- **L12** — the live privacy notice is attributed to the landing-page gate
  (`CONTRACT.md:488`), not the contact section (`:491`).
- **L13** — C6 and C7 are now both conflicts; C6 moved from §11.2 to §11.1.
- **L14** — this file logged 1,447 lines and `f2f5bcc` is 1,450; corrected, and the final
  count is 1,501.
- **L15** — the media `role` cites `version_media` (`DATABASE.md:4026-4046`) and notes
  that ADMIN names it only as a request filter (`ADMIN.md:343`).
- **L16** — the approval `state` key and its values are marked provisional.

Final document: 1,501 lines. Every table's pipe count was checked by script; the cited
`DATABASE.md` line numbers were re-read. No Critical or High remains.

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
- **M2 is a table, not a cross-reference.** The reviewer allowed either; the table keeps
  the legal payload in the same shape as the landing payload and puts `updated_on` in
  front of a developer, while the edit rules stay in §4.3.1 and the block limits are not
  copied twice in full.
- **C6 joins C7 as a conflict (L13).** L13 requires C6 and C7 to share a classification.
  C7 was already a conflict and the brief's mentor note keeps it in the conflict set, so
  C6 moved up from drift/gap instead of demoting C7. The final set is C1, C3, C4, C6 and
  C7; C2, C5 and the new C8 are drift. This makes the brief's phrase "C2/C5/C6 as
  drift/gap" stale: L13 and that phrase cannot both hold while C6 stays in drift, and the
  final document governs.
- **C8 is a drift row, not a new conflict.** ADMIN's "replace" is a stale word in a state
  list; the correct reading (a new row) is already in the same document, so it needs no
  decision.

## Files changed

- `Backend/docs/handover/ui-fields.md` — modified (stage 1, rewritten in stage 2, then
  the round-2 fixes).
- `Backend/docs/work/0003-ui-fields-handover.md` — new.
- `Backend/docs/work/README.md` — index row added.
- `Backend/docs/handover/mentor-update.md` — modified (§5 and §7 recomputed against the
  final file).

## Migrations

None. Documentation only.

## Tests

Documentation task; no test suite applies.

- **actual run** `git status --short`, `git diff --stat`, `git log --oneline -3` —
  confirmed only `Backend/docs/handover/ui-fields.md` was modified before stage 1, and
  the stage 1 commit contains one file.
- **actual run** `wc -l Backend/docs/handover/ui-fields.md` — 1117 before stage 1,
  1447 at the stage-2 checkpoint, **1450 at `f2f5bcc`** (the earlier log's 1,447 was
  three lines short), 1501 after the round-2 fixes; `mentor-update.md` is 164 lines.
- **actual run** `grep -n` for the named fields and drift terms — checked `limits.py`,
  `long_description`, `category`, `working_hours`, `client_name`, `not_found` and
  `replace`; all remaining hits are scoped citations or the database-only table.
- **actual run** source-line checks with `awk`/`sed` against `ADMIN.md`, `CONTRACT.md`
  and `DATABASE.md` — corrected two admin line ranges (see Work log).
- **actual run** a Python table check over `ui-fields.md` — every contiguous table has a
  consistent pipe count; no malformed row after the new §3.1.12 and §4.6 rows.
- **actual run** `git status --short` before the commit — only `ui-fields.md`,
  `mentor-update.md` and this work file are modified; `DATABASE.md` was restored to HEAD
  after an external process rewrote it (see Not verified).
- **actual run** a Python count of the field tables — 298 rows: 150 public (86 landing,
  17 legal, 35 settings, 5 routes, 7 enquiry) and 148 admin; §12's 15 database-only rows
  and §7's 45 limit rows are excluded. The mentor note quotes these numbers.
- **not run** `uv run pytest`, lint and typecheck — no Python or frontend code changed;
  the repository has no documentation linter. The independent review has since been
  dispatched and its outcome is in the Work log.

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

The restructured file was reviewed independently at `f2f5bcc`. It found no Critical and
no High: the five High findings were confirmed closed, all 48 admin endpoints matched
`ADMIN.md` §4 one-for-one, and a 30-field sample traced to its sources. It raised four
Medium and twelve Low findings.

All were fixed before the final commit: the mapping table's unmarked table names, the
missing legal-page payload, the work-file path, the unplaced approvals list, three wrong
`DATABASE.md` citations, the preview path notation, the in-review unpublish case, the
revoke 500 cap, `replace` as a drift item, the U7/U14 wording, the contact gate, the
C6/C7 classification, the line count, the `role` citation and the provisional approval
state.

Outcome: **accepted**. No open Critical or High. C1, C3, C4, C6 and C7 stay open as
source conflicts; §11 gives each a workaround that does not block slice 1.

## Docs updated

`Backend/docs/handover/ui-fields.md` and `Backend/docs/handover/mentor-update.md`, plus
this work file. `ADMIN.md`, `CONTRACT.md`, `DATABASE.md`, the OpenAPI schema and the ADRs
are unchanged, because this task resolves no source conflict and adds no endpoint.

## Remaining

None for this document. C1, C3, C4, C6 and C7 remain source conflicts to reconcile at
M14 (payloads) and M16 (admin); each has a buildable workaround in §11 and none blocks
slice 1.

## Next

Hand `ui-fields.md` and `mentor-update.md` to the frontend team. When M14 generates
OpenAPI, reconcile the provisional `†` names and U-items against it, and settle
C1/C3/C4/C6/C7 in the source documents at M16.

## Open questions

- C1: is `phone_hours` one text column (`ADMIN.md:718`, `DATABASE.md:1304-1305`) or the
  object `{summary, timezone}` (`CONTRACT.md:721-728`)? The same question covers
  `settings_location.phone_hours`.
- C3: which pair wins, 80/200 or 40/160?
- C4: are `path` and `slug` optional on create for every kind?
- C6: does an Editor preview settings (`ADMIN.md:364` table) or is it Admin only
  (`ADMIN.md:390-392` prose)?
- C7: one `/admin/audit` screen or a separate `/admin/sign-ins`?
- U15–U17: sort allowlist, staff removal, invite landing/set-password.

## Not verified

- The final review was independent and read the whole document at `f2f5bcc`; the fixes
  applied after it were checked by the orchestrator against the findings, not re-reviewed
  line by line.
- No line-by-line rendering check in a Markdown viewer; table pipe counts were checked by
  script, not by eye in the target CMS/editor.
- The FastAPI service and its generated OpenAPI schema do not exist, so no field name
  could be validated against a live contract.
- During the session an external process rewrote `Backend/docs/DATABASE.md` (table
  padding and a `contact_nphone` typo). It was restored with `git checkout --` and is not
  in this commit; the cause was not identified.
