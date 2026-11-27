# Backend build plan

Status: draft, for review. Written 27 November 2026.

Scope: the FastAPI service in `Backend/` that serves the Leafclutch UK Phase 1 website
and its admin panel. The frontend and admin UI are other folders with other contributors;
this plan ends when the backend satisfies `docs/CONTRACT.md` and `docs/ADMIN.md` and is
deployed.

## How this plan works

- One milestone is one task: one work file in this folder, one green commit (or a short
  series), one independent review, one push. No milestone is "mostly done".
- The schema milestones follow the 17 Alembic revisions in `docs/DATABASE.md` verbatim.
  Their order is not arbitrary: triggers call functions created in the same or an earlier
  revision.
- Every schema milestone proves `upgrade` and `downgrade` on an empty database and leaves
  `alembic check` clean.
- A milestone that creates a table also creates its grants and RLS policy in the
  milestone where `DATABASE.md` puts them, or records why it cannot yet.
- Sizes are S (under half a day), M (one to two), L (three to five). They are rough.

Note: `DATABASE.md` writes `cd api` in its command examples because it was written before
the team folder layout. In this repository the path is `Backend`.

The schema was executed by task 0003 in the design workspace on PostgreSQL 18.7: 57 `sql`
blocks applied, 46 base tables, 17 `PASS` lines, and the assertions were mutation-tested by
breaking the functions and watching them fail. `Backend/docs/runbooks/database-validation.sql`
is the reference harness for M2–M13. Our Compose image is PostgreSQL 16; align it to the
validated major, or re-run the harness on 16, before M2 starts.

## Traceability

Every PRD requirement ID mapped to the milestone that implements it and the check that
proves it. A requirement with no row is a gap, not something to explain away. "Frontend"
means the backend supplies the data and another folder renders it; it is still listed so
nothing is lost between teams.

| PRD area | IDs | Milestones | Proven by | Notes |
| --- | --- | --- | --- | --- |
| Landing page | LP-1–LP-5 | M5, M11, M14, M16 | Ten sections insert in PRD §5 order; page publish test; contract test | LP-5's five-to-eight rule is a CMS warning, not a publish gate |
| Navigation and footer | NV-1–NV-4 | M14, M16, M20 | Nav labels and footer links in the contract | Sticky header, mobile menu and focus states are frontend |
| Services and work | SV-1–SV-7 | M6, M11, M14, M16 | Service projection and unique title; approval per project | SV-2 products out of scope (decision 67); SV-6/SV-7 Phase 2 |
| Enquiries | EN-1–EN-10 | M9, M14, M18 | Validation, rate limit, outbox, first-reply timestamp | EN-10 booking left undelivered (decision 46); EN-1/3/6 are frontend copy |
| Admin | AD-1–AD-12 | M8, M15, M16, M20 | Role matrix, publish gates, audit rows | AD-11 not approved; AD-12 Phase 2 |
| Security | SE-1–SE-12 | M12, M15, M16, M18, M20, M21 | Anonymous isolation, role checks, `no-store`, secrets scan | SE-1/9/11 are deployment and ops; SE-12 is the preview path |
| Non-functional | NF-1–NF-9 | M14, M20 | Contract, caching, unique SEO title (a FastAPI check) | NF-1–4 and NF-9 are frontend; NF-8 locale codes still open |
| Legal and policy pages | PRD §12 | M7, M19, M11 | Legal publish gate and `/routes` | Copy is blocked on D-7 |
| Brand | DS-1–DS-5 | M7, M14 | Logo slot in settings and the contract | UI owns the rest |
| Measurement | SM-1–SM-5 | M18, M20 | `first_replied_at`, audit rows | Targets are the PRD's proposals |

`PRD.md` wraps IDs across lines (`EN-` on one line, `2` on the next), so `grep 'EN-2'`
misses half of them. Normalise before counting: `perl -0pi -e 's/([A-Z]{2,4})-\s*\n\s*(\d+)/$1-$2/g'`
on a copy, or parse with that substitution.

## Review focus

The traps that comparable builds get wrong. Each review checks the ones belonging to its
milestone; "looks correct in the diff" is not evidence.

| # | Trap | Milestone | What the review must see |
| --- | --- | --- | --- |
| 1 | Anonymous isolation leaks | M12, M14, M21 | A test that calls the public endpoint as `anon` and `authenticated` and gets nothing from drafts, users, enquiries, evidence or audit |
| 2 | Approval lifecycle | M8, M11, M16 | Publish refused without approval; expiry hides the item and queues revalidation; revocation does not unpublish |
| 3 | Repeat and concurrent transitions | M11, M16 | Publish, unpublish, archive and restore called twice, and concurrently, leave exactly one live version |
| 4 | Migration order | M2–M13 | Upgrade and downgrade from empty; every trigger resolves functions from its own or an earlier revision |
| 5 | Legal identity gate | M7, M19 | Null refused at publish; a blank or whitespace string refused by Pydantic, with a test |
| 6 | Section publishing | M11, M16 | A page publish takes the chosen section versions; a draft section keeps its live version; a never-published section blocks the page |
| 7 | Enquiry durability | M18 | Saved before email; outbox retry; the alert email carries no message body; rate limit keyed on both IP and email |
| 8 | Media promotion | M17 | A staged object is not publicly reachable before publish; evidence stays private; a deleted media row with a live reference is refused |
| 9 | Cache and revalidation | M14, M16, M20 | `no-store` on admin, preview and enquiry responses; preview `noindex`; publish queues a tag and the worker drains it |
| 10 | Delete refusals | M11, M16 | Seeded kinds, ever-published, approved, and referenced items each refuse with `409` and a named reason; the row survives; success writes one audit row and no revalidation |
| 11 | Unpublish creates drafts | M11, M16 | A landing-page unpublish leaves eleven drafts; `publish_page` accepts them; an open draft is reused, never duplicated; archive creates none |

## Phase A — Foundation

### M1. Skeleton (S)

Deliverables: `pyproject.toml` with Python 3.12, FastAPI, sync SQLAlchemy 2.0 + psycopg 3,
Alembic, Pydantic; `app/config.py`, `app/db.py`, `app/main.py`, `app/health.py`;
`migrations/`; `compose.yaml` with PostgreSQL 16; tests; README.

Exit: `ruff`, `mypy`, `pytest` green; `/health` returns 200; `alembic current` runs.
Blocked by: nothing.

## Phase B — Schema

Exit criteria are the same for all: upgrade and downgrade on a fresh database,
`alembic check` clean, and the constraints tested by at least one failing insert.

| Milestone | Revisions | Contents | Key exit check |
| --- | --- | --- | --- |
| M2. Extensions, enums, staff | 0001–0002 | Extensions, every enum, `staff`, last-Admin trigger, timestamp trigger | A second Admin removal is refused |
| M3. Media | 0003 | `media`, immutability trigger | A published media row cannot be edited |
| M4. Content spine | 0004 | `content_item`, `content_version`, `content_publication`, `content_seo`, immutability function | Editing a published version is refused |
| M5. Landing page | 0005 | `page_section`, `section_version`, paragraphs, process stages, assurances, FAQs, next steps, `section_version_item` | The ten sections insert in PRD §5 order |
| M6. Catalogue | 0006–0008 | Services and groups, projects and images and technologies, proof figures, testimonials, logos | Projections and unique service titles hold |
| M7. Legal and settings | 0009–0010 | Legal page blocks, settings singleton with identity, hours, footer links | One settings row only; working-hour shape holds |
| M8. Approvals | 0011 | `legal_approval`, `approval`, and their triggers | A legal page without a non-author approver cannot publish |
| M9. Enquiries and delivery | 0012–0013 | `enquiry`, `enquiry_note`, `rate_limit_event`, `email_outbox`, `revalidation` | Status transitions and first-reply write-once hold |
| M10. Audit | 0014 | `audit_log`, `sign_in_event`, append-only trigger, purge | An update to `audit_log` is refused |
| M11. Publish engine | 0015 | Every function and view: draft, publish, page publish, unpublish that returns the item to Draft with section drafts (decision 69), archive with drafts off, restore, `delete_content` and its five refusals (decision 70), projections, approval gates, enquiry transitions, retention | A full draft → review → publish → unpublish cycle runs in SQL; a landing-page unpublish leaves eleven drafts and republishes; delete refuses a published, approved, seeded or referenced item |
| M12. Roles, RLS, storage | 0016 | `api_runner`, `scheduler_runner`, grants, RLS policies, buckets | `anon` and `authenticated` are denied; `api_runner` reads what it should; the anonymous-isolation test passes |
| M13. Jobs | 0017 | `pg_cron` schedules | The schedules exist and an expiry run changes the expected rows |

M11 and M12 are the hard ones. Budget for them; do not merge them into one milestone.

## Phase C — API

### M14. Public read API (M)

The contract the frontend team consumes. Published-only endpoints from `CONTRACT.md`:
the page payload, `/routes`, settings, FAQs, and `sitemap`/`robots` inputs.

Exit: response bodies match `CONTRACT.md` field for field; a contract test fails when a
field is renamed; drafts, users, enquiries, evidence and audit rows are unreachable
anonymously; cache headers are correct.

This is the milestone that unblocks the frontend and admin contributors. Ship it as early
as the publish engine allows.

### M15. Auth and staff (M)

Supabase JWT verification, the staff row and role check on every protected request, MFA
state, 12-hour idle handling per `ADMIN.md` §2 (decision A6), `/auth/me`, sign-in events,
last-Admin protection. A `legal_page` or `settings` kind is Admin-only on every content,
page and preview path, and the three sign-in endpoints accept `aal1` before `aal2` is
reached.

Every staff write must either take `pg_advisory_xact_lock(hashtext('staff_last_admin'))`
before its first staff row lock or retry `40P01` with a bounded backoff. The
`staff_lock_writes` trigger orders the locks its own statement takes, but it cannot reorder
a lock the service already holds, so a pre-held `SELECT ... FOR UPDATE` can still form a
deadlock with the trigger. The advisory lock is held to commit, so staff write transactions
stay short.

Exit: a signed-out, expired, MFA-less and downgraded role each get the documented status;
an Editor gets `403` naming a legal page or settings; a deactivated staff member is
refused on the next request.

### M16. Admin content API (L)

List, detail, create draft, update draft, submit for review, publish, unpublish that
returns the item to Draft, archive, restore, `POST /content/{item_id}/delete` for a
never-published item, version history, preview payload, approvals, legal pages. Each write
maps to a `DATABASE.md` function, not hand-written SQL.

Exit: every admin action in `ADMIN.md` §3 has an endpoint in `ADMIN.md` §4; publish
refuses an unapproved project or a legal page without an approver; unpublish leaves a
draft and republish succeeds; delete refuses with `409` and a named reason, leaving the
row intact; one `delete` audit row and no revalidation row.

### M17. Media (M)

Upload through the API, staging bucket, MIME/size/pixel limits, alt text, promotion at
publish, replacement, soft delete, signed URLs for evidence. `/media*` covers only the
staging and site buckets; an evidence id returns `404` there and is reachable only through
the Admin `/evidence` path.

Exit: an upload cannot reach a public bucket before its content publishes; a deleted
media row with a live reference is refused; an Editor cannot read, sign or delete evidence
through `/media`.

### M18. Enquiries end to end (M)

Validation, honeypot, Cloudflare Turnstile, durable rate limit, save before email, consent
version, alert and confirmation through `email_outbox`, retry worker, admin list, notes,
export, first-reply timestamp, deletion for an access request.

Exit: a failed email never loses the enquiry; a repeated submission from the same key is
rate-limited; the alert email contains no full message.

### M19. Settings and site frame (S)

Settings draft and publish, legal identity, hours, footer links, logo, `nepal_site_url`.
Booking fields stay unpublished. The publish gate for the legal identity applies. M8 is
accepted as a known risk: there is no settings/landing two-way gate, so do not invent one.

Exit: the public settings endpoint reflects only the published version; a missing VAT
number omits the line rather than seeding one; unpublishing settings is allowed even while
the landing page is live, and that consequence is not "fixed" in code.

### M20. Audit and operations (S)

Audit list, sign-in list, readiness endpoint, structured logging, error envelope, CORS,
retention job wiring, `/openapi.json` review.

Exit: every admin write produces an audit row; no log line contains a token, password or
enquiry message; readiness reports the migration revision.

## Phase D — Hardening and delivery

### M21. Contract and security tests (M)

The test matrix in `ADMIN.md` §13 plus the anonymous-isolation and publish-gate tests from
`DATABASE.md`, including T44 (delete succeeds once and refuses five ways, leaving the row
and a single audit entry) and T45 (unpublish the landing page, then republish from the
eleven drafts). Run them against a real PostgreSQL with the real roles.

Exit: the suite proves the Musts, not the implementation, and unpublish/delete behave as
decisions 69 and 70 state.

### M22. Deployment (M)

Staging first: Supabase project in `eu-west-2`, migrations, seed, storage buckets, the API
host, environment variables, smoke tests. Production after staging passes, with the same
migrations and a backup.

Exit: staging serves `/health`, `/openapi.json` and the public page; a publish updates the
live page within a minute once the frontend is connected.

## Decision gates

These stop a milestone rather than being guessed:

| Decision | Blocks |
| --- | --- |
| D-7 legal identity values | Real settings content and the legal pages; not the schema |
| D-8 retention and lawful basis | Retention functions and the privacy notice; proposed values are implemented but must be confirmed |
| D-1 host and region | Deployment |
| Hreflang locale codes | Any value in `nepal_site_url`'s companion metadata; the column stays |
| Supabase project and keys per environment | M12 storage policies, M22 |
| Email provider and sender domain | M18 |

### Owner decisions

- **M8 — settings unpublished while the landing page is live.** Accepted 27 November 2026:
  no two-way gate. The risk stays recorded in `ADMIN.md` §14 and is not mitigated; an
  unpublish leaves a settings draft and the public frame can go empty until it is
  published again. Do not invent a gate.
- **D-13 — owner.** Deferred to week 4. No owner is named for content, enquiries, privacy
  and cookie reviews, document approval or production alerts. It does not block M18; it
  blocks the operational assignment that goes with it.

## Risks

- **M11/M12 are where the project is won or lost.** Publish functions and RLS are the two
  places a mistake is expensive and quiet. Review them with the database open, not from
  the diff alone.
- **The frontend is blocked on M14.** If the team needs the API sooner, publish the
  OpenAPI schema with fixture responses behind a flag, clearly marked as not
  implementation.
- **`DATABASE.md` is 200 KB.** Read the section for the milestone, never the whole file,
  and cite what you used in the work file.
- **Scope creep into Frontend/Admin.** The pre-push guard exists for this reason.

## Definition of done for the project

- Every endpoint in `CONTRACT.md` and `ADMIN.md` exists and is covered by a contract test.
- The anonymous surface exposes only published content.
- Migrations run from empty to head and back.
- Staging is deployed and seeded; the README's commands work from a clean clone.
- The work log has one closed entry per milestone, each with its review outcome.
