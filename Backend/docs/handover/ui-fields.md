# UI field inventory — public and admin endpoints

Status: handover document, written 27 November 2026 against commit `4a6b01c` on
`handover/ui-fields`. Line references are to that commit; `ADMIN.md`, `CONTRACT.md` and
`DATABASE.md` are unchanged from `3c6f46f`.

## 1. Read this first

- **What this is.** A build sheet for the two Next.js surfaces, ordered by the endpoints
  the frontend actually calls. It names every field the two source documents give a
  control, a limit or a state, and nothing else. The four public endpoints come first,
  then the 48 admin endpoints in the order a client would build them, then a screen
  index so the page view is not lost.
- **This is a design contract, not a live API.** The FastAPI service does not exist yet.
  When it does, its generated OpenAPI schema is authoritative, and this file must be
  reconciled with it. A field here that OpenAPI does not carry is a documentation bug,
  not a licence to call a route that is not there.
- **Public payload names are nested; admin request names are flat.** The public wire uses
  `primary_cta.label`, `privacy_note.text`, `company.legal_name` and
  `locations[].address`. The admin `PATCH` body is the kind's typed table, with flat
  columns: `primary_label`, `privacy_text`, `legal_name`, `settings_address_line`.
  Sending a nested public name to an admin body is a `422`. The mapping is in §2.5.
- **A name in plain code** appears in a CONTRACT payload, an ADMIN request body or an
  ADMIN screen description. **†** marks a database column named by DATABASE.md because
  the higher documents define no response schema; OpenAPI replaces it. DATABASE is used
  for a form name only where marked †, and it is the source for the numbered check.
- **The frontend never touches the database.** The browser calls Next.js only; Next.js
  calls FastAPI with `X-Service-Token`, and admin and preview calls also carry the staff
  bearer (`CONTRACT.md` "The Next-to-FastAPI link"; `ADMIN.md` §2). No Supabase database
  client, database credential or service key ships to the browser. The one exception is
  the Supabase Auth client used for TOTP enrolment in `/admin/account`, with the user's
  own session (`ADMIN.md` §2, A1).
- **Limits.** A bare number in a Limit column comes from CONTRACT.md "Field limits"
  (`CONTRACT.md:1088-1142`). A number ending in **†** is a database check cited only
  because the contract is silent. **Not stated** means neither document gives a number;
  do not add one.
- **Required.** **Yes at publish** means CONTRACT.md "What blocks a publish" names it as
  a gate. **Yes** means the item needs a value to render as designed; the Pydantic model
  decides whether it is enforced, because the gate table is silent. **Fixed** means the
  value is not editable. **Read-only** means the API supplies it.
- **Placeholders are not copy.** Strings in angle brackets, and every heading, quote,
  figure, logo and legal identity value, wait for approved content. Nothing here is
  seeded (`AGENTS.md`; `CONTRACT.md` preamble).
- **The surfaces.** Four public calls: `GET /api/v1/public/page?path=/`,
  `GET /api/v1/public/settings`, `GET /api/v1/public/routes` and
  `POST /api/v1/public/enquiries`. All are server-to-server with `X-Service-Token`; the
  enquiry is the only public write. There is no public media route
  (`CONTRACT.md` "The calls", "Media", decision 36). The admin base path is
  `/api/v1/admin`; Next exposes the same names under `/api/admin` and forwards them
  (`ADMIN.md` §4, A2).

## 2. Conventions — read once

### 2.1 Shared shapes

Admin success bodies are the resource, not a wrapper: a content read is
`{ "item": …, "version": … }`, a list is
`{ "items": […], "page": 1, "per_page": 20, "total": <n> }` (`ADMIN.md:253-254`). The
shapes below are the ones this file refers to; OpenAPI names the actual response keys.

**`ItemSummary`** — one row in every content list, built from the shared item chrome in
`ADMIN.md:214-216`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | the content item; every item route takes it, not a slug. |
| `kind` | enum | a `content_kind` value: `landing_page`, `page_section`, `legal_page`, `service_group`, `service`, `project`, `proof_figure`, `testimonial`, `client_logo`, `settings` (`ADMIN.md:381-384`). |
| `status` | enum | `draft`, `in_review`, `published`, `unpublished`, `archived`. |
| `revision` | integer | the open version's number, or the published version's when nothing is open. |
| `updated_by` † | string | "last changed by"; `coalesce(updated_by, created_by)`, or `published_by` when nothing is open. |
| `updated_at` † | ISO 8601 | "last changed at", same derivation. |
| `published_at` | ISO 8601 or null | null when not live. |

**`VersionSummary`** — one row in version history. ADMIN.md:234 fixes author, status,
revision and dates; §3.27 keeps the other version columns out of the UI.

| Field | Type | Notes |
| --- | --- | --- |
| `revision` | integer | `content_version.version_number` (`DATABASE.md:390`). |
| `status` | enum | `draft`, `in_review`, `published`; the full item state is on the item. |
| `created_by` † | uuid | the author; the legal-page approver must differ. |
| `created_at` † | ISO 8601 | created date. |
| `updated_at` † | ISO 8601 | last edit date. |
| `published_at` † | ISO 8601 or null | null for a version that never published. |

**`Page<T>`** — `{ "items": T[], "page": 1, "per_page": 20, "total": <n> }`
(`ADMIN.md:253-254`).

### 2.2 Pagination, sorting and filtering

- `page` is 1-based, default 1. `per_page` defaults to 20 and caps at 100; both defaults
  and the cap are proposed (A5; `ADMIN.md:255-256`).
- `sort=field` or `sort=-field` for descending. Only allowlisted fields are accepted;
  anything else is `422 validation_failed` (`ADMIN.md:257`). ADMIN names the rule but
  not the list; OpenAPI defines it (U15).
- Filters are explicit query parameters; there is no query language (`ADMIN.md:258`).
  The per-endpoint rows below name every filter the source gives.
- A list response carries `total`; a UI must not infer it from the page length.

### 2.3 Errors

**Public envelope.** One shape for every public failure (`CONTRACT.md:859-886`):

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Check the highlighted fields.",
    "fields": { "email": "Enter a valid email address." }
  }
}
```

| Code | Status | When |
| --- | --- | --- |
| `validation_failed` | 422 | A field is missing, too long or malformed; `fields` names each one. |
| `rate_limited` | 429 | Too many submissions from one address; `Retry-After` says when. |
| `verification_failed` | 400 | The Turnstile token is missing, expired or rejected. |
| `not_found` | 404 | No published page at that path; **page reads only, not the enquiry form**. |
| `service_unavailable` | 503 | FastAPI cannot reach the database; keep the visitor's text and show the site email. |
| `internal_error` | 500 | Anything unhandled; no internal detail in the body. |

A browser fetch rejection or timeout produces no envelope; the form treats it as
`service_unavailable` (`CONTRACT.md:888-889`).

**Admin envelope.** The same shape plus `blockers` and `request_id`
(`ADMIN.md:269-307`):

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

`fields` appears on `422` and is keyed by **field path**, for example
`sections[2].heading`; the UI focuses the first invalid field and announces the summary
(`ADMIN.md:804-805`). `blockers[]` appears on `409 publish_blocked`, each naming a gate.
`request_id` is also sent as `X-Request-ID` and is the only identifier in a 500 body
(`ADMIN.md:269-307`).

| Code | Status | When |
| --- | --- | --- |
| `validation_failed` | 422 | A field is missing, too long, malformed or not editable. |
| `unauthenticated` | 401 | No bearer, invalid signature or expired token. |
| `invalid_credentials` | 401 | Wrong email or password; the message does not say which. |
| `mfa_required` | 403 | Valid token without `aal2`, or a challenge still open; carries `challenge_id`. |
| `too_many_attempts` | 429 | The sign-in lock; `Retry-After` says when. |
| `forbidden` | 403 | Role does not allow it. |
| `account_inactive` | 403 | `staff.active` is false. |
| `csrf_failed` | 403 | Missing or foreign `Origin`, or a body without a JSON content type. |
| `not_found` | 404 | No such item, version, media, enquiry or staff row; also an item of the wrong kind. |
| `conflict` | 409 | The item is archived, the version is not publishable, or a permanent delete is refused (decision 70). |
| `publish_blocked` | 409 | Publish gates refuse; `blockers[]` names each. |
| `last_admin` | 409 | The change would remove the last active Admin. |
| `revision_conflict` | 412 | `If-Match` does not match the current open version. |
| `upload_rejected` | 422 | Type, size, pixels, alt text or magic bytes fail. |
| `invite_failed` | 502 | Supabase Auth refused the invite or reset. |
| `rate_limited` | 429 | Edge rate limit; `Retry-After` says when. |
| `service_unavailable` | 503 | FastAPI cannot reach the database or storage. |
| `internal_error` | 500 | Anything unhandled; no internal detail in the body. |

Universal admin failures are not repeated per endpoint: every admin call can return
`401 unauthenticated`, `403 forbidden`, `403 account_inactive`, `404 not_found`,
`429 rate_limited`, `500 internal_error` and `503 service_unavailable`; a mutation can
also return `403 csrf_failed` and `422 validation_failed` (`ADMIN.md:364-370`).

### 2.4 Concurrency: `ETag`, `If-Match` and `412`

- A content resource carries `ETag: "<item_id>:<version_id>"` (A3,
  `ADMIN.md:259-261`).
- `PATCH`, submit, publish, unpublish, archive and delete require `If-Match`; restore
  takes none (`ADMIN.md:263`, §4).
- A stale value is `412 revision_conflict` **with the current resource in the body**, so
  the UI can show a diff and stop the save. The same version with a forbidden action is
  `409 conflict`; a failed gate is `409 publish_blocked` with `blockers[]`
  (`ADMIN.md:443-452`).
- Write responses return the new state and a fresh `ETag`.
- Repeat publishes and unpublishes are idempotent by state: publishing the current
  pointer returns `200` and writes nothing; unpublishing an item with no pointer does
  the same (A4, `ADMIN.md:454-469`).

### 2.5 Admin request names — flat columns, not public payload names

The admin `PATCH` body is the kind's **typed table**, with flat columns: `ADMIN.md:329`
names "typed body" for the draft update and `ADMIN.md:399-402` says it is "the kind's
table", for example `section_version`, `project_version` and `settings_version`. Sending
`primary_cta.label` or `company.legal_name` to that body is a `422`. Use this mapping
wherever a form below shows a public name.

| Public payload name (CONTRACT) | Admin request name | Source |
| --- | --- | --- |
| `primary_cta.label` | `primary_label` | `DATABASE.md:614` |
| `primary_cta.href` | `primary_href` | `DATABASE.md:615` |
| `secondary_cta.label` | `secondary_label` | `DATABASE.md:616` |
| `secondary_cta.href` | `secondary_href` | `DATABASE.md:617` |
| `cta.label` | `cta_label` | `DATABASE.md:618` |
| `cta.href` | `cta_href` | `DATABASE.md:619` |
| `privacy_note.text` | `privacy_text` | `DATABASE.md:620` |
| `privacy_note.link_label` | `privacy_link_label` | `DATABASE.md:621` |
| `image` | `image_id` | `DATABASE.md:622` |
| `about.body` | `section_paragraph` rows †, `text` per paragraph | `DATABASE.md:690-700` |
| `company.legal_name` | `legal_name` | `DATABASE.md:1300` |
| `company.trading_name` | `trading_name` | `DATABASE.md:1301` |
| `company.country` | `country` | `DATABASE.md:1302` |
| `company.address` | `settings_address_line` rows †, `line` per row | `DATABASE.md:1359-1367` |
| `logo` | `site_logo_id` | `DATABASE.md:1314` |
| `contact.email` | `contact_email` | `DATABASE.md:1303` |
| `contact.phone` | `contact_phone` | `DATABASE.md:1304` |
| `contact.phone_hours` | `contact_phone_hours` | `DATABASE.md:1305` |
| `contact.hours.summary` | `hours_summary` | `DATABASE.md:1306` |
| `contact.hours.timezone` | `hours_timezone` | `DATABASE.md:1307` |
| `locations[]` | `settings_location` rows † (`name`, `country`, `phone`, `phone_hours`) | `DATABASE.md:1369-1382` |
| `locations[].address` | `settings_location_address_line` rows †, `line` per row | `DATABASE.md:1384-1400` |
| `footer_links[]` | `settings_footer_link` rows † (`label`, `href`) | `DATABASE.md:1402-1416` |
| `seo_defaults.title_suffix` | `seo_title_suffix` | `DATABASE.md:1309` |
| `seo_defaults.description` | `seo_description` | `DATABASE.md:1310` |
| `seo_defaults.og_image` | `seo_og_image_id` | `DATABASE.md:1311` |
| `form.services` | not in a request body: computed at read time from published services | `CONTRACT.md` "Site settings"; decision 48 |

A `†` entry is the database table the records live in, not a request key: the array key
in the `PATCH` body is OpenAPI's (U9), exactly as §4.3.1 states for the section children.

The same rule covers the other kinds: `project_version.images[]` is a row per image with
`media_id`, `project_version.technologies[]` is `project_technology[]` with `name`, and
`content_seo` is part of every page kind's body (`ADMIN.md:399-402`).

### 2.6 Cache and indexing

- Every admin and preview response carries `Cache-Control: no-store` and
  `X-Robots-Tag: noindex` (T36; `ADMIN.md` §11; SE-12).
- `/admin` is disallowed in `robots.txt` and unlinked from the public site. `/preview`
  is excluded from the nav, sitemap and every public cache tag (SE-12, NF-7).
- Public reads carry one cache tag per call: `page:<path>`, `settings` and `routes`
  (`CONTRACT.md` "The calls"). A publish or unpublish queues the tag for revalidation
  (`CONTRACT.md` "Revalidation").

### 2.7 Roles

Two roles, `admin` and `editor`, and no third in Phase 1 (`ADMIN.md:40-53`). Role is
checked server-side on every request, not by hiding a button: an Editor gets
`403 forbidden` from every Admin-only endpoint (AD-2, SE-3).

| Action | Admin | Editor |
| --- | --- | --- |
| Sign in, edit drafts, preview, upload media | yes | yes |
| Publish, unpublish, archive, permanent delete | yes | no |
| Legal pages and their approvals | yes | no |
| Proof approvals and evidence | yes | no |
| Enquiries, staff, settings, audit and sign-in logs | yes | no |

`publish`, `unpublish` and `delete` are Admin-only at `ADMIN.md:45-46`; `archive` is the
normal delete and is Admin-only in the endpoint inventory (`ADMIN.md:334`). An
Admin-only screen is absent from an Editor's navigation **and** returns `403` if called
(`ADMIN.md` §1, §8).

## 3. Public endpoints

All four are server-to-server: Next sends `X-Service-Token` and FastAPI rejects a request
without it before parsing the body (`CONTRACT.md:59-92`). None is reachable from the
browser.

### 3.1 `GET /api/v1/public/page?path=/`

| | |
| --- | --- |
| Method and path | `GET /api/v1/public/page?path=/` |
| Auth | service token only; no staff bearer |
| Cache tag | `page:<path>`; 24-hour maximum age backstop (`CONTRACT.md` "Revalidation") |
| Response | one page: landing or legal |
| Errors | `404 not_found` for no published page at that path |

The landing page is `type: "landing"` and returns the `sections[]` shape below. A legal
path returns `type: "legal"` and the document shape in §3.1.12, not `sections[]`. The
section array is the render order, fixed from
PRD §5 and **not editable in Phase 1**; an editor orders items inside a section, never
the sections themselves (`CONTRACT.md` "Landing page"; `DATABASE.md` `page_section`).
Each section's `key` doubles as its anchor (`#services`, `#work`), so a key can never be
renamed.

Two rules apply to every section:

- CTA **targets** are fixed by decision 54. Only labels are content. The hero's primary,
  the not-sure CTA and the settings `cta` point at `#contact`; the hero's secondary
  points at `#work` (`CONTRACT.md` "Landing page").
- Empty **proof figures, testimonials and FAQs are omitted at read time**, not blocked
  at publish. Services, work, how we work, about and contact are gated and never
  omitted (`CONTRACT.md` "What blocks a publish"; decision 8).

The header menu and the footer are **not settings fields**. Each of the five sections —
Services, Work, How we work, About, Contact — carries its own `nav_label`, and the
header renders those five values (NV-1). The footer's stored links are the separate
`footer_links` list on settings, seeded from those labels; legal links are appended from
`/routes` (`CONTRACT.md` "Site settings"; `ADMIN.md` §9; decision 6). The page payload
carries no header or footer object.

#### 3.1.1 Page shell

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `type` | string | fixed | — | `landing`. |
| `path` | string | fixed | — | `/`; one landing page, never created from the UI (A16). |
| `revision` | integer | read-only | — | page version number; increments on each page publish. |
| `published_at` | ISO 8601 | read-only | — | null when there is no live page. |
| `seo.title` | string | yes at publish | 60 | must be non-empty and unique across live pages (NF-5). |
| `seo.description` | string | yes at publish | 160 | must be non-empty and unique across live pages (NF-5). |
| `seo.og_image` | media object or null | no | 0–1 | same shape as `images[]`, host-free `/media/...` URL. |
| `seo.noindex` | boolean | no | — | default `false` (`DATABASE.md:490`); no editor control is defined (U1). |
| `sections[]` | array | fixed | 10 | render order; no add, remove or reorder. |
| `sections[].key` | enum | fixed | — | `hero`, `proof`, `services`, `not-sure`, `work`, `process`, `about`, `testimonials`, `faqs`, `contact`. |
| `sections[].type` | enum | fixed | — | `hero`, `proof_figures`, `service_groups`, `not_sure`, `featured_work`, `how_we_work`, `about`, `testimonials`, `faqs`, `contact`. |
| `sections[].nav_label` | string or null | yes for five | 24 | present on Services, Work, How we work, About, Contact; null on the other five. |
| `sections[].data` | object | fixed | — | shape by `key`, in §3.1.2–§3.1.11. |

Each section also has its own `status` and `revision` on the **admin** read only; the
public payload carries neither (`CONTRACT.md` "Landing page"; §4.5). The page is
published with `POST /api/v1/admin/pages/{item_id}/publish` and
`{page_version_id, sections[]}` (`ADMIN.md:332`); the element shape is not defined (U2).

#### 3.1.2 Hero

Key `hero`; the only section with an eyebrow and two CTAs. Its `heading` is the page's
only `h1` (`CONTRACT.md` "Head and structured data").

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `eyebrow` | string or null | no | 48 | optional kicker; null renders nothing (decision 15). |
| `heading` | string | yes | 70 | the one headline. |
| `body` | string | no | not stated | one or two lines; the publish gate does not require it. |
| `primary_cta.label` | string | yes | 30 | label is content. |
| `primary_cta.href` | string | fixed | — | `#contact`; read-only (decision 54). |
| `secondary_cta.label` | string | yes | 30 | label is content. |
| `secondary_cta.href` | string | fixed | — | `#work`; read-only (decision 54). |

#### 3.1.3 Proof figures

Key `proof`; the section has **no heading** and no copy of its own. Items are references
to `proof_figure` records, each with its own approval and order
(`CONTRACT.md` "Records behind the sections"; `DATABASE.md` `section_version` check). At
most four. Empty items hide the section at read time.

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `items[]` | array | no | 0–4 | array position is render order. |
| `items[].label` | string | yes | 40 | what the number counts. |
| `items[].value` | string | yes | 12 | stored as a string, not a number. |
| `items[].prefix` | string or null | no | 4 | e.g. a currency mark; never invent one. |
| `items[].suffix` | string or null | no | 4 | e.g. `+` or `%`. |

Every published figure needs an unexpired, unrevoked approval with the `figure` scope
(`ADMIN.md` §6). Approval state is admin-only and never on the public wire (decision 4).

#### 3.1.4 Services

Key `services`; `nav_label` is required at publish (NV-1). Three or four groups, two to
six services in each, service titles unique across the set and never `__other__`
(`CONTRACT.md` "Records behind the sections"; decisions 29 and 63).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `intro` | string | no | 200 | one sentence, sits beside the heading. |
| `nav_label` | string | yes | 24 | header label; also the anchor text. |
| `groups[]` | array | yes | 3–4 | groups are records. |
| `groups[].title` | string | yes | 40 | category name; renaming is one edit. |
| `groups[].items[]` | array | yes | 2–6 | services inside the group. |
| `groups[].items[].title` | string | yes | 60 | unique across all services; `__other__` refused. |
| `groups[].items[].summary` | string | yes | 160 | outcome-led sentence. |

The same live titles feed the enquiry chips through `contact.data.form.services`
(§3.1.11); a title that has ever published remains a valid enquiry choice after it is
unpublished (decision 61).

#### 3.1.5 Not sure what you need?

Key `not-sure`. The CTA lands on the form with the message field focused (LP-4).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | short prompt. |
| `body` | string | no | not stated | one line. |
| `cta.label` | string | yes | 30 | label is content. |
| `cta.href` | string | fixed | — | `#contact`; read-only (decision 54). |

#### 3.1.6 Featured work

Key `work`; `nav_label` is required at publish. Three to six published projects; fewer
than three blocks the section (`CONTRACT.md` "What blocks a publish"). Projects are
records with their own order and approval, and publishing a project moves it without a
page republish (`CONTRACT.md` "Records behind the sections").

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `intro` | string | no | 200 | one sentence, sits beside the heading. |
| `nav_label` | string | yes | 24 | header label. |
| `items[]` | array | yes | 3–6 | published projects; order comes from each project's own order, not this array. |
| `items[].id` | string | read-only | — | opaque, stable; the admin route key. |
| `items[].title` | string | yes | 60 | project title. |
| `items[].client` | string or null | no | 80 | null means withheld, and needs the `client_name` approval scope to name. |
| `items[].client_need` | string | yes | 280 | the problem, in one or two sentences. |
| `items[].built` | string | yes | 280 | what was built. |
| `items[].technologies` | string[] | no | 0–8 items, 40 each | rendered beside what was built (SV-3). |
| `items[].result` | string or null | no | 280 | null means withheld; claiming a result needs the `result` scope. |
| `items[].images[]` | array | no | 0–3 | screenshots; a project with images needs the `screenshots` scope. |
| `items[].images[].url` | string | read-only | — | site-relative `/media/<id>.<ext>`; never a provider host. |
| `items[].images[].alt` | string | yes | 120 | written by the uploader. |
| `items[].images[].width` | integer | read-only | — | intrinsic width, for CLS. |
| `items[].images[].height` | integer | read-only | — | intrinsic height, for CLS. |

#### 3.1.7 How we work

Key `process`; `nav_label` is required at publish. Exactly four stages and exactly three
assurances (code ownership, security, UK-hours contact). Stage numbers come from array
position, never a stored `01`, `02` (`CONTRACT.md` "Landing page"; decision 13).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `intro` | string | no | 200 | one sentence. |
| `nav_label` | string | yes | 24 | header label. |
| `stages[]` | array | yes | exactly 4 | position is the stage number. |
| `stages[].title` | string | yes | 40 | stage name. |
| `stages[].body` | string | yes | 160 | one line. |
| `assurances[]` | array | yes | exactly 3 | — |
| `assurances[].title` | string | yes | 40 | assurance name. |
| `assurances[].body` | string | yes | 160 | one line. |

#### 3.1.8 About

Key `about`; `nav_label` and a non-empty section are required at publish (NV-1). Phase 1
is prose plus one image; there is no team list (decision 65). `about.body` is an array,
one string per paragraph (decision 41).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `body` | string[] | yes | 1–4 paragraphs, 600 each | one textarea per paragraph; add and remove within the range. |
| `nav_label` | string | yes | 24 | header label. |
| `image` | media object or null | no | 0–1 | null until the identity is settled. |

#### 3.1.9 Testimonials

Key `testimonials`; heading only. At most six. Attribution is all-or-nothing: a null
`name` means the client withheld it, and then `role` and `company` are null too. The
quote needs the `quote` approval scope; the name needs `client_name`
(`CONTRACT.md:278-280`; "Records behind the sections"; decision 62). Empty items hide
the section at read time.

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `items[]` | array | no | 0–6 | — |
| `items[].id` | string | read-only | — | opaque, stable. |
| `items[].quote` | string | yes | 280 | the words the client approved in writing. |
| `items[].name` | string or null | no | 60 | null withholds the name; then `role` and `company` must also be null. |
| `items[].role` | string or null | no | 80 | null when withheld; otherwise optional. |
| `items[].company` | string or null | no | 80 | null when withheld; otherwise optional. |

#### 3.1.10 FAQs

Key `faqs`; heading only. Five to eight **published** questions; outside that range is a
CMS warning, never a publish refusal (LP-5 is a Should; decision A13). Each question
carries its own status and order; a draft question is visible in the admin and filtered
from the public payload (`CONTRACT.md` "Landing page"; `DATABASE.md` `faq_item`). Empty
items hide the section at read time.

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `items[]` | array | no | 5–8 published (warning); drafts do not count | — |
| `items[].question` | string | yes | 120 | plain text. |
| `items[].answer` | string | yes | 600 | plain text; no rich text or HTML (decision 12). |

The admin read also carries each question's `status` and order; see §4.3. Only
`published` questions reach the public payload.

#### 3.1.11 Contact

Key `contact`; `nav_label` is required at publish. The section needs a heading, at least
one promise and a non-empty privacy note (`CONTRACT.md:491`). The live privacy notice is
a **landing-page** gate, not a section gate: the page refuses to publish without one
(`CONTRACT.md:488`), and decision 27 states the two as one check. Email, phone, hours and
locations are **not** section fields: they come from settings (§3.2).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `body` | string | no | not stated | one line. |
| `nav_label` | string | yes | 24 | header label. |
| `next_steps[]` | array | yes | 1–4 items | the promise the confirmation carries is D-11's (decision 26). |
| `next_steps[].title` | string | yes | 80 (form cap 40, C3) | the promise; the database caps it at 40. |
| `next_steps[].body` | string | yes | 200 (form cap 160, C3) | one line of detail; the database caps it at 160. |
| `privacy_note.text` | string | yes | 240 | one sentence shown beside the form. |
| `privacy_note.link_label` | string | yes | 40 | link text; the target is `/privacy`. |
| `form.services` | string[] | read-only | — | computed at read time from published service titles, never stored (decision 48). |

`form.services` is computed, not edited. When it is empty the service field is hidden
and the enquiry sends `service: null` (`CONTRACT.md` "What the browser sends").

#### 3.1.12 Legal page

A legal path returns `type: "legal"` and this document shape (`CONTRACT.md:638-698`).
Blocks are edited on the legal-page screen; the four kinds, their limits and the
add/remove/reorder rules are in §4.3.1.

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `type` | string | fixed | — | `legal`. |
| `path` | string | fixed | — | `/privacy`, `/cookies`, `/terms` or `/accessibility`; set at create, no path edit (§4.3.1). |
| `revision` | integer | read-only | — | legal page version number; increments on each publish. |
| `published_at` | ISO 8601 | read-only | — | null when there is no live page. |
| `seo.title` | string | yes at publish | 60 | non-empty and unique across live pages (NF-5). |
| `seo.description` | string | yes at publish | 160 | non-empty and unique across live pages (NF-5). |
| `seo.og_image` | media object or null | no | 0–1 | same shape as `images[]`; host-free `/media/...` URL. |
| `seo.noindex` | boolean | no | — | default `false` (`DATABASE.md:490`); no editor control is defined (U1). |
| `title` | string | yes at publish | 70 | rendered as the page's `h1`; the footer uses `label` from `/routes`, not this. |
| `updated_on` | date | read-only | — | the publication instant's date in `Europe/London`, formatted as a UK date; never the server's session date. |
| `effective_on` | date | always | — | the draft may hold null, meaning the London publish date; a set date is shown as written and may be in the future. |
| `blocks[]` | array | yes | at least 1 | add, remove and reorder; limits in §4.3.1. |
| `blocks[].kind` | enum | yes | — | `h2`, `p`, `ul`, `table`. |
| `blocks[].text` | string | yes for `h2` and `p` | `h2` 60, `p` 2000 | plain text; no HTML or Markdown. |
| `blocks[].items[]` | string[] | yes for `ul` | 1–12 items, 200 each | list items. |
| `blocks[].columns[]` | string[] | yes for `table` | count not stated | column labels; the editor owns them (U10). |
| `blocks[].rows[][]` | string[][] | yes for `table` | 1–30 rows | one cell per column; cell length not stated. |

`label` is the footer text and is returned by `/routes`, not here; the company identity
line above the blocks comes from settings (`CONTRACT.md` "Legal page").

### 3.2 `GET /api/v1/public/settings`

| | |
| --- | --- |
| Method and path | `GET /api/v1/public/settings` |
| Auth | service token only |
| Cache tag | `settings` |
| Response | `{ revision, data: { … } }` |
| Errors | `500 internal_error`, `503 service_unavailable`; no `404` is defined |

Settings are one versioned item; the live site changes only on publish (`ADMIN.md` §9).
The public names below are nested; the admin request names are flat and mapped in §2.5.

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `revision` | integer | read-only | — | settings version number. |
| `data.company.legal_name` | string | yes at publish | not stated | the parent's exact legal name. |
| `data.company.trading_name` | string | no | not stated | trading name. |
| `data.company.country` | string | yes at publish | not stated | the parent's country. |
| `data.company.address` | string[] | yes at publish | 2–4 lines, 80 each | legal address; rendered on privacy, terms, footer and contact. |
| `data.company.uk_establishment` | boolean | no | — | true makes the regulation 63 fields required. |
| `data.company.home_registry` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `data.company.registration_number` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `data.company.head_office_location` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `data.company.legal_form` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `data.company.limited_liability` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `data.company.insolvency_information` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `data.company.vat_number` | string or null | no | not stated | the VAT line renders only when set. |
| `data.logo` | media object or null | no | 0–1 | header logo; null renders the repository asset. |
| `data.nepal_site_url` | string or null | no | 200 † | hreflang target; null until confirmed. |
| `data.contact.email` | string | yes at publish | 254 † | one monitored address for the whole site. |
| `data.contact.phone` | string or null | no | 32, E.164 | the site's contact line; requires `contact.phone_hours`. |
| `data.contact.phone_hours` | string or object | when `contact.phone` is set | shape disputed (C1) | the hours the line is answered. |
| `data.contact.hours.summary` | string | no | 120 | UK opening hours (`CONTRACT.md:1111`). |
| `data.contact.hours.timezone` | string | fixed | — | `Europe/London`; no other value is specified. |
| `data.locations[]` | array | no | — | contact list; a location appears only when it is real. |
| `data.locations[].name` | string | yes | 60 | city. |
| `data.locations[].address` | string[] | yes | 2–4 lines, 80 each | a real address; a city with no country is ambiguous. |
| `data.locations[].country` | string | yes | not stated | must sit beside the city. |
| `data.locations[].phone` | string or null | no | 32, E.164 | local contact line; requires `phone_hours`. |
| `data.locations[].phone_hours` | string or object | when `locations[].phone` is set | no limit stated | shape disputed (C1/C2). |
| `data.footer_note` | string | no | 160 | one line. |
| `data.footer_links[]` | array | no, seeded with 5 | — | ordered site links; legal links are appended from `/routes`, not stored here. |
| `data.footer_links[].label` | string | yes | 40 | link text. |
| `data.footer_links[].href` | string | yes | 200 | anchor or path. |
| `data.seo_defaults.title_suffix` | string | no | 40 | appended only when the page title does not already end with it. |
| `data.seo_defaults.description` | string | no | 160 | fills a page that omits its own. |
| `data.seo_defaults.og_image` | media object or null | no | 0–1 | fallback social card. |
| `data.cta.label` | string | yes at publish | 30 | header and footer button label. |
| `data.cta.href` | string | fixed | — | `#contact`; read-only (decision 54). |

The header menu labels are the five section `nav_label` values, not settings fields; the
footer links are `data.footer_links` seeded from them (§3.1). `booking_url` and
`booking_label` are stored but appear nowhere in this payload and cannot be edited
(decision 46, A7). `working_hours[]` is a database-only child row shape (U7; §12).

### 3.3 `GET /api/v1/public/routes`

| | |
| --- | --- |
| Method and path | `GET /api/v1/public/routes` |
| Auth | service token only |
| Cache tag | `routes` |
| Response | `{ items: [...] }` — every published path with footer and sitemap metadata |
| Errors | `500 internal_error`, `503 service_unavailable` |

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `items[].path` | string | read-only | — | published path, `/` or `/privacy`-style. |
| `items[].type` | enum | read-only | — | `landing` or `legal`; Phase 1 has two, a third is a schema change. |
| `items[].label` | string or null | read-only | 40 | footer link text; null for the landing page. |
| `items[].lastmod` | date | read-only | — | the publication instant's date in `Europe/London`. |
| `items[].noindex` | boolean | read-only | — | the page's flag; the sitemap may omit it while the footer still links it. |

`/routes` is how the footer gets legal links and how the sitemap gets every published
path (`CONTRACT.md` "The calls").

### 3.4 `POST /api/v1/public/enquiries`

| | |
| --- | --- |
| Browser call | `POST /api/enquiries` on the Next origin, same-origin JSON, 16KB cap |
| Next call | `POST /api/v1/public/enquiries`, service token, server-to-server |
| Cache | none; never cached |
| Success | `201 { "status": "received" }` |
| Errors | `validation_failed` 422, `rate_limited` 429, `verification_failed` 400, `service_unavailable` 503, `internal_error` 500 (`CONTRACT.md:859-886`). |

The form is component code. Its labels, validation copy, error copy and confirmation are
code, not editable content (decision 19).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `name` | string | yes | 1–100 | text; trimmed. |
| `email` | string | yes | 254 | one address; checked by Pydantic and again by the browser. |
| `company` | string or null | no | 0–120 | trimmed; null when empty. |
| `service` | string or null | yes when options exist | one ever-published title or `__other__`; 60 † | radio chips in one group; the last chip, "Something else", sends `__other__` and is not a service row. |
| `message` | string | yes | 1–2000 | plain text, line breaks kept. |
| `website` | string | must be empty | 0 | honeypot; hidden from sight and assistive technology. |
| `turnstile_token` | string | yes | — | Cloudflare Turnstile token; verified once, server-side, after the rate-limit check (`CONTRACT.md:836-845`, `:937`). |

**The Turnstile widget.** It sits above the send button and is not CMS content. States:
loading, ready, verifying, failed (the token expired or the challenge was rejected) and
not loaded. A failed or missing token keeps the visitor's text, asks for another try and
surfaces the API's `verification_failed` (400). If the script cannot load, or JavaScript
is off, the form shows the site email address instead of a dead button; there is no
fallback submission without a token (`CONTRACT.md:980-981`).

**BFF boundary.** The browser never sends an address. Next derives the visitor's single
`X-Client-IP` from the platform (`x-vercel-forwarded-for`; `CF-Connecting-IP` only when
the platform address is inside Cloudflare's published ranges) and sends it with
`X-Service-Token`; FastAPI rate-keys on that one header and never reads
`X-Forwarded-For` (`CONTRACT.md:75-92`). Logs carry only the enquiry id, the outcome and
the hashed address: never the message, the email or the raw address
(`CONTRACT.md:830-832`).

Not browser fields: `source_path` is set by Next.js from the same-origin `Referer` (path
only, no query string, 200 max); `consent_notice_version` is set by FastAPI at save time
as `landing-r<revision>+privacy-r<revision>` (64 max). The browser cannot forge either
(`CONTRACT.md:854-857`).

No phone, budget, timeframe or marketing tick box. EN-2 fixes the list; decision 46
dropped the budget field and the booking link; EN-3 sends without a marketing opt-in.

**Responses and states.** A honeypot hit returns 201 and saves nothing. A failed
confirmation email does not fail the submission. On 503, 500, a network failure or a
timeout, keep the visitor's text and show the site email (EN-8). Field errors go under
the field with `aria-invalid`, focus moves to the first, the confirmation is announced
and focused, and pressing send twice sends once (`CONTRACT.md` "What comes back", "After
a send"). Rate limits are 5 per 10 minutes and 20 per hour per address, and 3 per hour
per email; every attempt is counted, including rejections (`CONTRACT.md:889-925`).

## 4. Admin endpoints

Base path `/api/v1/admin`; Next proxies the same names under `/api/admin`. Every response
is `no-store` (T36). Every endpoint can return the universal failures in §2.3, which are
not repeated per row. The 48 rows below are the inventory in `ADMIN.md` §4, regrouped by
the client that calls them.

### 4.1 Auth and me — 5 endpoints

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `POST /auth/sign-in` | signed out | `email`, `password` | session tokens for Next, or `403 mfa_required` with `challenge_id` |
| `POST /auth/mfa/verify` | `aal1` | `challenge_id`, `code` | session tokens for Next |
| `POST /auth/sign-out` | any staff | — | `204` |
| `POST /auth/password-reset` | signed out | `email` | `202` always |
| `GET /me` | any staff | — | `staff_account`: `user_id`, `display_name`, `email`, `role`, `active`, `mfa_status`, `last_sign_in_at` |

- Sign-in goes browser → Next → FastAPI → Supabase Auth; FastAPI records every attempt,
  success or failure (`ADMIN.md` §2, A10). `invalid_credentials` never says whether the
  account exists (T41); repeated failures return `429 too_many_attempts` (T42).
- The MFA step is `mfa_required` with a `challenge_id`; the code is TOTP and the result
  is an AAL2 session (`ADMIN.md:110-120`; A6). `GET /me` is the one endpoint `aal1` may
  reach, with `/auth/mfa/verify` and `/auth/sign-out`.
- Password reset is Supabase Auth's email flow; the API returns `202` whether or not the
  address exists. A reset is audit-logged (`ADMIN.md:113-117`; A14).
- An invite is `POST /staff/invites` (§4.10). The invited person sets their own password
  through Supabase Auth's invite link; no route or field for that landing page is
  defined in ADMIN.md (U17), and the invite expires after 7 days (AD-1).
- Sign-in screen states: credentials, MFA challenge, error, locked (`429`), idle
  (`?reason=idle`) and expired (`?reason=expired`) (`ADMIN.md:121-128`).

### 4.2 Dashboard — 1 endpoint

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /dashboard` | both roles | — | drafts, in review, new enquiries, expiring approvals, failed revalidation (`ADMIN.md:322`) |

`ADMIN.md:322` describes the five counts in prose and names no JSON key; do not hard-code
names, build the cards against OpenAPI (U3). The dashboard endpoint is both roles, but
the enquiry screen and the actions on approvals and revalidation are Admin only. States:
loading, empty, error. Actions: follow a count to its filtered list; follow a blocker to
the item.

### 4.3 Content CRUD and versions — 8 endpoints

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /content` | both (legal_page/settings: Admin) | `kind`, `status`, `q`, `archived`, `page`, `per_page`, `sort` | `Page<ItemSummary>` |
| `POST /content` | both (legal_page: Admin) | `kind`, `path?`, `slug?` | item, first draft, `ETag` |
| `GET /content/{item_id}` | both (legal_page/settings: Admin) | — | `item`, `version`, typed body, children, `revision`, `ETag` |
| `GET /content/{item_id}/versions` | both (legal_page/settings: Admin) | `page` | `Page<VersionSummary>` |
| `GET /content/{item_id}/versions/{version_id}` | both (legal_page/settings: Admin) | — | typed body and children, read-only |
| `POST /content/{item_id}/drafts` | both (legal_page/settings: Admin) | — | existing open version or a new one, `ETag` |
| `PATCH /content/{item_id}/drafts/{version_id}` | both (legal_page/settings: Admin) | `If-Match`, typed body | version, `revision`, `ETag` |
| `POST /content/{item_id}/drafts/{version_id}/submit` | both (legal_page/settings: Admin) | `If-Match` | version, `status: in_review` |

- `GET /content` sorts and paginates by §2.2. An Editor's list omits `legal_page` and
  `settings`; naming either `kind` returns `403 forbidden` (`ADMIN.md:392-395`).
- `POST /content` creates the item and its first draft in one call. Only the creatable
  kinds accept it: `service_group`, `service`, `project`, `proof_figure`, `testimonial`,
  `client_logo` and `legal_page` (Admin only). The landing page, its ten sections and
  settings are seeded and never created from the UI (A16). `path` and `slug`
  optionality is C4.
- One open version per item; `POST /drafts` returns the existing open version with `200`
  rather than duplicating it (A4, `ADMIN.md` §5).
- `PATCH` updates the typed table and sets `content_version.updated_by`; it never edits a
  published version (`ADMIN.md:425-428`). A published item is edited by creating a draft
  copied from live first.
- Submit moves `draft → in_review`; an Admin may publish a draft directly and skip
  review (`ADMIN.md` §5).

#### 4.3.1 The typed body by kind

The request body is the kind's typed table with flat columns. `content_seo` is part of
every page kind's body (`ADMIN.md:399-402`). A field not listed here is not a Phase 1
control; long descriptions, categories and working-hour rows are in §12.

**Landing page, section, legal page — the common `content_seo` block**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `seo_title` † | string | yes at publish | 60 | non-empty and unique across live pages (NF-5); `DATABASE.md:488`. |
| `seo_description` † | string | yes at publish | 160 | non-empty and unique (NF-5); `DATABASE.md:489`. |
| `seo_noindex` † | boolean | no | — | database default `false` (`DATABASE.md:490`); no editor control is defined (U1). |
| `og_image_id` † | uuid or null | no | 0–1 | media row; public name `seo.og_image`. |

**Section — `section_version` plus children**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `heading` | string or null | yes for most | 70 | `proof` has none. |
| `eyebrow` | string or null | no | 48 | `hero` only. |
| `intro` | string or null | no | 200 | `services`, `work`, `process` only. |
| `body` | string or null | no | not stated | `hero`, `not-sure`, `contact` only. |
| `nav_label` | string or null | yes for services, work, process, about, contact | 24 | NV-1; null on the other five. |
| `primary_label` | string or null | hero | 30 | hero only. |
| `primary_href` | string or null | fixed | — | `#contact`; not editable (decision 54). |
| `secondary_label` | string or null | hero | 30 | hero only. |
| `secondary_href` | string or null | fixed | — | `#work`; not editable (decision 54). |
| `cta_label` | string or null | not-sure | 30 | not-sure only. |
| `cta_href` | string or null | fixed | — | `#contact`; not editable (decision 54). |
| `privacy_text` | string or null | contact | 240 | contact only. |
| `privacy_link_label` | string or null | contact | 40 | contact only. |
| `image_id` † | uuid or null | no | 0–1 | about only; `DATABASE.md:622`. |
| `paragraphs` | `section_paragraph` rows † | about | 1–4, `text` 600 | `text` per row; `DATABASE.md:690-700`. |
| `stages` | `process_stage` rows † | process | exactly 4; `title` 40, `body` 160 | `DATABASE.md:702-732`. |
| `assurances` | `process_assurance` rows † | process | exactly 3; `title` 40, `body` 160 | `DATABASE.md:712-732`. |
| `next_steps` | `contact_next_step` rows † | contact | 1–4; `title` 40 †, `body` 160 † | C3; `DATABASE.md:750-763`. |
| `faqs` | `faq_item` rows † | faqs | 5–8 published (warning); `question` 120, `answer` 600, `status` `published`/`draft` | `DATABASE.md:734-748`. |
| `items` | `section_version_item` rows † | proof, services, work, testimonials | — | `item_id`, `item_kind`, `sort_order` † (`DATABASE.md:813-834`). |

A `†` child is a database table; the request array's key is OpenAPI's (U9). `images[]`
and `technologies[]` are the two child names ADMIN itself gives (`ADMIN.md:400`).

`section_version_item` is how the four record-backed sections select their records:
`item_kind` is `service_group`, `project`, `proof_figure` or `testimonial`; `sort_order`
is present for groups, figures and testimonials, and null for projects, whose order is
the project's own (`DATABASE.md:836-848`).

**Service group — `service_group_version`**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `title` | string | yes | 40 | category name. |

**Service — `service_version`**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `group_item_id` | uuid | yes | — | the group it belongs to. |
| `title` | string | yes | 60 | unique across the set; `__other__` refused. |
| `summary` | string | yes | 160 | outcome-led sentence. |
| `sort_order` † | integer | no | — | order inside the group; `DATABASE.md:883`. |

**Project — `project_version` plus children**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `title` | string | yes | 60 | project title. |
| `client` | string or null | no | 80 | null withholds the name; naming needs the `client_name` scope. |
| `client_need` | string | yes | 280 | the problem, in one or two sentences. |
| `built` | string | yes | 280 | what was built. |
| `result` | string or null | no | 280 | claiming a result needs the `result` scope. |
| `sort_order` † | integer | no | — | live order in Featured work; `DATABASE.md:963`. |
| `technologies[]` | `project_technology[]` | no | 0–8; `name` 40 † | `name` per row; `DATABASE.md:983-993`. |
| `images[]` | `project_image[]` | no | 0–3; `media_id` †, `sort_order` † | landscape only, 16:10 at render; `DATABASE.md:995-1003`. |

**Proof figure — `proof_figure_version`**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `label` | string | yes | 40 | what the number counts. |
| `value` | string | yes | 12 | real numbers only. |
| `prefix` | string or null | no | 4 | never invent one. |
| `suffix` | string or null | no | 4 | never invent one. |

**Testimonial — `testimonial_version`**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `quote` | string | yes | 280 | the words the client approved in writing. |
| `name` | string or null | no | 60 | null withholds the name; then `role` and `company` must be null. |
| `role` | string or null | no | 80 | null when withheld; otherwise optional. |
| `company` | string or null | no | 80 | null when withheld; otherwise optional. |

**Client logo — `client_logo_version`**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `client_name` | string or null | no | not stated | null withholds the name; naming needs the `client_name` scope. |
| `image_id` † | uuid or null | yes when the mark is shown | 0–1 | site image; `DATABASE.md:1128`; no logo slot until D-9. |

**Legal page — `legal_page_version` plus blocks**

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `path` | string | yes at create | — | `/privacy`, `/cookies`, `/terms` or `/accessibility`; the API defines no path edit. |
| `label` | string | yes | 40 | footer link text; returned by `/routes`. |
| `title` | string | yes | 70 | rendered as the page's `h1`. |
| `effective_on` | date or null | no | — | null means the London publish date; a set date may be in the future. |
| `blocks[]` | `legal_block[]` | yes | at least 1 | add, remove and reorder. |
| `blocks[].kind` | enum | yes | — | `h2`, `p`, `ul`, `table`. |
| `blocks[].text` | string | yes for `h2` and `p` | `h2` 60, `p` 2000 | no HTML, no Markdown. |
| `blocks[].items[]` | string[] | yes for `ul` | 1–12 items, 200 each | list items. |
| `blocks[].columns[]` | string[] | yes for `table` | count not stated | column labels; the cookies sample uses Cookie, Purpose, Duration, and the prose also names provider. |
| `blocks[].rows[][]` | string[][] | yes for `table` | 1–30 rows | one cell per column; cell length not stated. |

`revision` and `updated_on` are derived and read-only, not body fields; the public shape
is §3.1.12.

#### 4.3.2 Shared item chrome

Every item screen shows `status` (`draft`, `in_review`, `published`, `unpublished`,
`archived`), the open version's `revision`, "last changed by" and when, and the publish
blockers before Publish is enabled (`ADMIN.md:214-216`). `unpublished` means no pointer
and no open draft. `updated_by` † is `coalesce(updated_by, created_by)`, or
`published_by` when nothing is open; `updated_at` † has the same derivation
(`ADMIN.md` §10). `blockers[]` arrives on `409 publish_blocked`; `warnings[]` is
non-blocking, and the FAQ count outside 5–8 is the known one (A13).

#### 4.3.3 Version history

`GET /content/{item_id}/versions` returns `Page<VersionSummary>`: `revision`, `status`,
`created_by` † (author), `created_at` †, `updated_at` † and `published_at` †. It is a
read-only list with a read-only view of any version; a published version is never
editable (`ADMIN.md:234`). `submitted_at` is not named as a field (§12).

### 4.4 Publish lifecycle — 6 endpoints

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `POST /content/{item_id}/publish` | Admin | `If-Match` | `revision`, `warnings[]`, revalidation state |
| `POST /pages/{item_id}/publish` | Admin | `If-Match`, `{page_version_id, sections[]}` | `revision`, `warnings[]`, `blockers[]` |
| `POST /content/{item_id}/unpublish` | Admin | `If-Match` | item state; pointer removed, draft created or the in-review version kept |
| `POST /content/{item_id}/archive` | Admin | `If-Match`, `{confirm_title}` | item state `archived` |
| `POST /content/{item_id}/restore` | Admin | — | item state `unpublished`, or the open draft that survived |
| `POST /content/{item_id}/delete` | Admin | `If-Match`, `{confirm_title}` | `204` |

- `POST /pages/{item_id}/publish` takes the page version and the section versions being
  published. A section left out keeps its current live version; a section that has never
  published blocks the page. All pointers move in one transaction, page last
  (`ADMIN.md:553-570`). The element shape of `sections[]` is U2.
- Publish gates return `409 publish_blocked` with `blockers[]` naming each; the response
  may carry `warnings[]` for a non-blocking Should-level issue (A13). The page gates are
  all ten sections live, both SEO fields, a live privacy notice and published settings
  (`CONTRACT.md` "What blocks a publish").
- **Unpublish** deletes the publication pointer and leaves the item on a draft copy of
  the last published version — created in the same transaction — or on the existing
  in-review version, which stays in review (`ADMIN.md:522`; decision 69). It names the
  public path and warns that the page disappears within a minute (`ADMIN.md` §3). An
  existing open draft is reused, never duplicated.
- **Archive** is the normal delete: it unpublishes first, then marks the item archived in
  one transaction; it creates no draft. Archiving the landing page archives its sections
  (`ADMIN.md` §5; decision 70).
- **Restore** clears the flags and leaves the item `unpublished`, or in the draft that
  survived; it does not republish and writes no revalidation row. It takes no `If-Match`.
- **Permanent delete** exists only for an item that was never published, carries no
  approval, is not one of the three fixed kinds (landing page, its sections, settings)
  and is not referenced by a section draft or a service group's services. It requires
  the typed title, cannot be undone, writes one `delete` audit row and frees the path or
  slug. A legal page is creatable, so a never-published legal draft may be deleted
  (decision 70).

### 4.5 Page read — 1 endpoint

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /pages/{item_id}` | both roles | — | sections, each `status`, `pointer` and `revision` (`ADMIN.md:337`) |

`pointer` is the section's current publication pointer: which version is live, or null
when the section has no live version (`ADMIN.md:337`). This is the dedicated page read;
an Editor may call it (`ADMIN.md:393`). It carries the landing page only, and its section
list is where an Editor sees per-section state.

### 4.6 Approvals — 4 endpoints

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /approvals` | Admin | `state`, `subject_kind`, `page` | approvals with current state |
| `POST /content/{item_id}/versions/{version_id}/approvals` | Admin | body below | approval |
| `POST /approvals/{approval_id}/revoke` | Admin | `{note}` | approval, now revoked |
| `POST /content/{item_id}/versions/{version_id}/legal-approval` | Admin | — | legal approval row |

An approval attaches to a **version**, not an item, so an edit to an approved quote,
result or mark needs a new approval before it can publish (decision 31; `ADMIN.md` §6).

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `subject_kind` | enum | read-only | — | derived from the version: `project`, `proof_figure`, `testimonial`, `client_logo`. |
| `approved_by_name` | string | yes | 120 † | the client contact, not the staff member. |
| `approved_by_email` | string or null | no | not stated | nullable; ADMIN lists it in the body but states no required rule (`ADMIN.md:603-604`; `DATABASE.md:1526`). |
| `approved_on` | date | yes | not in the future | the date the client approved. |
| `expires_on` | date or null | no | ≥ `approved_on` | null means no expiry. |
| `scopes[]` | enum[] | yes | subject-dependent | project: `client_name`, `result`, `mark`, `screenshots`; figure: `figure`; testimonial: `quote` plus optional `client_name`; logo: `mark` plus optional `client_name`. |
| `evidence_media_id` | uuid or null | no | evidence bucket | email or document in the private evidence bucket. |
| `recorded_by` | string | read-only | — | the Admin who recorded it. |
| `state` | enum | read-only | — | **Provisional key and values**, inferred from the screen badges (`ADMIN.md:179-180`): `live`, `awaiting approval`, `approval missing`, `expired`, `revoked`. ADMIN names no response key; OpenAPI defines it (U9). |
| `note` | string | yes on revoke | 500 † | the revocation note, stored as `revocation_note`; ADMIN names no limit, DATABASE caps it at 500 (`DATABASE.md:1548`). |

`subject_kind` and `recorded_by` are derived from the version and the caller and are not
in the request body. The revoke body is `{note}`, stored as `revocation_note`
(`ADMIN.md:340`); revocation cannot be undone, and the row keeps `revoked_at`,
`revoked_by` and the note (`ADMIN.md:625-630`). Revocation does not unpublish; it queues
revalidation only for pages whose live section versions reference the record, which may
be none. Expiry is a date in `Europe/London` (`ADMIN.md` §6).

The legal approval endpoint takes no body. The approver is the Admin who records it, and
the API refuses an approver who is the author (`ADMIN.md` §6; PRD §7).

### 4.7 Media and evidence — 6 endpoints

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `POST /media` | both | multipart file + `alt` | media row, staged |
| `GET /media` | both | `state`, `role`, `q`, `page` | `Page<MediaRow>` with usage |
| `GET /media/{media_id}` | both | — | media row; `url` signed for 5 minutes when private (proposed, A12) |
| `POST /media/{media_id}/delete` | both | — | media row, soft-deleted |
| `POST /evidence` | Admin | multipart file | media row in `evidence` |
| `GET /evidence/{media_id}/url` | Admin | — | `{url}`, signed for 60 seconds (proposed, A12) |

Evidence is never returned by `GET /media`: that list is `media-staging` and
`site-media` only, and an evidence id is `404 not_found` (T3; `ADMIN.md` §4).

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `id` | uuid | read-only | — | opaque; the route key. |
| `alt` | string | yes for every site image | 120 | required for every site image; evidence has no alt requirement (`DATABASE.md` `media_alt_required`). |
| `width` | integer | read-only | — | intrinsic width. |
| `height` | integer | read-only | — | intrinsic height. |
| `type` | string | read-only | — | MIME type, shown but never on the public wire (decision 53). |
| `size_bytes` | integer | read-only | ≤ 4MB | shown; never on the public wire. |
| `state` | enum | read-only | — | `staged`, `public`, `unused`, `deleted`. |
| `role` † | enum | no | — | `version_media.role` (`DATABASE.md:4026-4046`), values `project_image`, `about_image`, `og_image`, `client_logo`, `site_logo` (`DATABASE.md:169-175`); ADMIN names `role` as a `GET /media` filter (`ADMIN.md:343`), not a row schema. |
| `usage` † | integer or object[] | read-only | — | reference count in the list, references in the detail; ADMIN says "with usage" but names no key. |
| `uploaded_by` † | string | read-only | — | staff name (`DATABASE.md:270`). |
| `uploaded_at` | ISO 8601 | read-only | — | upload time. |
| `url` | string | read-only | — | signed while private; public `/media/...` when promoted. The list thumbnail. |
| `deleted_at` † | ISO 8601 or null | read-only | — | soft-delete time; the object goes when nothing references it. |

The media record is immutable: correcting alt text or replacing a file creates a **new
record**, and the old one stays while a version or approval references it
(`CONTRACT.md` "Media"; decision 37). ADMIN lists "replace" among the picker states
(`ADMIN.md:679-681`); it is an action that creates a new row: it uploads a new file,
repoints the reference and leaves the old row in place, so it belongs on a row, not in
the picker's state list (§11.2 C8). The picker states are idle, uploading with progress,
staged ("Publishes with the page"), public, unused, deleted, alt-text error,
type/size/pixel error and upload failed with retry.

Accepted types are JPEG, PNG and WebP for site media, plus PDF for evidence, checked by
magic bytes. The size cap is 4MB, the pre-decode guard is 40MP and 8192px per side, work
images are landscape 16:10, and the long edge is resized to 2000px (`CONTRACT.md`
"Media"; `ADMIN.md` §7). Evidence uploads go through `POST /evidence`, open only through
the signed link, and are never embedded (`ADMIN.md` §4, §6, §7; A12).

`ADMIN.md` names no multipart part name (U13). Do not assume `file` before OpenAPI.

### 4.8 Enquiries — 7 endpoints

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /enquiries` | Admin | `status`, `q`, `from`, `to`, `page` | `Page<EnquirySummary>` |
| `GET /enquiries/{enquiry_id}` | Admin | — | enquiry, `notes[]` |
| `PATCH /enquiries/{enquiry_id}` | Admin | `{status}` | enquiry |
| `POST /enquiries/{enquiry_id}/notes` | Admin | `{body}` | note |
| `POST /enquiries/{enquiry_id}/first-reply` | Admin | — | enquiry with `first_replied_at` |
| `GET /enquiries/export.csv` | Admin | same filters as the list | `text/csv` |
| `DELETE /enquiries/{enquiry_id}?confirm={enquiry_id}` | Admin | query `confirm` | `204` |

Admin only from list to delete; an Editor gets `403` and the screen is absent from their
navigation (`ADMIN.md` §8). Default order is newest first.

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `id` | uuid | read-only | — | route key. |
| `name` | string | read-only | 100 | from the submission. |
| `email` | string | read-only | 254 | from the submission. |
| `company` | string or null | read-only | 120 | from the submission. |
| `service` | string or null | read-only | 60 † | the title snapshot; null when the visitor chose "Something else". |
| `message` | string | read-only | 2000 | plain text; never emailed in the alert. |
| `source_path` | string | read-only | 200 | path only, no query string. |
| `consent_notice_version` | string | read-only | 64 | which landing and privacy revisions the visitor saw. |
| `status` | enum | yes | — | `new`, `in_progress`, `closed`; moves forward only, no reopening in Phase 1. |
| `created_at` † | ISO 8601 | read-only | — | received time. |
| `first_replied_at` | ISO 8601 or null | read-only | — | write-once; set by the first-reply action, not by triage. |
| `notes[].body` | string | yes on add | 1–4000 | internal only; never in an email. |
| `notes[].author_id` † | uuid | read-only | — | staff member. |
| `notes[].created_at` † | ISO 8601 | read-only | — | note time. |

Filters: `status`, `q` over name, email and company, `from`, `to`, page. Actions: open;
export CSV over the same filters. The export writes one audit row with the row count and
no personal data (AD-6, A14). Delete is the UK GDPR erasure path: typed record
confirmation, notes cascade, one audit row with no personal data (`ADMIN.md` §8).
The alert email carries name, company, service, received-at and a link, never the
message (`CONTRACT.md` "The emails"). States: loading, empty, filtered, error.

### 4.9 Settings — 1 endpoint

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /settings` | Admin | — | settings item, typed body, `revision`, `ETag` |

Settings writes use the content endpoints for the settings item (`PATCH /content/...`);
there is no separate settings write endpoint (`ADMIN.md:386-402`). The form's request
names are the flat `settings_version` and child-row columns, not the nested public
payload; §2.5 maps every one.

| Request field | Public name | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- | --- |
| `legal_name` | `company.legal_name` | string | yes at publish | not stated | the parent's exact legal name. |
| `trading_name` | `company.trading_name` | string or null | no | not stated | trading name. |
| `country` | `company.country` | string | yes at publish | not stated | the parent's country. |
| `settings_address_line` rows † | `company.address` | rows, `line` | yes at publish | 2–4 lines, 80 each | legal address. |
| `uk_establishment` | `company.uk_establishment` | boolean | no | — | true makes the regulation 63 fields required. |
| `home_registry` | `company.home_registry` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `registration_number` | `company.registration_number` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `head_office_location` | `company.head_office_location` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `legal_form` | `company.legal_form` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `limited_liability` | `company.limited_liability` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `insolvency_information` | `company.insolvency_information` | string or null | when `uk_establishment` | not stated | regulation 63. |
| `vat_number` | `company.vat_number` | string or null | no | not stated | the VAT line renders only when set. |
| `site_logo_id` † | `logo` | uuid or null | no | 0–1 | header logo. |
| `nepal_site_url` | `nepal_site_url` | string or null | no | 200 † | hreflang target; null until confirmed. |
| `contact_email` | `contact.email` | string | yes at publish | 254 † | one monitored address. |
| `contact_phone` | `contact.phone` | string or null | no | 32, E.164 | requires `contact_phone_hours`. |
| `contact_phone_hours` | `contact.phone_hours` | string or null | when `contact_phone` is set | shape disputed (C1) | the hours the line is answered. |
| `hours_summary` | `contact.hours.summary` | string or null | no | 120 | UK opening hours (`CONTRACT.md:1111`). |
| `hours_timezone` | `contact.hours.timezone` | string | fixed | — | `Europe/London`; no other value is specified. |
| `settings_location` rows † | `locations[]` | rows | no | — | `name` 60, `country` not stated, `phone` 32, `phone_hours` C1/C2. |
| `settings_location_address_line` rows † | `locations[].address` | rows, `line` | yes per location | 2–4 lines, 80 each | `DATABASE.md:1384-1400`. |
| `footer_note` | `footer_note` | string or null | no | 160 | one line. |
| `settings_footer_link` rows † | `footer_links[]` | rows, `label` 40, `href` 200 | no, seeded with 5 | — | ordered site links. |
| `seo_title_suffix` | `seo_defaults.title_suffix` | string or null | no | 40 | appended only when the title does not already end with it. |
| `seo_description` | `seo_defaults.description` | string or null | no | 160 | fills a page that omits its own. |
| `seo_og_image_id` † | `seo_defaults.og_image` | uuid or null | no | 0–1 | fallback social card. |
| `cta_label` | `cta.label` | string | yes at publish | 30 | header and footer button label. |
| `cta_href` | `cta.href` | string | fixed | — | `#contact`; read-only (decision 54). |

`booking_url` and `booking_label` are rejected with `422` when written (A7, decision 46);
do not render them. The settings item is a fixed kind: never created or deleted from the
UI, archive and restore exist (`ADMIN.md` §9; A16). States: draft, live, incomplete
identity, blocked. `working_hours[]` is not a form field (§12; U7).

### 4.10 Staff — 5 endpoints

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /staff` | Admin | `role`, `active`, `page` | `Page<StaffAccount>` |
| `POST /staff/invites` | Admin | `{email, display_name, role}` | staff row, invite state |
| `PATCH /staff/{user_id}` | Admin | `{role, active, display_name}` | staff row |
| `POST /staff/{user_id}/password-reset` | Admin | — | `202` |
| `POST /staff/{user_id}/mfa-reset` | Admin | — | `202` (A17) |

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `user_id` | uuid | read-only | — | route key. |
| `display_name` | string | yes | 100 † | shown in the list and audit. |
| `email` | string | yes | not stated | unique; Supabase Auth owns the identity. |
| `role` | enum | yes | — | `admin` or `editor`; no third role. |
| `active` | boolean | yes | — | deactivation returns `403 account_inactive` on the next call. |
| `mfa_status` | enum | read-only | — | `enrolled` or `none`; from `staff_account`. |
| `last_sign_in_at` | ISO 8601 or null | read-only | — | from Supabase Auth via `staff_account`. |

Invites go through Supabase Auth; the `staff` row is created only after the auth user
exists, so a failed invite leaves no usable role (`ADMIN.md` §2, §4). The PRD's Users
entity gives Admin "invite, change or **remove** users" (`PRD.md:408`; `ADMIN.md:49`),
but the endpoint inventory has no removal or deactivate-and-delete row; see U16. The
last active Admin cannot be demoted, deactivated or deleted (`409 last_admin`, AD-10).
States: invited (derived from `auth.users`, not stored, `ADMIN.md` §14), active,
inactive, last Admin. A password reset and an MFA reset are audit-logged (A14, A17).

### 4.11 Audit, sign-ins and revalidation — 3 endpoints

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /audit` | Admin | `actor`, `action`, `entity_kind`, `entity_id`, `from`, `to`, `page` | `Page<AuditRow>` |
| `GET /sign-ins` | Admin | `staff_id`, `outcome`, `from`, `to`, `page` | `Page<SignInRow>` |
| `GET /revalidation` | Admin | `status`, `page` | pending, failed and dead rows |

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `actor_id` | uuid or null | read-only | — | staff member; null after a staff deletion. |
| `action` | string | read-only | 80 † | e.g. publish, unpublish, archive, restore, delete, role change, approval. |
| `entity_kind` | string | read-only | 40 † | what was changed. |
| `entity_id` | string | read-only | 100 † | which row. |
| `version_id` | uuid | read-only | — | when the action names a version. |
| `page_id` | uuid | read-only | — | when a section publish names its page. |
| `path` | string | read-only | — | for unpublish, archive and delete. |
| `revision` | integer | read-only | — | for publish. |
| `affected_rows` | integer | read-only | — | for a retention run or an export count. |
| `created_at` | ISO 8601 | read-only | — | event time. |
| `staff_id` | uuid or null | read-only | — | sign-in row; null when the account is unknown. |
| `outcome` | enum | read-only | — | `success` or `failure`. |
| `ip_hash` | string | read-only | — | hashed address; never the raw address. |
| `user_agent_hash` | string | read-only | — | hashed user agent. |
| `occurred_at` | ISO 8601 | read-only | — | sign-in time. |

The audit log is append-only; the sign-in log is separate because it holds address and
agent hashes (`ADMIN.md` §10). `GET /revalidation` is defined in §4 (`ADMIN.md:363`), but
the §3 screen route `/admin/revalidation` is not: §11 names the screen and §3 lists none
(U14). The queue's exact row keys are not in ADMIN.md either: `tags`, `status`,
`attempts`, `next_attempt_at`, `last_error` exist only in `DATABASE.md:1715-1734`. Do
not build a table from the columns before the screen route and row schema are settled.

### 4.12 Preview — 1 endpoint

| Method and path | Auth | Request fields | Response fields |
| --- | --- | --- | --- |
| `GET /preview` | both (legal_page: Admin) | `path` | public shape with drafts, `preview: true`, staged media `url` |

| Field | Type | Required | Limit | Notes |
| --- | --- | --- | --- | --- |
| `path` | string | yes | — | `/` for the landing page, `/privacy` for a legal page. |
| `preview` | boolean | read-only | — | always `true`. |
| `sections[]` | array | read-only | — | each section's current draft in place of its published version. |
| staged media `url` | string | read-only | — | short-lived signed URL or staff-only `/preview/media/<id>`; never a public `/media/*` path. |

The completeness list beside the iframe is derived from empty required fields in the
same payload; it is not a separate response field (`ADMIN.md` §11). Responses are
`no-store` and `X-Robots-Tag: noindex`; the route is excluded from the nav, sitemap and
public cache tags. A settings preview is `403` under the prose and unspecified under the
table (C6). States: draft, blocked fields, staged media.

## 5. Screen → endpoint index

The old page view, kept so a screen can be found from the endpoint order. Every admin
route is in `ADMIN.md` §3.

| Screen | Primary endpoints |
| --- | --- |
| `/admin/sign-in` | `POST /auth/sign-in`, `POST /auth/mfa/verify`, `POST /auth/password-reset` |
| `/admin` | `GET /dashboard` |
| `/admin/pages/landing` | `GET /content?kind=landing_page`, `GET /pages/{item_id}`, page and section publish/unpublish/archive |
| `/admin/pages/landing/sections/[itemId]` | `GET /content/{item_id}`, `PATCH /content/{item_id}/drafts/{version_id}`, submit, publish, unpublish, archive, versions |
| `/admin/pages/legal` | `GET /content?kind=legal_page`, `POST /content`, legal publish/unpublish/archive/delete |
| `/admin/pages/legal/[itemId]` | content read/patch/submit, `POST .../legal-approval`, publish, versions |
| `/admin/services` | `GET /content?kind=service_group`, `POST /content` |
| `/admin/services/[itemId]` | content read/patch/submit/publish/unpublish/archive/delete/versions |
| `/admin/projects` | `GET /content?kind=project`, `POST /content` |
| `/admin/projects/[itemId]` | content read/patch/submit/publish/unpublish/archive/delete/versions, approvals |
| `/admin/proof` | `GET /content?kind=proof_figure`, `testimonial`, `client_logo`; `GET /approvals`; `POST /content` |
| `/admin/proof/proof_figure/[itemId]` | content read/patch/submit/publish/unpublish/archive/delete, approvals |
| `/admin/proof/testimonial/[itemId]` | the same proof endpoints for `testimonial` |
| `/admin/proof/client_logo/[itemId]` | the same proof endpoints for `client_logo`; no page slot (D-9) |
| `/admin/faqs` | `GET /content/{faq_section_item_id}`, `PATCH .../drafts/{version_id}` (FAQ rows are children of the section version) |
| `/admin/media` | `POST /media`, `GET /media`, `POST /media/{id}/delete` |
| `/admin/media/[id]` | `GET /media/{id}`, `POST /media/{id}/delete` |
| `/admin/enquiries` | `GET /enquiries`, `GET /enquiries/export.csv` |
| `/admin/enquiries/[id]` | `GET/PATCH /enquiries/{id}`, notes, first-reply, delete |
| `/admin/settings` | `GET /settings`, `PATCH /content/{item_id}/drafts/{version_id}`, publish/unpublish/archive/restore |
| `/admin/staff` | `GET /staff`, `POST /staff/invites`, `PATCH /staff/{user_id}`, password and MFA resets |
| `/admin/audit` | `GET /audit`, `GET /sign-ins` |
| `/admin/account` | `GET /me`, Supabase Auth TOTP enrolment |
| `/preview<path>` | `GET /preview` |
| `/admin/revalidation` | `GET /revalidation`; the screen route is named in §11 but absent from §3 (U14) |
| Evidence | no screen; `POST /evidence` and `GET /evidence/{media_id}/url` from the approval panel (U6) |

`GET /approvals` has no screen of its own: `ADMIN.md` §3 defines no `/admin/approvals`
route, so the approval list is the panel on `/admin/proof`, filtered by `subject_kind`,
and the approval state shown on `/admin/projects`. `POST /auth/sign-out` is a header
action on every admin screen, not a route in this index.

## 6. Build order

This is a delivery order, not a requirement. It follows the dependency between screens:
nothing publishes before sign-in and a draft editor exist, and nothing personal-data
heavy ships before the approval and settings surfaces are audited.

1. **Slice 1 — sign-in, content list, content editor, publish, media.** `POST
   /auth/sign-in`, `POST /auth/mfa/verify`, `/me`, `GET /content`, `GET/PATCH` the draft,
   submit, publish, unpublish, archive, versions, `GET /pages/{id}`, `POST/GET /media`.
   This is the shortest path to a page an Editor can change and an Admin can publish.
2. **Slice 2 — enquiries, settings, approvals.** The enquiry list/detail/notes/export/
   delete, the settings form and its publish gate, the approval list and the four
   approval endpoints. Enquiries and settings are Admin only; the approval panel is
   needed before any project, figure, testimonial or logo can publish.
3. **Slice 3 — staff, audit, export, revalidation operations.** Invites, role/active
   changes, resets, `GET /audit`, `GET /sign-ins`, the export path's audit row and the
   revalidation queue once its screen route and row schema are defined (U14). Staff
   removal and the invite landing page wait on U16/U17.

## 7. Field limits

Copied from CONTRACT.md "Field limits" (`CONTRACT.md:1088-1142`). That section is the
source; this readable table is not a second place to edit, and the generated OpenAPI
schema carries the same numbers.

| Field | Limit | State |
| --- | --- | --- |
| `eyebrow` | 48 characters, optional | decided field, proposed limit |
| `nav_label` | 24 characters | proposed |
| section `heading` | 70 characters | proposed |
| section `intro` | 200 characters, one sentence | proposed |
| `next_steps` | 1–4 items; `title` 80, `body` 200 | decided count, proposed lengths; the database caps 40/160 (C3) |
| `privacy_note.text` | 240 characters | proposed |
| `privacy_note.link_label` | 40 characters | proposed |
| service `title` | 60 characters | proposed |
| service `summary` | 160 characters | proposed |
| media `alt` | 120 characters | proposed |
| location `name` | 60 characters | proposed |
| location `phone` | 32 characters, E.164 formatted | proposed |
| contact `phone` | 32 characters, E.164 formatted, optional; requires `phone_hours` | proposed |
| contact `phone_hours.summary` | 120 characters, with `timezone` `Europe/London` | proposed |
| form `name` | 1–100 | proposed |
| form `email` | 254 | proposed |
| form `company` | 0–120, optional | proposed |
| form `message` | 1–2,000 | proposed |
| `client_need`, `built`, `result` | 280 characters each | proposed |
| project `client` | 80 characters, optional; null when withheld | proposed |
| project `technologies` | 0–8 items, 40 characters each | proposed |
| testimonial `quote` | 280 characters | proposed |
| testimonial `name` / `role` / `company` | 60 / 80 / 80 characters, each optional; all null when the name is withheld | proposed |
| evidence file | PDF, JPEG, PNG or WebP; 4MB | proposed |
| FAQ `answer` | 600 characters | proposed |
| legal `h2` | 60 characters | proposed |
| `about.body` paragraph | 1–4 paragraphs, 600 characters each | proposed |
| page `seo.title` | 60 characters | proposed |
| page `seo.description` | 160 characters | proposed |
| legal `title` | 70 characters | proposed |
| legal `label` | 40 characters | proposed |
| legal `p` | 2,000 characters | proposed |
| legal `ul` | 1–12 items, 200 characters each | proposed |
| legal `table` | 1–30 rows | proposed |
| project `title` | 60 characters | proposed |
| service group `title` | 40 characters | proposed |
| proof `label` / `value` / `prefix` / `suffix` | 40 / 12 / 4 / 4 characters | proposed |
| stage, assurance `title` / `body` | 40 / 160 characters | proposed |
| FAQ `question` | 120 characters | proposed |
| `footer_note` | 160 characters | proposed |
| `footer_links` item `label` / `href` | 40 / 200 characters | proposed |
| `seo_defaults.title_suffix` / `description` | 40 / 160 characters | proposed |
| legal `effective_on` | date, optional; null means the publish date | proposed |
| `cta.label` | 30 characters | proposed |
| location `address` | 2–4 lines, 80 characters each | proposed |

## 8. Shared behaviour

**The lifecycle.** `create_draft → draft → submit → in_review → publish → published`.
An Admin may publish a draft directly, skipping review. Editing a published item creates
a new draft copied from live; the live version is untouched. One open version per item;
the drafts endpoint returns the existing one rather than duplicating it (`ADMIN.md` §5).

**Unpublish leaves a draft or the in-review version.** Deleting the publication pointer
creates a draft copy from the last published version in the same transaction, or keeps
the open in-review version, which stays in review; an existing open draft is reused,
never duplicated (`ADMIN.md:522`; decision 69). Unpublishing the landing page also
removes its sections' pointers and ensures a draft for each of the ten sections, so it
can be republished. Unpublishing one section removes only that section's pointer; the
others keep theirs.

**Archive is the normal delete.** It unpublishes first, then marks the item archived, in
one transaction; it creates no draft. Archiving the landing page archives its sections.
Restore clears the flags and leaves the item `unpublished` (or in the draft that
survived); it does not republish, and writes no revalidation row (`ADMIN.md` §5;
decisions 69–70).

**Permanent delete** exists only for an item that was never published, carries no
approval, is not one of the three fixed kinds (the landing page, its sections, settings)
and is not referenced by a section draft or a service group's services. It requires the
typed title, cannot be undone, writes one `delete` audit row and frees the path or slug.
A legal page is creatable, so a never-published legal draft may be deleted (decision 70).

**Admin-only paths.** Legal pages and settings are Admin on every content read and write,
version read and preview; an Editor's `GET /content` omits them and naming either kind
returns `403` (but see C6 for the preview table's omission of settings). Enquiries,
staff, approvals, evidence and the audit and sign-in logs are Admin only. This is
enforced per request, not by hiding navigation (`ADMIN.md` §1, §4; AD-2).

**Evidence** is Admin-only, lives in the private `evidence` bucket, and is never returned
by `/media`: an Editor reading through `/media` sees no evidence row, and an evidence id
is `404`. It is opened through a 60-second signed link, never embedded (`ADMIN.md` §4, §7;
`CONTRACT.md` "Media"; A12).

**Cache and indexing.** Every admin and preview response carries
`Cache-Control: no-store` and `X-Robots-Tag: noindex`. `/admin` is disallowed in
`robots.txt` and unlinked from the public site. `/preview` is excluded from the nav,
sitemap and every public cache tag (SE-12, NF-7).

**Concurrency and confirmations.** Every content edit, submit, publish, unpublish, archive
and delete carries `If-Match`; restore takes none. A stale value is `412
revision_conflict` with the current resource so the UI can show a diff and stop the save.
Publish gates return `409 publish_blocked` with `blockers[]`. Archive and permanent delete
require the item title to be typed; enquiry deletion requires the record to be typed.
Unpublish names the public path and warns that the page disappears within a minute
(`ADMIN.md` §3–§4).

**Accessibility.** WCAG 2.2 AA: full keyboard operation, visible focus, logical order,
44px minimum targets, errors announced through `aria-live` and tied to their fields, no
focus trap, reduced motion respected, and no colour-only status (`ADMIN.md` §3,
`AGENTS.md`).

## 9. Do not build

- **No database access from Next.js.** The browser talks to Next.js; Next.js talks to
  FastAPI with the service token. No Supabase database client, SQL, database credential
  or service key in the frontend; the only Supabase use is the Auth enrolment call in §1
  (`AGENTS.md`; `ADMIN.md` §2, decision 2).
- **No product screens.** Products are out of scope by explicit decision; there is no
  product kind, table, view, slot or approval subject. Reintroducing them is a new
  `content_kind`, a PRD/D-3 decision and a migration (decision 67; SV-2).
- **No booking link and no budget field.** The columns exist as placeholders and are not
  editable; settings writes reject `booking_url` and `booking_label` with `422`
  (decision 46; A7; T30). EN-10 is left undelivered.
- **No cookie preference control.** The site sets no optional cookies, so the footer links
  the Cookies information page and no preference control exists (decision 52). Reopen the
  decision before building one.
- **No client-logo slot on the page.** The record, media and approval exist; D-9 decides
  whether a slot is added. Do not render a logo on the landing page until then
  (decision 44; open question 7).
- **No Google Workspace sign-in.** AD-11 is a Should "if approved" and is not approved.
  Phase 1 is Supabase Auth email + password + TOTP; Workspace would be a provider change,
  not a screen (ADMIN §14).
- **No price fields.** Phase 1 shows no prices or packages; D-10 is open and the settings
  form has no price field (`ADMIN.md` §14, D-10).
- **No invented copy, figures, logos, testimonials, team members or legal identity.**
  Every content value waits for approval; placeholders are not content (`AGENTS.md`;
  `CONTRACT.md` preamble; decision 65 for the deferred team).
- **No rich text or HTML in legal pages.** Four block kinds only; links are plain text
  until open question 2 is decided (decision 17).
- **No public media listing.** `GET /api/v1/public/media/*` does not exist and must 404;
  the public bucket URL is the only way to a published file (decision 36).
- **No section create, delete or reorder.** The ten sections and their order are fixed and
  seeded; an editor orders items inside a section (A16; decision 5).
- **No evidence library screen.** Evidence is uploaded from the approval form and opened
  through a signed link; there is no `/admin/evidence` route (U6).

## 10. Open decisions that affect UI

| Decision | State | What it means for the UI |
| --- | --- | --- |
| D-9 client-logo slot | Open | Build the logo record and approval; no page slot, no render, no placement control (decision 44). |
| Hreflang locale codes | Open | Only `nepal_site_url` exists; neither `en-NP` nor `ne-NP` is confirmed. Do not build a language switcher or emit hreflang (open question 3; `ADMIN.md` §14). |
| M8 settings/landing gate | Accepted 27 November 2026 | No two-way gate: settings may be unpublished while the landing page is live, and the site frame can go empty until republished. Do not invent a gate (`Backend/docs/work/PLAN.md:220-224`; `PROGRESS.md:310`). ADMIN.md §14 still lists it as open, so the documents disagree; see C5. |
| D-13 owners | Deferred to week 4 | No owner is named for content, enquiries, privacy and cookie reviews, document approval or production alerts. No UI field; the dashboard's alert destination is unassigned (`PLAN.md:226-230`; ADMIN §14). |
| AD-11 Google Workspace sign-in | Not approved | No Workspace button or provider; keep email + password + TOTP (`ADMIN.md` §14). |
| D-3 service catalogue | Open | The service screens edit whatever catalogue management confirms; do not seed or invent a catalogue (`ADMIN.md` §14). |
| D-7 legal identity | Open | The settings fields exist; no value is seeded. Build the form and its publish gate, not placeholder identity (open question 4; `ADMIN.md` §9). |
| D-8 retention | Open | The privacy notice must state the enquiry, audit, `ip_hash`/outbox and rate-limit periods before the form collects; the values are not UI fields (`CONTRACT.md` "Enquiry submission"; ADMIN §14). |
| D-10 prices | Open | No price or package field; Phase 1 shows none (`ADMIN.md` §14). |

## 11. Conflicts, drift and unspecified

Neither list is resolved here. Where the sources disagree — two documents, or one
document against itself — both citations are given; where a request body or response key
is missing, the OpenAPI schema must settle it before the control is built. "Drift" means
one statement is stale and there is one correct reading; "gap" means neither defines the
thing. Only C1, C3, C4, C6 and C7 need a decision.

### 11.1 Conflicts

| # | What | Source A | Source B | Effect on the UI |
| --- | --- | --- | --- | --- |
| C1 | `phone_hours` shape, and which field carries the 120-character hours limit | `CONTRACT.md:721-728`: `phone_hours` is null and `hours` is the object `{summary, timezone}`. `CONTRACT.md:1111`: the limit is named against `phone_hours.summary`, "with `timezone` Europe/London". | `ADMIN.md:718`: the typed column is `contact_phone_hours`, text. `DATABASE.md:1304-1305`: `contact_phone_hours text`, and the phone/hours constraint is a paired null check. The same text-column shape appears on `settings_location.phone_hours` (`DATABASE.md:1369-1381`). | The API decides whether phone hours are one text column or a summary plus timezone. Until it does, a single text input can map to `contact_phone_hours`; do not bind one control to both `phone_hours` and `hours.summary`, and do not render a timezone picker. The limit is 120 either way. |
| C3 | `next_steps` title and body limits | `CONTRACT.md:1102`: 1–4 items; `title` 80, `body` 200. | `DATABASE.md:758-763`: `contact_next_step.title` ≤ 40 and `body` ≤ 160. | **Cap the form at 40/160 until the two are reconciled.** The Pydantic limit does not settle it: it is built from the same CONTRACT row that says 80/200, so a form sending 60 characters is accepted by Pydantic and refused by the database. Change both sources in one revision; do not ship 80/200 first. |
| C4 | `slug` and `path` optionality on create | `ADMIN.md:324`: `POST /content` takes `{kind, path?, slug?}` — both optional. | `CONTRACT.md:396-397`: service and project records keep a `slug` for Phase 2. `DATABASE.md:348-353`: a `legal_page` and `landing_page` require a path, and a `service` and `project` require a slug. | The create form cannot assume either is optional. For a service or project, a missing slug reaches a database refusal; for a legal page, a missing path does. Make the field required for the kinds that need it, or wait for OpenAPI. |
| C6 | Preview role for settings | `ADMIN.md:364`: `GET /preview` is "both (legal_page: Admin)" and names no settings restriction. | `ADMIN.md:390-392`: "`legal_page` and `settings` require Admin on every content read and write, version read and preview". | An Editor's preview of settings is `403` under the prose and unspecified under the table. Do not offer it until the two statements agree; the API must pick one. |
| C7 | Sign-in log route | `ADMIN.md:202`: one screen, `/admin/audit`, covers "Audit log and sign-in log". | `ADMIN.md:362`: `GET /sign-ins`; `ADMIN.md:742`: the sign-in log is read by `/admin/sign-ins`, Admins. | The route set is unresolved; do not create a separate `/admin/sign-ins` navigation entry until it is confirmed. Both calls exist in the endpoint inventory. |

### 11.2 Drift and gaps

| # | What | Source A | Source B | Effect on the UI |
| --- | --- | --- | --- | --- |
| C2 (drift) | `locations[].phone_hours` shape | `CONTRACT.md:776-778`: a location with a phone "carries `phone_hours` in its own timezone", with "the same shape as `contact.hours`" (an object). `CONTRACT.md:735-736` shows `phone_hours: null`, and `CONTRACT.md:1108-1110` gives `location.phone` 32 but no `location.phone_hours` limit. | `DATABASE.md:1369-1381`: `settings_location.phone_hours text`. | This is the location half of C1, not a separate conflict: a text column and an object need different controls. No limit exists, so do not add one. Wait for OpenAPI, then use the same shape as C1. |
| C5 (drift) | M8: settings unpublished while the landing page is live | `ADMIN.md:930-931`: "Settings can be unpublished while the landing page is live, which would empty the site frame and legal identity; a gate needs a decision." | `Backend/docs/work/PLAN.md:220-224` and `PROGRESS.md:310`: the owner accepted M8 on 27 November, no gate, risk recorded and not mitigated. | No gate is the accepted behaviour, but ADMIN.md still calls it open. Build no gate; flag the doc drift to the orchestrator. |
| C8 (drift) | Media picker "replace" | `ADMIN.md:679-681`: lists `replace` among the media picker states, "(creates a new row)". | `CONTRACT.md` "Media" and `ADMIN.md` §7: replacing a file or correcting alt text creates a new record and repoints the reference, which is an action, not a state. | Offer `replace` on a row, not as a picker state; the picker's states are the ones in §4.7. |

### 11.3 Unspecified

| # | Item | What is missing | What to do |
| --- | --- | --- | --- |
| U1 | `seo.noindex` | The field is on the wire (`CONTRACT.md:160`, `:652`) and in `content_seo` with a database default of `false` (`DATABASE.md:490`), but neither document names an editor control. | Render it read-only, or wait for OpenAPI; do not add a toggle silently. |
| U2 | `sections[]` in page publish | `ADMIN.md:332` gives `{page_version_id, sections[]}` and no element shape. | The UI must show which section versions will publish; the element shape is for OpenAPI to define. |
| U3 | Dashboard keys and empty state | `ADMIN.md:322` describes the response in prose ("drafts, in review, new enquiries, expiring approvals, failed revalidation"); no JSON keys or counts are defined. | Do not hard-code key names. Build the five cards against OpenAPI. |
| U4 | Phase 2 fields on service and project records | `CONTRACT.md:396-397` says the records keep service and project `slug`, a service's `long_description` and a project's `category`; neither ADMIN screen table names an editor control for `long_description` or `category`, and no limit is given. | Do not invent a control or a limit. `slug` is the only one with a create-body reference (C4). |
| U5 | Project "image missing" state | `ADMIN.md:192` lists it, but no document defines when it applies. `CONTRACT.md:602` allows 0–3 images; open question 5 proposes 1–3. | Render the badge from the API state; do not derive it from an image count. |
| U6 | Evidence screen | The handover brief names an evidence screen; `ADMIN.md` §3 defines no `/admin/evidence` route. Evidence is uploaded from the approval form and opened by a signed link. | Build the upload and signed-link controls inside the approval panel; do not add a library route. |
| U7 | Structured working hours | `ADMIN.md:718` names `settings_working_hour` rows and `ADMIN.md:399-402` says the typed body includes working hours, but ADMIN names no row fields; DATABASE names the columns (§12) and `CONTRACT.md:725-728` exposes only `hours.summary` and `hours.timezone`; `DATABASE.md:1494-1496` says the rows are additive, an empty table is valid, and no gate counts them. | Build `hours_summary` and `hours_timezone`; do not build a structured hours editor until the row shape is in OpenAPI. |
| U8 | Account and MFA enrolment | `ADMIN.md:104-107` says enrolment uses the user's own Supabase session; no request or response shape is defined, and MFA recovery is A17 only. | Use the Supabase client for enrolment; do not invent FastAPI fields. |
| U9 | Admin response field names generally | `ADMIN.md` §4 defines request bodies and says success bodies are the resource, but most response schemas are prose. Names marked † in this file are database or view columns. | Treat OpenAPI as the naming authority; this file's † marks are provisional. |
| U10 | `legal` table columns and cells | `CONTRACT.md:663` shows three sample columns; `CONTRACT.md:695` says the editor owns purpose, duration and provider; `DATABASE.md:1191-1205` fixes only that a column has a non-empty label, and no cell length is given. | Let the editor define the column labels; do not hard-code three columns or invent a cell limit. |
| U11 | Project `category` limit | The field is kept on the record (`CONTRACT.md:396-397`) but has no limit in the field table and no editor control. | Wait for OpenAPI; do not add a limit. It is database-only (§12). |
| U12 | Settings identity field limits | `legal_name`, `trading_name`, `country`, the regulation 63 fields and `vat_number` have no limits in `CONTRACT.md` "Field limits" or `ADMIN.md` §9. | Do not inherit an unrelated limit; use the Pydantic schema. |
| U13 | Multipart part names for uploads | `ADMIN.md:342` says `POST /media` takes "multipart file + `alt`"; `ADMIN.md:346` says `POST /evidence` takes "multipart file". The file part's name is not given. | Wait for OpenAPI before wiring the upload; do not assume `file`. |
| U14 | Revalidation queue screen | `ADMIN.md` §11 names the screen `/admin/revalidation`, but §3 defines no such route. `GET /revalidation` is defined in §4 (`ADMIN.md:363`); the row fields (`tags`, `status`, `attempts`, `next_attempt_at`, `last_error`) are only in `DATABASE.md:1715-1734`. | Link the dashboard's failed count to the queue once the §3 screen and the row schema are defined; do not build a table from the columns. |
| U15 | Sort allowlist | `ADMIN.md:257` requires an allowlist and names none. | OpenAPI must list the sortable fields per endpoint; until then accept only the fields an endpoint actually returns and refuse the rest with `422`. |
| U16 | Staff removal | `PRD.md:408` and `ADMIN.md:49` give Admin "invite, change or remove users", and AD-10 names deactivation, but the endpoint inventory has no delete/remove staff row. | Do not invent a delete endpoint. Ask whether removal means `active: false` (which exists) or a new route and what happens to the person's audit rows. |
| U17 | Invite landing and set-password | `ADMIN.md:96-98` says the person sets their own password through Supabase Auth's invite link, and the invite expires after 7 days (AD-1), but no route, screen or request shape is defined. | Use Supabase's hosted flow if that is the decision; do not build a Next route until it is. |

## 12. Database only — not a UI field

These columns are in `DATABASE.md` but not in a CONTRACT payload or an ADMIN request or
response. Do not put them in a form or a table. They are listed so a schema-first
developer does not mistake them for controls.

| Column | Why it is not a UI field |
| --- | --- |
| `service_version.long_description` | A Phase 2 field the record keeps; no Phase 1 control is specified and no limit is given (`CONTRACT.md:396-397`; U4). |
| `project_version.category` | The same: a Phase 2 field with no Phase 1 control and no limit (`CONTRACT.md:396-397`; U11). |
| `settings_working_hour.day_of_week`, `opens_at`, `closes_at`, `is_closed` | The row shape is only in `DATABASE.md`; `ADMIN.md` names working hours in the typed body but no fields. Build `hours_summary`/`hours_timezone` instead (U7). |
| `content_item.next_version` | Internal counter; `revision` is the exposed version number. |
| `page_section.sort_order` | Seeded and fixed; the admin exposes no section reorder (A16; decision 5). |
| `content_version.submitted_at` | Version history shows author, status, revision and dates; this column is not named as a field. |
| `content_publication.version_id` | The pointer's version id; the UI reads `revision`, `published_at` and `published_by`. |
| `media.object_path`, `bucket`, `visibility`, `checksum_sha256`, `promoted_at` | Storage internals; the UI shows `state`, `url`, dimensions and type. |
| `service.live_title`, `service.live_sort_order`, `project.live_sort_order` | Live projections; the editor uses the version's `title` and `sort_order`. |
| `settings_version.booking_url`, `booking_label` | Not editable; a write is refused with `422` (A7, decision 46). |
| `enquiry.ip_hash`, `updated_at`, `closed_at` | Not named for the admin screen; the detail shows status and `created_at`/`first_replied_at`. |
| `email_outbox.*`, `rate_limit_event.*` | Delivery and rate-limit internals; no admin screen reads them. |
| `audit_log.id`, `sign_in_event.id` | Row keys, not displayed. |
| `staff.created_by`, `created_at`, `updated_at` | Staff changes are audit-derived (`ADMIN.md` §10). |
| `approval.version_id`, `created_at`, `revoked_at`, `revoked_by` | The current state and the revocation note are shown; these columns are internal. |

## 13. Source map

Line ranges are at `4a6b01c`; the source documents are unchanged from `3c6f46f`.

| This file | Source | Lines |
| --- | --- | --- |
| 1. Read this first | `CONTRACT.md` Scope, The calls, The Next-to-FastAPI link | 15-92 |
| 1. Read this first | `ADMIN.md` §1–§2 | 30-167 |
| 2.1 Shared shapes | `ADMIN.md` §3 shared screen behaviour, §4 conventions | 207-267 |
| 2.2 Pagination and sorting | `ADMIN.md` §4 Conventions | 249-258 |
| 2.3 Errors | `ADMIN.md` §4 Error envelope; `CONTRACT.md` What comes back | 269-307; 859-886 |
| 2.4 Concurrency | `ADMIN.md` §4 Concurrency, Idempotency | 433-469 |
| 2.5 Request names | `ADMIN.md` §4 typed body; `DATABASE.md` tables cited | 329, 399-402; — |
| 2.6 Cache and indexing | `CONTRACT.md` The calls, Revalidation; SE-12, NF-7 | 26-58, 94-144 |
| 2.7 Roles | `ADMIN.md` §1 role matrix, AD-2 | 38-60 |
| 3.1 `/public/page` — shell, hero, proof, services, not-sure | `CONTRACT.md` Landing page | 146-211 |
| 3.1 `/public/page` — work, process, about, testimonials, FAQs, contact | `CONTRACT.md` Landing page | 212-345 |
| 3.1 `/public/page` — head, structured data | `CONTRACT.md` Head and structured data | 347-360 |
| 3.1 `/public/page` — records, approvals, caps, preview | `CONTRACT.md` Records behind the sections, Preview | 362-464 |
| 3.1 `/public/page` — what blocks a publish, empty sections | `CONTRACT.md` What blocks a publish | 484-512 |
| 3.1.12 `/public/page` — legal page | `CONTRACT.md` Legal page | 638-698 |
| 3.2 `/public/settings` | `CONTRACT.md` Site settings, Field limits; `ADMIN.md` §9 | 699-816, 1096-1142; 709-735 |
| 3.3 `/public/routes` | `CONTRACT.md` The calls | 26-58 |
| 3.4 `/public/enquiries` | `CONTRACT.md` Enquiry submission, Fields, After a send, The emails | 818-1002 |
| 4.1 Auth and me | `ADMIN.md` §2 Sign-in; §4 `/auth/*`; §13 T41–T43 | 91-128, 317-320, 885-887 |
| 4.2 Dashboard | `ADMIN.md` §3; §4 `GET /dashboard` | 184, 322 |
| 4.3 Content CRUD and versions | `ADMIN.md` §4 content endpoints, §5 lifecycle; `DATABASE.md` typed tables | 324-337, 399-410, 504-552; — |
| 4.3.1 Typed bodies | `DATABASE.md` `section_version`, `service_version`, `project_version`, `proof_figure_version`, `testimonial_version`, `client_logo_version`, `legal_page_version`; `ADMIN.md` §4 typed body | 606-700, 877-1143; 399-402 |
| 4.4 Publish lifecycle | `ADMIN.md` §5; §4 publish/unpublish/archive/delete; decisions 69–70 | 324-337, 504-586 |
| 4.5 Page read | `ADMIN.md` §4 `GET /pages/{item_id}` | 337 |
| 4.6 Approvals | `ADMIN.md` §6 Proof approvals, legal pages; §4 approvals | 588-649, 338-341 |
| 4.7 Media and evidence | `CONTRACT.md` Media; `ADMIN.md` §7; §4 media/evidence | 514-613; 651-681, 342-347 |
| 4.8 Enquiries | `ADMIN.md` §8; §4 enquiry endpoints; `CONTRACT.md` Fields | 683-707, 348-354; 927-965 |
| 4.9 Settings | `ADMIN.md` §9; §4 `GET /settings`; `DATABASE.md` `settings_version` | 709-735, 355; 1298-1416 |
| 4.10 Staff | `ADMIN.md` §2, §4 staff, §10, §14; `DATABASE.md` `staff` | 91-108, 356-360, 737-760, 939-951; 201-248 |
| 4.11 Audit, sign-ins, revalidation | `ADMIN.md` §10, §11; §4 `/audit`, `/sign-ins`, `/revalidation` | 737-797, 361-363 |
| 4.12 Preview | `CONTRACT.md` Preview; `ADMIN.md` §11 | 445-464; 762-797 |
| 5. Screen index | `ADMIN.md` §3 routes | 176-206 |
| 6. Build order | Delivery order; no source requirement | — |
| 7. Field limits | `CONTRACT.md` Field limits | 1088-1142 |
| 8. Shared behaviour | `CONTRACT.md` Revalidation, What blocks a publish; `ADMIN.md` §3–§5, §7, §12 | 94-144, 484-512; 207-243, 366-403, 504-586, 651-681, 799-834 |
| 9. Do not build | `CONTRACT.md` decisions 36, 44, 46, 52, 67; `ADMIN.md` §14; `AGENTS.md` | 1043-1077; 891-933 |
| 10. Open decisions | `CONTRACT.md` Open questions; `ADMIN.md` §14; `PLAN.md` Owner decisions | 1144-1183; 891-933; 218-230 |
| 11. Conflicts and unspecified | The cited lines in each row | — |
| 12. Database only | `DATABASE.md` tables cited in each row; `ADMIN.md` §9 for the booking columns | — |
