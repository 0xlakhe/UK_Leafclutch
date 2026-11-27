# Admin specification

Status: draft, for approval before scaffolding. Started 27 November 2026. Nothing here
is implemented.

This is the admin half of Phase 1: the staff CMS at `/admin`, the API behind it, and the
tests that prove it. It does not repeat the PRD; it cites it. Every statement cites its
source inline: a PRD section or requirement ID, a `CONTRACT.md` decision or section, a
`DATABASE.md` object, or an `AGENTS.md` rule. Where the sources leave a choice, it is
recorded as a decision (A1–A17 in §4) with its reason and the alternative rejected, or
left open in §14. A number no source fixes is marked *proposed*.

Sources, in order of authority for their own subject:

- `PRD.md` — the product, legal and quality requirements (§7, §8, §9, §11, §12, §13,
  §18).
- `CONTRACT.md` — the public wire shape, the service-token boundary, preview and
  revalidation.
- `DATABASE.md` — tables, publish functions, approvals, media promotion, RLS and audit.
- `AGENTS.md` — the confirmed stack and repository rules.

Three conflicts are listed in §14, each with both citations. The two PRD §7 conflicts
over unpublish and delete were settled by the owner and are implemented per
`CONTRACT.md` decisions 69 and 70. The PRD's "no separate API server" (§9) is superseded
by `AGENTS.md`: FastAPI is the backend and Next.js owns the UI.

Products are out of scope (decision 67, `CONTRACT.md`). No screen, endpoint or test in
this document reads or writes a product.

## 1. Purpose, scope and roles

The admin exists so staff can keep the site current without a developer (PRD §1) while
the public site keeps returning published, approved content only (SE-4).

### Role matrix

Copied from PRD §7 (page 9). This table is the specification; the database enforces the
last-Admin rule and FastAPI enforces every other cell on every request.

| Action                                                   | Admin | Editor |
| -------------------------------------------------------- | ----- | ------ |
| Sign in                                                   | Yes   | Yes    |
| Create and edit drafts (page text, services, projects, media) | Yes | Yes |
| Preview drafts                                            | Yes   | Yes    |
| Publish, unpublish                                        | Yes   | No     |
| Delete content                                            | Yes   | No     |
| Edit legal pages and approval records                     | Yes   | No     |
| View and manage enquiries                                 | Yes   | No     |
| Invite, change or remove users                            | Yes   | No     |
| Site settings (contact details, footer, SEO defaults)     | Yes   | No     |

Two roles are enough for Phase 1 (PRD §7). A third "Sales" role is a later decision
(PRD §7) and is not modelled.

### Admin-only surfaces

Enquiries (personal data), staff accounts, site settings, legal pages and their
approvals, proof approval records, deletes (archive and permanent delete), the audit log
and the sign-in log. An Editor receives `403 forbidden` from every one of those
endpoints, not a hidden button (AD-2, SE-3).

### Out of scope

Phase 2 and 3 content (service and project pages, blog, careers, AI assistant; PRD §3),
team profiles (PRD §8; PRD §5's "if approved"), products (decision 67), client accounts
or portals, payments, a CRM, multi-language content, marketing automation and
personalisation, price calculators and AI-written copy (PRD §3). No screen here edits
public control copy: field labels,
validation messages, the confirmation text, the 404 and the consent banner are code
(`CONTRACT.md`, "What the CMS owns").

## 2. Architecture and auth flow

```
Browser ──HTTPS──► Next.js /admin ──service token + staff bearer──► FastAPI ──SQL──► PostgreSQL
   │                    │                                              ├── Supabase Auth (password, TOTP)
   │                    └── session cookies                            └── Supabase Storage (service role)
   └── Supabase Auth: TOTP enrolment only, with the user's own session
```

- The browser talks only to Next.js, except TOTP enrolment, which uses the user's own
  session with Supabase Auth. It never calls FastAPI and never reaches PostgreSQL
  (decision 2).
- Next.js renders `/admin`, holds the session cookies and proxies every admin call.
- FastAPI owns authorisation, sign-in, all SQL, media objects, email and cache
  revalidation.
- Supabase Auth stores the password hash, TOTP factors, invites and reset tokens.
  FastAPI passes a password to Supabase in memory during sign-in and keeps no copy. It
  never stores a password, an MFA secret or a factor.

### Sign-in, invite and reset

1. An Admin invites a person by email and role. FastAPI calls Supabase Auth's admin
   invite, then inserts the `staff` row only after the auth user exists, so a failed
   invite leaves no usable role (`DATABASE.md`, Staff). The invite expires after 7 days
   (AD-1, PRD page 9).
2. The person sets their own password through Supabase Auth's invite link.
3. Sign-in goes through Next to FastAPI, which calls Supabase Auth's password grant.
   FastAPI writes a `sign_in_event` for every attempt, success or failure, and applies
   the lock (A10). Next stores the returned session in its cookies.
4. If the account has a verified TOTP factor, the password step returns
   `mfa_required` with a challenge id. The code is verified through Next and FastAPI to
   Supabase, and the resulting AAL2 session is stored by Next.
5. Enrolment in `/admin/account` is the one place the browser reaches Supabase with the
   user's own session, because the authenticator secret has to reach the user's app.
6. Password reset is Supabase Auth's email flow: self-service from `/admin/sign-in`, or
   triggered by an Admin from `/admin/staff`.

### Session and the staff bearer

- The Supabase session is stored in HTTP-only, `Secure`, `SameSite=Lax` cookies by
  Next.js. The access token is short-lived (1 hour; proposed, A6); Next refreshes it.
- Every proxied call carries `Authorization: Bearer <access token>`,
  `X-Service-Token`, `Origin` and `X-Client-IP` (the address Next derived, per
  `CONTRACT.md`).
- FastAPI checks, in order:
  1. the service token in constant time before routing (`401` without it, per
     `CONTRACT.md`);
  2. the JWT signature against Supabase's JWKS, `exp`, `iss` and `aud`;
  3. the `aal` claim: `aal2` required for every endpoint except `GET /me`,
     `/auth/mfa/verify` and `/auth/sign-out`, which are allowed at `aal1`; the UI reads
     `GET /me` to send the user to enrolment (`403 mfa_required`);
  4. the token's age: `iat` no older than 1 hour (proposed, A6), because Next refreshes
     on activity;
  5. the `staff` row for `sub`: it exists, `active` is true and its `role` decides the
     request (`403 account_inactive` or `403 forbidden`; A6).
- FastAPI loads `staff` on every request. There is no role cache, so a demotion takes
  effect on the next call.

### The 12-hour idle rule

FastAPI sees a bearer, not a session, so it cannot measure idle time. The rule is
enforced where the session lives:

- Next's `/admin` middleware keeps an `admin_seen` cookie, updated on admin page and
  API requests but not on static assets. More than 12 hours since the last update (PRD
  §7, page 9), it clears the Supabase cookies and redirects to
  `/admin/sign-in?reason=idle`.
- Supabase's refresh-token rotation and the 1-hour access token (proposed, A6) bound
  how long a stale token can be replayed.
- FastAPI's token-age check is the backstop if a caller skips Next.

This split is decision A6. It is honest about what a bearer can prove, and it is the
only part of session handling that depends on Next.

### CSRF, origin and headers

- `SameSite=Lax` on the session cookies; every state-changing request requires an
  `Origin` equal to the site origin, and `application/json` only when a body is present,
  else `403 csrf_failed` (A11).
- Next accepts admin mutations only on `/api/admin/*`; there is no GET that mutates.
- Every admin and preview response carries `Cache-Control: no-store` and
  `X-Robots-Tag: noindex`; `/admin` is disallowed in `robots.txt` and unlinked from
  the public site (SE-12, NF-7).
- Security headers (CSP, HSTS, `X-Frame-Options: DENY` for `/admin`, `nosniff`, strict
  referrer policy) come from SE-1 and apply to the admin too.

### State changes

| Event | What happens |
| --- | --- |
| Role changed | The next FastAPI call reads the new `staff.role`. A demoted Admin sees `403 forbidden`; the UI says the role changed and reloads `/admin`. |
| Account deactivated | `staff.active = false`; every call returns `403 account_inactive`; Next clears the cookies and redirects to sign-in. An in-flight request fails the same way. |
| Last Admin demoted, deactivated or deleted | `enforce_last_admin` in `DATABASE.md` raises (AD-10); FastAPI maps it to `409 last_admin`; nothing changes. |
| Session expired | Next refreshes; if the refresh fails, it clears cookies and redirects with `?reason=expired`. Calls that arrive stale get `401 unauthenticated` and the client redirects. |
| MFA missing | `403 mfa_required` for everything but `GET /me`, `/auth/mfa/verify` and `/auth/sign-out`; the UI routes to `/admin/account` to enrol. |
| Signed out | `POST /auth/sign-out` ends the Supabase session; Next clears the cookies; `sign_in_event` unchanged (sign-out is not an attempt). |

## 3. Admin screen inventory

`/admin` is one Next.js route group, staff-only, `noindex`, unlinked. Item routes take
the `content_item.id`, not a slug, because Phase 1 has no service or project pages.
Every content screen supports the full set in "Shared screen behaviour" below; the
States column names only what is unusual for that screen. Item states come from
`content_version.status`, `content_publication` and `content_item.archived_at` in
`DATABASE.md`. `unpublished` is no live pointer and no open draft: the state a restored
item returns to. Unpublish leaves a draft (decision 69), so an unpublished item does not
land there; an archived item is shown as `archived`. Approval
badges ("awaiting approval", "approval missing", "expired", "revoked") come from
`approval` and `legal_approval`. The routes and the interaction patterns are A15.

| Route | Purpose | Roles | Main states |
| --- | --- | --- | --- |
| `/admin` | Dashboard: counts, blockers, expiring approvals, failed revalidation | Admin, Editor | loading, empty, error |
| `/admin/pages/landing` | Landing page SEO, sections list, page publish | Admin, Editor (publish: Admin) | draft, in review, live, unpublished, blocked publish |
| `/admin/pages/landing/sections/[itemId]` | One section's copy and references | Admin, Editor | draft, in review, live, unpublished, version history |
| `/admin/pages/legal` | Legal page list with approval state | Admin | live, awaiting approval, approval missing |
| `/admin/pages/legal/[itemId]` | Blocks editor, effective date, approval, publish | Admin | draft, approved, published, approval missing |
| `/admin/services` | Service groups and services, order | Admin, Editor | draft, live, archived |
| `/admin/services/[itemId]` | One service or group | Admin, Editor | as above |
| `/admin/projects` | Project list, order, approval state | Admin, Editor | draft, live, approval expired |
| `/admin/projects/[itemId]` | Copy, technologies, images, approval | Admin, Editor (approvals: Admin) | draft, live, image missing, blocked |
| `/admin/proof` | Figures, testimonials, client logos, with approvals | Admin, Editor (approvals: Admin) | live, expired, revoked, no slot (logos) |
| `/admin/proof/[kind]/[itemId]` | One proof item | Admin, Editor | as above |
| `/admin/faqs` | FAQ items inside the FAQ section draft | Admin, Editor | inside 5–8 (ok), outside (warning) |
| `/admin/media` | Library, staged and public, with usage | Admin, Editor | uploading, staged, public, unused, deleted |
| `/admin/media/[id]` | Alt text, dimensions, usage, replace action | Admin, Editor | editing alt (creates a new row), in use, replacing |
| `/admin/enquiries` | Enquiry list and filters | Admin | loading, empty, filtered, error |
| `/admin/enquiries/[id]` | Detail, status, notes, first reply, delete | Admin | new, in progress, closed |
| `/admin/settings` | Site frame and legal identity | Admin | draft, live, incomplete identity, blocked |
| `/admin/staff` | Staff list, invite, role, active, MFA state | Admin | invited, active, inactive, last Admin |
| `/admin/audit` | Audit log and sign-in log | Admin | loading, filtered, empty |
| `/admin/revalidation` | Revalidation queue: pending, failed, dead | Admin | loading, empty, filtered, failed |
| `/admin/account` | Own MFA, password, session | Admin, Editor | enrolled, not enrolled, reset |
| `/admin/sign-in` | Supabase sign-in | signed out | credentials, MFA challenge, error, locked |
| `/preview<path>` | Renders a draft through FastAPI (Next catch-all) | Admin, Editor (settings: Admin) | draft, blocked fields, staged media |

### Shared screen behaviour

Every list has a loading skeleton, an empty state with the primary action, an error
state with retry, and keeps filters in the URL. Every editor autosaves the draft on a
short debounce through the same `PATCH`, shows "Saved at HH:MM" from the returned
`revision`, and blocks navigation with an unsaved-changes prompt when a save failed.

Every item screen shows status (`draft`, `in_review`, `published`, `unpublished`,
`archived`), the open version's revision, "last changed by" and when, and the publish
blockers before the Publish button is enabled.

Destructive actions are confirmations that name what changes:

- **Unpublish** names the public path and warns that the page disappears within a
  minute (PRD §7, page 10; `CONTRACT.md`, Revalidation); it returns the item to Draft
  with a draft copy of the last published version (decision 69).
- **Archive** names the item, states that it unpublishes first, and requires the item
  title to be typed.
- **Delete** requires the item title to be typed, names the path or slug that becomes
  free, and states that it cannot be undone. It is offered only for an item that was
  never published, carries no approval, is not one of the three fixed kinds that are
  never created from the UI (the landing page, its sections and settings) and is not
  referenced (decision 70). A legal page is creatable, so a never-published legal draft
  may be deleted.
- **Delete enquiry** requires the record to be typed and states that it cannot be
  undone; it is the UK GDPR erasure path.

Version history is a list of versions with author, status, revision and dates, and a
read-only view of any version. A published version is never editable.

### Accessibility

WCAG 2.2 AA is the target (NF-1; AGENTS.md, Quality gates): full keyboard operation
with visible focus in a logical order, 44px minimum targets, form errors announced
through an `aria-live` region and tied to their fields, no focus trap, reduced motion
respected, and no colour-only status. The section editor's preview pane is an iframe
with a title; the editor must still be usable when the pane is collapsed.

## 4. Admin API contract

Base path on FastAPI: `/api/v1/admin`. Next exposes the same names under `/api/admin`
and forwards them; the browser never sees the FastAPI host.

### Conventions

- JSON, `snake_case`, UUID strings, ISO 8601 UTC timestamps, `YYYY-MM-DD` dates.
- Success bodies are the resource, not a wrapper: `{ "item": …, "version": … }` for a
  content read, `{ "items": […], "page": 1, "per_page": 20, "total": <n> }` for a list.
- Pagination: `page` (1-based, default 1), `per_page` (default 20, maximum 100; A5, the
  default and the cap are proposed).
- Sorting: `sort=field` or `sort=-field`; only allowlisted fields, else `422`.
- Filtering: explicit query parameters; no query language.
- A content resource carries `revision` (the open version's `version_number`, or the
  published version's when nothing is open) and an `ETag` of
  `"<item_id>:<version_id>"` (A3).
- FastAPI's generated OpenAPI schema is the API contract; this table is a readable
  copy. The Next admin client is generated from it, and CI fails if the generated types
  differ from the server (`AGENTS.md`).
- `PATCH` and publish require `If-Match`. A stale value is `412 revision_conflict`;
  a state that forbids the action is `409` (see the error table).
- Write responses return the new state and a fresh `ETag`.

### Error envelope

One envelope for every failure:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Check the highlighted fields.",
    "fields": { "heading": "A heading is required." },
    "blockers": [],
    "request_id": "req_01H…"
  }
}
```

`fields` appears on `422`; `blockers` appears on `409 publish_blocked`. `request_id` is
also sent as `X-Request-ID` and is the only identifier in a 500 body.

| Code | Status | When |
| --- | --- | --- |
| `validation_failed` | 422 | A field is missing, too long, malformed or not editable |
| `unauthenticated` | 401 | No bearer, invalid signature, expired token |
| `invalid_credentials` | 401 | Wrong email or password; the message does not say which |
| `mfa_required` | 403 | Valid token without `aal2`, or a challenge still open |
| `too_many_attempts` | 429 | The sign-in lock; `Retry-After` says when |
| `forbidden` | 403 | Role does not allow it |
| `account_inactive` | 403 | `staff.active` is false |
| `csrf_failed` | 403 | Missing or foreign `Origin`, or a body without a JSON content type |
| `not_found` | 404 | No such item, version, media, enquiry or staff row |
| `conflict` | 409 | The item is archived, the version is not publishable, or a permanent delete is refused (decision 70) |
| `publish_blocked` | 409 | Publish gates refuse; `blockers[]` names each |
| `last_admin` | 409 | The change would remove the last active Admin |
| `revision_conflict` | 412 | `If-Match` does not match the current open version |
| `upload_rejected` | 422 | Type, size, pixels, alt text or magic bytes fail |
| `invite_failed` | 502 | Supabase Auth refused the invite or reset |
| `rate_limited` | 429 | Edge rate limit; `Retry-After` says when |
| `service_unavailable` | 503 | FastAPI cannot reach the database or storage |
| `internal_error` | 500 | Anything unhandled; no internal detail in the body |

`404` is returned for an item of the wrong kind as well as a missing one, so a caller
cannot probe kinds. The codes and statuses are A11; `CONTRACT.md` fixes the public
envelope and the admin set extends it.

### Endpoints

| Method | Path | Purpose | Role | Request | Response | Cache | Database operation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| POST | `/auth/sign-in` | Email + password; records the attempt | signed out | `{email, password}` | session tokens for Next, or `mfa_required` with a challenge | `no-store` | `insert into sign_in_event`; Supabase Auth password grant |
| POST | `/auth/mfa/verify` | TOTP code for the challenge | aal1 | `{challenge_id, code}` | session tokens for Next | `no-store` | `sign_in_event`; Supabase Auth MFA verify |
| POST | `/auth/sign-out` | End the session | any staff | — | `204` | `no-store` | none (Supabase Auth session; Next cookies) |
| POST | `/auth/password-reset` | Send a reset email | signed out | `{email}` | `202` always | `no-store` | `audit_log` (reset requested) |
| GET | `/me` | Who am I, MFA state, role | any staff | — | `staff_account` row | `no-store` | `staff_account` view |
| GET | `/dashboard` | Counts and alerts | both | — | drafts, in review, new enquiries, expiring approvals, failed revalidation | `no-store` | reads `content_version`, `content_publication`, `approval`, `enquiry`, `revalidation` |
| GET | `/content` | List items | both (legal_page/settings: Admin) | `kind`, `status`, `q`, `archived`, `page`, `per_page`, `sort` | paginated items | `no-store` | `content_item`, `content_version` (+ typed table) |
| POST | `/content` | Create an item and its first draft | both (legal_page: Admin) | `{kind, path, slug}` | item, draft, `ETag` | `no-store` | `insert into content_item`, then `create_draft` |
| GET | `/content/{item_id}` | Item, open version, live version, children | both (legal_page/settings: Admin) | — | item, version, typed body, children, `revision`, `ETag` | `no-store` | `content_item`, `content_version`, `content_publication`, typed table |
| GET | `/content/{item_id}/versions` | Version history | both (legal_page/settings: Admin) | `page` | versions with author and dates | `no-store` | `content_version` |
| GET | `/content/{item_id}/versions/{version_id}` | One version, read-only | both (legal_page/settings: Admin) | — | typed body and children | `no-store` | `content_version` + typed table |
| POST | `/content/{item_id}/drafts` | Create a draft from live | both (legal_page/settings: Admin) | — | existing open version or a new one, `ETag` | `no-store` | `create_draft` |
| PATCH | `/content/{item_id}/drafts/{version_id}` | Update the draft | both (legal_page/settings: Admin) | `If-Match`, typed body | version, `revision`, `ETag` | `no-store` | typed table update; `content_version.updated_by` |
| POST | `/content/{item_id}/drafts/{version_id}/submit` | Draft → in review | both (legal_page/settings: Admin) | `If-Match` | version | `no-store` | `content_version` update (`in_review`) |
| POST | `/content/{item_id}/publish` | Publish one item | Admin | `If-Match` | revision, warnings[], revalidation state | `no-store` | `publish_content` |
| POST | `/pages/{item_id}/publish` | Publish the landing page | Admin | `If-Match`, `{page_version_id, sections[]}` | revision, warnings[], blockers | `no-store` | `publish_page` |
| POST | `/content/{item_id}/unpublish` | Remove from the site | Admin | `If-Match` | item state | `no-store` | `unpublish_content` |
| POST | `/content/{item_id}/archive` | Archive (the normal delete) | Admin | `If-Match`, `{confirm_title}` | item state | `no-store` | `archive_content` |
| POST | `/content/{item_id}/restore` | Undo an archive | Admin | — | item state | `no-store` | `restore_content` |
| POST | `/content/{item_id}/delete` | Permanently delete a never-published item | Admin | `If-Match`, `{confirm_title}` | `204` | `no-store` | `delete_content` |
| GET | `/pages/{item_id}` | Page with its sections | both | — | sections, each status, pointer and revision | `no-store` | `page_section`, `content_item`, `content_version`, `content_publication` |
| GET | `/approvals` | Approvals list | Admin | `state`, `subject_kind`, `page` | approvals | `no-store` | `approval` (+ `media`) |
| POST | `/content/{item_id}/versions/{version_id}/approvals` | Record an approval | Admin | body below | approval | `no-store` | `insert into approval` |
| POST | `/approvals/{approval_id}/revoke` | Revoke with a note | Admin | `{note}` | approval | `no-store` | `revoke_approval` |
| POST | `/content/{item_id}/versions/{version_id}/legal-approval` | Legal approval | Admin | — | legal approval row | `no-store` | `insert into legal_approval` |
| POST | `/media` | Upload a site image | both | multipart file + `alt` | media row, staged | `no-store` | insert into `media`; object in `media-staging` |
| GET | `/media` | Library of non-evidence media | both | `state`, `role`, `q`, `page` | media rows with usage | `no-store` | `media` where `bucket in ('media-staging','site-media')`; `media_usage` |
| GET | `/media/{media_id}` | One non-evidence record with a signed URL if private | both | — | media row, `url` (5 minutes, proposed, A12) | `no-store` | `media` (non-evidence bucket) |
| POST | `/media/{media_id}/delete` | Soft delete non-evidence media | both | — | media row | `no-store` | `media.deleted_at` (non-evidence bucket) |
| POST | `/evidence` | Upload evidence | Admin | multipart file | media row in `evidence` | `no-store` | `insert into media` (evidence bucket) |
| GET | `/evidence/{media_id}/url` | Signed link | Admin | — | `{url}` (60 seconds, proposed, A12) | `no-store` | `media` (signed URL) |
| GET | `/enquiries` | List | Admin | `status`, `q`, `from`, `to`, `page` | paginated enquiries | `no-store` | `enquiry` |
| GET | `/enquiries/{enquiry_id}` | Detail with notes | Admin | — | enquiry, notes | `no-store` | `enquiry`, `enquiry_note` |
| PATCH | `/enquiries/{enquiry_id}` | Status only | Admin | `{status}` | enquiry | `no-store` | `update enquiry` (status trigger) |
| POST | `/enquiries/{enquiry_id}/notes` | Internal note | Admin | `{body}` | note | `no-store` | `insert into enquiry_note` |
| POST | `/enquiries/{enquiry_id}/first-reply` | Record first reply once | Admin | — | enquiry | `no-store` | `update enquiry set first_replied_at` (trigger) |
| GET | `/enquiries/export.csv` | CSV export | Admin | same filters | `text/csv` | `no-store` | `enquiry`; `audit_log` |
| DELETE | `/enquiries/{enquiry_id}?confirm={enquiry_id}` | Erasure | Admin | query `confirm` | `204` | `no-store` | `delete from enquiry`; `audit_log` |
| GET | `/settings` | Settings draft and live | Admin | — | settings item, typed body, `revision` | `no-store` | `settings_version` + child rows |
| GET | `/staff` | Staff list | Admin | `role`, `active`, `page` | `staff_account` rows | `no-store` | `staff_account` |
| POST | `/staff/invites` | Invite | Admin | `{email, display_name, role}` | staff row, invite state | `no-store` | Supabase Auth invite; `insert into staff`; `audit_log` |
| PATCH | `/staff/{user_id}` | Role, active, name | Admin | `{role, active, display_name}` | staff row | `no-store` | `update staff` (`enforce_last_admin`) |
| POST | `/staff/{user_id}/password-reset` | Send reset | Admin | — | `202` | `no-store` | Supabase Auth; `audit_log` |
| POST | `/staff/{user_id}/mfa-reset` | Remove TOTP factors | Admin | — | `202` (see §14) | `no-store` | Supabase Auth; `audit_log` |
| GET | `/audit` | Audit log | Admin | `actor`, `action`, `entity_kind`, `entity_id`, `from`, `to`, `page` | paginated rows | `no-store` | `audit_log` |
| GET | `/sign-ins` | Sign-in log | Admin | `staff_id`, `outcome`, `from`, `to`, `page` | paginated rows | `no-store` | `sign_in_event` |
| GET | `/revalidation` | Queue state | Admin | `status`, `page` | pending, failed, dead rows | `no-store` | `revalidation` |
| GET | `/preview` | Draft payload for a path | both (legal_page/settings: Admin) | `path` | public shape with drafts, `preview: true` | `no-store` | published tables + draft typed rows (read only) |

On create, `path` is required for `landing_page` and `legal_page`, and `slug` for
`service` and `project`; a `page_section` takes neither (`DATABASE.md:348-353`).

Universal failures are not repeated per row. Every endpoint can return
`401 unauthenticated`, `403 forbidden`, `403 account_inactive`, `404 not_found`,
`429 rate_limited`, `500 internal_error` and `503 service_unavailable`. A mutation can
also return `403 csrf_failed` and `422 validation_failed`. Codes distinctive to a group:

| Endpoint group | Extra codes |
| --- | --- |
| Draft edit, publish, unpublish, archive, delete | `412 revision_conflict`, `409 conflict` (each refusal), `404 not_found` |
| Publish | `409 publish_blocked` with `blockers[]` |
| Approvals, legal approval | `409 conflict` (wrong version state), `403 forbidden` for Editor |
| Media and evidence upload | `422 upload_rejected` |
| Staff invite and changes | `409 last_admin`, `502 invite_failed` |
| Enquiry status and first reply | `409 conflict` (illegal transition, second reply) |
| Preview | `404 not_found` for an unknown path |

Content kinds served by `/content`: `landing_page`, `page_section`, `legal_page`,
`service_group`, `service`, `project`, `proof_figure`, `testimonial`, `client_logo`,
`settings` (the `content_kind` enum in `DATABASE.md`). Only the creatable kinds accept
`POST /content`: `service_group`, `service`,
`project`, `proof_figure`, `testimonial`, `client_logo` and `legal_page` (Admin only).
The landing page, its ten sections and the settings singleton are seeded and are never
created from the UI (A16). `GET /settings` is a convenience read; settings writes use the
content endpoints for the settings item.

`legal_page` and `settings` require Admin on every content read and write, version
read and preview; an Editor gets `403 forbidden`. An Editor's `GET /content` omits
`legal_page` and `settings`, and naming either `kind` returns `403 forbidden`.
`GET /pages/{item_id}` serves the landing page only, so its Role is both.

Four endpoints are session operations that touch no table (`/auth/sign-out`) or write
only `sign_in_event` or `audit_log` (`/auth/sign-in`, `/auth/mfa/verify`,
`/auth/password-reset`); every other row reads or writes the tables named.

The typed body is the kind's table, for example `section_version` with its
`sections[]` children, `service_version` with `group_item_id`, `project_version` with
`images[]` and `technologies[]`, `settings_version` with address lines, locations,
working hours and footer links. `content_seo` is part of every page kind's body.

### Endpoint to database operation

| Write | Operation |
| --- | --- |
| Create an item | insert `content_item`, then `create_draft`, which inserts the empty typed row |
| Create draft | `create_draft(item_id, actor)` |
| Edit draft | update the typed row and children; set `content_version.updated_by` |
| Submit review | `update content_version set status = 'in_review', submitted_at = now()` |
| Publish an item | `publish_content(item_id, version_id, actor)` |
| Publish the page | `publish_page(page_id, page_version_id, section_versions[], actor)` |
| Unpublish | `unpublish_content(item_id, actor)` |
| Archive | `archive_content(item_id, actor)` |
| Restore | `restore_content(item_id, actor)` |
| Delete | `delete_content(item_id, actor)` |
| Revoke an approval | `revoke_approval(approval_id, actor, note)` |
| Record an approval | `insert into approval (…)` |
| Record a legal approval | `insert into legal_approval (…)` |
| Upload media | insert `media`, then the object in `media-staging` |
| Delete media | set `media.deleted_at`; the object is removed when nothing references it |
| Enquiry status | `update enquiry set status = …` (the trigger enforces the flow) |
| Enquiry note | `insert into enquiry_note (…)` |
| First reply | `update enquiry set first_replied_at = now()` once (trigger refuses a second value) |
| Delete enquiry | `delete from enquiry`; notes cascade; one `audit_log` row with no personal data |
| Invite | Supabase Auth admin invite, then `insert into staff` |
| Sign-in attempt | `insert into sign_in_event`; the lock counts recent failures |
| Role or active change | `update staff`; `enforce_last_admin` guards it |

Publish and unpublish write the `revalidation` row and the `audit_log` row in the same
transaction. Approval revocation always writes the `audit_log` row and writes
`revalidation` rows only for pages whose live section versions reference the record,
which may be none. Archive always writes the `archive` audit row; when it removes a live
pointer — the item's own or, for a landing page, a section's — it also writes an
`unpublish` audit row naming the archived item and a `revalidation` row. Restore writes
the audit row only; delete writes one `delete` audit row and no revalidation row;
`create_draft` writes neither. The API writes
the audit row for direct writes (media, approvals, enquiries, staff) in the same
transaction as the change.

### Concurrency

`If-Match` carries the `ETag` from the last read. FastAPI compares it to the open
version before writing:

- different version or revision → `412 revision_conflict`, with the current resource in
  the body so the UI can show a diff and stop the save;
- same version but the action is wrong (no open draft, archived, already published) →
  `409 conflict`;
- publish that fails a gate → `409 publish_blocked`, `blockers[]` naming each.

### Idempotency and retries

Phase 1 has no idempotency-key store, so writes are made idempotent by state:

- Publishing a version that is already the publication pointer returns `200` with the
  same revision and writes nothing; it does not raise. The API checks the pointer before
  calling `publish_content`, because the function accepts only an open version.
- Unpublishing an item that has no pointer returns `200` without calling
  `unpublish_content`. The function itself always deletes, writes a revalidation and an
  audit row, and creates a draft when it removed a pointer, so an unconditional retry
  would add noise.
- Archiving an archived item returns `409 conflict`; restoring one that is not archived
  does the same.
- Uploads are not idempotent: a retry creates a second media row, so the client disables
  the control while a request is in flight and deletes the orphan if it was a duplicate.
- The enquiry form is the only public write; its retry rules live in `CONTRACT.md`.

True at-least-once delivery to the revalidation worker is handled by the outbox, not by
the admin API.

### Rate limits

- Public enquiry limits (5 per 10 minutes and 20 per hour per address, 3 per hour per
  email) are unchanged and separate (`CONTRACT.md`, Enquiry submission).
- Admin endpoints are behind staff auth; Phase 1 adds an edge limit of 120 requests per
  minute per staff member (proposed, A9) at the Vercel WAF, returning `429 rate_limited`
  with `Retry-After`. It is configuration, not a table (A9, needs ops sign-off).
- `POST /media` and `POST /evidence` are capped at 20 per minute per staff member
  (proposed, A9).

### Decisions this document makes

| # | Decision | Reason | Alternative rejected |
| --- | --- | --- | --- |
| A1 | The browser reaches only Next; FastAPI and PostgreSQL are never browser-reachable; Supabase Auth is reached through FastAPI, except TOTP enrolment | One BFF boundary; A10 covers the sign-in and MFA proxy, and enrolment needs the secret in the user's app | Browser reaches FastAPI or Supabase Auth directly: the service-token boundary is bypassed |
| A2 | FastAPI base path `/api/v1/admin`, proxied by Next at `/api/admin` | One name, two hops; the browser never sees the FastAPI host (`CONTRACT.md`, The Next-to-FastAPI link) | Expose the FastAPI host to the browser: breaks the service-token boundary (`CONTRACT.md` decision 55) |
| A3 | `ETag` `"<item_id>:<version_id>"`, with `If-Match` required on edits and publishes | The open version is already the concurrency key, so no new counter | `revision` in the body only: a concurrent save silently wins |
| A4 | No idempotency-key store; the API short-circuits repeat publishes and unpublishes | No such table exists and the pointer is the state | An `idempotency_key` table: a schema change for a risk the pointer already covers |
| A5 | `page`/`per_page` pagination (default 20, maximum 100 — proposed) and a sort allowlist | Bounded queries and predictable pages | Cursor pagination: unnecessary at this scale and more client code |
| A6 | 12-hour idle in Next; FastAPI verifies the JWT, requires `aal2` for every endpoint except `GET /me`, `/auth/mfa/verify` and `/auth/sign-out`, caps token age at 1 hour (proposed) and reads the role per request; Next holds the AAL2 session | A bearer proves a session, not idle time; PRD §7 sets the 12 hours; AAL2 cannot exist before verification, and a user must be able to sign out | A server-side session table: a new schema for a rule Next can enforce |
| A7 | Settings writes reject `booking_url` and `booking_label` with `422` instead of storing them | Decision 46 keeps the link off; accepting edits would collect data the site may not publish | Accept and ignore: the editor would think the change was saved |
| A8 | Promotion happens inside publish; no separate promote endpoint | The public copy and the pointer must commit together (`CONTRACT.md` decision 35) | A promote endpoint: two phases that can leave a public file with no pointer |
| A9 | Admin rate limits at the edge: 120 requests/min per staff member and 20 uploads/min (proposed) | No table, and per-instance counters are wrong on serverless | A Postgres counter table: a new schema for a limit no source fixes |
| A10 | Sign-in and MFA verification are proxied through Next and FastAPI | AD-7 and AD-10 need every attempt recorded and a lock that cannot be skipped | Browser to Supabase Auth directly: failures go unrecorded |
| A11 | Admin errors reuse `CONTRACT.md`'s envelope with an extended code list; `X-Request-ID`; `SameSite=Lax`; `Origin` on every mutation and JSON only when a body is present | `CONTRACT.md` fixes the public envelope; a second shape would be a second contract | A separate admin envelope, or a mutating GET: two shapes and a CSRF hole |
| A12 | Signed URL lifetimes: 5 minutes for admin thumbnails, 60 seconds for evidence (both proposed) | Short enough to bound a leaked link, long enough for a page load | One lifetime for both; or public evidence URLs (`CONTRACT.md`, Media: the `evidence` bucket is private; SE-7) |
| A13 | A publish that succeeds with a non-blocking Should-level issue returns `warnings[]` | LP-5's FAQ section is a Should, so the 5–8 count must not block a Must-level publish (`CONTRACT.md`, What blocks a publish) | Block on the count: turns a Should into a Must |
| A14 | The audit log also records invites, deactivations, password resets, MFA resets and enquiry exports | AD-7 and `DATABASE.md` name the minimum; these are account-security and personal-data events a reviewer will ask for | Audit only the named actions |
| A15 | Screen routes and interaction patterns: `<id>` item routes, autosaved drafts on a debounce, URL-held filters, typed-title confirmation for archive and permanent delete, typed-record confirmation for enquiry deletion, and the derived `unpublished` label for a restored item with no pointer and no open draft | Sources fix statuses, roles and gates, but not the interaction model; without one the screens cannot be built | Explicit save buttons and free-form confirmations: lost edits and an accidental archive one click away |
| A16 | The landing page, its ten sections and the settings row are seeded, never created from the UI | The set and order are fixed (PRD §5; `page_section_key` and `content_item_settings_singleton` in DATABASE.md), so a create action could only duplicate or reorder them | Create-from-UI: needs reorder controls that PRD §5 does not grant |
| A17 | An Admin resets another user's MFA factors; the user re-enrols | The PRD requires MFA but specifies no recovery; an Admin-led reset keeps the account recoverable without weakening the second factor, because the user must enrol again | User self-service reset, or no reset: the first lets a compromised session remove its own factor; the second locks a lost device out permanently |

## 5. Content lifecycle and publishing

```
create_draft ──► draft ──submit──► in_review ──publish──► published (pointer set)
                   ▲                    │                      │
                   └──── new draft ◄────┘                      │
                                                               ├─ unpublish → pointer
                                                               │  deleted, draft created
                                                               └─ archive → unpublish + flag
```

| From | Action | To | Who |
| --- | --- | --- | --- |
| none | `create_draft` | draft | Admin, Editor |
| draft | submit | in_review | Admin, Editor |
| draft | publish | published | Admin (skips review) |
| in_review | publish | published | Admin |
| published | edit | a new draft copied from live; live unchanged | Admin, Editor |
| published | unpublish | draft, or the existing in-review version; pointer deleted, draft copied from the last published version | Admin |
| unpublished | `create_draft` | draft copied from the last published version | Admin, Editor |
| never published (draft, in_review or archived) | delete | row removed | Admin |
| any | archive | archived (unpublished first, one transaction) | Admin |
| archived | restore | archived flags cleared; not live until republished | Admin |

- One open version per item is a unique index; `create_draft` returns the existing open
  version (`200`) when there is one, so the drafts endpoint is idempotent.
- A published version and its typed rows are immutable. Editing a live item never
  touches it.
- **Unpublish** deletes the publication pointer and creates a draft copy from the last
  published version in the same transaction (decision 69); an existing open draft is
  reused, never duplicated. The published version stays for history, and the item
  returns to Draft as PRD §7 says. Unpublishing the landing page also removes its
  sections' pointers and ensures a draft for each of the ten sections, so `publish_page`
  can republish them; without the section drafts the page could not be republished.
  Unpublishing one section deletes only that section's pointer: the section disappears
  from the live page until it is republished, and the other sections keep their
  pointers.
- **Archive** is the normal delete: it unpublishes a live item and creates no draft.
  Archiving the landing page unpublishes every live section pointer, whether or not the
  page's own pointer is present, and archives its sections in the same transaction.
  **Restore** clears the flags, sections included, leaves the item `unpublished` or in
  the open draft that survived the archive, and does not republish; the next Edit continues or creates
  the draft, and no revalidation row is written.
- **Delete** permanently removes an item that was never published, carries no approval,
  is not one of the three fixed kinds that are never created from the UI (the landing
  page, its sections and settings) and is not referenced by a section draft or a service
  group's services (decision 70). It asks for the typed title, cannot be undone, writes
  one `delete` audit row and no revalidation row, and frees the item's path or slug. A
  legal page is creatable, so a never-published legal draft may be deleted.

### Publishing a page

The landing page is one content item with ten section items (PRD §5; the
`page_section_key` enum in `DATABASE.md`; decision 6). `publish_page` takes the page
version and the section versions being published:

1. The page must have an open version, all SEO fields, a live privacy notice and
   published settings (`CONTRACT.md`, What blocks a publish).
2. Every section must have a live version after the call. A section the Admin does not
   include keeps its current live version; a section that has never published blocks the
   page.
3. All pointers move in one transaction, page last. Any gate failure rolls back every
   pointer.

The API returns the blockers from FastAPI's checks before calling SQL, and maps a
raised gate to the same `blockers[]` shape when SQL refuses. A publish that succeeds
with a non-blocking issue returns `warnings[]`; the FAQ count outside 5–8 is one
(PRD §5; LP-5 is a Should, so `CONTRACT.md` makes it a CMS warning, not a refusal).

### Where validation lives

| Rule | Layer |
| --- | --- |
| One open version; immutable published versions; pointer integrity | SQL (`content_version`, `content_publication`) |
| Section counts: 3–4 groups, 3–6 projects, ≤4 figures, ≤6 testimonials, ≥1 About paragraph | SQL (`assert_section_counts`): 3–4 groups and 3–6 projects from PRD §5 items 4 and 6 and SV-1; ≤4 figures, ≤6 testimonials and ≥1 About paragraph from `assert_section_counts`. |
| Legal block kinds: `h2`, `p`, `ul`, `table` (decision 17); one cell per column; list and table completeness | SQL (`assert_publishable_version`; `CONTRACT.md`, Legal page) |
| Settings identity always present; regulation 63 when `uk_establishment`; 2–4 address lines; VAT line only with a number | SQL (`settings_version`, `settings_address_line`; PRD §12; `CONTRACT.md`, Field limits) |
| Approval present and unexpired for projects, figures, testimonials and logos; screenshots scope when images exist | SQL (`assert_approval`, `assert_publishable_version`; decision 31) |
| Legal approver exists and is not the author | SQL (`assert_legal_approval`; PRD §7) |
| Last active Admin cannot be removed | SQL (`enforce_last_admin`; AD-10) |
| Delete only for a never-published, unapproved item that is not one of the three fixed kinds (the landing page, its sections and settings) and is unreferenced | SQL (`delete_content`; decision 70) |
| Hero has both CTAs; exactly four stages and three assurances; five nav labels; privacy note; unique SEO title and description; cookies table matches `cookies.json`; service title uniqueness; `__other__` refused (decision 63); empty or whitespace-only values rejected | FastAPI/Pydantic and the publish service (PRD §5; `CONTRACT.md`, What blocks a publish; decision 38; decision 29; `DATABASE.md`, Notes for requirements.md and Site settings) |
| FAQ count outside 5–8 | FastAPI warning only; never a refusal (PRD §5; LP-5 is a Should) |
| Field-level format and length | Pydantic, mirrored in Next for early feedback; the server is authoritative (`CONTRACT.md`, Field limits) |

## 6. Approvals and legal pages

### Proof approvals

An approval attaches to a version, not to an item (decision 31), so editing an approved
quote or result requires a new approval.

| Field | Meaning |
| --- | --- |
| `subject_kind` | `project`, `proof_figure`, `testimonial` or `client_logo` |
| `scopes` | What the client permitted; see below |
| `approved_by_name`, `approved_by_email` | The client contact who approved; not the staff member |
| `approved_on` | The date the client approved; never in the future |
| `expires_on` | Null for no expiry; otherwise ≥ `approved_on` |
| `evidence_media_id` | Email or document in the `evidence` bucket; optional |
| `recorded_by` | The Admin who recorded it |

| Subject | Scopes |
| --- | --- |
| Project | any of `client_name`, `result`, `mark`, `screenshots`; `screenshots` required when the version has images |
| Proof figure | exactly `figure` |
| Testimonial | `quote` plus optionally `client_name`; the API refuses a version claiming a name without the `client_name` scope (`DATABASE.md`; the API checks field coverage, and decision 62 allows the quote without the name) |
| Client logo | `mark` plus optionally `client_name` |

The scope rules are the `assert_approval` trigger in `DATABASE.md`; "`screenshots` when
the version has images" is `assert_publishable_version`.

Rules:

- Only an Admin records or revokes an approval. The body is
  `{approved_by_name, approved_by_email, approved_on, expires_on, scopes[], evidence_media_id}`;
  `subject_kind` and `recorded_by` are derived from the version and the caller. The UI
  shows the current state on the item, and the publish button is disabled with the
  reason when no live approval covers the version's claims.
- An approval is created against a draft or in-review version. FastAPI refuses one for a
  published version; the trigger enforces it.
- **Expiry** is a date in `Europe/London`. The daily job queues revalidation for pages
  holding the item (`DATABASE.md`, Retention and scheduled jobs), and the public read
  filters expired and revoked approvals, so the item disappears from the live page even
  though its version stays published. The page may then show fewer than the section's
  publish-time count; that is intended, and R-6's fallback.
- **Revocation** is `revoke_approval(id, actor, note)`. It does not unpublish, and it
  cannot be undone: the row keeps `revoked_at`, `revoked_by` and the note, and the
  trigger refuses reactivation.
- Evidence is never returned by a public call. The admin opens it through a 60-second
  signed URL (proposed, A12).

### Legal pages

- Legal pages are edited by an Admin only (PRD §7).
- `legal_approval` names the version's author (`created_by`) and an approver who is an
  active Admin and not the author. Any later edit creates a new version and needs its
  own approval.
- Blocks are `h2`, `p`, `ul` and `table` only. No HTML, no Markdown. Links are plain
  text until a link block is approved (`CONTRACT.md`, open question 2).
- The cookies page's table must match `cookies.json` in both directions: every cookie
  the site sets appears, and nothing else does. FastAPI checks names before publish.
- `effective_on` is nullable; null renders the London publish date (`CONTRACT.md`,
  Legal page).
- The privacy notice cannot be unpublished or archived while the landing page is live,
  because the form would collect without the notice. The API returns
  `409 publish_blocked` with that blocker.

## 7. Media

Uploads go through Next to FastAPI; the browser never writes to Supabase.

The PRD fixes type and size checks, required alt text and private evidence (SE-7,
AD-9). The formats, 4MB, pixel bounds, 16:10 and the 120-character alt limit are
Leafclutch proposals recorded in `CONTRACT.md`, not PRD requirements.

1. `POST /media` accepts one file and `alt`. FastAPI checks magic bytes, the 4MB cap,
   the 40MP/8192px decode guard, strips metadata, converts to sRGB WebP, resizes the
   long edge to 2000px, and stores it in `media-staging` with an opaque path.
2. The row is `private` until the version that references it is published. Publishing
   copies each attached object to `site-media`, marks the row public with `promoted_at`,
   and only then commits the pointer. A failed publish removes the copies it made.
3. Replacement never overwrites: a new file, a new row and a new reference. The old row
   stays while a version or approval references it.
4. Deletion is soft (`deleted_at`); the object is removed once nothing references it.
   Media referenced by any version is never deleted (decision 57).
5. Evidence (`POST /evidence`) accepts PDF, JPEG, PNG and WebP and stays private.

| Limit | Value (`CONTRACT.md`, Media) |
| --- | --- |
| Types | JPEG, PNG, WebP by magic bytes (evidence also PDF) |
| Size | 4MB |
| Pixels | at most 40MP and 8192px per side before decode; 1200px minimum width; long edge 2000px |
| Shape | landscape only for work images, 16:10 at render |
| Alt text | required, at most 120 characters (`CONTRACT.md`, Media; `DATABASE.md` `media_alt_length`) |

Media picker states: idle, uploading with progress, staged (badge "Publishes with the
page"), public, unused, alt-text error, type/size/pixel error, upload failed with retry,
and the replace action (creates a new row).

## 8. Enquiries

Admin-only from list to delete. An Editor gets `403` and the screen is absent from their
navigation.

- List filters: status, free text over name/email/company, date range, pagination. The
  default order is newest first.
- Status moves `new → in_progress → closed`; the trigger refuses skips and reversals
  (`DATABASE.md` `enquiry_status_flow`). Reopening a closed enquiry is not supported in
  Phase 1.
- Notes are internal, 1–4000 characters, authored and timestamped (`DATABASE.md`
  `enquiry_note`); they never appear in an email.
- **First reply** is a write-once action: `POST /first-reply` sets `first_replied_at` once
  and the trigger refuses a second value (`DATABASE.md` `guard_first_reply`). It is not
  set by triage. SM-3 measures it.
- **Export** is CSV over the same filters, with the full message, and writes one audit
  row recording the export and its row count, with no personal data (AD-6; A14; the
  format is proposed — the PRD says export).
- **Delete** is a hard delete for a UK GDPR request. Notes cascade, the audit row keeps
  the fact and the count, not the content.
- The alert email carries name, service and a link to the record, never the message
  (PRD §8, page 13; SE-10).
- The consent-notice version is displayed on the detail screen, so staff can see which
  privacy notice the visitor saw.
- Retention is 24 months by `purge_expired_enquiries` (PRD §8; pending D-8).

## 9. Settings and site frame

Settings are one `content_item` of kind `settings`, edited through the content endpoints
and published like any versioned item. The live site changes only on publish. The fields
below live on `settings_version` and its child rows in `DATABASE.md`.

| Group | Fields |
| --- | --- |
| Legal identity | `legal_name`, `trading_name`, `country`, address lines, `uk_establishment`, `home_registry`, `registration_number`, `head_office_location`, `legal_form`, `limited_liability`, `insolvency_information`, `vat_number` |
| Contact | `contact_email`, `contact_phone`, `contact_phone_hours`, `hours_summary`, `hours_timezone` (`Europe/London`; `CONTRACT.md`, Site settings), `settings_working_hour` rows |
| Locations | `settings_location` with address lines, country, phone and phone hours |
| Frame | `site_logo_id`, `footer_note`, `settings_footer_link` rows (wire name `footer_links`), `seo_title_suffix`, `seo_description`, `seo_og_image_id` (wire names under `seo_defaults`), `cta_label`, fixed `cta_href` (decision 54), `nepal_site_url` |

- The header is the settings logo, the CTA and the five section nav labels (PRD §5 menu;
  `CONTRACT.md`, What blocks a publish, NV-1); the footer is the footer links, the legal
  identity, the legal routes and the Cookies page. Neither is a `page_section`
  (decision 6, decision 52).
- The footer links Cookies, not "Cookie preferences": no optional cookies exist, so
  there is no preference to set.
- A phone requires hours. A location is shown only when it is real. A UK number is a
  contact line, not an office (`CONTRACT.md` decisions 33 and 64; `CONTRACT.md`, Site
  settings; PRD §12).
- Regulation 63 fields are required only when `uk_establishment` is true; the VAT line
  renders only when `vat_number` is set. Values are D-7's; nothing is seeded.
- `booking_url` and `booking_label` exist in the draft table but are not editable or
  exposed here; D-12 keeps the link off (decision 46, A7).
- `nepal_site_url` is editable; the hreflang locale codes are not stored (open, §14).

## 10. Audit and sign-in

| Record | Written by | Contents | Read by |
| --- | --- | --- | --- |
| `audit_log` | FastAPI, in the action's transaction | actor, action, entity kind and id, version, page, path, revision, affected rows, time | `/admin/audit`, Admins |
| `sign_in_event` | FastAPI on every sign-in attempt | staff id (null if unknown), outcome, IP hash, user-agent hash, time | `/admin/audit` (sign-ins tab), Admins |

- Recorded actions: role changes, publishes, unpublishes, archives, restores, content
  deletes, legal approvals, approval records and revocations, media promotion and
  deletion, enquiry triage, first reply and deletion, and settings changes, as AD-7 and
  `DATABASE.md` name them; invites, deactivations, password and MFA resets and enquiry
  exports (A14).
- Append-only: `audit_log` has no update or delete grant for `api_runner` and a trigger
  refuses mutation; the retention job is the only deletion path, after 12 months (PRD
  §8; `purge_audit_log`).
- No password, token, MFA secret, enquiry message or evidence content is ever written to
  either record (SE-10).
- "Last changed by" on an item is `coalesce(updated_by, created_by)` on the open version,
  or `published_by`/`published_at` when nothing is open (`DATABASE.md`, AD-8).
- Media uses `uploaded_by`/`uploaded_at`; enquiry triage and reply are audit-derived, as
  are staff changes (invites, role changes and resets), with no dedicated column for any
  of them (`DATABASE.md`, Notes for requirements.md: AD-8 for enquiries and staff).
- Sign-in rows live 12 months (`DATABASE.md` `purge_sign_in_events`; PRD §8).
  A deleted staff account leaves its rows with a null `staff_id`.

## 11. Preview and revalidation

**Preview** is `GET /api/v1/admin/preview?path=/`: the public payload shape with
`preview: true`, each section's current draft in place of its published version, and
nothing cached. It is staff-session-only and never public.

- `/preview<path>` on the Next origin reads the session, forwards the bearer, and
  renders the real components in an iframe inside the editor: `/preview/` for the
  landing page, `/preview/privacy` for a legal page. It is excluded from the nav, the
  sitemap and every public cache tag.
- Responses are `no-store` and `X-Robots-Tag: noindex` (SE-12).
- Staged images appear as short-lived signed URLs, scoped to the staff session; the
  public payload never carries a signed URL.
- Empty required fields stay empty, and the editor shows the completeness list beside the
  iframe from the same payload.

**Revalidation** is an outbox:

- Publish and unpublish write both a `revalidation` row and an `audit_log` row in the
  same transaction as the change. Approval revocation always writes the `audit_log` row
  and writes `revalidation` rows only for pages whose live section versions reference
  the record, which may be none. Archive always writes the `archive` audit row and,
  when it removes a live pointer — the item's own or, for a landing page, a section's —
  also writes the `unpublish` audit row naming the archived item and a `revalidation`
  row; restore writes the audit row only; delete writes one `delete` audit row and no
  revalidation row; `create_draft` writes neither.
- A FastAPI worker posts the tags to Next (`POST /api/revalidate`, shared secret),
  marks the row sent, and retries with backoff. A publish is complete when the row is
  written, not when Next answers.
- Target: the live page changes within one minute (PRD §7, page 10; `CONTRACT.md`,
  Revalidation). Backstop: public reads have a 24-hour maximum age (`revalidate: 86400`;
  `CONTRACT.md` decision 59).
- Expiry runs at 23:05 and 00:05 UTC to hit London midnight in GMT and BST
  (`CONTRACT.md`, Revalidation).
- A row still pending after five minutes, or dead after its last attempt, alerts the
  named owner (`CONTRACT.md`, Revalidation); `/admin/revalidation` shows the queue.
- Admin and preview responses are never cached.

## 12. Validation, errors and security

- Every write validates on the server. The Next form mirrors the rules for early
  feedback; it is never the authority. Empty or whitespace-only strings are rejected by
  Pydantic even where SQL only rejects null (`DATABASE.md`, Notes for requirements.md).
- `422` returns `fields` keyed by field path (`sections[2].heading`), and the UI focuses
  the first invalid field and announces the summary.
- Commands that change state are POST/PATCH/DELETE with a same-origin `Origin` and,
  when they carry a body, `application/json`; there is no mutating GET (A11).
- Role is checked on every request (AD-2, SE-3); active state and MFA are checked there
  too (AD-1, SE-2, A6), not only in the UI.
- The last active Admin cannot be demoted, deactivated or deleted (`enforce_last_admin`,
  AD-10).
- Repeated failed sign-ins are slowed or locked (AD-10; A10). FastAPI counts recent
  `sign_in_event` failures for the account and the address and returns
  `429 too_many_attempts` once the configured threshold is met; Supabase Auth's own
  rate limit is the second guard. The password is held in memory for the Supabase call
  and is never stored or logged.
- Secrets live in server environment variables only; the browser holds a session cookie,
  never a service key or database credential (SE-8).
- Public reads stay published-only. The anonymous test proves drafts, staff, enquiries,
  evidence and audit rows are unreachable: `anon` and `authenticated` have no table or
  sequence grants, no schema usage, and the Data API is off (SE-4, R-5).

| Concern | Control |
| --- | --- |
| Transport | HTTPS, HSTS, CSP, no framing of `/admin`, `nosniff`, strict referrer |
| Session | HTTP-only `Secure` `SameSite=Lax` cookies, 1-hour access token, 12-hour idle (A6; PRD §7 for the 12 hours) |
| Authorization | Role read from `staff` per request; admin-only routes and services |
| MFA | `aal2` required on every endpoint except `GET /me`, `/auth/mfa/verify` and `/auth/sign-out` |
| CSRF | `Origin` on every mutation; JSON content type when a body is present (A11) |
| Uploads | Magic bytes, size, pixel guard, metadata strip, private staging |
| Evidence | Private bucket, 60-second signed links (proposed, A12), Admin only |
| Public isolation | No grants to `anon`/`authenticated`; published views only |
| Secrets | Server-side only; none in the repository or the browser |
| Logging | Outcome and ids only; no message, password or token |

## 13. Test matrix

Each row is one automated test. Role tests call the endpoint as that actor; the public
isolation test runs anonymously against every table and view. Numbers in the test inputs
are fixtures chosen against the limits in §5 and §7 (FAQ count, 4MB, 40MP — PRD §5;
`CONTRACT.md`), not new limits.

| # | Role | Scenario | Expected |
| --- | --- | --- | --- |
| T1 | signed out | Any endpoint that needs a bearer | `401 unauthenticated` |
| T2 | staff, `aal1` | Any endpoint except `GET /me`, `/auth/mfa/verify` and `/auth/sign-out` | `403 mfa_required` |
| T3 | Editor | Publish, unpublish, archive, delete, legal-page edits, settings, enquiries, staff, approvals; read or delete evidence through `/media`; read or write a legal page or settings through the generic content endpoints; unfiltered `GET /content`; preview a legal page | `403 forbidden` for the Admin-only actions, legal-page/settings content calls and legal-page preview; `/media` returns no evidence row or URL, and an evidence id is `404 not_found`; the unfiltered `GET /content` list omits `legal_page` and `settings` |
| T4 | Editor | Create draft, edit, submit for review and preview a service, project and proof item; upload media; edit a landing-page section and FAQs | `200`; live unchanged |
| T5 | Admin | Publish own draft without review | live pointer moves; audit row |
| T6 | Admin | Publish with a stale `If-Match` | `412 revision_conflict` |
| T7 | Admin | Publish with a gate missing (hero CTA) | `409 publish_blocked` with a blocker naming the field |
| T8 | Admin | Publish the page with one section never published | `409`; no pointer moves |
| T9 | Admin | Publish the page with unchanged sections | their live versions stay; page pointer moves |
| T10 | Admin | Edit a published item | a new draft is created; live payload byte-identical |
| T11 | Admin | Unpublish | pointer removed; draft copied from the last published version; version kept; revalidation row written |
| T12 | Admin | Archive a live item | unpublish then archive in one transaction; one revalidation; no draft created; the `unpublish` and `archive` audit rows |
| T13 | Admin | Restore an archived item | flags cleared; still not live; item shows `unpublished`, or the open draft that survived the archive; no revalidation |
| T14 | Admin | Unpublish the privacy notice while the landing page is live | `409 publish_blocked` |
| T15 | Admin | Demote, deactivate or remove the last Admin | `409 last_admin`; row unchanged |
| T16 | Admin | Reviewer approves a legal page, then edits it | the new version needs a new approval |
| T17 | Admin | Publish a legal page with the author as approver | refused |
| T18 | Admin | Publish a project with images and no `screenshots` scope | refused; `409` |
| T19 | Admin | Revoke a live item's approval, then revoke one not on a live page | the live item leaves the page at the next render, its version stays published; the off-page revocation writes the audit row and no revalidation row; a new draft cannot publish until re-approved |
| T20 | Admin | Approval expires overnight | expiry job queues tags; the page loses the item at the next London midnight, within five minutes |
| T21 | Editor | Record or revoke an approval | `403 forbidden` |
| T22 | Admin | Upload a 5MB file, a PNG renamed `.jpg`, and a 50MP image | `422 upload_rejected` for each |
| T23 | Admin | Upload without alt text | `422`; no object stored |
| T24 | Admin | Publish a version referencing a staged image | object copied to `site-media`; row public before the pointer commits |
| T25 | Admin | Delete an enquiry | `204`; notes gone; audit row with no personal data |
| T26 | Admin | Set `first_replied_at` twice; read the audit log | the second write is refused; the first writes an audit row naming the actor and time |
| T27 | Admin | Export enquiries | CSV with the filtered set; audit row with the count |
| T28 | Admin | Publish settings with `legal_name` null | `409`; blocker names the field |
| T29 | Admin | Publish settings with `uk_establishment` true and no registration number | `409` |
| T30 | Admin | Set `booking_url` | `422`; the field is not editable in Phase 1 |
| T31 | Admin | Publish a page with four FAQs | publishes; the response carries a warning, not a blocker |
| T32 | Admin | Publish two pages with the same SEO title | second is refused before SQL |
| T33 | Admin | Invite, change role, reset password, reset MFA; read the audit log | Supabase call recorded; an audit row naming the actor and time for each; no secret in the response |
| T34 | signed out | Anonymous read of every admin path and public view | no draft, staff, enquiry, evidence or audit row |
| T35 | signed out | `GET /api/v1/public/page?path=/<unpublished-path>` for a draft path | `404 not_found`; no draft content |
| T36 | Admin | Every admin and preview response | `no-store` and `X-Robots-Tag: noindex` |
| T37 | Admin | Publish and read the queue | `revalidation` row sent by the worker within a minute; retry on failure |
| T38 | Admin | Keyboard-only pass on every screen | focus visible, order logical, 44px targets (AGENTS.md), no trap |
| T39 | Admin | Form error announced | `aria-live` summary and field association |
| T40 | Admin | A mutation with a body and a non-JSON content type, and a cross-origin POST | `403 csrf_failed` |
| T41 | signed out | Wrong password, then the right one | one `sign_in_event` failure, then a success; the error never says whether the account exists |
| T42 | signed out | Repeated failures past the threshold | `429 too_many_attempts`; a correct password is still refused until the window passes |
| T43 | signed out | TOTP code wrong, then right | AAL1 only after the first; AAL2 after the second; both attempts recorded |
| T44 | Admin | Delete a never-published item, then try a published, an approved, one of the three fixed kinds (landing page, section, settings), a referenced and a `service_group` item that still has a `service_version` row | `204` and the row gone with one `delete` audit row; each refusal `409 conflict` and the row stays |
| T45 | Admin | Unpublish the landing page, then republish it | eleven drafts exist (created or reused); `publish_page` accepts them; page live |

## 14. Open decisions and schema dependencies

### Conflicts between sources

| Fact | Source A | Source B | Question | ADMIN.md follows |
| --- | --- | --- | --- | --- |
| The backend | PRD §9 (page 14): Next.js route handlers and server actions, "No separate API server"; Prisma and Zod | `AGENTS.md`: FastAPI is the backend, with SQLAlchemy and Pydantic, and it supersedes PRD §9 | Does the PRD need reissuing with the confirmed stack? | AGENTS.md, because the repository rule says it supersedes |
| Footer cookie link | PRD §5 item 12 and NV-3 ("cookie preferences"), PRD §12's pages list ("cookie information and preferences") | `CONTRACT.md` decision 52: no optional cookies, so the footer links Cookies and no preference control exists | Reopen decision 52, or update the PRD wording? | Decision 52 |
| Booking link | PRD §18 D-12 recommendation: booking link yes (Google Calendar) | `CONTRACT.md` decision 46: the owner answered no booking link and no budget field | None open: the answer is later than the recommendation | Decision 46 |

The unpublish and delete conflicts are settled by `CONTRACT.md` decisions 69 and 70:
PRD §7 wins over `DATABASE.md`'s previous pointer-only unpublish and archive-only
delete.

### PRD §18 decisions that affect the admin

| ID | State | Effect on the admin |
| --- | --- | --- |
| D-1 | Open | Final stack and host after the Nepal audit. If it changes, this document's API contract is revisited; the screens and rules stand. |
| D-3 | Open | UK audience priority and the service catalogue. Products are out of scope (decision 67); the service screens edit whatever catalogue management confirms. |
| D-4 | Answered 26 Nov (decision 45) | Analytics is Plausible (decision 45); legal's exemption sign-off is still needed. No admin screen beyond settings defaults. |
| D-5 | Answered (CONTRACT.md, closing paragraph of Open before the admin document) | Custom admin confirmed; Payload is reconsidered only in Phase 2. |
| D-7 | Open | Legal identity values, Companies House status and VAT number. The settings form has the fields; nothing is seeded. |
| D-8 | Open | Retention sign-off: enquiries 24 months, audit and sign-ins 12 months, `ip_hash` and outbox 30 days, rate limits 7 days. The privacy notice must state all of them before the form collects (`DATABASE.md` `purge_sign_in_events`; PRD §8; `CONTRACT.md` decision 56 and Enquiry submission). |
| D-9 | Open | Whether a client-logo slot is added. The record, media and approval exist; no screen renders a logo on the page until decided. |
| D-10 | Open | Prices or packages. Phase 1 shows none; the settings form has no price field and the admin cannot publish one. |
| D-11 | Answered 26 Nov (decision 39) | Email only, one UK working day, until UK hours are staffed (decision 39). |
| D-12 | Answered 26 Nov (decision 46) | No booking link and no budget field: decision 46 rejects the PRD §18 recommendation of a Google Calendar booking link and an optional budget field. The columns are placeholders and are not editable. |
| D-13 | Open | Owners for website content, enquiries, privacy and cookie reviews, document approval, and production alerts (PRD §18); this document names no owner, and §8's enquiry handling and §11's alerts need one. |

Also open and visible in the admin:

- AD-11 Google Workspace sign-in for staff is a Should "if approved"; it is not
  approved. Supabase Auth email + password + TOTP is the Phase 1 path, and Workspace
  sign-in would be a provider change, not a screen change.
- Hreflang locale codes (`en-NP`/`ne-NP`) and the Nepal URL value; only
  `nepal_site_url` exists.
- The typed 1-working-day promise (one typed `next_steps` item or four free ones;
  `CONTRACT.md` decision 39; D-11).
- Settings can be unpublished while the landing page is live, which empties the site
  frame and legal identity until republished. Accepted 27 November: no two-way gate; the
  risk is recorded, not mitigated.
- A constrained legal link block (open question 2).
- At least one screenshot per project (open question 5).

### Schema dependencies and gaps

These are recorded, not fixed. None is a schema change in this document.

1. **No admin session table.** The 12-hour idle rule is enforced in Next (A6). If the
   PRD is read as requiring a server-side idle record, a `staff_session` table is a new
   schema change.
2. **No idempotency-key store.** Repeat publishes and unpublishes are short-circuited
   in the API (A4). True at-least-once for other writes would need a table.
3. **No admin rate-limit store.** The edge limit (A9) is configuration; a per-staff
   counter in Postgres would need a table.
4. **MFA recovery is not specified by the PRD.** `POST /staff/{id}/mfa-reset` is the
   proposed path (an Admin removes the factors through Supabase and the user re-enrols),
   and A17 records the decision because it is a route around a Must control.
5. **Invites have no local record.** Supabase owns them; the `staff` row is created only
   after the auth user exists. An "invited" state is derived from `auth.users`, not
   stored here.
6. **Admin search across typed tables.** `content_item` indexes kind and path; a
   free-text search over `service_version.title`, `project_version.title` and
   `legal_page_version.title` will need per-table indexes or a search view. Flagged as a
   performance dependency, not a correctness gap.
7. **Client-logo slot (D-9).** No page reference exists; the admin can record and approve
   a logo but cannot place it.
8. **Audit of enquiry reads.** The audit log records export and delete, not every view.
   If read access must be audited, that is a new action and a write on every detail read.
9. **Products (decision 67).** Removed. Any future product screen needs a new
   `content_kind`, a typed table, a D-3 decision and a migration.

The identifier check is §F of `docs/work/0001-admin-provenance.md`; its justification
list for the admin-only terms is under `## Tests` in that file.

### What this document does not cover

Public-site behaviour, the enquiry form's visitor-facing rules, revalidation mechanics
inside Next, backups, environments, monitoring, DNS, email deliverability and the
security headers' exact values. Those belong to `requirements.md`, the runbook and
`CONTRACT.md`.
