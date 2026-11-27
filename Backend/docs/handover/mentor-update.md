# Backend progress update — 27 November 2026

Drawn from `docs/work/PLAN.md`, `PROGRESS.md`, the task files, the validation runbook and
`git log`; each claim cites its record, and limits are under "Not verified".

## 1. Status

The FastAPI service for the Leafclutch UK Phase 1 site and admin panel. The build branch is
`prabesh`; this note and the UI field inventory are on `handover/ui-fields`. M1 (skeleton)
is delivered and reviewed. M2 (extensions, enums and staff) is in progress: two commits on
`prabesh` (`8fe79b1`, `64cf3b2`), but its task file says `in-progress` with an empty
`## Review`, and `PROGRESS.md` has no M2 entry, so it is not counted as delivered. M2 is not
blocked; D-7 blocks real settings and legal content (not the schema), the email provider
blocks M18, and D-1 blocks deployment.

## 2. Delivered

| Item | Evidence | Commit |
| --- | --- | --- |
| M1 skeleton | `/health` 200, `alembic current` exit 0, ruff and mypy green; suite closes at 29 tests (`0001-skeleton.md`) | `e92da74`, `79d68f3`, `06b61b6` |
| Test-target guard | Refuses a non-`_test` database, non-loopback host, query string, invalid port and ambient production URL; 29 tests in both import modes | `af66155`, `44c4d5e` |
| Design-document sync | Five files (ADMIN, CONTRACT, DATABASE, runbook md and sql) replaced by the reviewed copies; byte-identical by `cmp` and `sha256sum` | `89ebb56` |
| PostgreSQL 18 alignment | Compose on `postgres:18` with the 18 volume path; M2's recorded run used PostgreSQL 18.7 | `2718d0f` |
| Plan and traceability | 22 milestones; every PRD ID mapped to a milestone and its proof; 11 review traps | `f5fe65e`, `ad567c9` |
| Schema validation | 57 blocks, 46 tables, 17 `PASS`, psql exit 0, assertions mutation-tested; run in the design workspace (task 0003) | harness `89ebb56` |

M1's four review rounds included two rejections — three Medium findings, then one High (a
query-string bypass in the test guard). Fixes: `06b61b6`, `af66155`, `44c4d5e`; four Low
findings deferred with triggers (`0001-skeleton.md` §Review, `d8c0ac8`).

## 3. Where it sits in the plan

Phase A (M1) is done, Phase B (M2–M13) is at M2, and Phases C (M14–M20) and D (M21–M22)
are not started.

M2 is revisions 0001–0002. Its first runs failed — `alembic check` on the missing
`auth.users` metadata, then 13 tests on that foreign key — and are kept as superseded. The
latest is 54 tests on PostgreSQL 18.7 with `alembic check` clean and a downgrade/upgrade
round trip (`0002-extensions-enums-staff.md` on `prabesh`); it stays in progress until the
review is recorded. Next come M3 media, M4
content spine and M5 landing page, where the ten sections insert in PRD §5 order. M11
(publish engine) and M12 (roles, RLS, storage) are the hard ones (`PLAN.md:106`); M14
unblocks the frontend and admin (`PLAN.md:110-120`); M22 is staging, then production.
Sizes are S/M/L; no dates exist.

## 4. Design and decisions

- **Decision 69 — unpublish returns items to Draft.** Every pointer an unpublish removes
  leaves a draft (eleven for the landing page). Without it `publish_page` could not
  republish: it requires every section live, and `_publish_version` accepts only draft or
  in-review. M11 implements it; review focus 11 tests it.
- **Decision 70 — archive is the normal delete.** A permanent delete exists only for an
  item never published, unapproved, not one of the three fixed kinds (landing page, its
  sections, settings) and unreferenced; a never-published legal draft may be deleted. It
  has five refusals; M16 exposes `POST /content/{item_id}/delete`; a refusal is `409` with
  a named reason and the row intact, and success writes one audit row and no revalidation
  row (T44).

Both are at `CONTRACT.md:1076-1077`. The reviewed documents, synced in `89ebb56`, were
executed rather than read: M2–M13 migrate to a schema that has run, with
`database-validation.sql` as the harness. The same review put M15's Admin-only legal pages
and settings, M16's delete endpoint and M17's evidence isolation into the plan
(`3c6f46f`). The data layer is settled: sync SQLAlchemy 2.0, psycopg 3, Python 3.12
(`DATABASE.md` open question 1).

## 5. Frontend handover

`docs/handover/ui-fields.md` (the current revision — `f2f5bcc` plus the review fixes,
sources unchanged from `3c6f46f`) is the build sheet for the landing page and `/admin`,
regrouped by the call the frontend makes: four public endpoints, then the 48 admin
endpoints of `ADMIN.md` §4, then a screen index, build order, limits, shared behaviour,
do-not-build, open decisions, conflicts and a source map (§13). It names 298 field rows —
150 public (86 landing sections, 17 legal page, 35 settings, 5 routes, 7 enquiry form) and
148 admin (typed bodies, approvals, media, enquiries, staff, audit and preview), excluding
§12's 15 database-only rows — with † for a provisional database column. It records five
conflicts (C1, C3, C4, C6, C7), three drift or gap items (C2, C5, C8) and 17 unspecified
items (U1–U17) rather than choosing; §9 lists what not to build. It is a design contract,
not a live API; OpenAPI becomes authoritative when it exists (U9). The task file is
`docs/work/0003-ui-fields-handover.md`.

## 6. Decisions taken and deferred

| Decision | State | What it means |
| --- | --- | --- |
| M8 — settings unpublished while the page is live | Accepted 27 November 2026, no gate | Settings may be unpublished while the page is live, emptying the site frame until republished. The risk stays in `ADMIN.md` §14, unmitigated. |
| D-13 — owners | Deferred to week 4 | No owner for content, enquiries, privacy and cookie reviews, document approval or production alerts; the operational assignment waits, M18 does not. |
| Hreflang locale codes | Open | `en-NP`/`ne-NP` unconfirmed; only `nepal_site_url` exists; no switcher or hreflang. |
| Production Supabase major | To be confirmed at deployment (M22) | Local on validated PostgreSQL 18; re-run the harness at M22 if production differs. |
| D-7, D-8, D-1, email provider | Open | Block real legal and settings values, the privacy notice, deployment, and M18. |

## 7. Risks and open questions

`ui-fields.md` §11 records five source conflicts. Each has a buildable workaround or a
clear wait in that section; none blocks slice 1 of the build order:

| # | Conflict | Effect |
| --- | --- | --- |
| C1 | `contact.phone_hours`: the contract has `hours` as `{summary, timezone}` with the 120-character limit on `phone_hours.summary`; `ADMIN.md` and `DATABASE.md` have `contact_phone_hours` as a text column | One 120-character text input bound to `contact_phone_hours`; no timezone picker; OpenAPI settles the object-versus-text shape. |
| C3 | `next_steps`, 80/200 in the contract against 40/160 in the database | Fails at the database boundary. |
| C4 | `slug`/`path` optionality on create | The create form cannot know which field is required. |
| C6 | An Editor previewing settings: §4's preview table says both roles, §4's prose says Admin | Do not offer it until the API picks one. |
| C7 | The sign-in log route: one `/admin/audit` screen or a separate `/admin/sign-ins` | No separate navigation entry until confirmed. |

C2 (the location half of C1), C5 (M8 still open in `ADMIN.md` §14) and C8 (ADMIN lists
`replace` among the media picker states) are recorded as drift or gaps, not as decisions
that block a control. The 17 unspecified items are U1–U17 in §11.3.

Only `GET /health` is implemented, so the OpenAPI schema the frontend and admin are told to
treat as authoritative does not exist; admin response names stay provisional until M16,
public payloads until M14. Screens can be built on documented shapes; response fields
cannot.

Also open: M11/M12, where `PLAN.md:230` says the project is won or lost; validation covers
unpublish, archive and delete only (`pg_cron`, storage, real `auth.users` and media
promotion uncovered, the broader fixture uncommitted); and the M2 work file records two
`DATABASE.md` follow-ups, the unguarded `enforce_last_admin()` and the
downgrade-extensions line.

## 8. Next

1. M2: record the review outcome and close it.
2. M3 media, M4 content spine, M5 landing page.
3. M6–M13, with M11 and M12 reviewed against a database, not a diff.
4. M14–M20, M21 contract and security tests, M22 staging then production.

From `Backend/` on this branch, a mentor can check:

```bash
uv run pytest -q                  # 29 passed (M2's database tests are on prabesh)
uv run ruff check .               # All checks passed!
uv run mypy app                   # no issues found
docker compose ps                 # after `up -d --wait db`: postgres:18, healthy
uv run alembic current            # exit 0; no revisions on this branch
git log --oneline prabesh         # the hashes above
sed -n '1076,1077p' docs/CONTRACT.md   # decisions 69 and 70
```

## 9. Evidence

All 27 November 2026, from the records named:

- Task 0001 at `44c4d5e`: ruff "All checks passed!", mypy clean in 5 files, 29 tests in
  both import modes.
- Guard runs: a query override and a port injection each fail collection with their rule
  (exit 4); a malformed URL's password appears zero times.
- Compose then: healthy at `127.0.0.1:5434->5432`, image `postgres:16`; `2718d0f` moved it
  to 18.
- Validation: 57 blocks, 46 tables, 17 `PASS`, psql exit 0 (`database-validation.md`).
- Sync: `cmp`/`sha256sum` identical on five files; `delete_content` 8 times in `DATABASE.md`
  and 3 in `ADMIN.md`; decisions 69 and 70 at `CONTRACT.md:1076-1077`.
- `ui-fields.md` at `4a6b01c`: 294 field rows (90 landing, 204 admin), C1–C7, U1–U14.
- M2, in progress and not delivered: 54 passed on PostgreSQL 18.7, `alembic check` clean,
  up/down round trip (`0002-extensions-enums-staff.md` §Tests).

## Not verified

- No contract endpoint exists, so no `CONTRACT.md` payload, field or status code is proven;
  the generated schema carries only `/health`.
- The 17 `PASS` assertions cover unpublish, archive and delete only; `pg_cron`, Supabase
  storage, the real `auth.users` and media promotion were not exercised.
- M2's numbers are quoted from its work file, not re-run for this note; no review outcome
  is recorded.
- The 294 rows are a count of the `| Field |` tables at `4a6b01c`, §3.27 excluded; the
  document prints no total.
- The production Supabase major is unconfirmed until M22.
