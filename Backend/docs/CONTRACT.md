# Public content contract

Status: draft, for discussion. Started 26 November 2026. The prototype was removed
from the working tree the same day, so nothing described here is implemented yet.

This records what the Next.js server receives from FastAPI while rendering the
public site, what the browser sends when someone enquires, what the CMS owns, and
the decisions taken so far. It is not `requirements.md` yet: the admin API,
authentication, the publishing state machine, the admin side of enquiries and the
audit log are still to be designed.

Every string in angle brackets is a placeholder for copy. None of it is approved
text, and no value here should be treated as content.

## Scope

Phase 1 only: one landing page, the privacy notice, cookie information and
accessibility statement (website terms only once approved), a 404, and the staff
CMS behind them. `/privacy`, `/cookies`, `/terms` and `/accessibility` are the only
paths besides `/`. The browser never calls FastAPI. Next.js fetches during render,
so the contract is server-to-server and needs no CORS.

The 404 is code: the site frame from settings, a route home and the contact link,
not a CMS page.

## The calls

| Call                               | Returns                                     | Cache tag       |
| ---------------------------------- | ------------------------------------------- | --------------- |
| `GET /api/v1/public/page?path=/` | one page, landing or legal                  | `page:<path>` |
| `GET /api/v1/public/settings`    | shared site settings                        | `settings`    |
| `GET /api/v1/public/routes`      | published paths, for the footer and sitemap | `routes`      |

One call per page plus one for settings. There is no single `/site` blob: a page
only carries what it renders, and publishing one page revalidates one tag. The
form's write call, `POST /api/v1/public/enquiries`, is under
[Enquiry submission](#enquiry-submission); it is the only write on the public
surface.

`/routes` returns every published path with the metadata the footer and the sitemap
each need:

```json
{
  "items": [
    { "path": "/", "type": "landing", "label": null, "lastmod": "2026-11-26", "noindex": false },
    { "path": "/privacy", "type": "legal", "label": "Privacy notice", "lastmod": "2026-11-01", "noindex": false }
  ]
}
```

`type` separates legal links from the landing page in the footer, `label` is the
footer's link text so a page title need not be its label, and `lastmod` dates the
sitemap entry. `lastmod` is the publication instant's date in `Europe/London`, not the
server's session date. `noindex` is the page's flag, so the sitemap can leave a page out
while the footer still links it. Phase 1 has two types; a third is a schema change, not
a CMS edit.

## The Next-to-FastAPI link

The calls above are server-to-server, and that has to be enforced, not assumed.

- Every request Next makes to FastAPI carries `X-Service-Token`, a per-environment
  secret of at least 32 random bytes, compared in constant time before routing. A
  request without it gets a bare `401`; FastAPI rejects it before parsing the body, so
  a direct caller cannot reach the public routes or skip Next's checks.
- Admin and preview calls carry the staff bearer as well. The service token says the
  caller is the site; the bearer says which staff member is asking.
- FastAPI also caps a request body at 16KB for the public surface, so the Next cap is
  not the only one. A larger body is refused with `413` before Pydantic runs.
- Where FastAPI's host offers a static egress range or a private network, its firewall
  allows only Vercel, and Cloudflare if Cloudflare proxies FastAPI. The token is the
  control; the allowlist is defence in depth, because Vercel's egress is not static on
  every plan.
- FastAPI never reads `X-Forwarded-For`. The only trusted source of the visitor's
  address is a single `X-Client-IP`, sent by Next and honoured only on a request that
  presents the service token.

Next derives that address from the platform, never from the visitor:

- On Vercel, `x-vercel-forwarded-for` is the address Vercel saw. Vercel overwrites
  `x-forwarded-for` to prevent spoofing, and the `x-vercel-` header survives a proxy in
  front.
- When Cloudflare proxies the site, the Vercel value is Cloudflare's edge, not the
  visitor. Next uses `CF-Connecting-IP` only when the platform address is in
  Cloudflare's published ranges, and otherwise falls back to the platform address. The
  range list is configuration, refreshed on deploy, not fetched at request time.
- If neither yields a valid address, the request is keyed as `unknown` and shares one
  strict bucket. It does not become a fresh identity per request.

The enquiry id, the outcome and the address hash may be logged. The message is not
logged, and the raw address is neither stored nor logged.

## Revalidation

Next caches each public read under the tag in the table. On-demand revalidation is the
normal path, and a 24-hour maximum age is the backstop: a publish or unpublish normally
changes the page within a minute, and an expiry that the daily job misses still clears
within a day. Each read is fetched with `next: { tags: [...], revalidate: 86400 }`; the
tag is what a publish purges, and the lifetime only bounds how long a missed purge can
survive. A publish writes a `revalidation` row in the same transaction as the pointer
move, and a worker drains it:

```
POST /api/revalidate          (Next, shared secret in a header)
{ "tags": ["page:/", "routes"] }
```

| Change                                                | Tags                                                                           |
| ----------------------------------------------------- | ------------------------------------------------------------------------------ |
| a page published                                      | `page:<path>`, `routes` (the path may be new)                              |
| settings published                                    | `settings`, `page:/`, and every legal page tag from `/routes`            |
| a service or group published                          | `page:/` — the landing page projects it                                     |
| a project, figure or quote published                  | `page:/`                                                                     |
| a page unpublished or archived (deleted in the admin) | `page:<path>`, `routes`; a service or group uses `page:/`                |
| an archive restored                                   | none until it is republished; a restore returns it to the CMS, not to the site |
| an approval withdrawn or revoked                      | `page:/` in Phase 1                                                          |
| an approval that expired at midnight                  | the tags of every page holding the item                                        |

Archive is the Phase 1 delete: it unpublishes first, then marks the item archived, in
one transaction, so the public change is an unpublish. Restore clears the archive flags
and nothing else; the item is not live until an Admin republishes it, and that publish
writes its own row.

The worker retries with backoff, so a Next outage delays the page rather than failing
the publish, and the audit records the pending row until it clears. A publish is done
when the row is written, not when Next answers; the worker polls faster than the PRD's
"within 1 minute", so the worst case stays inside it. A row still pending after five
minutes, or dead after its last attempt, alerts the named owner.

The expiry job runs just after midnight in London. Supabase's `pg_cron` evaluates
schedules in UTC, so it is scheduled at 23:05 and 00:05 UTC. One of the two runs is
always within five minutes of 00:05 Europe/London, in GMT and in BST; the other may
queue the same page again, and a duplicate purge is harmless. A failed run, a missing
success in `cron.job_run_details` for more than 26 hours, or a pending revalidation row
older than five minutes alerts the named owner. If nobody acts, the 24-hour cache
ceiling still clears the page.

No cache lifetime is set on the public reads beyond that 24-hour ceiling, so nothing
between FastAPI and Next holds a copy. Admin and preview responses are `no-store`.

## Landing page

`type: "landing"`. The array order is the render order.

```json
{
  "type": "landing",
  "path": "/",
  "revision": 12,
  "published_at": "2026-11-26T09:14:00Z",
  "seo": {
    "title": "<page title>",
    "description": "<meta description>",
    "og_image": null,
    "noindex": false
  },
  "sections": [
    {
      "key": "hero",
      "type": "hero",
      "nav_label": null,
      "data": {
        "eyebrow": "<optional kicker, may be null>",
        "heading": "<the one headline>",
        "body": "<one or two lines>",
        "primary_cta": { "label": "Discuss your project", "href": "#contact" },
        "secondary_cta": { "label": "See our work", "href": "#work" }
      }
    },
    {
      "key": "proof",
      "type": "proof_figures",
      "nav_label": null,
      "data": {
        "items": [
          { "label": "<what the number counts>", "value": "12", "prefix": null, "suffix": null }
        ]
      }
    },
    {
      "key": "services",
      "type": "service_groups",
      "nav_label": "Services",
      "data": {
        "heading": "<heading>",
        "intro": "<one line, sits beside the heading>",
        "groups": [
          {
            "title": "<category>",
            "items": [
              { "title": "<service>", "summary": "<outcome-led sentence>" }
            ]
          }
        ]
      }
    },
    {
      "key": "not-sure",
      "type": "not_sure",
      "nav_label": null,
      "data": {
        "heading": "<short prompt>",
        "body": "<one line>",
        "cta": { "label": "<label>", "href": "#contact" }
      }
    },
    {
      "key": "work",
      "type": "featured_work",
      "nav_label": "Work",
      "data": {
        "heading": "<heading>",
        "intro": "<one line, sits beside the heading>",
        "items": [
          {
            "id": "<opaque, stable>",
            "title": "<project title>",
            "client": null,
            "client_need": "<the problem, in one or two sentences>",
            "built": "<what we built>",
            "technologies": ["<technology>"],
            "result": null,
            "images": [
              {
                "url": "/media/<id>.webp",
                "alt": "<what it shows>",
                "width": 1600,
                "height": 1000
              }
            ]
          }
        ]
      }
    },
    {
      "key": "process",
      "type": "how_we_work",
      "nav_label": "How we work",
      "data": {
        "heading": "<heading>",
        "intro": "<one line>",
        "stages": [
          { "title": "<stage>", "body": "<one line>" }
        ],
        "assurances": [
          { "title": "<assurance>", "body": "<one line>" }
        ]
      }
    },
    {
      "key": "about",
      "type": "about",
      "nav_label": "About",
      "data": {
        "heading": "<heading>",
        "body": [
          "<paragraph>",
          "<paragraph>"
        ],
        "image": null
      }
    },
    {
      "key": "testimonials",
      "type": "testimonials",
      "nav_label": null,
      "data": {
        "heading": "<heading>",
        "items": [
          {
            "id": "<opaque, stable>",
            "quote": "<quote approved in writing>",
            "name": "<client name, or null when withheld>",
            "role": "<role, or null>",
            "company": "<company, or null>"
          }
        ]
      }
    },
    {
      "key": "faqs",
      "type": "faqs",
      "nav_label": null,
      "data": {
        "heading": "<heading>",
        "items": [
          { "question": "<question>", "answer": "<plain-text answer>" }
        ]
      }
    },
    {
      "key": "contact",
      "type": "contact",
      "nav_label": "Contact",
      "data": {
        "heading": "<heading>",
        "body": "<one line>",
        "next_steps": [
          { "title": "<the promise>", "body": "<one line of detail>" }
        ],
        "privacy_note": {
          "text": "<one sentence shown beside the form>",
          "link_label": "<link text>"
        },
        "form": {
          "services": [
            "<published service title>",
            "<published service title>"
          ]
        }
      }
    }
  ]
}
```

The array order is `page_section.sort_order`, seeded from PRD §5 and not editable in
Phase 1: the editor orders items inside a section, never the sections themselves.
`revision` is the page version's number, incremented on each page publish, and the only
internal counter on the public wire. Each section also has its own revision and status
on the admin read; the public payload carries only live sections, so neither appears
here. Section keys double as anchors (`#services`, `#work`), so a key is stable and
renaming one breaks every link to it.

FAQ items are returned in `sort_order`, and only items whose `status` is `published`;
the admin read carries each item's status, so a draft question is visible there and
absent here.

`seo.og_image` is a media object of the same shape as `images[]`, or null. Next builds
the absolute URL for the meta tag from the site-relative path, so the payload never
carries a host.

The not-sure prompt's CTA lands on the form with the message field focused (LP-4).
A project's `technologies` is the list SV-3 asks for; the expanded work row renders it
beside what was built, not in the title.

The CTA `href`s are fixed anchors (decision 54): `#contact` for the hero's primary,
the not-sure CTA and the settings `cta`; `#work` for the hero's secondary. Labels are
content; targets are not, because EN-1 and LP-1 are Musts and a free URL field lets an
editor break them.

### Head and structured data

The hero's `heading` is the page's only `h1`; section headings are `h2`, item titles
`h3` or lower, and the legal page's `title` is its `h1`. The 404 has one `h1` too
(NF-5). Every published page carries a non-empty, unique `seo.title` and
`seo.description`; Next derives the Open Graph tags from them and from
`seo.og_image`. The document is `lang="en-GB"` (NF-8); hreflang is open question 3.
Next emits JSON-LD for `Organization` from settings, `Service` from each published
service and `FAQPage` from the published FAQs, and none of it from an empty or
unpublished item (NF-6).

`sitemap.xml` is built from `/routes` without the `noindex` pages; `robots.txt`
disallows `/admin` and `/preview`, and both responses also carry
`X-Robots-Tag: noindex` (NF-7).

### Records behind the sections

Every one of the ten sections is a record with its own versions, status and
publication pointer. A section version stores its copy and, for four sections, an
ordered set of references to records that carry their own publish state or approval.

| Record            | Backs                                        | Approval |
| ----------------- | -------------------------------------------- | -------- |
| `service_group` | the categories in Services                   | no       |
| `service`       | the items in Services, and the enquiry chips | no       |
| `project`       | the items in Featured work                   | yes      |
| `proof_figure`  | the row in Proof figures                     | yes      |
| `testimonial`   | the items in Testimonials                    | yes      |
| `client_logo`   | a proof item with no page slot until D-9     | yes      |

The hero, not-sure prompt, how we work, about, FAQs and contact reference no records;
their versions are copy. FAQs stay inside the FAQ section's version as child rows, and
each question carries the PRD's `status` and `order`; a `draft` question is filtered
from the public read, so the FAQ has its own status without a version table. The FAQ
section itself is versioned like every other section.

A group is a record rather than a string on each service so renaming a category is
one edit, not one per service. A project's order lives on the project version and is
projected to the live `project` row, so publishing the project moves it in Featured work
without a page republish. The services section orders groups; services order themselves
inside a group.

Versions belong to each section, not to the page (decision 51): one Publish still
produces one page update and one cache tag, because the Admin's click publishes the
ready section versions and the page in one transaction. A section left in draft keeps
its previous published version, so the live page is never half-updated. The page itself
owns only SEO and the OG image. PRD §8's per-section versions are implemented rather
than collapsed.

The records keep the Phase 2 fields §8 names — service and project `slug`, a service's
long description, a project's `category` — even though the payload does not carry
them; decision 9 is about the wire, not the table. Software products are out of
scope by explicit decision (SV-2, PRD §7): no product kind, table, view, slot or
approval subject is modelled. Reintroducing products requires a new `content_kind`,
a typed table, a PRD/D-3 decision and a migration (decision 67). No public Phase 1
payload changes, because no product route or page was ever exposed.

An approval attaches to a version, not to the item. A testimonial's quote is the
words the client approved; editing it creates a new version, which needs a new
approval before it can publish. The same holds for a project's result and its
screenshots, and for a client logo's mark. The approval also says what it permits —
naming the client, claiming the result, using the mark — because a client can approve
the work and withhold their name. A testimonial approval always carries `quote`;
`client_name` is optional, and when it is absent the name, role and company are all
null on the wire. The quote renders anonymously, and the payload cannot attribute it to
a client who withheld the name. Expiry is applied in the read query, and the daily job
revalidates the tags of pages holding an item whose approval expired at midnight, so a
cached page cannot outlive the approval by more than the cache ceiling.

A project with images cannot publish until an unexpired approval carries the
`screenshots` scope; the API checks the client and result scopes against the version's
claims, and the database checks the image scope because `version_media` is a table it
can see.

Caps, using PRD §5's numbers where it gives them: three or four service groups
(publishing fewer than three is refused, because SV-1 is a Must), two to six services
per group, three to six projects (fewer than three blocks the work section, because
§5 fixes 3–6 and NV-1 needs the Work link), at most four proof figures, at most six
testimonials, exactly four stages, exactly three assurances (code ownership, security
and UK-hours contact), and five to eight published FAQs (a FastAPI/Pydantic CMS
warning on published rows, because LP-5 is a Should; the database does not refuse
the section).
Service titles are
unique across the set, because the enquiry stores one title, and none may be the
reserved value `__other__`. Deleting a service does not touch published enquiries: they
store the title, not a reference.

`about.body` is an array, one string per paragraph. The alternative stores line
breaks inside a string and trusts every renderer to split them the same way; the
legal block model already chose the array, so about follows it. One to four
paragraphs.

The PRD's "and the team (if approved)" is deferred: Phase 1 About is prose and one
image, with no team list. PRD §8 puts team profiles in their own tables only when that
feature is approved, so a named team is a Phase 2 change. If it is pulled forward, the
shape is an optional `about.team` array of `{ name, role, image }`, with a `team_image`
media role and real names and consent; it is not filled with invented people.

### Preview

Preview returns the same shape as the public payload with `"preview": true`, each
section's current draft in the place of its published version, and no caching. It is
the page as it would publish, not a second document: the editor's preview iframe
renders the real components, so a layout problem appears where it would appear. Empty
required fields stay empty, and the admin shows the completeness list beside the iframe
from the same payload rather than from a field the public shape does not need.

A preview response is `no-store` and carries `X-Robots-Tag: noindex`. The iframe
loads `/preview<path>` on the site's own origin; that route reads the staff session
cookie, forwards the bearer to `GET /api/v1/admin/preview?path=`, and is excluded
from the nav, the sitemap and every public cache tag.

A preview of an unpublished draft must show images that are still in the private
staging bucket. The preview payload is the one place the media `url` differs from the
public shape: it is a short-lived signed URL from FastAPI, or a staff-only
`/preview/media/<id>` route, never a public `/media/*` path. The response is `no-store`
and the link is scoped to that staff session. The public payload never carries a
signed URL.

## What the CMS owns

Every marketing and legal string a visitor reads is content. The control copy —
labels, validation, errors and the confirmation — is code with the rest of the shape.

| Editable in `/admin`                                                 | Code                                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------------ |
| Hero, services, work, process, about, testimonials, FAQs, contact copy | The order and set of sections, fixed by PRD §5        |
| Service groups and services, projects, figures, testimonials           | Fields, limits, ids, revision and publish state        |
| Uploads, alt text and the header logo | Colours, type and spacing (the repository logo stays the fallback) |
| Legal page blocks, including the cookie table                          | Consent banner, form labels, validation and error copy |
| Settings: legal identity, email, phone, hours, locations, footer note  | The enquiry emails and the 404                         |
|                                                                        | The confirmation's framing (decision 26)               |

The line is deliberate. An editor who can reorder sections turns a PRD guarantee
into a preference, and a heading with no cap breaks the layout at 320px. The strings
about how the site works rather than what Leafclutch offers change with a deploy.

### What blocks a publish

| Content                          | Refuses without                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The landing page                 | every one of its ten sections live; a non-empty, unique `seo.title` and `seo.description` (NF-5); a live privacy notice; published site settings                                                                                                                                                                                                                                                       |
| The hero section                 | a heading, a primary CTA pointing at the form and a secondary CTA pointing at the work section (LP-1)                                                                                                                                                                                                                                                                                                  |
| The not-sure section             | a CTA pointing at the form, so EN-1's after-services button exists                                                                                                                                                                                                                                                                                                                                     |
| The contact section              | a heading, one promise and a non-empty privacy note                                                                                                                                                                                                                                                                                                                                                    |
| The landing page's other sections | a `nav_label` on Services, Work, How we work, About and Contact (NV-1); a non-empty about section (NV-1); three or four service groups (SV-1); three to six published projects (§5); four stages and three assurances                                                                                                                   |
| The FAQ section              | five to eight published FAQs (a CMS warning, not a publish refusal; draft questions do not count)                                                                                                                                                                                                                                                                                                                       |
| Site settings                    | `company.legal_name`, `company.country`, a non-empty `company.address`, a `contact.email`, and a `cta` pointing at the form (EN-1); a `contact.phone` only with `contact.phone_hours`                                                                                                                                                                                                     |
| A legal page                     | a non-empty footer `label`, a title, at least one block, a non-empty, unique `seo.title` and `seo.description` (NF-5), and an approver who is not the author (a null `effective_on` renders the publish date)                                                                                                                                                                                   |
| The cookies page                 | cookie names matching `cookies.json` exactly, in both directions                                                                                                                                                                                                                                                                                                                                      |
| A project, figure, testimonial or client logo | an unexpired approval covering what the version claims; a logo needs `mark`, and `client_name` only when named                                                                                                                                                                                                                                                                |

Presence and targets are gated; position is not. LP-1's "both visible without
scrolling" and NV-1's sticky header are component tests, and a CTA label can change
without breaking the anchor the gate checked.

Empty proof figures, testimonials and FAQs are omitted at read time rather than
blocked at publish, so the page can go live before that proof exists. LP-3 and §5's
testimonials require that hiding, and R-2's fallback relies on it for figures and on
`client`/`result` being null for work. Services, work, how we work, about and contact
are gated above and are never omitted.

The privacy gate is two-way: the privacy notice cannot be unpublished or archived while
the landing page is live, because the form would collect without the notice it links to.
Unpublish the landing page first, or publish a replacement notice. Archive is an
unpublish plus a flag, so the same check applies to it.

## Media

The PRD fixes where images live and what the admin must know about them, not how they
are processed. Each environment has its own project and buckets, and the media bucket
is copied to a second location (pages 14–15, SE-7). The media record carries file,
type, size, alt text, uploaded by and uploaded on (page 12). Alt text is required,
uploads are checked for type and size before they are stored, and nothing is kept on
the app server (pages 10, 19). NF-9 judges the result: compressed modern formats,
correct sizes, descriptive alt text, no Lighthouse image warnings (page 22).
Cloudinary is only for advanced image processing (page 14), so resizing and format
conversion stay with FastAPI.

Three buckets:

| Bucket            | Visibility | Holds                                                                |
| ----------------- | ---------- | -------------------------------------------------------------------- |
| `media-staging` | private    | every site image from upload until the version using it is published |
| `site-media`    | public     | the published copy of a site image, served at `/media/<id>.<ext>`  |
| `evidence`      | private    | approval evidence, contracts and client correspondence               |

A site image is uploaded to `media-staging`, and its media row is private and staged.
The editor can attach it to a draft; nothing is public yet. When the draft is
published, FastAPI copies each attached object to `site-media`, marks the row public,
and only then commits the pointer move. If the publish transaction fails, FastAPI
deletes the copies it made and marks those rows deleted, so no unreferenced file stays
public; the draft reports the images as needing re-upload. The rule is: a file is
public only when a published version references it, which is what SM-4 requires for
screenshots as well as for names and quotes. Preview and the admin thumbnails read the
staged object through a short-lived signed URL, never the public bucket.

The PRD gives no formats, size cap, pixel bounds or crop. These are Leafclutch
decisions, not PRD requirements, and the values are proposals rather than measured
limits:

| Step           | Rule                                                                                                             |
| -------------- | ---------------------------------------------------------------------------------------------------------------- |
| Accepted types | JPEG, PNG, WebP, by magic bytes, never by filename or content type                                               |
| Size           | 4MB at most                                                                                                      |
| Pixels         | at most 40 megapixels and 8192px on either side before decode; 1200px minimum width, long edge resized to 2000px |
| Shape          | Landscape only for work images, cropped 16:10 at render                                                          |
| Metadata       | EXIF, GPS and the colour profile removed; output is sRGB WebP                                                    |
| Name           | An opaque random id; the original filename is discarded                                                          |
| Alt text       | Required, 120 characters at most, written by the uploader                                                        |

The 4MB cap is set by the path, not by taste: Vercel Functions accept a 4.5MB request
body by default, and the upload goes through the BFF. A 20MiB opt-in exists in beta;
Phase 1 does not rely on it. A larger original must be resized before upload, because
the 2000px output is the file that is stored. FastAPI refuses an image whose declared
or decoded pixel count exceeds the guard before it decodes the full bitmap, so a
compressed bomb cannot exhaust the worker.

Evidence is not the image pipeline. Its bucket accepts PDF, JPEG, PNG and WebP, 4MB at
most, checked by magic bytes. A PDF is stored as uploaded and opened through a
short-lived signed URL; the site never renders it inline, and the admin downloads it
rather than embedding it. An image in this bucket still passes the decode guard.
Contracts and client correspondence go here too; the PRD names evidence only, so that
is a Leafclutch addition.

Uploads go to Next.js, which forwards them to FastAPI; the browser never writes to
Supabase. FastAPI checks the bytes, strips metadata and stores the result; the record
is created only when all of that succeeds.

A media record is immutable: `id`, `type`, `size_bytes`, `url`, `width`, `height`,
`alt`, `uploaded_by`, `uploaded_at`. `type` and `size_bytes` are the PRD's type and
size (page 12): the admin shows them, and the wire never carries them. Replacing a
file or correcting alt text creates a new record, so a published page's snapshot never
changes underneath it; "replace" therefore repoints the reference rather than
overwriting a stored file. Promotion from staged to public is the one other transition,
and it is one-way. Removing an image drops the reference; the object is deleted once no
version references it.

Version history is kept for the life of the Phase 1 site, so an image that any version
ever referenced is never deleted. That resolves the apparent conflict between "keep
previous versions" (PRD §7) and "delete once unreferenced": garbage collection only
reclaims uploads that no version ever referenced, or that were detached from a draft
before it published. Storage growth is accepted, because a published page must keep
rendering its snapshot.

The wire carries `{ "url", "alt", "width", "height" }` and nothing else. The URL is
site-relative on purpose: Next rewrites `/media/*` to the public bucket, so content
never carries a provider host and moving storage is a rewrite rather than a content
migration. The bucket holds one file per upload, resized to 2000px on its long edge;
Next's optimizer derives the srcset widths from it. The intrinsic size reserves the
box and keeps CLS under 0.1. Paths are immutable, so assets cache for a year.

| Slot        | Where                             | Count                                    |
| ----------- | --------------------------------- | ---------------------------------------- |
| Header logo | settings `logo` | 0–1, null renders the repository asset |
| Work images | `sections[work].items[].images` | 0–3 per project                         |
| About image | `sections[about].data.image`    | 0–1, null until the identity is settled |
| Social card | the page's `seo.og_image`       | 0–1, null today                         |
| Client logo | No slot                           | Record and approval exist; D-9 decides a slot |

There is no media route on the public API. `GET /api/v1/public/media/*` does not
exist and the anonymous test asserts a 404, because a listing would expose uploads and
proof nobody approved. The public bucket URL is the only way to a published file, and
a staged file has no public URL at all. Proof evidence lives in the private bucket
that no public call can read, through short-lived signed links (page 14). Contracts and
client correspondence go there too; the PRD names evidence only, so that is a
Leafclutch addition.

## Analytics and consent

Plausible, cookieless, plus Search Console verification (decision 45). No banner and
no preferences control on that basis: nothing non-essential is set, so there is
nothing to consent to — subject to the Turnstile check below.

The cookie page lists what the site actually sets: the Supabase cookies after a staff
sign-in, and anything Turnstile sets. Turnstile is the one to verify on the finished
site, because its script loads for every visitor; if it writes a cookie, it belongs
in `cookies.json` before the landing page can publish, and if legal finds it is not
strictly necessary, it needs consent like any other non-essential script. Legal
decides whether the bot check is strictly necessary, and the site does not assume it
either way.

If legal finds Plausible is not exempt, or Turnstile is not strictly necessary, the
banner returns: Reject all as visible as Accept all, no non-essential script before
consent, and the preferences control PRD §5 lists in the footer. That changes this
section, not the payload.

Plausible events cover PRD §14: Enquire clicks by location, form starts, submissions,
form errors and traffic source. There is no "Book a call" event because decision 46
dropped the link.

## Legal page

`type: "legal"`. Same endpoint, different shape: a document, not sections.

```json
{
  "type": "legal",
  "path": "/privacy",
  "revision": 12,
  "published_at": "2026-11-26T09:14:00Z",
  "seo": {
    "title": "<page title>",
    "description": "<meta description>",
    "og_image": null,
    "noindex": false
  },
  "title": "<page title>",
  "updated_on": "2026-11-26",
  "effective_on": "2026-11-26",
  "blocks": [
    { "kind": "h2", "text": "<heading>" },
    { "kind": "p", "text": "<paragraph>" },
    { "kind": "ul", "items": ["<item>"] },
    {
      "kind": "table",
      "columns": ["Cookie", "Purpose", "Duration"],
      "rows": [["<name>", "<purpose>", "<duration>"]]
    }
  ]
}
```

Four block kinds. No HTML and no Markdown from the CMS, so the output cannot
carry a script, a broken link or a heading level that breaks the page outline.
`updated_on` is a real date because the privacy notice and the accessibility
statement have to show when they last changed; the page formats it as a UK date. It is
the publication instant's date in `Europe/London`, not the server's session date, so a
publish late on a BST evening still shows the UK day.

`effective_on` is the PRD's effective date field. The draft may hold null, meaning
"the date it publishes"; the payload always carries a date, resolved in
`Europe/London`. A set date is shown as written and may be in the future, which is what
an effective date is for. `updated_on` stays the last change, so the page can say both
"last updated" and "effective from" without one standing in for the other.

The footer's label for a legal page is not in this payload: it is stored on the page
document and returned by `/routes`, because the page renders `title` as its `h1` while
the footer may use a shorter label. `/routes` also derives `lastmod` from the same
`Europe/London` date, so the sitemap and the page agree.

The company identity line above the blocks is rendered from settings, not typed into
the copy, so the footer, Contact section, privacy notice and terms cannot disagree
(PRD §12); a UK establishment renders its regulation 63 lines from the same
settings.

The cookies page uses the `table` block, and publishing it is refused unless its
cookie names match the checked-in `cookies.json` exactly, in both directions. The
editor owns purpose, duration and provider; the file owns existence, and the web
build reads the same file so it cannot set a cookie the page has never heard of.
Adding a cookie is a code change that fails to publish until the page catches up.

## Site settings

```json
{
  "revision": 12,
  "data": {
    "company": {
      "legal_name": "<the parent's exact legal name>",
      "trading_name": "Leafclutch",
      "country": "Nepal",
      "address": ["<street>", "<city>", "<postcode>"],
      "uk_establishment": false,
      "home_registry": null,
      "registration_number": null,
      "head_office_location": null,
      "legal_form": null,
      "limited_liability": null,
      "insolvency_information": null,
      "vat_number": null
    },
    "logo": null,
    "nepal_site_url": null,
    "contact": {
      "email": "<the one monitored address>",
      "phone": null,
      "phone_hours": null,
      "hours": {
        "summary": "<UK opening hours>",
        "timezone": "Europe/London"
      }
    },
    "locations": [
      {
        "name": "<city>",
        "address": ["<street>", "<city>", "<postcode>"],
        "country": "<country>",
        "phone": null,
        "phone_hours": null
      }
    ],
    "footer_note": "<one line>",
    "footer_links": [
      { "label": "Services", "href": "#services" },
      { "label": "Work", "href": "#work" },
      { "label": "How we work", "href": "#process" },
      { "label": "About", "href": "#about" },
      { "label": "Contact", "href": "#contact" }
    ],
    "seo_defaults": {
      "title_suffix": " | Leafclutch",
      "description": "<default meta description>",
      "og_image": null
    },
    "cta": { "label": "Enquire", "href": "#contact" }
  }
}
```

One email serves the whole site. The form, the footer and every location block point
at it, because the enquiry inbox does not vary by location and a visitor should never
have to guess which address is read.

`contact.phone` is the site's own contact line. It is null unless the line is answered,
and it requires `contact.phone_hours` whenever it is set, because a number listed
outside the hours it is answered is worse than no number. It lives in `contact`, not in
`locations`, so a staffed UK line needs no UK street address: the PRD allows a contact
line without a UK office, and the label is component copy. The number is rendered in
the Contact section; the footer's legal identity still comes from `company.address`.

`company.address` is the legal address and is rendered on the privacy notice, the
terms, the footer and the Contact section from settings, so §12's identity cannot
drift between them. `locations` is where the team actually is: a list in the contact
section, with the footer keeping the legal line and a link to it. The two can describe
the same place; neither is invented.

A location appears only when it is real. A street address on a UK-facing site is a
claim of presence, not styling, and a city with no country beside it is ambiguous.
A location's `phone` is null unless the line is answered, and a location with a phone
carries `phone_hours` in its own timezone. `phone_hours` has the same shape as
`contact.hours`; the site's opening hours are always the UK hours in `contact.hours`,
and a location's `phone_hours` only qualifies that local line. A phone is labelled a
contact line, never a UK office unless an office exists (page 20); the label is
component copy. There is no social block. The regulation 63 and VAT lines render only
when `company.uk_establishment` is true, and the VAT line only when `vat_number`
is set; otherwise the registration block is absent. `logo` is a media object of
the same shape as `images[]`, or null, which renders the repository asset.
`nepal_site_url` is the NF-8 hreflang target, null until the Nepal URL is
confirmed; the locale codes are still open (open question 3). The stored but
unpublished `booking_url` and `booking_label` appear nowhere here (decision 46).

An address is two to four lines (the field limit below says so), because a Nepali
address has no postcode and a UK one has more than a street; the renderer joins them
with line breaks and nothing in the payload says which line is which.

The contact section reads settings for the email, the phone, the hours and the
locations. `contact.data.form.services` is computed at read time from the published
services, not stored in the version, so the chips cannot drift from the section above
them; preview computes it from that page's draft services.

The header and footer render the same `cta`. PRD EN-1 wants an Enquire button in the
header, the hero, after services and in the footer; the hero and after-services ones
are section content, and the header and footer read settings, so all four point at
the form and a label change is one edit.

`footer_links` is the PRD's footer links field. It stores the ordered site links,
seeded with the five above; legal links are appended from `/routes` because their
visibility follows publication and a static list would go stale. `seo_defaults` is the
PRD's SEO defaults field: `description` and `og_image` fill a page that omits them, and
`title_suffix` is appended to a page title that does not already end with it. A page's
own `seo` always wins, and every Phase 1 page still carries a unique `seo.title` for
NF-5.

The footer's legal list comes from `/routes`, so an unapproved terms page is simply
absent. Its section links are `footer_links`, which is seeded from the header's
`nav_label` list; the seed is one edit, and an editor changing one list twice is the
cost of storing the PRD's field. The cookie page is labelled Cookies rather than Cookie
preferences, because with no optional cookies there is no preference to set (decision
52).

## Enquiry submission

The contact section always renders the form. The browser posts to Next.js; Next.js
posts to FastAPI. Nothing browser-facing calls FastAPI, so the submission uses the
same BFF boundary as the reads.

| Hop                | Call                              | Holds                  |
| ------------------ | --------------------------------- | ---------------------- |
| Browser → Next.js | `POST /api/enquiries`           | JSON, same origin      |
| Next.js → FastAPI | `POST /api/v1/public/enquiries` | JSON, server to server |

The Next route accepts only `POST`, only `application/json`, only its own origin by
`Origin` and `Sec-Fetch-Site`, and caps the body at 16KB before forwarding. Nothing
about the request is logged except the enquiry id, the outcome and the hashed
address; the message is never written to a log.

### What the browser sends

```json
{
  "name": "<name>",
  "email": "<email>",
  "company": null,
  "service": "<an ever-published title, or __other__>",
  "message": "<the project, plain text>",
  "turnstile_token": "<token>",
  "website": ""
}
```

`service` is the selected chip. The last chip, "Something else", is component copy,
not a service row; it sends the reserved value `__other__`. FastAPI accepts that value
and stores `service_title` as null, so the choice is recorded without inventing a
service. Any other string must be an ever-published title. When the CMS has no
services, the field is hidden and `service` is null.

`website` is the honeypot: hidden from sight and from assistive technology, empty
for every real visitor. The browser does not send the source page or the consent
version; Next.js sets the first from the same-origin `Referer`, and FastAPI sets
the second at save time, so a visitor cannot forge either.

### What comes back

Success, `201`:

```json
{ "status": "received" }
```

Failure, one envelope for every public call:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Check the highlighted fields.",
    "fields": { "email": "Enter a valid email address." }
  }
}
```

| Code                    | Status | When                                                                               |
| ----------------------- | ------ | ---------------------------------------------------------------------------------- |
| `validation_failed`   | 422    | A field is missing, too long or malformed; `fields` names each one               |
| `rate_limited`        | 429    | Too many submissions from one address; `Retry-After` says when                   |
| `verification_failed` | 400    | The Turnstile token is missing, expired or rejected                                |
| `not_found`           | 404    | No published page at that path                                                     |
| `service_unavailable` | 503    | FastAPI cannot reach the database; keep the visitor's text and show the site email |
| `internal_error`      | 500    | Anything unhandled; no internal detail in the body                                 |

A browser fetch rejection or timeout produces no envelope; the form treats it as
`service_unavailable` and uses the same fallback.

A honeypot hit returns `201` and saves no enquiry: a bot learns nothing from a
success. The attempt is still counted by the rate limit. A failed confirmation email
does not fail the submission, because the enquiry is saved first and the email is
retried. A `503`, a `500`, a network failure or a timeout shows the site email address
beside the error, so EN-8's fallback is on screen.

Rate limits: 5 attempts per 10 minutes and 20 per hour from one address, and 3 per hour
for one email address. Every attempt is counted, not only saved enquiries. FastAPI
writes a `rate_limit_event` row before the honeypot, Turnstile and validation checks,
so a flood of invalid submissions, failed tokens or honeypot hits is limited by the
same rule. The event is committed on its own, so a rejected attempt cannot escape the
count. The counts are in Postgres over the hashed address and hashed email, not an
in-memory counter, so a restart does not reset them and several workers share one
answer. A Cloudflare rule can be the first line only if the site is deliberately
proxied and tested, as PRD §9 requires; the Postgres limits are the enforced ones.
Turnstile is verified once, after the limit check and before anything is saved; a
rejected token keeps the form filled and asks for another try.

The raw IP is never stored or logged. `ip_hash` on the enquiry is an HMAC of the
address with a server secret, kept for 30 days and then set to null by a job; the
rate-limit events are kept for 7 days. A hashed address is still personal data, so
both periods go in the privacy notice, and D-8's answer must cover them.

Retention is 24 months for the enquiry, its notes and its two outbox rows, then a
scheduled delete. Outbox rows are also deleted 30 days after they are sent, or 30 days
after a dead row was created, so a visitor's name and email do not sit in the mail
queue longer than the delivery needs them. PRD §8 proposes the 24 months (page 13) and
D-8's legal answer confirms it, along with the shorter periods, before launch; the
privacy notice states them before the form collects.

An erasure request deletes the person's enquiry rows, which cascades to the notes and
the outbox. The audit log keeps the fact that an Admin deleted them, with no name,
email, message or address. The request is answered within one month, and the identity
check is recorded. The PRD already gives Admins export and delete (page 11); this adds
the retention clock and the no-personal-data audit rule.

### Fields

| Field                      | Required               | Limit                                     | Notes                                                     |
| -------------------------- | ---------------------- | ----------------------------------------- | --------------------------------------------------------- |
| `name`                   | yes                    | 1–100                                    | trimmed                                                   |
| `email`                  | yes                    | 254                                       | one address, checked by Pydantic and again by the browser |
| `company`                | no                     | 0–120                                    | trimmed; null when empty                                  |
| `service`                | yes when options exist | one ever-published title or `__other__` | `__other__` is the Something else chip; stored as null  |
| `message`                | yes                    | 1–2000                                   | plain text, line breaks kept                              |
| `website`                | must be empty          | 0                                         | honeypot, never shown                                     |
| `turnstile_token`        | yes                    | —                                        | verified once, server-side                                |
| `source_path`            | set by Next.js         | 200                                       | path only, no query string                                |
| `consent_notice_version` | set by FastAPI         | 64                                        | `landing-r<revision>+privacy-r<revision>`               |

No phone, budget or timeframe field. PRD EN-2 fixes the list to name, email,
company (optional), service and message; the reference's specific EUR bands and
timeframes are not PRD requirements, and the 26 November answer to D-12 dropped both
its budget field and its booking link (decision 46). Phase 1 shows no prices. No
marketing tick box: EN-3 says the form sends without one. The privacy note sits beside
the form, under the send button, and links to `/privacy`.

The form is one column below 768px; above it, the heading, body and promises sit
in a left column and the form in the right, the reference's rhythm. Services are
radio chips in a single group, not the reference's checkboxes, because the enquiry
stores one service. "Something else" is appended by the component, not a service
row, so a visitor is never forced to choose a wrong one.

`service` must be one of the titles the site has ever published, not only one that is
live now, or the reserved value `__other__`. The check runs against published `service`
versions, including ones that were unpublished after the page rendered, so a title that
was on the page when it rendered is still accepted and an invented string is not. The
title is stored as a snapshot: the choice was valid when it was made, and rejecting it
would lose a real enquiry to a content edit. `__other__` is accepted for the
"Something else" chip and stored as null, so the CMS does not gain a fake service. If
the CMS has no services, `service` is null and the field is hidden.

Publishing the contact section requires a non-empty privacy note and a published
privacy notice; the API refuses the publish otherwise. That makes EN-3 a rule of
the CMS rather than a thing to remember.

### After a send

The form is replaced in place by a fixed confirmation carrying the promise from
PRD EN-6: within 1 UK working day. The promise is code, not CMS content, because
EN-6 makes it a launch requirement and an editor must not be able to delete it.
The full sentence is copy; the promise itself is D-11, confirmed on 26 November:
email only, one UK working day, until UK hours are staffed.

Field errors appear under the field, `aria-invalid` is set, and focus moves to the
first one. The confirmation is announced and focused. Pressing send twice sends
once. The text survives every failed send: a 429 or 503, a fetch that rejects, or a
request that times out before Next answers. A network failure, timeout or 502/504 is
treated like `service_unavailable`: keep the text, show the site email, and offer
retry. If Turnstile cannot load, or JavaScript is off, the form shows the enquiry email
address instead of a dead button.

Turnstile is a third-party script loaded on the landing page. Whether it is
strictly necessary, and so needs no prior consent, is for the cookie page and the
privacy notice to record; the site does not classify it by default.

### The emails

Two per enquiry, both rows in the outbox written in the same transaction as the
enquiry:

| Email        | To                  | Carries                                                                                                                                                      |
| ------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Alert        | the monitored inbox | name, company, service, received-at in UK time, and a link to the enquiry; never the message                                                                 |
| Confirmation | the visitor         | a short summary (name, service, received-at), the 1 UK working day promise, the site email and a reference; not the message, which stays in the admin record |

The alert omits the message, so an inbox compromise leaks less than the database
would. The confirmation is EN-7's "Should" and it ships; its failure does not fail the
submission, because the outbox retries. Both leave from the sending subdomain with SPF,
DKIM and DMARC in place, and both are sent in plain text and HTML. Both set `Reply-To`
to `contact.email`, so a reply reaches the monitored inbox (PRD §8); the From address
stays on the sending subdomain.

## Decisions

| #  | Decision                                                                                                    | Why                                                                                                                                                                                                                   |
| -- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | One call per page, plus one for settings                                                                    | A page carries only what it renders; publishing revalidates one tag                                                                                                                                                   |
| 2  | Server-to-server only; no browser tokens or CORS                                                            | The browser talks to Next.js; Next.js talks to FastAPI                                                                                                                                                                |
| 3  | Only published and currently approved content                                                               | Expired or revoked approvals disappear from the payload entirely                                                                                                                                                      |
| 4  | Approval records never leave the API                                                                        | The wire carries no approver, evidence or expiry, so it cannot leak                                                                                                                                                   |
| 5  | Array order is render order                                                                                 | No `sort_order` on the wire; the editor orders items, and PRD §5 fixes the sections                                                                                                                                |
| 6  | Header and footer are site frame, not sections                                                              | They come from settings plus a nav derived from sections                                                                                                                                                              |
| 7  | Nav is derived from `nav_label` on visible sections                                                       | A withheld section cannot leave a dead menu link                                                                                                                                                                      |
| 8  | Empty optional sections are omitted by the API                                                              | No empty shells with nothing to hide client-side; services, work, process, about and contact are gated instead                                                                                                        |
| 9  | No `slug` on the wire                                                                                     | Phase 1 has no service pages, so the payload has no link to one; the record keeps its slug for Phase 2 (§8)                                                                                                          |
| 10 | `images` is an array                                                                                      | PRD §5 says screenshots, not screenshot; holds nought to three                                                                                                                                                       |
| 11 | `client` and `result` are nullable; null means withheld                                                 | Naming a client and claiming an outcome both need approval                                                                                                                                                            |
| 12 | FAQ answers are plain text                                                                                  | Five short answers do not justify a rich-text editor or an XSS surface                                                                                                                                                |
| 13 | Stage numbers come from array position                                                                      | The CMS does not store "01", "02", "03"                                                                                                                                                                               |
| 14 | One media object per image, with intrinsic size                                                             | Next generates the srcset; width and height keep CLS under 0.1                                                                                                                                                        |
| 15 | Hero keeps an optional `eyebrow`                                                                          | A user decision (26 Nov), not required by PRD §5; null renders no eyebrow                                                                                                                                            |
| 16 | `next_steps` is 1–4 editor-managed promises                                                              | The CMS adds and deletes them; the schema caps count and length only (user decision, 26 Nov)                                                                                                                          |
| 17 | Legal pages use four block kinds, no HTML                                                                   | Renders safely without a sanitiser and keeps the heading outline intact                                                                                                                                               |
| 18 | `revision` is the only internal counter exposed                                                           | It drives cache keys; `version_number` was internal state the page never read                                                                                                                                       |
| 19 | Field labels, validation and the confirmation are code; the heading, promises and privacy note are content  | EN-3, EN-4 and EN-6 are launch requirements an editor must not be able to edit away                                                                                                                                   |
| 20 | Services are single-select radio chips built from published service titles                                  | The enquiry stores one `service`; the reference's checkboxes would change the schema                                                                                                                                |
| 21 | "Something else" is appended by the component, not a service row                                            | A visitor is never forced to choose a wrong service, and the CMS does not gain a fake one                                                                                                                             |
| 22 | No phone, budget or timeframe fields                                                                        | EN-2 fixes the field list; the reference's EUR bands are out, and Phase 1 shows no prices                                                                                                                             |
| 23 | The browser posts to Next.js; Next.js posts to FastAPI                                                      | The same BFF boundary as the reads: no CORS and no browser-facing FastAPI                                                                                                                                             |
| 24 | Honeypot hits get a success response and no record                                                          | A bot cannot tell a discard from a save                                                                                                                                                                               |
| 25 | `consent_notice_version` is `landing-r<revision>+privacy-r<revision>`                                   | It reproduces what the visitor saw with no number for a human to remember to bump                                                                                                                                     |
| 26 | The confirmation is fixed copy carrying the 1 UK working day promise                                        | PRD EN-6 and D-11's recommendation; D-11 confirmed 26 November                                                                                                                                                        |
| 27 | The contact section cannot publish without a privacy note and a live privacy notice                         | EN-3 and the repository rule become a publish check, not a habit                                                                                                                                                      |
| 28 | Services and service groups are records, projected into the section                                         | PRD gives services a publish state, and Phase 2 pages attach to the same rows                                                                                                                                         |
| 29 | Service titles are unique across the set                                                                    | The enquiry stores one title, so duplicates make the choice ambiguous                                                                                                                                                 |
| 30 | Every section is a record; services, projects, figures, testimonials and logos are referenced records | A section's status and versions are its own, and a referenced record keeps its own publish state or approval                                                                                                              |
| 31 | An approval attaches to a version, not to an item                                                           | Editing an approved quote or result must be re-approved before it can publish                                                                                                                                         |
| 32 | One email for the site; locations differ by name, address and phone                                         | The form has one inbox, and per-location addresses would send enquiries where nobody reads                                                                                                                            |
| 33 | A listed phone requires staffed hours in its own timezone                                                   | A number answered outside the hours it advertises is worse than no number                                                                                                                                             |
| 34 | Locations are settings, not a section                                                                       | The contact section and the footer read the same list, so they cannot disagree                                                                                                                                        |
| 35 | Site images upload to a private staging bucket and are copied to the public bucket at publish               | SM-4 covers screenshots, so an unapproved draft file must not be fetchable even by an unguessable URL; the copy is one storage call per image                                                                         |
| 36 | No media route on the public API                                                                            | A listing would expose drafts and proof nobody approved                                                                                                                                                               |
| 37 | Media records and their paths are immutable                                                                 | A published snapshot stays valid and assets can cache for a year; promotion is the one one-way exception                                                                                                              |
| 38 | The cookie table is CMS content checked against `cookies.json`                                            | PRD §12 binds the page to what the site sets, and an editor cannot know that                                                                                                                                         |
| 39 | Email only, one UK working day, until UK hours are staffed                                                  | D-11 confirmed 26 Nov; a working day is Monday to Friday excluding England and Wales bank holidays                                                                                                                    |
| 40 | Preview is the public payload with `preview: true` and drafts in place                                    | One shape to keep honest; the editor sees the page it will publish                                                                                                                                                    |
| 41 | `about.body` is an array of paragraphs                                                                    | Storing line breaks in a string depends on every renderer splitting them identically                                                                                                                                  |
| 42 | `/routes` carries `path`, `type`, `label`, `lastmod` and `noindex`                              | The footer needs the type and label, the sitemap needs the date and the flag, from one call                                                                                                                           |
| 43 | Header and footer read one settings `cta`                                                                 | EN-1's four buttons must not drift apart; two are content and two are frame                                                                                                                                           |
| 44 | Client logos exist as records but have no render slot in Phase 1                                             | PRD §5 has no logo slot; D-9 is open, so the data model and approval exist without a page reference (open question 7)                                                                                                |
| 45 | Plausible and Search Console; no consent banner                                                             | D-4 answered 26 Nov; cookieless, subject to legal's exemption sign-off (page 21)                                                                                                                                      |
| 46 | No budget field and no booking link in Phase 1                                                              | D-12 answered 26 Nov: the owner wants neither. EN-2 fixes the short form, and EN-10's booking link is a Should. EN-10 already describes a link that opens in a new tab, not an embed, so consent was never the reason |
| 47 | Media is served from the site's own `/media/*`, rewritten to the bucket                                   | Content carries no provider host; changing storage is a rewrite, not a content migration                                                                                                                              |
| 48 | `form.services` is computed at read time                                                                  | A stored copy would drift from the services section above it                                                                                                                                                          |
| 49 | Two emails per enquiry, both outbox rows                                                                    | EN-7's confirmation ships, and the alert leaves the message out                                                                                                                                                       |
| 50 | Rate limits count every attempt in Postgres, and the raw IP is never stored                                 | A restart does not reset the count, invalid and honeypot floods are limited too, and the address stays unrecoverable                                                                                                  |
| 51 | Versions belong to each section, not to the page                                                           | PRD §8 gives each section a status and draft and published versions; one Publish still updates the page and one cache tag, in one transaction                                                                        |
| 52 | The footer links Cookies, not Cookie preferences                                                            | No optional cookies exist, so there is no preference to set; NV-3's link resolves to the cookie information page                                                                                                      |
| 53 | Media records store `type` and `size_bytes`; the wire omits both                                        | PRD page 12 lists type and size in the admin record; the public payload has no use for either                                                                                                                         |
| 54 | CTA targets are fixed anchors; only labels are content                                                      | EN-1's four buttons and LP-1's two must not drift, and a free URL field lets an editor break a Must                                                                                                                   |
| 55 | Next authenticates to FastAPI with a service token, and the client IP travels in a header only Next can set | The BFF boundary is a security control only if FastAPI can tell Next from a direct caller                                                                                                                             |
| 56 | Rate-limit events live 7 days; the enquiry's `ip_hash` is nulled after 30 days                            | A hashed address is still personal data, and the limit needs it for hours, not two years                                                                                                                              |
| 57 | Version history is kept for the life of the Phase 1 site; media referenced by any version is never deleted  | Published versions are immutable and kept, so GC only reclaims uploads no version ever referenced                                                                                                                     |
| 58 | Field limits are defined once, and both validators derive from them                                         | The PRD assumed shared Zod rules; with FastAPI the source is one data table that builds Pydantic and the generated Next client                                                                                        |
| 59 | Public reads have a 24-hour maximum age                                                                     | An approval expiry must clear even if the daily job or its alert fails                                                                                                                                                |
| 60 | Evidence uploads accept PDF as well as images                                                               | Contracts and correspondence are PDFs, and the private bucket is where they go                                                                                                                                        |
| 61 | A service title is valid if it has ever been published                                                      | A title unpublished after the page rendered was still a real choice; an invented string was not                                                                                                                       |
| 62 | Testimonial attribution is optional and all-or-nothing                                                      | An approval can allow the quote and withhold the name, as `project.client` already allows                                                                                                                           |
| 63 | "Something else" sends the reserved value `__other__`, stored as null                                     | The chip is not a service row, and inventing one would put a fake choice in the CMS                                                                                                                                   |
| 64 | The site's contact phone lives in settings, not in a location                                               | EN-9 asks for a UK phone if staffed, and the PRD allows a contact line without a UK office                                                                                                                            |
| 65 | Phase 1 About is prose plus one image; team profiles are Phase 2                                            | The PRD says "the team (if approved)" and §8 puts team profiles in separate tables only when approved                                                                                                                |
| 66 | Every entity and main field in PRD §8 has a named home                                                     | The PRD is mentor-approved; a field is implemented with its PRD meaning or recorded as deferred, never renamed or folded into a neighbour                                                                              |
| 67 | Products are out of scope by explicit decision | SV-2, PRD §7: no product kind, table, view, slot or approval subject is modelled; reintroduction needs a new `content_kind`, a typed table, a PRD/D-3 decision and a migration. No public Phase 1 payload changes: no product route or page was ever exposed |
| 68 | Preview stays authenticated-only; no token table | Every approver is staff under MFA with a 12-hour idle expiry; SE-12's private, no-store and noindex are met by the staff session, not by a shareable bearer                                                                                                           |

## Deliberately absent

No approval record, approver name, version number, draft flag, section status, author,
per-section `updated_at`, staff, media library, enquiry data or design tokens. If it is
not rendered, it is not sent: a payload with nowhere to put a draft is easier to prove
safe. The admin read carries each section's status and revision; the public payload
carries neither. A client logo is a record with its approval but no page slot, so it is
absent from the public payload until D-9 approves one (decision 44, open question 7).

## Field limits

These limits are defined once, in a plain data table at `api/app/content/limits.py`.
The FastAPI Pydantic models are built from it, the OpenAPI schema carries the same
numbers, and a build step generates the Next.js Zod schema and its TypeScript types.
CI fails if this table, the Pydantic models or the generated client differ. The table
below is the readable copy, not a second place to edit.

| Field                                                 | Limit                                                                      | State                           |
| ----------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------- |
| `eyebrow`                                           | 48 characters, optional                                                    | decided field, proposed limit   |
| `nav_label`                                         | 24 characters                                                              | proposed                        |
| section `heading`                                   | 70 characters                                                              | proposed                        |
| section `intro`                                     | 200 characters, one sentence                                               | proposed                        |
| `next_steps`                                        | 1–4 items; `title` 80, `body` 200                                     | decided count, proposed lengths |
| `privacy_note.text`                                 | 240 characters                                                             | proposed                        |
| `privacy_note.link_label`                           | 40 characters                                                              | proposed                        |
| service `title`                                     | 60 characters                                                              | proposed                        |
| service `summary`                                   | 160 characters                                                             | proposed                        |
| media `alt`                                         | 120 characters                                                             | proposed                        |
| location `name`                                     | 60 characters                                                              | proposed                        |
| location `phone`                                    | 32 characters, E.164 formatted                                             | proposed                        |
| contact `phone`                                     | 32 characters, E.164 formatted, optional; requires `phone_hours`         | proposed                        |
| contact `phone_hours.summary`                       | 120 characters, with `timezone` `Europe/London`                        | proposed                        |
| form `name`                                         | 1–100                                                                     | proposed                        |
| form `email`                                        | 254                                                                        | proposed                        |
| form `company`                                      | 0–120, optional                                                           | proposed                        |
| form `message`                                      | 1–2,000                                                                   | proposed                        |
| `client_need`, `built`, `result`                | 280 characters each                                                        | proposed                        |
| project `client`                                    | 80 characters, optional; null when withheld                                | proposed                        |
| project `technologies`                              | 0–8 items, 40 characters each                                             | proposed                        |
| testimonial `quote`                                 | 280 characters                                                             | proposed                        |
| testimonial `name` / `role` / `company`         | 60 / 80 / 80 characters, each optional; all null when the name is withheld | proposed                        |
| evidence file                                         | PDF, JPEG, PNG or WebP; 4MB                                                | proposed                        |
| FAQ `answer`                                        | 600 characters                                                             | proposed                        |
| legal `h2`                                          | 60 characters                                                              | proposed                        |
| `about.body` paragraph                              | 1–4 paragraphs, 600 characters each                                       | proposed                        |
| page `seo.title`                                    | 60 characters                                                              | proposed                        |
| page `seo.description`                              | 160 characters                                                             | proposed                        |
| legal `title`                                       | 70 characters                                                              | proposed                        |
| legal `label`                                       | 40 characters                                                              | proposed                        |
| legal `p`                                           | 2,000 characters                                                           | proposed                        |
| legal `ul`                                          | 1–12 items, 200 characters each                                           | proposed                        |
| legal `table`                                       | 1–30 rows                                                                 | proposed                        |
| project `title`                                     | 60 characters                                                              | proposed                        |
| service group `title`                               | 40 characters                                                              | proposed                        |
| proof `label` / `value` / `prefix` / `suffix` | 40 / 12 / 4 / 4 characters                                                 | proposed                        |
| stage, assurance `title` / `body`                 | 40 / 160 characters                                                        | proposed                        |
| FAQ `question`                                      | 120 characters                                                             | proposed                        |
| `footer_note`                                       | 160 characters                                                             | proposed                        |
| `footer_links` item `label` / `href`                | 40 / 200 characters                                                        | proposed                        |
| `seo_defaults.title_suffix` / `description`         | 40 / 160 characters                                                        | proposed                        |
| legal `effective_on`                                | date, optional; null means the publish date                                | proposed                        |
| `cta.label`                                         | 30 characters                                                              | proposed                        |
| location `address`                                  | 2–4 lines, 80 characters each                                             | proposed                        |

## Open questions

1. **Contact reply time.** One `next_steps` item typed `reply_time`, rewordable but
   not deletable, so EN-6 cannot be edited away? Or four free promises, which an
   editor can remove along with the promise the confirmation makes. Proposed: the
   typed item. It narrows the 1–4 add-and-delete decision rather than replacing it;
   the other three stay free.
2. **Legal links.** The four block kinds have no inline link, so the privacy notice
   can name the ICO and each processor only as plain text. Proposed: a constrained
   link kind, because a legal page with no clickable contact or complaint route is
   worse than one with a validator. It does not allow HTML.
3. **Hreflang (NF-8).** The PRD requires hreflang links between the UK and Nepal
   sites, but gives neither the Nepal URL nor its language tag. `nepal_site_url`
   now exists on settings and is exposed, but the Nepal URL value and both locale
   codes still need confirmation — neither `en-NP` nor `ne-NP` is assumed.
4. **D-7's conditional fields.** If the branch is a registered UK establishment, §12
   requires the regulation 63 details (home registry, registration number,
   head-office location, legal form, limited-liability status, insolvency
   information) and a VAT number only if registered. `company` now carries
   `uk_establishment`, the six regulation 63 fields and `vat_number`, gated at
   publish when `uk_establishment` is true; values still need D-7, and nothing is
   seeded.
5. **At least one screenshot per published project?** PRD §5 and SV-3 list
   screenshots as part of featured work, while the contract allows 0–3 images.
   Proposed: 1–3, because a project row with no image is the thin portfolio §4 warns
   against and DS-3 asks for real screenshots; the cost is waiting for approved
   images before the work section can publish.
6. **D-8 retention sign-off.** The PRD proposes 24 months for enquiries and 12 for
   audit. This contract adds 30 days for the enquiry's `ip_hash` and the outbox, and
   7 days for rate-limit events, because a hashed address is still personal data.
   D-8's answer and the privacy notice must state all four periods before the form
   collects.
7. **Client logos (D-9).** PRD §7, §8, §16 and D-9 treat a client logo as a proof type,
   while decision 44 keeps it out of Phase 1 because §5's landing page has no logo slot.
   The schema now carries the `client_logo` content kind, media role and `mark` approval
   scope, so D-9 decides only whether a slot is added. A slot is a page reference and a
   render change, not a table change; it needs its own approval before build.

Analytics and D-12 were answered on 26 November: Plausible with Search Console
(decision 45), and neither the budget field nor the booking link (decision 46).

## Open before the admin document

| Question         | The PRD settles                                                                                                                           | It does not                                                                                                                      |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Auth and session | Supabase Auth: invite-only, email and password, TOTP MFA, HTTP-only cookies, a 7-day invite, sessions ending after 12 idle hours (page 9) | How FastAPI verifies a session. §9 assumed no separate API server (page 14), so the BFF-to-FastAPI flow is outside the document |
| FastAPI's host   | London is required for Vercel `lhr1` and Supabase `eu-west-2` (page 14); `AGENTS.md` keeps FastAPI in a London region               | The host itself. D-1, the Nepal infrastructure audit, may still change the stack (page 26)                                       |
| Email retry      | Resend, or Postmark; SPF, DKIM and DMARC on a separate sending subdomain (pages 14, 17)                                                   | How a failed send is retried. The PRD requires the failure to be logged and retried (page 13) but does not design the mechanism  |

Analytics is no longer here: D-4 is answered as Plausible (decision 45), and only
legal's exemption sign-off and the Turnstile cookie check wait on the finished site.

One conflict follows from the FastAPI decision, and `AGENTS.md` supersedes the PRD in
it: §9's "No separate API server". D-5's custom admin remains: the UI stays in
Next.js at `/admin`, and FastAPI performs its operations.

## Not covered yet

The admin API, authentication and MFA, idle expiry, the publishing state machine,
the media upload endpoint, the admin side of enquiries and approvals, and the audit
log. Revalidation is described above because publishing writes its rows; the admin
side is what remains. The admin document also owns the per-section editor and how the
Publish call chooses which section versions go with the page. None of the rest changes
what is described above except the upload endpoint's response shape.

Outside this document: security headers and HSTS (SE-1), dependency alerts (SE-9),
the breach plan (SE-11), environments, backups and restore, monitoring and CI (pages
15 and 23). They belong in `requirements.md` and the ops runbook; none is decided
here.

The database schema and its Alembic migration plan are in `DATABASE.md`.
