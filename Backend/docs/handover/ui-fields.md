# UI field inventory — landing page and admin

Status: handover document, written 27 November 2026 against commit `3c6f46f` on
`handover/ui-fields`. Line references in this file are to that commit.

## 1. Read this first

- **What this is.** A build sheet for the two Next.js surfaces: the public landing page
  and the staff CMS at `/admin`. It names every field the two source documents give a
  control, a limit or a state, and nothing else.
- **This is a design contract, not a live API.** The FastAPI service does not exist yet.
  When it does, its generated OpenAPI schema is authoritative, and this file must be
  reconciled with it. A field here that OpenAPI does not carry is a documentation bug,
  not a licence to call a route that is not there.
- **Fields are wire names**, the JSON keys, not database columns. Where ADMIN.md names a
  database column because it defines no response schema, the name is marked **†** and
  the OpenAPI schema replaces it. A name in plain code appears in a CONTRACT payload, an
  ADMIN request body or an ADMIN screen description.
- **The frontend never touches the database.** The browser calls Next.js only; Next.js
  calls FastAPI with `X-Service-Token`, and admin and preview calls also carry the staff
  bearer (`CONTRACT.md` "The Next-to-FastAPI link"; `ADMIN.md` §2). No Supabase database
  client, database credential or service key ships to the browser. The one exception is
  the Supabase Auth client used for TOTP enrolment in `/admin/account`, with the user's
  own session (`ADMIN.md` §2, A1).
- **Limits.** A bare number in the Limit column comes from CONTRACT.md "Field limits".
  A number ending in **†** is a database check cited only because the contract is
  silent. **Not stated** means neither document gives a number; do not add one.
- **Required.** **Yes at publish** means CONTRACT.md "What blocks a publish" names it as
  a gate. **Yes** means the item needs a value to render as designed; the Pydantic model
  decides whether it is enforced, because the gate table is silent. **Fixed** means the
  value is not editable. **Read-only** means the API supplies it.
- **Placeholders are not copy.** Strings in angle brackets, and every heading, quote,
  figure, logo and legal identity value, wait for approved content. Nothing here is
  seeded (`AGENTS.md`; `CONTRACT.md` preamble).
- **The public calls.** `GET /api/v1/public/page?path=/` returns the landing page;
  `GET /api/v1/public/settings` returns the site frame; `POST /api/v1/public/enquiries`
  is the only public write. All three are server-to-server. There is no public media
  route (`CONTRACT.md` "The calls", "Media", decision 36).

## 2. Landing page

The payload is `type: "landing"`. The section array is the render order, fixed from
PRD §5 and **not editable in Phase 1**; an editor orders items inside a section, never
the sections themselves (`CONTRACT.md` "Landing page"; `DATABASE.md` `page_section`).
Each section's key doubles as its anchor (`#services`, `#work`), so a key can never be
renamed.

Two rules apply to every section below:

- CTA **targets** are fixed by decision 54. Only labels are content. The hero's primary,
  the not-sure CTA and the settings `cta` point at `#contact`; the hero's secondary
  points at `#work` (`CONTRACT.md` "Landing page").
- Empty **proof figures, testimonials and FAQs are omitted at read time**, not blocked
  at publish. Services, work, how we work, about and contact are gated and never
  omitted (`CONTRACT.md` "What blocks a publish"; decision 8).

The header and footer are not sections. They are settings: logo, CTA, the five
`nav_label` values, footer links, legal identity and legal routes. Build them from
§3.22, not from this chapter (`CONTRACT.md` "What the CMS owns"; decision 6). The
footer's legal links and the sitemap come from `GET /api/v1/public/routes`
(`path`, `type`, `label`, `lastmod`, `noindex`), not from the page payload
(`CONTRACT.md` "The calls").

### 2.1 Page shell

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `path` | string | fixed | — | `/`; one landing page, never created from the UI (A16). |
| `revision` | integer | read-only | — | page version number; increments on each page publish. |
| `published_at` | ISO 8601 | read-only | — | null when there is no live page. |
| `seo.title` | string | yes at publish | 60 | text; must be non-empty and unique across live pages (NF-5). |
| `seo.description` | string | yes at publish | 160 | textarea; must be non-empty and unique across live pages (NF-5). |
| `seo.og_image` | media object or null | no | 0–1 | media picker; same shape as `images[]`, host-free `/media/...` URL. |
| `seo.noindex` | boolean | no | — | on the wire; no editor control is defined (U1). Default `false`. |
| `sections[]` | array | fixed | 10 | render order; no add, remove or reorder. |
| `sections[].key` | enum | fixed | — | `hero`, `proof`, `services`, `not-sure`, `work`, `process`, `about`, `testimonials`, `faqs`, `contact`. |
| `sections[].status` | enum | read-only | — | admin read only: `draft`, `in_review`, `published`, `unpublished`, `archived`. |
| `sections[].revision` | integer | read-only | — | admin read only; the public payload carries neither status nor revision. |

The page is published with `POST /api/v1/admin/pages/{item_id}/publish` and
`{page_version_id, sections[]}` (`ADMIN.md` §4). The element shape of `sections[]` is
not defined (U2).

### 2.2 Hero

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

### 2.3 Proof figures

Key `proof`; the section has **no heading** and no copy of its own. Items are references
to `proof_figure` records, each with its own approval and order
(`CONTRACT.md` "Records behind the sections"; `DATABASE.md` `section_version` check).
At most four. Empty items hide the section at read time.

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `items[]` | array | no | 0–4 | drag to order; array position is render order. |
| `items[].label` | string | yes | 40 | what the number counts. |
| `items[].value` | string | yes | 12 | stored as a string, not a number. |
| `items[].prefix` | string or null | no | 4 | e.g. a currency mark; never invent one. |
| `items[].suffix` | string or null | no | 4 | e.g. `+` or `%`. |

Every published figure needs an unexpired, unrevoked approval with the `figure` scope
(`ADMIN.md` §6). Approval state is admin-only and never on the public wire (decision 4).

### 2.4 Services

Key `services`; `nav_label` is required at publish (NV-1). Three or four groups, two to
six services in each, service titles unique across the set and never `__other__`
(`CONTRACT.md` "Records behind the sections"; decisions 29 and 63).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `intro` | string | no | 200 | one sentence, sits beside the heading. |
| `nav_label` | string | yes | 24 | header and footer label; also the anchor text. |
| `groups[]` | array | yes | 3–4 | drag to order; groups are records. |
| `groups[].title` | string | yes | 40 | category name; renaming is one edit. |
| `groups[].items[]` | array | yes | 2–6 | services inside the group; drag to order. |
| `groups[].items[].title` | string | yes | 60 | unique across all services; `__other__` refused. |
| `groups[].items[].summary` | string | yes | 160 | outcome-led sentence. |

The same live titles feed the enquiry chips through
`contact.data.form.services` (§2.11); a title that has ever published remains a valid
enquiry choice after it is unpublished (decision 61).

### 2.5 Not sure what you need?

Key `not-sure`. The CTA lands on the form with the message field focused (LP-4).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | short prompt. |
| `body` | string | no | not stated | one line. |
| `cta.label` | string | yes | 30 | label is content. |
| `cta.href` | string | fixed | — | `#contact`; read-only (decision 54). |

### 2.6 Featured work

Key `work`; `nav_label` is required at publish. Three to six published projects; fewer
than three blocks the section (`CONTRACT.md` "What blocks a publish"). Projects are
records with their own order and approval, and publishing a project moves it without a
page republish (`CONTRACT.md` "Records behind the sections").

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `intro` | string | no | 200 | one sentence, sits beside the heading. |
| `nav_label` | string | yes | 24 | header and footer label. |
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

### 2.7 How we work

Key `process`; `nav_label` is required at publish. Exactly four stages and exactly three
assurances (code ownership, security, UK-hours contact). Stage numbers come from array
position, never a stored `01`, `02` (`CONTRACT.md` "Landing page"; decision 13).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `intro` | string | no | 200 | one sentence. |
| `nav_label` | string | yes | 24 | header and footer label. |
| `stages[]` | array | yes | exactly 4 | drag to order; position is the stage number. |
| `stages[].title` | string | yes | 40 | stage name. |
| `stages[].body` | string | yes | 160 | one line. |
| `assurances[]` | array | yes | exactly 3 | drag to order. |
| `assurances[].title` | string | yes | 40 | assurance name. |
| `assurances[].body` | string | yes | 160 | one line. |

### 2.8 About

Key `about`; `nav_label` and a non-empty section are required at publish (NV-1). Phase 1
is prose plus one image; there is no team list (decision 65).
`about.body` is an array, one string per paragraph (decision 41).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `body` | string[] | yes | 1–4 paragraphs, 600 each | one textarea per paragraph; add and remove within the range. |
| `nav_label` | string | yes | 24 | header and footer label. |
| `image` | media object or null | no | 0–1 | media picker; null until the identity is settled. |

### 2.9 Testimonials

Key `testimonials`; heading only. At most six. Attribution is all-or-nothing: a null
`name` means the client withheld it, and then `role` and `company` are null too. The
quote needs the `quote` approval scope; the name needs `client_name` (`CONTRACT.md`
"Records behind the sections"; decision 62). Empty items hide the section at read time.

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `items[]` | array | no | 0–6 | drag to order. |
| `items[].id` | string | read-only | — | opaque, stable. |
| `items[].quote` | string | yes | 280 | the words the client approved in writing. |
| `items[].name` | string or null | no | 60 | null withholds the name; then `role` and `company` must also be null. |
| `items[].role` | string or null | no | 80 | null when withheld; otherwise optional. |
| `items[].company` | string or null | no | 80 | null when withheld; otherwise optional. |

### 2.10 FAQs

Key `faqs`; heading only. Five to eight **published** questions; outside that range is a
CMS warning, never a publish refusal (LP-5 is a Should; decision A13). Each question
carries its own status and order; a draft question is visible in the admin and filtered
from the public payload (`CONTRACT.md` "Landing page"; `DATABASE.md` `faq_item`). Empty
items hide the section at read time.

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `items[]` | array | no | 5–8 published (warning); drafts do not count | drag to order. |
| `items[].question` | string | yes | 120 | plain text. |
| `items[].answer` | string | yes | 600 | plain text; no rich text or HTML (decision 12). |

The admin read also carries each question's `status` and order; see §3.16. Only
`published` questions reach the public payload.

### 2.11 Contact

Key `contact`; `nav_label` is required at publish. The section needs a heading, at least
one promise and a non-empty privacy note, plus a live privacy notice
(`CONTRACT.md` "What blocks a publish"; decision 27). Email, phone, hours and locations
are **not** section fields: they come from settings (§3.22).

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | 70 | section heading. |
| `body` | string | no | not stated | one line. |
| `nav_label` | string | yes | 24 | header and footer label. |
| `next_steps[]` | array | yes | 1–4 items | add and remove; the promise the confirmation carries is D-11's (decision 26). |
| `next_steps[].title` | string | yes | 80 | the promise. See C3: the database caps this at 40. |
| `next_steps[].body` | string | yes | 200 | one line of detail. See C3: the database caps this at 160. |
| `privacy_note.text` | string | yes | 240 | one sentence shown beside the form. |
| `privacy_note.link_label` | string | yes | 40 | link text; the target is `/privacy`. |
| `form.services` | string[] | read-only | — | computed at read time from published service titles, never stored (decision 48). |

`form.services` is computed, not edited. When it is empty the service field is hidden
and the enquiry sends `service: null` (`CONTRACT.md` "What the browser sends").

### 2.12 Contact form — code, not CMS content

The form is component code. Its labels, validation copy, error copy and confirmation are
code, not editable content (decision 19). The browser posts to Next.js at
`POST /api/enquiries`; Next.js forwards to `POST /api/v1/public/enquiries`
(`CONTRACT.md` "Enquiry submission").

| Field | Type | Required | Limit | Control and notes |
| --- | --- | --- | --- | --- |
| `name` | string | yes | 1–100 | text; trimmed. |
| `email` | string | yes | 254 | one address; checked by Pydantic and again by the browser. |
| `company` | string or null | no | 0–120 | trimmed; null when empty. |
| `service` | string | yes when options exist | one ever-published title or `__other__` | radio chips in one group; the last chip, "Something else", sends `__other__` and is not a service row. |
| `message` | string | yes | 1–2000 | plain text, line breaks kept. |
| `website` | string | must be empty | 0 | honeypot; hidden from sight and assistive technology. |

Not browser fields: `source_path` is set by Next.js from the same-origin `Referer`
(path only, no query string, 200 max); `consent_notice_version` is set by FastAPI at save
time as `landing-r<revision>+privacy-r<revision>` (64 max). The browser cannot forge
either (`CONTRACT.md` "Fields").

No phone, budget, timeframe or marketing tick box. EN-2 fixes the list; decision 46
dropped the budget field and the booking link; EN-3 sends without a marketing opt-in.

**Responses and states.** Success is `201 { "status": "received" }`. Failure uses one
envelope: `{error: {code, message, fields?}}`. The codes are `validation_failed` (422,
`fields` names each), `rate_limited` (429, `Retry-After`), `verification_failed` (400),
`not_found` (404), `service_unavailable` (503) and `internal_error` (500). A honeypot hit
returns 201 and saves nothing. A failed confirmation email does not fail the submission.
On 503, 500, a network failure or a timeout, keep the visitor's text and show the site
email (EN-8). Field errors go under the field with `aria-invalid`, focus moves to the
first, the confirmation is announced and focused, and pressing send twice sends once
(`CONTRACT.md` "What comes back", "After a send").

## 3. Admin panel

`/admin` is one staff-only route group. Item routes take `content_item.id`, not a slug.
Every list has a loading skeleton, an empty state with the primary action, an error state
with retry, and keeps filters in the URL. Every editor autosaves on a debounce through
the same `PATCH`, shows "Saved at HH:MM" from the returned `revision`, and blocks
navigation when a save failed (`ADMIN.md` §3 "Shared screen behaviour").

Role is enforced server-side on every request, not by hiding a button: an Editor gets
`403 forbidden` from every Admin-only endpoint (`ADMIN.md` §1, AD-2). The two roles are
`admin` and `editor`; there is no third role in Phase 1.

### 3.0 Shared item chrome — every content screen

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `status` | enum | read-only | — | `draft`, `in_review`, `published`, `unpublished`, `archived`; `unpublished` means no pointer and no open draft. |
| `revision` | integer | read-only | — | the open version's number, or the published version's when nothing is open. |
| `updated_by` † | string | read-only | — | "last changed by"; `coalesce(updated_by, created_by)`, or `published_by` when nothing is open (`ADMIN.md` §10). |
| `updated_at` † | ISO 8601 | read-only | — | "last changed at", same derivation. |
| `published_by` † | string | read-only | — | who last published; null when not live. |
| `published_at` | ISO 8601 | read-only | — | null when not live. |
| `blockers[]` | object[] | read-only | — | on `409 publish_blocked`; each names a gate. Publish stays disabled while non-empty. |
| `warnings[]` | object[] | read-only | — | non-blocking issues; the FAQ count outside 5–8 is the known one. |
| `ETag` / `If-Match` | header | required on every mutation | — | `"<item_id>:<version_id>"`; a stale value is `412 revision_conflict`. |

A published version is never editable. Editing a live item creates a draft copied from
live and leaves the live payload unchanged (`ADMIN.md` §5, T10).

### 3.1 Sign-in — `/admin/sign-in`

Signed-out screen. Sign-in goes browser → Next.js → FastAPI → Supabase Auth; FastAPI
records every attempt, success or failure (`ADMIN.md` §2, A10).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `email` | string | yes | not stated | signed out; the error never says whether the account exists (T41). |
| `password` | string | yes | not stated | signed out; held in memory for the Supabase call, never stored or logged. |
| `challenge_id` | string | yes at the MFA step | — | returned by `mfa_required`; hidden field. |
| `code` | string | yes at the MFA step | not stated | TOTP code from the authenticator app; `POST /auth/mfa/verify`. |

Actions: sign in; verify the code; request a password reset (`{email}`, always `202`);
sign out. States: credentials, MFA challenge, error, locked (`429 too_many_attempts`),
idle (`?reason=idle`), expired (`?reason=expired`).

### 3.2 Dashboard — `/admin`

Both roles. Read-only counts and alerts (`ADMIN.md` §3, §4 `GET /dashboard`).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| draft count | integer | read-only | — | both roles; no key is named in ADMIN §4 (U3). |
| in-review count | integer | read-only | — | both roles; no key named (U3). |
| new-enquiry count | integer | read-only | — | the dashboard endpoint is both roles (ADMIN §4); the enquiry screen itself is Admin only. |
| expiring approvals | array | read-only | — | Admin only to act on; both may see the count. |
| failed revalidation | array | read-only | — | Admin only to act on. |

Actions: follow a count to its filtered list; follow a blocker to the item. States:
loading, empty, error.

### 3.3 Landing page — `/admin/pages/landing`

Admin and Editor; publish, unpublish and archive are Admin only. The page's SEO fields are
§2.1; the section list shows each section's status and revision.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `sections[].key` | enum | read-only | — | fixed order; no drag handle (A16). |
| `sections[].status` | enum | read-only | — | per section; a section left in draft keeps its previous live version. |
| `sections[].revision` | integer | read-only | — | per section. |

Page status, revision, `published_at` and `blockers[]` are the shared chrome in §3.0.
Publish stays disabled while any blocker remains: all ten sections live, both SEO fields,
a live privacy notice and published settings.

Actions: edit SEO; open a section; preview; submit the page for review; publish the page
(Admin); unpublish (Admin); archive (Admin); view version history. The page publish body
is `{page_version_id, sections[]}`; the element shape is U2. States: draft, in review,
live, unpublished, blocked publish.

### 3.4 Section editor — `/admin/pages/landing/sections/[itemId]`

Admin and Editor. The editor renders the fields of the section's `key` from §2.2–2.11,
plus the rows below. It never creates, reorders or deletes sections.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `nav_label` | string | yes for services, work, process, about, contact | 24 | required at publish (NV-1); null for the other five. |
| `sort_order` | integer | no | — | order of referenced service groups, proof figures or testimonials; projects order themselves through their own `sort_order`. |

Section `status`, `revision` and `blockers[]` are the shared chrome in §3.0. Empty proof
figures, testimonials or FAQs are omitted at read time, not blocked.

Actions: autosave `PATCH /content/{item_id}/drafts/{version_id}`; submit for review;
preview; publish the section (Admin); unpublish the section (Admin); archive (Admin);
version history. The section cannot be permanently deleted (decision 70). States: draft,
in review, live, unpublished, version history.

### 3.5 Legal page list — `/admin/pages/legal`

Admin only on every read and write, version read and preview (`ADMIN.md` §4). An Editor
does not see the route and gets `403 forbidden` if it calls.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `title` | string | yes | 70 | page `h1`; not the footer label. |
| `label` | string | yes | 40 | footer link text; returned by `/routes`, not by the page payload. |
| `path` | string | yes | — | `/privacy`, `/cookies`, `/terms` or `/accessibility`. |

`status` and `published_at` are the shared chrome in §3.0; the approval badge renders
`live`, `awaiting approval`, `approval missing`, `expired` or `revoked`.

Actions: create a legal page (Admin) with `{kind: "legal_page", path}`; open. Delete is
offered only for a never-published draft (decision 70). States: live, awaiting approval,
approval missing.

### 3.6 Legal page editor — `/admin/pages/legal/[itemId]`

Admin only. Four block kinds only: `h2`, `p`, `ul`, `table`; no HTML and no Markdown
(decision 17). Links are plain text until open question 2 is decided.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `path` | string | yes | — | set at create; the API defines no path edit. |
| `label` | string | yes | 40 | footer link text; returned by `/routes`. |
| `title` | string | yes | 70 | rendered as the page's `h1`. |
| `effective_on` | date or null | no | — | null means the London publish date; the payload always carries a resolved date, and a set date may be in the future. |
| `blocks[]` | array | yes | at least 1 | add, remove and reorder blocks. |
| `blocks[].kind` | enum | yes | — | `h2`, `p`, `ul`, `table`. |
| `blocks[].text` | string | yes for `h2` and `p` | `h2` 60, `p` 2000 | no HTML, no Markdown. |
| `blocks[].items[]` | string[] | yes for `ul` | 1–12 items, 200 each | list items. |
| `blocks[].columns[]` | string[] | yes for `table` | count not stated | column labels; the cookies page sample uses Cookie, Purpose, Duration, and the prose also names provider. |
| `blocks[].rows[][]` | string[][] | yes for `table` | 1–30 rows | one cell per column; cell length not stated. |
| `seo.title` | string | yes at publish | 60 | non-empty and unique (NF-5). |
| `seo.description` | string | yes at publish | 160 | non-empty and unique (NF-5). |
| `seo.og_image` | media object or null | no | 0–1 | media picker. |
| `seo.noindex` | boolean | no | — | see U1. |
| `updated_on` | date | read-only | — | the publication date in `Europe/London`; shown as a UK date. |
| `created_by` | uuid | read-only | — | the version's author; the approver must differ. |

The approver is the Admin who records the approval; the endpoint takes no approver field,
and the API refuses an approver who is the author (`ADMIN.md` §6).

Actions: add, remove and reorder blocks; submit; record the legal approval
(`POST .../legal-approval`, no body); publish (Admin); unpublish (Admin); archive
(Admin); delete a never-published draft (Admin); preview; version history. States: draft,
approved, published, approval missing. The cookies page additionally requires its table
names to match `cookies.json` exactly, in both directions (decision 38).

### 3.7 Services — `/admin/services`

Admin and Editor. Service groups and services are separate records, each with its own
status. Three to four groups and two to six services per group are page-level gates; a
group with live services cannot be unpublished until they are (`CONTRACT.md` "What
blocks a publish"; `DATABASE.md` "Services").

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `group.title` | string | yes | 40 | category name. |
| `group.sort_order` | integer | no | — | order of groups in the Services section. |
| `group.status` | enum | read-only | — | content status: `draft`, `in_review`, `published`, `unpublished`, `archived`. |
| `service.title` | string | yes | 60 | unique across the set; `__other__` refused. |
| `service.summary` | string | yes | 160 | outcome-led sentence. |
| `service.group_item_id` | uuid | yes | — | the group it belongs to. |
| `service.sort_order` | integer | no | — | order inside the group; 2–6 live per group. |
| `service.status` | enum | read-only | — | content status, as for a group. |
| `service.slug` | string | see C4 | format only (†) | Phase 2 page slug; no Phase 1 route (decision 9). |

Actions: create a group or service (`{kind, slug?}`); open; reorder groups; reorder
services inside a group. States: draft, live, archived.

### 3.8 Service or group editor — `/admin/services/[itemId]`

Admin and Editor. One screen, two shapes selected by `kind`.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `title` | string | yes | 40 group / 60 service | group category or service title. |
| `summary` | string | service only | 160 | outcome-led sentence. |
| `group_item_id` | uuid | service only | — | cannot publish under an unpublished group. |
| `sort_order` | integer | no | — | group order, or service order inside its group. |
| `slug` | string | see C4 | format only (†) | Phase 2 field; no public link in Phase 1. |
| `long_description` | string | no | not stated | Phase 2 field the record keeps; no Phase 1 control is specified (U4). |

Actions: save; submit; publish; unpublish; archive; delete a never-published, unapproved,
unreferenced item (Admin, decision 70); version history. States: draft, in review, live,
archived.

### 3.9 Projects — `/admin/projects`

Admin and Editor; approvals are Admin only. List shows projects in their live order, with
approval state (`ADMIN.md` §3).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `title` | string | yes | 60 | project title. |
| `client` | string or null | no | 80 | null withholds the name. |
| `sort_order` | integer | no | — | live order in Featured work; publishing the project moves it without a page republish. |

`status` is the shared chrome in §3.0; the approval badge renders `live`, `expired`,
`revoked` or `missing`.

Actions: create (`{kind: "project", slug?}`); open; reorder. States: draft, live,
approval expired.

### 3.10 Project editor — `/admin/projects/[itemId]`

Admin and Editor; the approval panel is Admin only.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `title` | string | yes | 60 | project title. |
| `client` | string or null | no | 80 | naming the client needs the `client_name` scope. |
| `client_need` | string | yes | 280 | the problem, in one or two sentences. |
| `built` | string | yes | 280 | what was built. |
| `result` | string or null | no | 280 | claiming a result needs the `result` scope. |
| `technologies[]` | array | no | 0–8 items | reorder. |
| `technologies[].name` | string | yes | 40 | one technology. |
| `images[]` | array | no | 0–3 | media picker; landscape only, 16:10 at render. |
| `images[].media_id` † | uuid | yes | — | the media record; replacement creates a new row. |
| `images[].alt` | string | yes | 120 | from the media record. |
| `sort_order` | integer | no | — | live order in Featured work. |
| `slug` | string | see C4 | format only (†) | Phase 2 page slug; no Phase 1 route. |
| `category` | string | no | not stated | Phase 2 field the record keeps; no Phase 1 control is specified (U4). |

Approval is the panel in §3.11, Admin only; publish stays disabled without a live approval
covering the version's claims.

Actions: save; attach, remove and reorder images; record or revoke an approval (Admin);
submit; publish; unpublish; archive; delete a never-published, unapproved, unreferenced
item (Admin, decision 70); preview; version history. States: draft, live, image missing
(U5), blocked.

### 3.11 Approval panel — shared by projects, figures, testimonials and logos

Admin only. An approval attaches to a **version**, not an item, so an edit to an approved
quote, result or mark needs a new approval before it can publish (decision 31;
`ADMIN.md` §6).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `subject_kind` | enum | read-only | — | derived from the version: `project`, `proof_figure`, `testimonial`, `client_logo`. |
| `approved_by_name` | string | yes | 120 † | the client contact, not the staff member. |
| `approved_by_email` | string | listed in the body; nullability not stated | not stated | the client contact's email. |
| `approved_on` | date | yes | not in the future | the date the client approved. |
| `expires_on` | date or null | no | ≥ `approved_on` | null means no expiry. |
| `scopes[]` | enum[] | yes | subject-dependent | project: `client_name`, `result`, `mark`, `screenshots`; figure: `figure`; testimonial: `quote` plus optional `client_name`; logo: `mark` plus optional `client_name`. |
| `evidence_media_id` | uuid or null | no | evidence bucket | email or document in the private evidence bucket. |
| `recorded_by` | string | read-only | — | the Admin who recorded it. |
| `revocation_note` | string | yes on revoke | 500 † | revocation cannot be undone; the row keeps `revoked_at`, `revoked_by` and the note. |

The item renders the current approval state: `live`, `awaiting approval`,
`approval missing`, `expired` or `revoked`.

### 3.12 Proof — `/admin/proof`

Admin and Editor; approvals are Admin only. One list for the three proof kinds, filtered
by kind. A client logo has a record and an approval but **no page slot** until D-9
(decision 44).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `kind` | enum | yes | — | `proof_figure`, `testimonial`, `client_logo`. |
| `label` | string | figure only | 40 | what the number counts. |
| `value` | string | figure only | 12 | stored as a string. |
| `quote` | string | testimonial only | 280 | the approved words. |
| `client_name` | string or null | logo, or testimonial when named | not stated | null withholds the name. |

Actions: create a proof item of a kind; filter by kind; open. States: live, expired,
revoked, no slot (logos). The approval badge is derived from §3.11.

### 3.13 Proof figure editor — `/admin/proof/proof_figure/[itemId]`

Admin and Editor; approval is Admin only.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `label` | string | yes | 40 | what the number counts. |
| `value` | string | yes | 12 | real numbers only. |
| `prefix` | string or null | no | 4 | never invent one. |
| `suffix` | string or null | no | 4 | never invent one. |

Approval is the panel in §3.11, Admin only; a figure needs exactly the `figure` scope.

Actions: save; submit; publish; unpublish; archive; delete a never-published, unapproved,
unreferenced item (Admin, decision 70); record or revoke an approval (Admin); version
history. States: draft, live, expired, revoked.

### 3.14 Testimonial editor — `/admin/proof/testimonial/[itemId]`

Admin and Editor; approval is Admin only.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `quote` | string | yes | 280 | the words the client approved in writing. |
| `name` | string or null | no | 60 | null withholds the name; then `role` and `company` must be null. |
| `role` | string or null | no | 80 | null when withheld; otherwise optional. |
| `company` | string or null | no | 80 | null when withheld; otherwise optional. |

Approval is the panel in §3.11, Admin only; `quote` is always required and `client_name`
only when the name may be shown.

Actions: save; submit; publish; unpublish; archive; delete a never-published, unapproved,
unreferenced item (Admin, decision 70); record or revoke an approval (Admin); version
history. States: draft, live, expired, revoked.

### 3.15 Client logo editor — `/admin/proof/client_logo/[itemId]`

Admin and Editor; approval is Admin only. There is no page slot in Phase 1.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `client_name` | string or null | no | not stated | null withholds the name; naming needs the `client_name` scope. |
| `image_id` | uuid | yes when the mark is shown | 0–1 | site image, alt 120, landscape rules do not apply to a logo. |

Approval is the panel in §3.11, Admin only; `mark` is always required and `client_name`
only when named.

Actions: save; submit; publish; unpublish; archive; delete a never-published, unapproved,
unreferenced item (Admin, decision 70); record or revoke an approval (Admin); version
history. States: live, expired, revoked, no slot.

### 3.16 FAQs — `/admin/faqs`

Admin and Editor. FAQ items are child rows of the FAQ section's draft version, not content
items, so this screen has no archive or delete content action; items are added, removed
and reordered inside the draft (`ADMIN.md` §3; `CONTRACT.md` "Records behind the
sections").

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `question` | string | yes | 120 | plain text. |
| `answer` | string | yes | 600 | plain text. |
| `status` | enum | yes | — | `published` or `draft`; draft is filtered from the public read. |
| `sort_order` | integer | no | — | render order. |

Actions: add, remove and reorder questions; set a question's status; save the draft.
States: published count 5–8 (ok), outside (warning). The count is a CMS warning, never a
publish refusal (A13).

### 3.17 Media library — `/admin/media`

Admin and Editor. Non-evidence media only: `media-staging` and `site-media`. Evidence is
never returned here (`ADMIN.md` §4 `GET /media`; T3).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `id` | uuid | read-only | — | opaque; the route key. |
| `alt` | string | yes | 120 | required for every site image. |
| `width` | integer | read-only | — | intrinsic width. |
| `height` | integer | read-only | — | intrinsic height. |
| `type` | string | read-only | — | MIME type, shown but never on the public wire (decision 53). |
| `size_bytes` | integer | read-only | ≤ 4MB | shown; never on the public wire. |
| `state` | enum | read-only | — | `staged`, `public`, `unused`, `deleted`. |
| `usage` † | integer | read-only | — | reference count; ADMIN §4 says "with usage" but names no key. |
| `uploaded_by` | string | read-only | — | staff name. |
| `uploaded_at` | ISO 8601 | read-only | — | upload time. |
| `url` | string | read-only | — | signed while private (5 minutes, proposed, A12); public `/media/...` when promoted. Rendered as the list thumbnail. |

Filters: `state`, `role`, `q`, page. Actions: upload (`multipart file + alt`); open; soft
delete; retry a failed upload. States: uploading with progress, staged ("Publishes with
the page"), public, unused, deleted, alt-text error, type/size/pixel error, upload failed
with retry, replace (creates a new row).

### 3.18 Media detail — `/admin/media/[id]`

Admin and Editor. A media record is immutable: correcting alt text or replacing a file
creates a **new record**, and the old one stays while a version or approval references it
(`CONTRACT.md` "Media"; decision 37).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `usage` | object[] | read-only | — | which versions and approvals reference the record. |
| `deleted_at` † | ISO 8601 | read-only | — | soft-delete time; the object goes when nothing references it. |

Actions: replace the file (new row); correct alt text (new row, then repoint); soft
delete; open the signed URL. The other fields are §3.17; `state` is the shared media state.
States: editing alt, in use.

### 3.19 Evidence — no screen is defined

`ADMIN.md` §3 defines **no** `/admin/evidence` route. Evidence is uploaded from the
approval form and opened through a signed link; it is never a library screen and never
through `/media` (U6). Admin only.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| file (part name not stated) | binary | yes | PDF, JPEG, PNG or WebP; 4MB | Admin only; magic-byte checked. ADMIN §4 names "multipart file" but not the part name (U13). |
| `evidence_media_id` | uuid | no | — | attaches the evidence to an approval (§3.11). |
| `url` | string | read-only | 60 seconds (proposed, A12) | Admin only; signed, never public. |

Actions: upload (`POST /evidence`); open (`GET /evidence/{media_id}/url`); attach to an
approval. States: upload rejected (`422 upload_rejected`), signed link expired. There is no
alt text requirement for evidence (`DATABASE.md` `media_alt_required`).

### 3.20 Enquiries — `/admin/enquiries`

Admin only from list to delete. An Editor gets `403` and the screen is absent from their
navigation (`ADMIN.md` §8). Default order is newest first.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `id` | uuid | read-only | — | route key. |
| `name` | string | read-only | 100 | from the submission. |
| `email` | string | read-only | 254 | from the submission. |
| `company` | string or null | read-only | 120 | from the submission. |
| `service` | string or null | read-only | 60 | the title snapshot; null when the visitor chose "Something else". |
| `status` | enum | yes | — | `new`, `in_progress`, `closed`; moves forward only. |
| `created_at` † | ISO 8601 | read-only | — | received time. |
| `first_replied_at` | ISO 8601 or null | read-only | — | write-once; set by the first-reply action, not by triage. |

Filters: `status`, `q` over name, email and company, `from`, `to`, page. Actions: open;
export CSV over the same filters. States: loading, empty, filtered, error.

### 3.21 Enquiry detail — `/admin/enquiries/[id]`

Admin only. The message is shown here and never in the alert email
(`CONTRACT.md` "The emails").

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `name` | string | read-only | 100 | personal data. |
| `email` | string | read-only | 254 | personal data. |
| `company` | string or null | read-only | 120 | personal data. |
| `service` | string or null | read-only | 60 | title snapshot; null for `__other__`. |
| `message` | string | read-only | 2000 | plain text; never emailed in the alert. |
| `source_path` | string | read-only | 200 | path only, no query string. |
| `consent_notice_version` | string | read-only | 64 | which landing and privacy revisions the visitor saw. |
| `status` | enum | yes | — | `new`, `in_progress`, `closed`; no reopening in Phase 1. |
| `created_at` † | ISO 8601 | read-only | — | received time. |
| `first_replied_at` | ISO 8601 or null | read-only | — | write-once. |
| `notes[].body` | string | yes on add | 1–4000 | internal only; never in an email. |
| `notes[].author_id` † | uuid | read-only | — | staff member. |
| `notes[].created_at` † | ISO 8601 | read-only | — | note time. |

Actions: move status forward; add a note; record the first reply once; export; delete the
enquiry (typed record confirmation, the UK GDPR erasure path). States: new, in progress,
closed.

### 3.22 Settings — `/admin/settings`

Admin only. Settings are one versioned item, published like any other; the live site
changes only on publish (`ADMIN.md` §9). Fixed kinds are never created or deleted from the
UI (A16); archive and restore exist, and M8 accepts that settings may be unpublished while
the landing page is live.

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `company.legal_name` | string | yes at publish | not stated | the parent's exact legal name. |
| `company.trading_name` | string | no | not stated | trading name. |
| `company.country` | string | yes at publish | not stated | the parent's country. |
| `company.address` | string[] | yes at publish | 2–4 lines; per-line limit not stated | legal address; rendered on privacy, terms, footer and contact. |
| `company.uk_establishment` | boolean | no | — | true makes the regulation 63 fields required. |
| `company.home_registry` | string | when `uk_establishment` | not stated | regulation 63. |
| `company.registration_number` | string | when `uk_establishment` | not stated | regulation 63. |
| `company.head_office_location` | string | when `uk_establishment` | not stated | regulation 63. |
| `company.legal_form` | string | when `uk_establishment` | not stated | regulation 63. |
| `company.limited_liability` | string | when `uk_establishment` | not stated | regulation 63. |
| `company.insolvency_information` | string | when `uk_establishment` | not stated | regulation 63. |
| `company.vat_number` | string or null | no | not stated | the VAT line renders only when set. |
| `logo` | media object or null | no | 0–1 | header logo; null renders the repository asset. |
| `nepal_site_url` | string or null | no | 200 † | hreflang target; null until confirmed. |
| `contact.email` | string | yes at publish | 254 † | one monitored address for the whole site. |
| `contact.phone` | string or null | no | 32, E.164 | the site's contact line; requires `contact.phone_hours`. |
| `contact.phone_hours` | string or object | when `contact.phone` is set | shape disputed (C1) | the hours the line is answered. |
| `contact.hours.summary` | string | no | not stated | UK opening hours; the 120 limit is named against `phone_hours.summary` (C1). |
| `contact.hours.timezone` | string | fixed | — | `Europe/London`; no other value is specified. |
| `locations[]` | array | no | — | contact list; a location appears only when it is real. |
| `locations[].name` | string | yes | 60 | city. |
| `locations[].address` | string[] | yes | 2–4 lines, 80 each | a real address; a city with no country is ambiguous. |
| `locations[].country` | string | yes | not stated | must sit beside the city. |
| `locations[].phone` | string or null | no | 32, E.164 | local contact line; requires `phone_hours`. |
| `locations[].phone_hours` | string or object | when `locations[].phone` is set | no limit stated | shape disputed (C2). |
| `footer_note` | string | no | 160 | one line. |
| `footer_links[]` | array | no, seeded with 5 | — | ordered site links; legal links are appended from `/routes`, not stored here. |
| `footer_links[].label` | string | yes | 40 | link text. |
| `footer_links[].href` | string | yes | 200 | anchor or path. |
| `seo_defaults.title_suffix` | string | no | 40 | appended only when the page title does not already end with it. |
| `seo_defaults.description` | string | no | 160 | fills a page that omits its own. |
| `seo_defaults.og_image` | media object or null | no | 0–1 | fallback social card. |
| `cta.label` | string | yes at publish | 30 | header and footer button label. |
| `cta.href` | string | fixed | — | `#contact`; read-only (decision 54). |
| `working_hours[]` | array | no | — | in the admin typed body; shape not specified in ADMIN (U7); an empty table is valid. |

Actions: save; submit; publish; unpublish; archive; restore; preview. Delete is not
offered (fixed kind, A16). `booking_url` and `booking_label` are rejected with `422`
(A7); do not render them. States: draft, live, incomplete identity, blocked.

### 3.23 Staff — `/admin/staff`

Admin only. Invites go through Supabase Auth; the `staff` row is created only after the
auth user exists, so a failed invite leaves no usable role (`ADMIN.md` §2, §4).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `user_id` | uuid | read-only | — | route key. |
| `display_name` | string | yes | 100 † | shown in the list and audit. |
| `email` | string | yes | not stated | unique; Supabase Auth owns the identity. |
| `role` | enum | yes | — | `admin` or `editor`; no third role. |
| `active` | boolean | yes | — | deactivation returns `403 account_inactive` on the next call. |
| `mfa_status` | enum | read-only | — | `enrolled` or `none`; from `staff_account`. |
| `last_sign_in_at` | ISO 8601 or null | read-only | — | from Supabase Auth via `staff_account`. |

Actions: invite (`{email, display_name, role}`); change role, active or display name;
send a password reset; reset another user's MFA (Admin, A17). States: invited (derived
from `auth.users`, not stored, ADMIN §14), active, inactive, last Admin. The last active
Admin cannot be demoted, deactivated or deleted (`409 last_admin`, AD-10).

### 3.24 Audit and sign-in log — `/admin/audit`

Admin only. One screen with two logs. The audit log is append-only; the sign-in log is
separate because it holds address and agent hashes (`ADMIN.md` §10).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `actor_id` | uuid | read-only | — | staff member, or null after a staff deletion. |
| `action` | string | read-only | 80 † | e.g. publish, unpublish, archive, restore, delete, role change, approval. |
| `entity_kind` | string | read-only | 40 † | what was changed. |
| `entity_id` | string | read-only | 100 † | which row. |
| `version_id` | uuid | read-only | — | when the action names a version. |
| `page_id` | uuid | read-only | — | when a section publish names its page. |
| `path` | string | read-only | — | for unpublish, archive and delete. |
| `revision` | integer | read-only | — | for publish. |
| `affected_rows` | integer | read-only | — | for a retention run or an export count. |
| `created_at` | ISO 8601 | read-only | — | event time. |
| `staff_id` | uuid | read-only | — | sign-in row; null when the account is unknown. |
| `outcome` | enum | read-only | — | `success` or `failure`. |
| `ip_hash` | string | read-only | — | hashed address; never the raw address. |
| `user_agent_hash` | string | read-only | — | hashed user agent. |
| `occurred_at` | ISO 8601 | read-only | — | sign-in time. |

Filters: audit `actor`, `action`, `entity_kind`, `entity_id`, `from`, `to`, page; sign-in
`staff_id`, `outcome`, `from`, `to`, page. Actions: filter; paginate. States: loading,
filtered, empty.

### 3.25 Account and MFA — `/admin/account`

Both roles. Own MFA, password and session. Enrolment is the one place the browser talks to
Supabase Auth with the user's own session (`ADMIN.md` §2).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `display_name` | string | read-only | 100 † | own name; edited from `/admin/staff` by an Admin. |
| `email` | string | read-only | not stated | own address. |
| `role` | enum | read-only | — | `admin` or `editor`. |
| `mfa_status` | enum | read-only | — | `enrolled` or `none`. |
| TOTP enrolment | object | yes to reach AAL2 | — | QR or secret plus a code; a UI control whose wire shape is not defined (U8). |

Actions: enrol MFA; verify; sign out; request a password reset through Supabase Auth's
email flow. States: enrolled, not enrolled, reset.

### 3.26 Preview — `/preview<path>`

Admin and Editor; a legal page is Admin only. The route reads the staff session, forwards
the bearer to `GET /api/v1/admin/preview?path=`, and renders the real components in an
iframe (`CONTRACT.md` "Preview"; `ADMIN.md` §11).

| Field | Type | Required | Limit | Role or state that gates it |
| --- | --- | --- | --- | --- |
| `path` | string | yes | — | `/` for the landing page, `/privacy` for a legal page. |
| `preview` | boolean | read-only | — | always `true`. |
| `sections[]` | array | read-only | — | each section's current draft in place of its published version. |
| staged media `url` | string | read-only | — | short-lived signed URL or staff-only `/preview/media/<id>`; never a public `/media/*` path. |

The completeness list beside the iframe is derived from empty required fields in the same
payload; it is not a separate response field. Actions: open the iframe; collapse the
preview pane while keeping the editor usable. States: draft, blocked fields, staged media.
The response is `no-store` and `X-Robots-Tag: noindex`; the route is excluded from the nav,
sitemap and public cache tags.

### 3.27 Database only — not a UI field

These columns are in `DATABASE.md` but not in a CONTRACT payload or an ADMIN request or
response. Do not put them in a form or a table. They are listed so a schema-first
developer does not mistake them for controls.

| Column | Why it is not a UI field |
| --- | --- |
| `content_item.next_version` | Internal counter; `revision` is the exposed version number. |
| `page_section.sort_order` | Seeded and fixed; the admin exposes no section reorder (A16; decision 5). |
| `content_version.submitted_at` | Version history shows author, status, revision and dates; this column is not named as a field. |
| `content_publication.version_id` | The pointer's version id; the UI reads `revision`, `published_at` and `published_by`. |
| `media.object_path`, `bucket`, `visibility`, `checksum_sha256`, `promoted_at` | Storage internals; the UI shows `state`, `url`, dimensions and type. |
| `service.live_title`, `service.live_sort_order`, `project.live_sort_order` | Live projections; the editor uses the version's `title` and `sort_order`. |
| `settings_version.booking_url`, `booking_label` | Not editable; a write is refused with `422` (A7, decision 46). |
| `settings_working_hour.day_of_week`, `opens_at`, `closes_at`, `is_closed` | The row shape is only in `DATABASE.md`; see U7. |
| `enquiry.ip_hash`, `updated_at`, `closed_at` | Not named for the admin screen; the detail shows status and `created_at`/`first_replied_at`. |
| `email_outbox.*`, `rate_limit_event.*` | Delivery and rate-limit internals; no admin screen reads them. |
| `audit_log.id`, `sign_in_event.id` | Row keys, not displayed. |
| `staff.created_by`, `created_at`, `updated_at` | Staff changes are audit-derived (`ADMIN.md` §10). |
| `approval.version_id`, `created_at`, `revoked_at`, `revoked_by` | The current state and the revocation note are shown; these columns are internal. |

## 4. Shared behaviour

**The lifecycle.** `create_draft → draft → submit → in_review → publish → published`.
An Admin may publish a draft directly, skipping review. Editing a published item creates a
new draft copied from live; the live version is untouched. One open version per item; the
drafts endpoint returns the existing one rather than duplicating it (`ADMIN.md` §5).

**Unpublish returns to Draft.** Deleting the publication pointer creates a draft copy
from the last published version in the same transaction (decision 69). Unpublishing the
landing page also removes its sections' pointers and ensures a draft for each of the ten
sections, so it can be republished. Unpublishing one section removes only that section's
pointer; the others keep theirs. An existing open draft is reused, never duplicated.

**Archive is the normal delete.** It unpublishes first, then marks the item archived, in
one transaction; it creates no draft. Archiving the landing page archives its sections.
Restore clears the flags and leaves the item `unpublished` (or in the draft that survived);
it does not republish, and writes no revalidation row (`ADMIN.md` §5; decisions 69–70).

**Permanent delete** exists only for an item that was never published, carries no
approval, is not one of the three fixed kinds (the landing page, its sections, settings)
and is not referenced by a section draft or a service group's services. It requires the
typed title, cannot be undone, writes one `delete` audit row and frees the path or slug.
A legal page is creatable, so a never-published legal draft may be deleted (decision 70).

**Admin-only paths.** Legal pages and settings are Admin on every content read and write,
version read and preview; an Editor's `GET /content` omits them and naming either kind
returns `403` (but see C6 for the preview table's omission of settings). Enquiries, staff,
approvals, evidence and the audit and sign-in logs are Admin only. This is enforced per
request, not by hiding navigation (`ADMIN.md` §1, §4; AD-2).

**Evidence** is Admin-only, lives in the private `evidence` bucket, and is never returned
by `/media`: an Editor reading through `/media` sees no evidence row, and an evidence id is
`404`. It is opened through a 60-second signed link, never embedded (`ADMIN.md` §4, §7;
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

## 5. Field limits

Copied from CONTRACT.md "Field limits" at `CONTRACT.md:1096-1142`. The readable table is
not a second place to edit; the source is the plain data table at
`api/app/content/limits.py`, and the generated OpenAPI schema carries the same numbers.

| Field | Limit | State |
| --- | --- | --- |
| `eyebrow` | 48 characters, optional | decided field, proposed limit |
| `nav_label` | 24 characters | proposed |
| section `heading` | 70 characters | proposed |
| section `intro` | 200 characters, one sentence | proposed |
| `next_steps` | 1–4 items; `title` 80, `body` 200 | decided count, proposed lengths |
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

## 6. Do not build

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

## 7. Open decisions that affect UI

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

## 8. Conflicts and unspecified

Neither list is resolved here. Where the two documents disagree, both citations are
given; where a request body or response key is missing, the OpenAPI schema must settle it
before the control is built.

### 8.1 Conflicts

| # | What | Source A | Source B | Effect on the UI |
| --- | --- | --- | --- | --- |
| C1 | `contact.phone_hours` shape, and which field carries the 120-character hours limit | `CONTRACT.md:721-728`: `phone_hours` is `null` and `hours` is the object `{summary, timezone}`. `CONTRACT.md:1111`: the limit is named against `phone_hours.summary`, "with `timezone` Europe/London". | `ADMIN.md:718`: the field is `contact_phone_hours`, a text column. `DATABASE.md:1304-1305`: `contact_phone_hours text`, and the phone/hours constraint is a paired null check. | Do not build a phone-hours control until the shape is settled: a single text field and an object with `summary`/`timezone` need different forms. |
| C2 | `locations[].phone_hours` shape | `CONTRACT.md:776-778`: a location with a phone "carries `phone_hours` in its own timezone", and `phone_hours` has "the same shape as `contact.hours`" (an object). | `CONTRACT.md:735-736`: the payload sample shows `phone_hours: null` (a scalar). `CONTRACT.md:1108-1110`: the limit table gives `location.phone` 32 but no `location.phone_hours` limit at all. | A location form cannot know whether to render a text field or a summary plus timezone. Wait for OpenAPI. |
| C3 | `next_steps` title and body limits | `CONTRACT.md:1102`: 1–4 items; `title` 80, `body` 200. | `DATABASE.md:758-763`: `contact_next_step.title` ≤ 40 and `body` ≤ 160. | A form that accepts 80/200 will be refused at the database boundary. Use the server's Pydantic limit, not either document's number, once OpenAPI exists. |
| C4 | `slug` and `path` optionality on create | `ADMIN.md:324`: `POST /content` takes `{kind, path?, slug?}` — both optional. | `CONTRACT.md:396-397`: service and project records keep a `slug` for Phase 2. `DATABASE.md:348-353`: a `legal_page` and `landing_page` require a path, and a `service` and `project` require a slug. | The create form cannot assume either is optional. For a service or project, a missing slug reaches a database refusal; for a legal page, a missing path does. |
| C5 | M8: settings unpublished while the landing page is live | `ADMIN.md:930-931`: "Settings can be unpublished while the landing page is live, which would empty the site frame and legal identity; a gate needs a decision." | `Backend/docs/work/PLAN.md:220-224` and `PROGRESS.md:310`: the owner accepted M8 on 27 November, no gate, risk recorded and not mitigated. | No gate is the accepted behaviour, but ADMIN.md still calls it open. Build no gate; flag the doc drift to the orchestrator. |
| C6 | Preview role for settings | `ADMIN.md:364`: `GET /preview` is "both (legal_page: Admin)". | `ADMIN.md:390-392`: "`legal_page` and `settings` require Admin on every content read and write, version read and preview". | An Editor's preview of settings is `403` under the prose and unspecified under the table. Do not offer it until settled. |
| C7 | Sign-in log route | `ADMIN.md:202`: one screen, `/admin/audit`, covers "Audit log and sign-in log". | `ADMIN.md:362`: `GET /sign-ins`; `ADMIN.md:742`: the sign-in log is read by `/admin/sign-ins`, Admins. | The route set is unresolved; do not create a separate `/admin/sign-ins` navigation entry until it is confirmed. |

### 8.2 Unspecified

| # | Item | What is missing | What to do |
| --- | --- | --- | --- |
| U1 | `seo.noindex` | The field is on the wire (`CONTRACT.md:160`, `:652`) and in `content_seo`, but neither document names an editor control or a default rule. | Render it as a read-only flag, or wait for OpenAPI; do not add a toggle silently. |
| U2 | `sections[]` in page publish | `ADMIN.md:332` gives `{page_version_id, sections[]}` and no element shape. | The UI must show which section versions will publish; the element shape is for OpenAPI to define. |
| U3 | Dashboard keys and empty state | `ADMIN.md:322` describes the response in prose ("drafts, in review, new enquiries, expiring approvals, failed revalidation"); no JSON keys or counts are defined. | Do not hard-code key names. Build the five cards against OpenAPI. |
| U4 | Phase 2 fields on service and project records | `CONTRACT.md:396-397` says the records keep service and project `slug`, a service's `long_description` and a project's `category`; neither ADMIN screen table names an editor control for `long_description` or `category`, and no limit is given. | Do not invent a control or a limit. `slug` is the only one with a create-body reference (C4). |
| U5 | Project "image missing" state | `ADMIN.md:192` lists it, but no document defines when it applies. `CONTRACT.md:602` allows 0–3 images; open question 5 proposes 1–3. | Render the badge from the API state; do not derive it from an image count. |
| U6 | Evidence screen | The handover brief names an evidence screen; `ADMIN.md` §3 defines no `/admin/evidence` route. Evidence is uploaded from the approval form and opened by a signed link. | Build the upload and signed-link controls inside the approval panel; do not add a library route. |
| U7 | Structured working hours | `ADMIN.md:718` names `settings_working_hour` rows and `ADMIN.md:399-402` says the typed body includes working hours, but no document names the row's fields; `CONTRACT.md:725-728` exposes only `hours.summary` and `hours.timezone`; `DATABASE.md:1494-1496` says the rows are additive, an empty table is valid, and no gate counts them. | Build `contact.hours.summary` and `timezone`; do not build a structured hours editor until the row shape is in OpenAPI. |
| U8 | Account and MFA enrolment | `ADMIN.md:104-107` says enrolment uses the user's own Supabase session; no request or response shape is defined, and MFA recovery is A17 only. | Use the Supabase client for enrolment; do not invent FastAPI fields. |
| U9 | Admin response field names generally | `ADMIN.md` §4 defines request bodies and says success bodies are the resource, but most response schemas are prose. Names marked † in this file are database or view columns. | Treat OpenAPI as the naming authority; this file's † marks are provisional. |
| U10 | `legal` table columns and cells | `CONTRACT.md:663` shows three sample columns; `CONTRACT.md:695` says the editor owns purpose, duration and provider; `DATABASE.md:1191-1205` fixes only that a column has a non-empty label, and no cell length is given. | Let the editor define the column labels; do not hard-code three columns or invent a cell limit. |
| U11 | Project `category` limit | The field is kept on the record (`CONTRACT.md:396-397`) but has no limit in the field table and no editor control. | Wait for OpenAPI; do not add a limit. |
| U12 | Settings identity field limits | `company.legal_name`, `trading_name`, `country`, the regulation 63 fields and `vat_number` have no limits in `CONTRACT.md` "Field limits" or `ADMIN.md` §9. | Do not inherit an unrelated limit; use the Pydantic schema. |
| U13 | Multipart part names for uploads | `ADMIN.md:342` says `POST /media` takes "multipart file + `alt`"; `ADMIN.md:346` says `POST /evidence` takes "multipart file". The file part's name is not given. | Wait for OpenAPI before wiring the upload; do not assume `file`. |
| U14 | Revalidation queue screen | `ADMIN.md` §11 names `/admin/revalidation` and `GET /revalidation`, but §3 defines no such route and the row fields (`tags`, `status`, `attempts`, `next_attempt_at`, `last_error`) are only in `DATABASE.md`. | Link the dashboard's failed count to the queue once the route and row schema are defined; do not build a table from the columns. |

## 9. Source map

Line ranges are at `3c6f46f`.

| This file | Source | Lines |
| --- | --- | --- |
| 1. Read this first | `CONTRACT.md` Scope, The calls, The Next-to-FastAPI link | 15-92 |
| 1. Read this first | `ADMIN.md` §1–§2 | 30-167 |
| 2. Landing page — shell, hero, proof, services, not-sure | `CONTRACT.md` Landing page | 146-211 |
| 2. Landing page — work, process, about, testimonials, FAQs, contact | `CONTRACT.md` Landing page | 212-345 |
| 2. Landing page — head, structured data | `CONTRACT.md` Head and structured data | 347-360 |
| 2. Landing page — records, approvals, caps, preview | `CONTRACT.md` Records behind the sections, Preview | 362-464 |
| 2. Landing page — what blocks a publish, empty sections | `CONTRACT.md` What blocks a publish | 484-512 |
| 2.12 Contact form | `CONTRACT.md` Enquiry submission, Fields, After a send | 818-1002 |
| 3.0 Shared item chrome | `ADMIN.md` §3 Shared screen behaviour, §4 Conventions, §10 | 207-243, 250-267, 737-760 |
| 3.1 Sign-in | `ADMIN.md` §2 Sign-in; §4 `/auth/*`; §13 T41–T43 | 91-108, 317-320, 885-887 |
| 3.2 Dashboard | `ADMIN.md` §3; §4 `GET /dashboard` | 184, 322 |
| 3.3–3.4 Landing page and section editor | `ADMIN.md` §3 routes; §4 pages endpoints; §5 Publishing a page | 185-186, 332, 337, 553-570 |
| 3.5–3.6 Legal pages | `ADMIN.md` §3 routes; §6 Legal pages; §4 legal-approval; `CONTRACT.md` Legal page | 187-188, 341, 635-649; 638-697 |
| 3.7–3.8 Services | `CONTRACT.md` Records behind the sections; `ADMIN.md` §3 routes | 362-443; 189-190 |
| 3.9–3.10 Projects | `CONTRACT.md` Landing page work, Records; `ADMIN.md` §3 routes; §6 approval scopes | 212-239, 362-443; 191-192, 605-610 |
| 3.11 Approval panel | `ADMIN.md` §6 Proof approvals; §4 approvals endpoints | 588-633, 338-341 |
| 3.12–3.15 Proof items | `CONTRACT.md` Landing page proof and testimonials, Media slot table; `ADMIN.md` §3, §6 | 175-184, 268-284, 599-605; 193-194, 605-610 |
| 3.16 FAQs | `CONTRACT.md` Landing page FAQs, caps; `ADMIN.md` §3, §5 | 285-295, 421-428; 195, 585 |
| 3.17–3.18 Media | `CONTRACT.md` Media; `ADMIN.md` §7; §4 media endpoints | 514-613; 651-681, 342-345 |
| 3.19 Evidence | `CONTRACT.md` Media; `ADMIN.md` §4 evidence endpoints, §6, §7 | 565-570, 607-613; 346-347, 632-633 |
| 3.20–3.21 Enquiries | `ADMIN.md` §8; §4 enquiry endpoints; `CONTRACT.md` Fields | 683-707, 348-354; 927-965 |
| 3.22 Settings | `CONTRACT.md` Site settings, Field limits; `ADMIN.md` §9 | 699-816, 1096-1142; 709-735 |
| 3.23 Staff | `ADMIN.md` §2, §4 staff endpoints, §10, §14; `DATABASE.md` `staff` | 91-108, 356-360, 737-760, 939-951; 198-254 |
| 3.24 Audit and sign-in | `ADMIN.md` §10; §4 `/audit`, `/sign-ins` | 737-760, 361-362 |
| 3.25 Account and MFA | `ADMIN.md` §2, §3, §14 | 104-107, 203, 923-925 |
| 3.26 Preview | `CONTRACT.md` Preview; `ADMIN.md` §11 | 445-464; 762-797 |
| 3.27 Database only | `DATABASE.md` tables cited in the row; `ADMIN.md` §9 for the booking columns | — |
| 4. Shared behaviour | `CONTRACT.md` Revalidation, What blocks a publish; `ADMIN.md` §3, §4, §5, §7, §12 | 94-144, 484-512; 207-243, 366-403, 504-586, 651-681, 799-834 |
| 5. Field limits | `CONTRACT.md` Field limits | 1088-1142 |
| 6. Do not build | `CONTRACT.md` decisions 36, 44, 46, 52, 67; `ADMIN.md` §14; `AGENTS.md` | 1043-1077; 891-933 |
| 7. Open decisions | `CONTRACT.md` Open questions; `ADMIN.md` §14; `PLAN.md` Owner decisions | 1144-1183; 891-933; 218-230 |
| 8. Conflicts and unspecified | The cited lines in each row | — |
