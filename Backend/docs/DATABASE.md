# Database schema and migrations

Status: draft, for approval before scaffolding. Started 26 November 2026. Storage
revised on 27 November 2026: every field is a typed column or a child row; no column
holds a document. PRD gap closure applied on 27 November 2026 (eight items addressed,
plus the product scope exclusion; see the section at the end). Nothing here is implemented yet.

This is the PostgreSQL schema for the FastAPI service and the Alembic migration plan
that creates it. It follows `CONTRACT.md` for the wire shape and `PRD.md` for the
requirements; where the PRD leaves a choice, the choice is marked as a decision rather
than presented as a PRD rule. The wire contract changes only for the settings
identity, the `logo` slot and the `nepal_site_url` hreflang target; no page payload
changes. `CONTRACT.md` also records decisions 6, 46, 52 and 67 (header/footer frame,
no booking/budget, Cookies page, products out of scope); none of them adds a schema
field.

The database is Supabase PostgreSQL in `eu-west-2` (London). Only FastAPI holds
runtime credentials. The browser never reaches it, and the Supabase Data API is off
for these tables.

## What this document decides

- **Typed storage, not documents.** Every field the PRD names for an entity is a
  column, or a row in a child table when the field is a list of records. Ordered
  lists — paragraphs, address lines, technologies, legal list items, table columns
  and table cells — are child rows. No column holds a JSON or JSONB document, and
  none is used at runtime. The only arrays left hold a small set of labels on an
  operational row, `revalidation.tags` and `approval.scopes`, and both are bounded
  by a check.
- **Version model:** each content item has one open draft or in-review version at a
  time; published versions are immutable; a publication pointer says which version is
  live. The version itself is an identity row; the content of that version is a typed
  row keyed by `version_id` and, for lists, child rows.
- **Pages are built from section records:** each landing-page section is its own
  content item with its own versions, status and publication pointer. The page item
  owns SEO and the section order. Publishing a page publishes the ready section
  versions in one transaction, so a section has a real draft and a real published
  version (PRD §8's Page sections row), while the Admin still clicks one Publish.
- **Records are referenced, not copied:** a section version selects service groups,
  projects, figures and testimonials. The public read resolves each reference to that
  record's live version, so publishing a record updates the page without republishing
  the page.
- **Staff identity:** Supabase Auth owns credentials, MFA, invites and sessions.
  `public.staff` owns role and active state. `staff_account` is the read-only view
  that exposes name, email, role, MFA status, active and last sign-in as one row.
- **Approvals attach to versions.** A new version of a project, figure, testimonial or
  client logo needs a new approval. Legal pages have a separate approver record, and
  the approver cannot be the author.
- **Media rows are immutable except one promotion.** Replacing a file or correcting alt
  text creates a new row. A site image is staged privately and promoted to the public
  bucket at publish. Objects are deleted only when no version or approval references
  them, and version history is kept, so a previously published image is never deleted.
- **Enquiries are saved before email.** The enquiry and its two outbox rows are written
  in one transaction; a worker sends them with retries.
- **Revalidation is an outbox.** A publish or unpublish writes `revalidation` rows in
  the same transaction, and archive writes them through its unpublish when the item, or a
  live section of a landing page, was live; a permanent delete writes none, because the
  item never published. A FastAPI worker drains them. Restore writes none, because it
  does not publish.
- **Audit is append-only.** Sign-in attempts (success and failure, for AD-7 and the
  AD-10 slowdown) are written by FastAPI to `sign_in_event` and purged after
  12 months; application actions are written to `audit_log`. Supabase Auth's own
  audit log is not the record, because its retention cannot be verified from this
  repository and the 12-month record is a PRD obligation.
- **RLS is the second guard.** `anon` and `authenticated` are revoked; FastAPI's
  `api_runner` role bypasses RLS. The Data API stays off.
- **PRD fidelity:** every entity and main field in PRD §8's data model has a named
  home with the PRD's meaning. Nothing is dropped or folded into a neighbour: a
  section's status is not the page's, an FAQ's status is its own, a project's order is
  its own, and a legal page's effective date is a field rather than a render of the
  publish date.

## Model at a glance

| Table                     | Holds                                                                                             |
| ------------------------- | ------------------------------------------------------------------------------------------------- |
| `staff`                 | Staff role and active state, linked to `auth.users`                                             |
| `media`                 | One row per stored file: staged, public or evidence                                               |
| `content_item`          | One row per logical page, section, service, project, figure, testimonial, logo or settings record |
| `content_version`       | Version identity, status, author and timestamps                                                   |
| `content_publication`   | The version currently live for an item                                                            |
| `content_seo`           | SEO title, description, noindex and OG image for any page version                                 |
| `page_section`          | Section item, page, key and render order                                                          |
| `section_version`       | One section's copy, with the columns that section uses                                            |
| `section_paragraph`     | The About section's paragraphs, ordered                                                           |
| `process_stage`         | The four how-we-work stages                                                                       |
| `process_assurance`     | The three assurances below the stages                                                             |
| `faq_item`              | Question, answer, status and order inside the FAQ section                                         |
| `contact_next_step`     | The promises shown after the form                                                                 |
| `section_version_item`  | Ordered section references to service groups, projects, figures and testimonials                  |
| `service_group_version` | A service category's title                                                                        |
| `service_version`       | A service's copy, group and order                                                                 |
| `service`               | Live projection of a published service, with its group and unique title                           |
| `project_version`       | A project's copy and order                                                                        |
| `project_image`         | A project version's images, ordered                                                               |
| `project_technology`    | A project version's technologies, ordered                                                         |
| `project`               | Live projection of a published project, carrying its Featured-work order                          |
| `proof_figure_version`  | A figure's label, value, prefix and suffix                                                        |
| `testimonial_version`   | A quote and its optional attribution                                                              |
| `client_logo_version`   | A client name and its logo image                                                                  |
| `legal_page_version`    | A legal page's footer label, title and effective date                                             |
| `legal_block`           | A legal page's heading or paragraph block                                                         |
| `legal_block_item`      | A list block's items, ordered                                                                     |
| `legal_block_column`    | A table block's column labels, ordered                                                            |
| `legal_block_row`       | A table block's rows, ordered                                                                     |
| `legal_block_cell`      | One cell of a table block row                                                                     |
| `settings_version`      | The settings singleton's legal, identity, contact, hours, logo, hreflang, SEO and CTA fields      |
| `settings_address_line` | The legal identity's address lines, ordered                                                       |
| `settings_location`     | A real place shown on the site                                                                    |
| `settings_location_address_line` | A location's address lines, ordered                                                      |
| `settings_footer_link`  | A stored footer link                                                                              |
| `settings_working_hour` | One structured opening interval: ISO day, opens/closes or closed, split intervals allowed         |
| `legal_approval`        | The non-author approver for a legal page version                                                  |
| `approval`              | Client permission attached to a project, figure, testimonial or logo version                      |
| `enquiry`               | One submitted enquiry, with its consent version and source page                                   |
| `enquiry_note`          | Internal notes, Admin-only                                                                        |
| `rate_limit_event`      | Hashed IP and email keys for durable rate limiting                                                |
| `email_outbox`          | The alert and confirmation emails, retried by a worker                                            |
| `revalidation`          | Next.js cache tags waiting for a worker                                                           |
| `audit_log`             | Append-only record of staff actions                                                               |
| `sign_in_event`         | One staff sign-in attempt: who, when, address and agent hashes, outcome; purged after 12 months    |

## Enums

```sql
create extension if not exists pgcrypto;
create extension if not exists citext;

create type staff_role as enum ('admin', 'editor');

create type content_kind as enum (
  'landing_page',
  'page_section',
  'legal_page',
  'service_group',
  'service',
  'project',
  'proof_figure',
  'testimonial',
  'client_logo',
  'settings'
);

create type page_section_key as enum (
  'hero',
  'proof',
  'services',
  'not-sure',
  'work',
  'process',
  'about',
  'testimonials',
  'faqs',
  'contact'
);

create type version_status as enum ('draft', 'in_review', 'published');

create type approval_scope as enum (
  'client_name',
  'result',
  'mark',
  'screenshots',
  'quote',
  'figure'
);

create type media_visibility as enum ('public', 'private');

create type media_role as enum (
  'project_image',
  'about_image',
  'og_image',
  'client_logo',
  'site_logo'
);

create type enquiry_status as enum ('new', 'in_progress', 'closed');

create type faq_status as enum ('published', 'draft');

create type legal_block_kind as enum ('h2', 'p', 'ul', 'table');

create type email_kind as enum ('enquiry_alert', 'enquiry_confirmation');

create type email_status as enum ('pending', 'sent', 'failed', 'dead');

create type revalidation_status as enum ('pending', 'sent', 'failed', 'dead');
```

`media_visibility` is `public` for a promoted site image and `private` for a staged
site image or evidence; the bucket column says which of the two private cases it is.

`pg_cron` is enabled by Supabase for the scheduled jobs; the job migration checks for
it rather than assuming a plain PostgreSQL install has it.

## Tables

### Staff

```sql
create table staff (
  user_id uuid primary key references auth.users (id) on delete restrict,
  email citext not null,
  display_name text not null,
  role staff_role not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_by uuid references staff (user_id) on delete set null,
  constraint staff_email_unique unique (email),
  constraint staff_display_name_length check (char_length(display_name) between 1 and 100)
);

create index staff_active_role_idx on staff (role) where active;
```

The email is denormalised so the admin list does not need the Supabase Admin API for
every row. It is written when the invite is sent and kept in step by the invite and
email-change flows. `last_sign_in_at`, MFA enrolment and password state stay in
`auth.users`; duplicating them would create a second source of truth.

There is no local invite table. Supabase Auth sends the invite, enforces the 7-day
expiry and owns MFA. FastAPI creates the `staff` row only after the auth user exists,
so a failed invite leaves no usable role.

The PRD's Users entity lists name, email, role, MFA status, active and last sign-in.
The first, third, fourth and fifth are `staff` columns; the other two stay in Supabase
Auth because duplicating them would create a second source of truth. `staff_account`
exposes the whole entity as one read-only row:

```sql
create view staff_account as
select
  s.user_id,
  s.display_name,
  s.email,
  s.role,
  s.active,
  case
    when exists (
      select 1 from auth.mfa_factors f
      where f.user_id = s.user_id and f.status = 'verified'
    ) then 'enrolled'
    else 'none'
  end as mfa_status,
  u.last_sign_in_at
from staff s
join auth.users u on u.id = s.user_id;
```

`auth.mfa_factors` is Supabase's table of enrolled second factors; a factor that is
still `unverified` does not count. The view is granted to `api_runner` only. A plain
PostgreSQL test harness creates the minimal `auth.users` and `auth.mfa_factors` tables
it needs, as it already does for the foreign key.

### Media

```sql
create table media (
  id uuid primary key default gen_random_uuid(),
  visibility media_visibility not null,
  bucket text not null,
  object_path text not null,
  mime_type text not null,
  size_bytes bigint not null,
  width integer,
  height integer,
  alt text,
  checksum_sha256 bytea not null,
  uploaded_by uuid not null references staff (user_id) on delete restrict,
  uploaded_at timestamptz not null default now(),
  promoted_at timestamptz,
  deleted_at timestamptz,

  constraint media_object_unique unique (bucket, object_path),
  constraint media_bucket check (bucket in ('media-staging', 'site-media', 'evidence')),
  constraint media_visibility_bucket check (
    (visibility = 'public' and bucket = 'site-media') or
    (visibility = 'private' and bucket in ('media-staging', 'evidence'))
  ),
  constraint media_promotion check (
    (visibility = 'public') = (promoted_at is not null)
  ),
  constraint media_deleted_after_upload check (
    deleted_at is null or deleted_at >= uploaded_at
  ),
  constraint media_promoted_after_upload check (
    promoted_at is null or promoted_at >= uploaded_at
  ),
  constraint media_object_path check (
    char_length(object_path) between 1 and 300 and object_path !~ '^/'
  ),
  constraint media_mime_length check (char_length(mime_type) between 1 and 100),
  constraint media_size check (size_bytes > 0 and size_bytes <= 4194304),
  constraint media_checksum check (octet_length(checksum_sha256) = 32),
  constraint media_alt_length check (alt is null or char_length(alt) between 1 and 120),
  constraint media_alt_required check (bucket = 'evidence' or alt is not null),
  constraint media_types check (
    (bucket = 'evidence'
      and mime_type in ('application/pdf', 'image/jpeg', 'image/png', 'image/webp'))
    or (bucket <> 'evidence'
      and mime_type in ('image/jpeg', 'image/png', 'image/webp'))
  ),
  constraint media_width check (width is null or width > 0),
  constraint media_height check (height is null or height > 0),
  constraint media_image_dimensions check (
    mime_type not like 'image/%' or (width is not null and height is not null)
  )
);
```

`media` is immutable except for one promotion and one `deleted_at` value. A replacement
creates a new id, path and row; the old row stays while a version or approval references
it. `promoted_at` and `deleted_at` must not precede `uploaded_at`, and once `deleted_at` is
set it cannot be changed or cleared.

Rows are normally created `private` in `media-staging`, but the database does not prevent a
direct public insert: the upload path is the only writer, and deletion is governed by the
later reference checks and the M12 grants.

A site image is inserted `private` in `media-staging` and stays there while it is only
on a draft. Publishing copies the object to `site-media` and updates the row to
`public` with `promoted_at` set; that transition is one-way. A public row can never
return to staged, and an evidence row can never become public. `alt` is required for
every site image, staged or public, and optional for private evidence. The 4MB cap is
the Vercel Functions request-body limit (4.5MB, with a 20MiB beta Phase 1 does not use)
less headroom, because the upload passes through the BFF. The pixel guard and the
formats are Leafclutch decisions; the PRD requires type and size checks, Supabase
Storage and required alt text.

The evidence bucket accepts PDF as well as JPEG, PNG and WebP. A PDF is not rendered by
the site or inline in the admin; staff open it through a short-lived signed URL. Images
in either bucket pass the same decode guard: at most 40 megapixels and 8192px on either
side before the bitmap is decoded.

The object path is `<id>.<extension>`, with the extension derived from the stored
format, so the original filename never reaches storage or the URL. The database check on
`object_path` is a length and leading-slash guard, not a traversal check: M17 builds
`<id>.<extension>` from the stored id and format and must not trust an incoming value.

### Content items and versions

```sql
create table content_item (
  id uuid primary key default gen_random_uuid(),
  kind content_kind not null,
  path text,
  slug text,
  created_at timestamptz not null default now(),
  created_by uuid not null references staff (user_id) on delete restrict,
  next_version integer not null default 1,
  archived_at timestamptz,
  archived_by uuid references staff (user_id) on delete restrict,

  constraint content_item_next_version check (next_version > 0),
  constraint content_item_path_format check (
    path is null or path ~ '^/([a-z0-9-]+(/[a-z0-9-]+)*)?$'
  ),
  constraint content_item_slug_format check (
    slug is null or slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
  ),
  constraint content_item_path_required check (
    kind not in ('landing_page', 'legal_page') or path is not null
  ),
  constraint content_item_slug_required check (
    kind not in ('service', 'project') or slug is not null
  ),
  constraint content_item_settings_shape check (
    kind <> 'settings' or (path is null and slug is null)
  ),
  constraint content_item_section_shape check (
    kind <> 'page_section' or (path is null and slug is null)
  ),
  constraint content_item_archive check (
    (archived_at is null) = (archived_by is null)
  ),
  unique (id, kind)
);

create unique index content_item_path_key on content_item (path) where path is not null;
create unique index content_item_kind_slug_key on content_item (kind, slug) where slug is not null;
create unique index content_item_settings_singleton on content_item (kind) where kind = 'settings';
create index content_item_kind_idx on content_item (kind) where archived_at is null;
```

The `unique (id, kind)` constraint is redundant with the primary key, and exists so
typed child tables can use a composite foreign key that proves the kind. It is cheaper
than a trigger on every insert.

Deleting content in the admin has two paths. `archive_content` is the normal delete: it
unpublishes the item, sets `archived_at` and `archived_by`, and keeps the versions for
audit. The archive update is refused while a publication pointer still names the item;
`archive_content` deletes the pointer first. For a landing page it also unpublishes every
section pointer, including when the page itself is not live. `archived_by` is
`on delete restrict`: staff are deactivated rather than deleted, and the archive record
is audit evidence.
`restore_content` clears the flags; a restored item is not live until it is republished. `delete_content` permanently removes an item that was never published, has
no approval or legal approval, is not one of the three fixed kinds that are never created
from the UI (the landing page, its sections and settings) and is not referenced by a
section draft or a service group's services; a legal page is creatable, so a
never-published legal draft may be deleted. The row and its versions cascade, and its
path or slug is freed.

```sql
create table content_version (
  id uuid primary key default gen_random_uuid(),
  item_id uuid not null references content_item (id) on delete cascade,
  version_number integer not null,
  status version_status not null default 'draft',
  created_by uuid not null references staff (user_id) on delete restrict,
  updated_by uuid references staff (user_id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  submitted_at timestamptz,
  published_at timestamptz,
  published_by uuid references staff (user_id) on delete restrict,

  constraint content_version_number check (version_number > 0),
  constraint content_version_published check (
    (status = 'published') = (published_at is not null)
  ),
  constraint content_version_publisher check (
    (status = 'published') = (published_by is not null)
  ),
  constraint content_version_review check (
    status <> 'in_review' or submitted_at is not null
  ),
  unique (item_id, version_number),
  unique (item_id, id)
);

create unique index content_version_one_open
  on content_version (item_id)
  where status in ('draft', 'in_review');

create index content_version_item_status_idx on content_version (item_id, status);
```

A draft can be edited in place. It becomes `in_review` when an Editor submits it, and
`published` when an Admin publishes. The partial unique index is what makes "one open
version" a database rule rather than a convention. A published version is immutable;
the trigger below refuses later updates and deletes, so deleting the item cascades
nothing away. `delete_content` only ever deletes never-published items.

The version row is an identity and state row. Its content is a typed row keyed by
`version_id`: `content_seo` and `legal_page_version` for a legal page, `content_seo`
for the landing page, `section_version` for a section, `service_version` for a service,
and so on. The version row and its typed row are inserted in the same transaction.
There is no document to validate, so the database checks the field type and
length, and the copy rules that need cross-field or cross-item knowledge stay in
Pydantic and FastAPI.

The API sets `updated_by` on each draft edit; `created_by` stays the author, which is
what the legal approval compares against.

```sql
create or replace function bump_next_version()
returns trigger
language plpgsql
as $$
begin
  update content_item
    set next_version = greatest(next_version, new.version_number + 1)
  where id = new.item_id;
  return null;
end;
$$;

create trigger content_version_bump_next
  after insert on content_version
  for each row execute function bump_next_version();
```

The trigger keeps `next_version` ahead of any version inserted directly, so a
bootstrap or a data migration cannot make `create_draft` reuse a number.

```sql
create table content_publication (
  item_id uuid primary key references content_item (id) on delete cascade,
  version_id uuid not null,
  published_at timestamptz not null default now(),
  published_by uuid not null references staff (user_id) on delete restrict,

  constraint content_publication_version_fk
    foreign key (item_id, version_id)
    references content_version (item_id, id)
    on delete restrict
);
```

The publication pointer is the only thing that makes content live. Unpublishing
deletes this row and creates a draft copy from the last published version in the same
transaction; the published versions remain for history. A page's revision on the wire is
the pointed version's `version_number`.

The archive guard makes the pointer rule structural. `archive_content` unpublishes
first, so the guard passes on the normal path, which includes a landing page whose live
sections outlive its own pointer, and a direct archive that left the item live is refused.
The condition is read without locking the section rows, so a concurrent section publish
can still trip the guard; the archive rolls back cleanly and is safe to retry.

```sql
create or replace function prevent_archived_with_publication()
returns trigger
language plpgsql
as $$
begin
  if old.archived_at is null
     and new.archived_at is not null
     and exists (
       select 1 from content_publication where item_id = new.id
     ) then
    raise exception 'archive removes the publication pointer first';
  end if;
  return new;
end;
$$;

create trigger content_item_archive_guard
  before update on content_item
  for each row execute function prevent_archived_with_publication();
```

## Page sections

### Page SEO

Every version that renders as a page carries one `content_seo` row: the landing page,
each legal page, and in Phase 2 each service, project and blog post. One table, so a new
page kind does not repeat four columns and its trigger.

```sql
create table content_seo (
  version_id uuid primary key references content_version (id) on delete cascade,
  seo_title text,
  seo_description text,
  seo_noindex boolean not null default false,
  og_image_id uuid references media (id) on delete restrict,

  constraint content_seo_title_length check (
    seo_title is null or char_length(seo_title) between 1 and 60
  ),
  constraint content_seo_description_length check (
    seo_description is null or char_length(seo_description) between 1 and 160
  )
);
```

A draft may hold a null title or description while the editor works; the publish gate
refuses a page without both. `og_image_id` is the page's social card, 0–1 by column.
Uniqueness across live pages (NF-5) is a FastAPI check, because a unique index cannot
span a view; a duplicate title is caught before the publish call. A kind that does not
render a page, such as a service group or a section, has no `content_seo` row.

### Section items

A landing page is made of ten section records. Their keys and order come from PRD §5:
hero, proof, services, not sure, work, process, about, testimonials, FAQs and contact.
The page itself has no copy; it owns SEO and the OG image.

PRD §5 lists twelve sections including the header and footer. The header and footer
are site-frame settings, not `page_section` records: the header is the settings
logo slot, the CTA and the five section `nav_label` values; the footer is the
`settings_version` footer links (including Cookies), legal identity, legal routes
and the Cookies page (decision 52; no optional cookies, so no preferences control).
Every one of the twelve sections' editable data therefore has a home, and
that is how LP-2's "every section editable" is satisfied without duplicating content:

| PRD §5 section | Editable home |
|---|---|
| Header | `settings_version` logo, CTA and the five `section_version.nav_label` values |
| Hero | `page_section` + `section_version` |
| Proof figures | `page_section` + `proof_figure` references |
| Services | `page_section` + `service_group` references |
| Not sure | `page_section` + `section_version` CTA |
| Featured work | `page_section` + `project` references |
| How we work | `page_section` + `process_stage`/`process_assurance` |
| About | `page_section` + `section_paragraph`/image |
| Testimonials | `page_section` + `testimonial` references |
| FAQs | `page_section` + `faq_item` |
| Contact | `page_section` + `contact_next_step`/privacy fields + settings |
| Footer | `settings_version` footer links (including Cookies), legal identity, legal routes and the Cookies page (decision 52; no optional cookies, so no preferences control) |

PRD NV-3's "cookie preferences" link is resolved by decision 52: the site sets no
optional cookies, so the footer links the Cookies information page and there is no
preference control to render. If the PRD must be read literally, decision 52 must be
reopened; this document follows the decision.

```sql
create table page_section (
  item_id uuid primary key,
  kind content_kind not null default 'page_section',
  page_id uuid not null,
  page_kind content_kind not null default 'landing_page',
  section_key page_section_key not null,
  sort_order integer not null,

  constraint page_section_kind check (kind = 'page_section'),
  constraint page_section_page_kind check (page_kind = 'landing_page'),
  constraint page_section_item_fk
    foreign key (item_id, kind)
    references content_item (id, kind)
    on delete cascade,
  constraint page_section_page_fk
    foreign key (page_id, page_kind)
    references content_item (id, kind)
    on delete cascade,
  constraint page_section_key_unique unique (page_id, section_key),
  constraint page_section_order_unique unique (page_id, sort_order),
  constraint page_section_sort check (sort_order >= 0)
);

create index page_section_page_idx on page_section (page_id, sort_order);

create or replace function assert_page_section_row()
returns trigger
language plpgsql
as $$
begin
  if new.kind = 'page_section' and not exists (
    select 1 from page_section where item_id = new.id
  ) then
    raise exception 'page section item % needs a page_section row', new.id;
  end if;
  return null;
end;
$$;

create constraint trigger content_item_page_section_row
  after insert on content_item
  deferrable initially deferred
  for each row execute function assert_page_section_row();
```

The API inserts the item and its `page_section` row in one transaction; the deferred
constraint trigger fails the commit if it forgets the row. `section_key` is an enum, so
a typo cannot invent a section. The unique pair on `(page_id, sort_order)` means two
sections cannot trade the same place.

`page_section.sort_order` holds the PRD's section `order`. PRD §5 fixes the order at
launch, and §8's permissions table gives page sections no reorder control, so the admin
writes the seeded values and exposes no drag handle; the field is a column, not an
accident of array position, and a later approval can make it editable without a
migration.

### Section copy

One row per section version. The columns a section uses are fixed by its key; the
checks below refuse a hero row carrying a testimonial quote, or an about row carrying a
CTA. A draft may leave any copy null; the publish gates and Pydantic require it.

```sql
create table section_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  section_key page_section_key not null,
  heading text,
  intro text,
  body text,
  nav_label text,
  eyebrow text,
  primary_label text,
  primary_href text,
  secondary_label text,
  secondary_href text,
  cta_label text,
  cta_href text,
  privacy_text text,
  privacy_link_label text,
  image_id uuid references media (id) on delete restrict,

  constraint section_version_heading_length check (
    heading is null or char_length(heading) <= 70
  ),
  constraint section_version_heading_key check (
    section_key <> 'proof' or heading is null
  ),
  constraint section_version_intro_key check (
    section_key in ('services', 'work', 'process') or intro is null
  ),
  constraint section_version_body_key check (
    section_key in ('hero', 'not-sure', 'contact') or body is null
  ),
  constraint section_version_nav_key check (
    section_key in ('services', 'work', 'process', 'about', 'contact')
    or nav_label is null
  ),
  constraint section_version_eyebrow_key check (
    section_key = 'hero' or eyebrow is null
  ),
  constraint section_version_hero_ctas check (
    section_key = 'hero'
    or (primary_label is null and primary_href is null
        and secondary_label is null and secondary_href is null)
  ),
  constraint section_version_cta_key check (
    section_key = 'not-sure'
    or (cta_label is null and cta_href is null)
  ),
  constraint section_version_privacy_key check (
    section_key = 'contact'
    or (privacy_text is null and privacy_link_label is null)
  ),
  constraint section_version_image_key check (
    section_key = 'about' or image_id is null
  ),
  constraint section_version_cta_label_length check (
    (primary_label is null or char_length(primary_label) <= 30)
    and (secondary_label is null or char_length(secondary_label) <= 30)
    and (cta_label is null or char_length(cta_label) <= 30)
  ),
  constraint section_version_href_length check (
    (primary_href is null or char_length(primary_href) <= 200)
    and (secondary_href is null or char_length(secondary_href) <= 200)
    and (cta_href is null or char_length(cta_href) <= 200)
  )
);
```

The key edges:

| Section          | Columns it uses                                                        |
| ---------------- | ---------------------------------------------------------------------- |
| `hero`         | heading, eyebrow, body, both CTA label/href pairs                      |
| `proof`        | none; the row comes from the references                                |
| `services`     | heading, intro, nav_label                                              |
| `not-sure`     | heading, body, CTA label/href                                          |
| `work`         | heading, intro, nav_label                                              |
| `process`      | heading, intro, nav_label, plus stages and assurances                  |
| `about`        | heading, its paragraph rows, nav_label, image                          |
| `testimonials` | heading                                                                |
| `faqs`         | heading, plus the question rows                                        |
| `contact`      | heading, body, nav_label, privacy text and link label, plus next steps |

### Lists inside a section

```sql
create table section_paragraph (
  version_id uuid not null references content_version (id) on delete cascade,
  sort_order integer not null,
  text text not null,

  primary key (version_id, sort_order),
  constraint section_paragraph_sort check (sort_order between 0 and 3),
  constraint section_paragraph_length check (
    char_length(text) between 1 and 600
  )
);

create table process_stage (
  version_id uuid not null references content_version (id) on delete cascade,
  sort_order integer not null,
  title text,
  body text,

  primary key (version_id, sort_order),
  constraint process_stage_sort check (sort_order between 0 and 3),
  constraint process_stage_title_length check (
    title is null or char_length(title) <= 40
  ),
  constraint process_stage_body_length check (
    body is null or char_length(body) <= 160
  )
);

create table process_assurance (
  version_id uuid not null references content_version (id) on delete cascade,
  sort_order integer not null,
  title text,
  body text,

  primary key (version_id, sort_order),
  constraint process_assurance_sort check (sort_order between 0 and 2),
  constraint process_assurance_title_length check (
    title is null or char_length(title) <= 40
  ),
  constraint process_assurance_body_length check (
    body is null or char_length(body) <= 160
  )
);

create table faq_item (
  version_id uuid not null references content_version (id) on delete cascade,
  sort_order integer not null,
  question text,
  answer text,
  status faq_status not null default 'published',

  primary key (version_id, sort_order),
  constraint faq_question_length check (
    question is null or char_length(question) <= 120
  ),
  constraint faq_answer_length check (
    answer is null or char_length(answer) <= 600
  )
);

create table contact_next_step (
  version_id uuid not null references content_version (id) on delete cascade,
  sort_order integer not null,
  title text,
  body text,

  primary key (version_id, sort_order),
  constraint contact_next_step_sort check (sort_order between 0 and 3),
  constraint contact_next_step_title_length check (
    title is null or char_length(title) <= 40
  ),
  constraint contact_next_step_body_length check (
    body is null or char_length(body) <= 160
  )
);

create or replace function assert_section_child()
returns trigger
language plpgsql
as $$
declare
  v_key page_section_key;
begin
  select section_key into v_key
  from section_version
  where version_id = new.version_id;

  if v_key is null or v_key::text <> tg_argv[0] then
    raise exception 'row belongs to section %, not %', v_key, tg_argv[0];
  end if;

  return new;
end;
$$;

create trigger section_paragraph_section
  before insert or update on section_paragraph
  for each row execute function assert_section_child('about');

create trigger process_stage_section
  before insert or update on process_stage
  for each row execute function assert_section_child('process');

create trigger process_assurance_section
  before insert or update on process_assurance
  for each row execute function assert_section_child('process');

create trigger faq_item_section
  before insert or update on faq_item
  for each row execute function assert_section_child('faqs');

create trigger contact_next_step_section
  before insert or update on contact_next_step
  for each row execute function assert_section_child('contact');
```

A paragraph belongs only to the About section, a stage or assurance only to the process
section, an FAQ only to the FAQ section, and a next step only to the contact section.
The trigger reads the version's key, so a row cannot be attached to the wrong section.

### Section references

```sql
create table section_version_item (
  version_id uuid not null references content_version (id) on delete cascade,
  item_id uuid not null,
  item_kind content_kind not null,
  sort_order integer,

  constraint section_version_item_pk primary key (version_id, item_id),
  constraint section_version_item_kind check (
    item_kind in ('service_group', 'project', 'proof_figure', 'testimonial')
  ),
  constraint section_version_item_sort check (sort_order is null or sort_order >= 0),
  constraint section_version_item_order check (
    (item_kind = 'project') = (sort_order is null)
  ),
  constraint section_version_item_fk
    foreign key (item_id, item_kind)
    references content_item (id, kind)
    on delete restrict
);

create unique index section_version_item_order_key
  on section_version_item (version_id, sort_order)
  where sort_order is not null;

create index section_version_item_lookup_idx on section_version_item (item_id);
```

A section version references records by item id, not by version id. That is what lets a
project publish without a page republish: the public read takes the record's current
live version. The section version owns the selection, and the selection is copied into
each new draft.

The four record-backed sections are services, work, proof and testimonials; the other
six sections have no references. Services references are service groups and carry a
render order. Work references are projects and carry no order, because a project's
order is `project.live_sort_order`; storing it twice would let the two disagree. Proof
and testimonial references carry the order shown in their rows, because the PRD gives
those entities no order field of their own.

## Records

### Services

```sql
create table service_group (
  item_id uuid primary key,
  kind content_kind not null default 'service_group',

  constraint service_group_kind check (kind = 'service_group'),
  constraint service_group_item_fk
    foreign key (item_id, kind)
    references content_item (id, kind)
    on delete cascade
);

create table service_group_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  title text,

  constraint service_group_title_length check (
    title is null or char_length(title) between 1 and 40
  )
);

create table service_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  group_item_id uuid references service_group (item_id) on delete restrict,
  title text,
  summary text,
  long_description text,
  sort_order integer not null default 0,

  constraint service_version_title_length check (
    title is null or char_length(title) between 1 and 60
  ),
  constraint service_version_title_reserved check (
    title is null or lower(title) <> '__other__'
  ),
  constraint service_version_sort check (sort_order >= 0)
);

create index service_version_group_idx on service_version (group_item_id, sort_order);

create table service (
  item_id uuid primary key,
  kind content_kind not null default 'service',
  group_item_id uuid not null references service_group (item_id) on delete restrict,
  live_title text not null,
  live_sort_order integer not null default 0,
  published_at timestamptz not null default now(),

  constraint service_kind check (kind = 'service'),
  constraint service_item_fk
    foreign key (item_id, kind)
    references content_item (id, kind)
    on delete cascade,
  constraint service_title_length check (char_length(live_title) between 1 and 60),
  constraint service_title_reserved check (lower(live_title) <> '__other__'),
  constraint service_sort check (live_sort_order >= 0)
);

create unique index service_live_title_key on service (lower(live_title));
create index service_group_idx on service (group_item_id, live_sort_order);

create or replace function ensure_service_group_row()
returns trigger
language plpgsql
as $$
begin
  if new.kind = 'service_group' then
    insert into service_group (item_id) values (new.id)
    on conflict (item_id) do nothing;
  end if;
  return new;
end;
$$;

create trigger content_item_service_group
  after insert on content_item
  for each row execute function ensure_service_group_row();
```

`content_item` of kind `service_group` gets its typed row from an after-insert trigger,
so the admin API creates one record, not two. A service group that exists only as a
`content_item` cannot be given services by mistake.

`service` is a projection of the live service version, not a second draft. The
publication trigger writes it from the winning version's typed row and removes it on
unpublish. That gives the enquiry chips one unique title per live service. The check on
`live_title` also refuses the reserved value `__other__`, which the enquiry uses for the
"Something else" chip; the API rejects it at save, so the constraint is a second guard
rather than the user-facing error.

A service cannot be published under an unpublished group; the trigger that fills the
`service` table refuses it. A group with live services cannot be unpublished until they
are unpublished, so the page and the form cannot disagree about which services exist.
The API also requires two to six live services in each group before the landing page
publishes; SQL checks the group count and the service title, not the per-group count.

### Projects

```sql
create table project_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  title text,
  client text,
  client_need text,
  built text,
  result text,
  category text,
  sort_order integer not null default 0,

  constraint project_title_length check (
    title is null or char_length(title) <= 60
  ),
  constraint project_client_length check (
    client is null or char_length(client) <= 80
  ),
  constraint project_need_length check (
    client_need is null or char_length(client_need) <= 280
  ),
  constraint project_built_length check (
    built is null or char_length(built) <= 280
  ),
  constraint project_result_length check (
    result is null or char_length(result) <= 280
  ),
  constraint project_sort check (sort_order >= 0)
);

create table project_technology (
  version_id uuid not null references project_version (version_id) on delete cascade,
  sort_order integer not null,
  name text not null,

  constraint project_technology_pk primary key (version_id, sort_order),
  constraint project_technology_sort check (sort_order between 0 and 7),
  constraint project_technology_name_length check (
    char_length(name) between 1 and 40
  )
);

create table project_image (
  version_id uuid not null references project_version (version_id) on delete cascade,
  sort_order integer not null,
  media_id uuid not null references media (id) on delete restrict,

  constraint project_image_pk primary key (version_id, sort_order),
  constraint project_image_media_unique unique (version_id, media_id),
  constraint project_image_sort check (sort_order between 0 and 2)
);

create or replace function assert_project_image_count()
returns trigger
language plpgsql
as $$
declare
  n integer;
begin
  select count(*) into n
  from project_image
  where version_id = new.version_id;

  if n > 3 then
    raise exception 'a project has at most three images';
  end if;

  return new;
end;
$$;

create trigger project_image_count
  before insert on project_image
  for each row execute function assert_project_image_count();
```

`sort_order` is 0–2 and unique per version, so at most three images. The publish gate
requires a `screenshots` scope when any image is attached.

```sql
create table project (
  item_id uuid primary key,
  kind content_kind not null default 'project',
  live_sort_order integer not null default 0,
  published_at timestamptz not null default now(),

  constraint project_kind check (kind = 'project'),
  constraint project_item_fk
    foreign key (item_id, kind)
    references content_item (id, kind)
    on delete cascade,
  constraint project_sort check (live_sort_order >= 0)
);

create index project_sort_idx on project (live_sort_order);

create or replace function ensure_project_row()
returns trigger
language plpgsql
as $$
begin
  if new.kind = 'project' then
    insert into project (item_id) values (new.id)
    on conflict (item_id) do nothing;
  end if;
  return new;
end;
$$;

create trigger content_item_project
  after insert on content_item
  for each row execute function ensure_project_row();
```

`project.live_sort_order` is the PRD's project `order`, projected from the published
version's `sort_order`. A draft project order can differ from the live one; the Featured
work section reads the live projection, so publishing the project changes its place on
the page without republishing the page. The typed row is created with the item and
starts at 0.

### Proof items

The PRD has one proof entity with a `type`. Here each type is its own content kind and
its own version table, so a figure cannot carry a quote and a logo cannot carry a
number. `content_item.kind` is the type.

```sql
create table proof_figure_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  label text,
  value text,
  prefix text,
  suffix text,

  constraint proof_figure_label_length check (
    label is null or char_length(label) <= 40
  ),
  constraint proof_figure_value_length check (
    value is null or char_length(value) <= 12
  ),
  constraint proof_figure_prefix_length check (
    prefix is null or char_length(prefix) <= 4
  ),
  constraint proof_figure_suffix_length check (
    suffix is null or char_length(suffix) <= 4
  )
);

create table testimonial_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  quote text,
  name text,
  role text,
  company text,

  constraint testimonial_quote_length check (
    quote is null or char_length(quote) <= 280
  ),
  constraint testimonial_name_length check (
    name is null or char_length(name) <= 60
  ),
  constraint testimonial_role_length check (
    role is null or char_length(role) <= 80
  ),
  constraint testimonial_company_length check (
    company is null or char_length(company) <= 80
  ),
  constraint testimonial_attribution check (
    name is not null or (role is null and company is null)
  )
);

create table client_logo_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  client_name text,
  image_id uuid references media (id) on delete restrict
);
```

Testimonial attribution is all-or-nothing: a null `name` means the client withheld it,
and `role` and `company` are then null too. When `name` is present, `role` and `company`
may still be null individually. The version's approval always carries the `quote` scope
and carries `client_name` only when the name may be shown.

A client logo carries its attribution; the image is `image_id`, 0–1 by column. The kind
exists so D-9 has a home and every proof item can carry an approval; the page has no
render slot until D-9 approves showing client marks.

### Legal pages

```sql
create table legal_page_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  label text,
  title text,
  effective_on date,

  constraint legal_page_label_length check (
    label is null or char_length(label) between 1 and 40
  ),
  constraint legal_page_title_length check (
    title is null or char_length(title) between 1 and 70
  )
);

create table legal_block (
  version_id uuid not null references content_version (id) on delete cascade,
  sort_order integer not null,
  kind legal_block_kind not null,
  text text,

  constraint legal_block_pk primary key (version_id, sort_order),
  constraint legal_block_sort check (sort_order >= 0),
  constraint legal_block_shape check (
    (kind = 'h2' and text is not null and char_length(text) between 1 and 60)
    or (kind = 'p' and text is not null and char_length(text) between 1 and 2000)
    or (kind in ('ul', 'table') and text is null)
  )
);

create table legal_block_item (
  version_id uuid not null,
  block_sort_order integer not null,
  sort_order integer not null,
  text text not null,

  constraint legal_block_item_pk
    primary key (version_id, block_sort_order, sort_order),
  constraint legal_block_item_sort check (sort_order between 0 and 11),
  constraint legal_block_item_length check (
    char_length(text) between 1 and 200
  ),
  constraint legal_block_item_fk
    foreign key (version_id, block_sort_order)
    references legal_block (version_id, sort_order)
    on delete cascade
);

create table legal_block_column (
  version_id uuid not null,
  block_sort_order integer not null,
  sort_order integer not null,
  label text not null,

  constraint legal_block_column_pk
    primary key (version_id, block_sort_order, sort_order),
  constraint legal_block_column_sort check (sort_order >= 0),
  constraint legal_block_column_label check (char_length(label) >= 1),
  constraint legal_block_column_fk
    foreign key (version_id, block_sort_order)
    references legal_block (version_id, sort_order)
    on delete cascade
);

create table legal_block_row (
  version_id uuid not null,
  block_sort_order integer not null,
  sort_order integer not null,

  constraint legal_block_row_pk
    primary key (version_id, block_sort_order, sort_order),
  constraint legal_block_row_sort check (sort_order between 0 and 29),
  constraint legal_block_row_fk
    foreign key (version_id, block_sort_order)
    references legal_block (version_id, sort_order)
    on delete cascade
);

create table legal_block_cell (
  version_id uuid not null,
  block_sort_order integer not null,
  row_sort_order integer not null,
  column_sort_order integer not null,
  text text not null,

  constraint legal_block_cell_pk primary key (
    version_id, block_sort_order, row_sort_order, column_sort_order
  ),
  constraint legal_block_cell_fk
    foreign key (version_id, block_sort_order, row_sort_order)
    references legal_block_row (version_id, block_sort_order, sort_order)
    on delete cascade
);

create or replace function assert_legal_block_child()
returns trigger
language plpgsql
as $$
declare
  v_kind legal_block_kind;
begin
  select kind into v_kind
  from legal_block
  where version_id = new.version_id
    and sort_order = new.block_sort_order;

  if v_kind is null then
    raise exception 'legal block % not found', new.block_sort_order;
  end if;
  if v_kind <> tg_argv[0]::legal_block_kind then
    raise exception 'this row needs a % block, found %', tg_argv[0], v_kind;
  end if;

  return new;
end;
$$;

create trigger legal_block_item_assert
  before insert or update on legal_block_item
  for each row execute function assert_legal_block_child('ul');

create trigger legal_block_column_assert
  before insert or update on legal_block_column
  for each row execute function assert_legal_block_child('table');

create trigger legal_block_row_assert
  before insert or update on legal_block_row
  for each row execute function assert_legal_block_child('table');

create trigger legal_block_cell_assert
  before insert or update on legal_block_cell
  for each row execute function assert_legal_block_child('table');
```

A block keeps only its kind and its own text; its list items, column labels, rows and
cells are rows keyed by the block. A list block cannot hold table rows and a table
block cannot hold list items, which the trigger checks. The shape rules that span rows
— a list with no items, a table with no columns, a row with the wrong number of cells —
are publish gates, because a draft is allowed to be half-built.

A legal page stores its footer label, title, blocks and effective date. `effective_on`
is the PRD's effective date field. A null means "the date it was published"; the API
resolves it to the publication instant's date in `Europe/London`. A date is stored when
legal wants the page to say it takes effect on a named day, which can be later than the
publish date.

Four block kinds. No HTML and no Markdown from the CMS, so the output cannot carry a
script, a broken link or a heading level that breaks the page outline. The `label` is
the footer's link text and is returned by `/routes`; the page itself renders `title` as
its `h1`, so the two can differ. It lives on the page version rather than on
`content_item` because it is content, versioned with the page.

### Site settings

```sql
create table settings_version (
  version_id uuid primary key references content_version (id) on delete cascade,
  legal_name text,
  trading_name text,
  country text,
  contact_email citext,
  contact_phone text,
  contact_phone_hours text,
  hours_summary text,
  hours_timezone text not null default 'Europe/London',
  footer_note text,
  seo_title_suffix text,
  seo_description text,
  seo_og_image_id uuid references media (id) on delete restrict,
  cta_label text,
  cta_href text,
  site_logo_id uuid references media (id) on delete restrict,
  nepal_site_url text,
  booking_url text,
  booking_label text,
  uk_establishment boolean not null default false,
  home_registry text,
  registration_number text,
  head_office_location text,
  legal_form text,
  limited_liability text,
  insolvency_information text,
  vat_number text,

  constraint settings_email_length check (
    contact_email is null or char_length(contact_email) <= 254
  ),
  constraint settings_phone_hours check (
    contact_phone is null or contact_phone_hours is not null
  ),
  constraint settings_footer_note_length check (
    footer_note is null or char_length(footer_note) <= 160
  ),
  constraint settings_suffix_length check (
    seo_title_suffix is null or char_length(seo_title_suffix) <= 40
  ),
  constraint settings_description_length check (
    seo_description is null or char_length(seo_description) <= 160
  ),
  constraint settings_cta_label_length check (
    cta_label is null or char_length(cta_label) <= 30
  ),
  constraint settings_cta_href_length check (
    cta_href is null or char_length(cta_href) <= 200
  ),
  constraint settings_booking_label_length check (
    booking_label is null or char_length(booking_label) <= 30
  ),
  constraint settings_booking_url_length check (
    booking_url is null or char_length(booking_url) <= 200
  ),
  constraint settings_nepal_url_length check (
    nepal_site_url is null or char_length(nepal_site_url) <= 200
  )
);

create table settings_address_line (
  version_id uuid not null references settings_version (version_id) on delete cascade,
  sort_order integer not null,
  line text not null,

  constraint settings_address_line_pk primary key (version_id, sort_order),
  constraint settings_address_line_sort check (sort_order between 0 and 3),
  constraint settings_address_line_text check (char_length(line) >= 1)
);

create table settings_location (
  version_id uuid not null references settings_version (version_id) on delete cascade,
  sort_order integer not null,
  name text,
  country text,
  phone text,
  phone_hours text,

  constraint settings_location_pk primary key (version_id, sort_order),
  constraint settings_location_sort check (sort_order >= 0),
  constraint settings_location_phone_hours check (
    phone is null or phone_hours is not null
  )
);

create table settings_location_address_line (
  version_id uuid not null,
  location_sort_order integer not null,
  sort_order integer not null,
  line text not null,

  constraint settings_location_address_line_pk
    primary key (version_id, location_sort_order, sort_order),
  constraint settings_location_address_line_sort check (
    sort_order between 0 and 3
  ),
  constraint settings_location_address_line_text check (char_length(line) >= 1),
  constraint settings_location_address_line_fk
    foreign key (version_id, location_sort_order)
    references settings_location (version_id, sort_order)
    on delete cascade
);

create table settings_footer_link (
  version_id uuid not null references settings_version (version_id) on delete cascade,
  sort_order integer not null,
  label text,
  href text,

  constraint settings_footer_link_pk primary key (version_id, sort_order),
  constraint settings_footer_link_sort check (sort_order >= 0),
  constraint settings_footer_link_label_length check (
    label is null or char_length(label) <= 40
  ),
  constraint settings_footer_link_href_length check (
    href is null or char_length(href) <= 200
  )
);

create table settings_working_hour (
  version_id uuid not null references settings_version (version_id) on delete cascade,
  day_of_week integer not null,
  sort_order integer not null default 0,
  opens_at time,
  closes_at time,
  is_closed boolean not null default false,

  constraint settings_working_hour_pk primary key (version_id, day_of_week, sort_order),
  constraint settings_working_hour_day check (day_of_week between 1 and 7),
  constraint settings_working_hour_sort check (sort_order >= 0),
  constraint settings_working_hour_shape check (
    (is_closed and opens_at is null and closes_at is null)
    or (not is_closed
        and opens_at is not null
        and closes_at is not null
        and closes_at > opens_at)
  )
);

create index settings_working_hour_lookup_idx on settings_working_hour (version_id, day_of_week);
```

One email serves the whole site. The form, the footer and every location block point
at it, because the enquiry inbox does not vary by location and a visitor should never
have to guess which address is read.

`contact_phone` is the site's own contact line. It is null unless the line is answered,
and it requires `contact_phone_hours` whenever it is set, because a number listed
outside the hours it is answered is worse than no number. It lives on the settings
version, not on a location, so a staffed UK line needs no UK street address: the PRD
allows a contact line without a UK office, and the label is component copy. The number
is rendered in the Contact section; the footer's legal identity still comes from
`legal_name` and `settings_address_line`.

`settings_address_line` is the legal identity's geographic address, two to four lines;
`settings_location_address_line` does the same for a real place, and
`settings_location` holds only real places. The line count is a publish gate, so a
half-typed address stays a draft. `footer_links` is the PRD's footer links field: the
ordered site links, seeded with the five section links. Legal links are appended from
`/routes` rather than stored here, because a legal page may appear or disappear with
its approval and a static list would drift out of step. `seo_defaults` is the PRD's SEO
defaults field: `seo_description` and `seo_og_image_id` fill a page that omits them,
and `seo_title_suffix` is appended to a page title that does not already end with it. A
page's own values always win; every Phase 1 page still carries its own unique
`seo_title` for NF-5.

`uk_establishment` marks a branch registered with Companies House as a UK
establishment (PRD §12, D-7 open). When it is true, the publish gate requires the
regulation 63 details — `country`, `home_registry`, `registration_number`,
`head_office_location`, `legal_form`, `limited_liability` and
`insolvency_information` — and the footer, Contact section, privacy notice and
terms render them from settings, so the four cannot disagree. When it is false
they stay null and unrendered. `vat_number` is null unless the company is
VAT-registered; a null VAT number means the VAT line is absent, never invented
(PRD §12). No real values are seeded; D-7's answer fills them. The identity gate is
null-only by design: FastAPI/Pydantic must reject empty or whitespace-only values,
so no blank-string check is added here.

`nepal_site_url` is the NF-8 hreflang target, nullable until the Nepal URL is
confirmed. The hreflang locale codes also need confirmation and are not guessed
here — neither `en-NP` nor `ne-NP` is stored; `nepal_site_url` stays the only
hreflang field. `booking_url` and `booking_label` are a placeholder that D-12 has
not approved: D-12 was answered on 26 November with no booking link (decision 46
in `CONTRACT.md`), so the not-approved path applies and they stay unpublished — no
publish gate reads them, no seeded value exists, and `published_settings` does not
expose them. The link would open in a new tab; there is no embed. The budget field
is not added (decision 46). EN-10 is a Should left undelivered by decision 46, not an
open decision. None of the three new
URL/label columns carries a format check: the values for D-7, D-12 and the hreflang
target are unconfirmed, so the schema checks length only.

`site_logo_id` is the LP-2 header-logo slot: 0–1 by column, a site image like any
other (staged privately, promoted at publish, covered by `version_media` and the
image promotion gate). A null logo renders the repository asset, so the brand mark
stays DS-1's existing logo either way; size and placement stay component code.
`hours_summary` stays the display string the contract's `contact.hours` needs; the
`settings_working_hour` rows are additive detail for future validation or derived
rendering, and an empty table is valid, so no publish gate counts them (EN-9's
phone rule stays on the `contact_phone_hours` text). Footer details (legal
identity and address), `settings_footer_link` and the Enquire CTA stay editable as
before — the PRD names no other footer text field, so none is added
(`footer_note` is the one line the PRD's footer allows).

## Approvals

```sql
create table legal_approval (
  version_id uuid primary key references content_version (id) on delete cascade,
  author_id uuid not null references staff (user_id) on delete restrict,
  approver_id uuid not null references staff (user_id) on delete restrict,
  approved_at timestamptz not null default now(),

  constraint legal_approval_distinct check (author_id <> approver_id)
);
```

The author is the version's `created_by`, checked by trigger. The approver must be an
active Admin and must differ from the author. A legal page cannot publish without this
row. Editing the page creates a new version, so the new version needs its own approval.

```sql
create table approval (
  id uuid primary key default gen_random_uuid(),
  version_id uuid not null references content_version (id) on delete cascade,
  subject_kind content_kind not null,
  scopes approval_scope[] not null,
  approved_by_name text not null,
  approved_by_email citext,
  approved_on date not null,
  expires_on date,
  evidence_media_id uuid references media (id) on delete restrict,
  recorded_by uuid not null references staff (user_id) on delete restrict,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  revoked_by uuid references staff (user_id) on delete restrict,
  revocation_note text,

  constraint approval_subject check (
    subject_kind in ('project', 'proof_figure', 'testimonial', 'client_logo')
  ),
  constraint approval_scopes check (cardinality(scopes) between 1 and 6),
  constraint approval_name check (char_length(approved_by_name) between 1 and 120),
  constraint approval_dates check (
    expires_on is null or expires_on >= approved_on
  ),
  constraint approval_revocation check (
    revoked_at is null or revoked_by is not null
  ),
  constraint approval_note check (
    revocation_note is null or char_length(revocation_note) <= 500
  )
);

create index approval_version_idx on approval (version_id);
create index approval_expiry_idx
  on approval (expires_on)
  where revoked_at is null and expires_on is not null;
```

More than one approval may exist for a version; the publish gate needs at least one
live approval covering what the version claims. That avoids a partial unique index
that would block a replacement after an expiry, and leaves room for a second
permission (for example naming a client and showing screenshots separately). The API
checks field coverage; the trigger checks the subject kind, the scopes and the
evidence bucket.

## Enquiries

```sql
create table enquiry (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email citext not null,
  company text,
  service_title text,
  message text not null,
  source_path text not null,
  consent_notice_version text not null,
  status enquiry_status not null default 'new',
  ip_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  first_replied_at timestamptz,
  closed_at timestamptz,

  constraint enquiry_name check (char_length(name) between 1 and 100),
  constraint enquiry_email check (char_length(email) <= 254),
  constraint enquiry_company check (
    company is null or char_length(company) <= 120
  ),
  constraint enquiry_service check (
    service_title is null or char_length(service_title) between 1 and 60
  ),
  constraint enquiry_message check (char_length(message) between 1 and 2000),
  constraint enquiry_source check (
    char_length(source_path) between 1 and 200
    and source_path like '/%'
    and position('?' in source_path) = 0
  ),
  constraint enquiry_consent check (
    consent_notice_version ~ '^landing-r[0-9]+\+privacy-r[0-9]+$'
  ),
  constraint enquiry_ip_hash check (ip_hash is null or ip_hash ~ '^[0-9a-f]{64}$'),
  constraint enquiry_first_reply check (
    first_replied_at is null or first_replied_at >= created_at
  ),
  constraint enquiry_closed check (
    closed_at is null or closed_at >= created_at
  )
);

create index enquiry_created_idx on enquiry (created_at desc);
create index enquiry_status_idx on enquiry (status, created_at desc);
create index enquiry_email_idx on enquiry (email);
```

The service title is a snapshot, not a foreign key: a service can be renamed or
unpublished after submission, and the enquiry must keep what the visitor chose. At
submit, FastAPI accepts a title that any published `service_version` has used, not only
a live one, so a title unpublished after the page rendered is still valid and an
invented string is not. The reserved value `__other__` is accepted for the "Something
else" chip and stored as null, so no fake service row exists. `ip_hash` is an HMAC of
the address with a server secret; the raw address is never stored or logged. It is
nullable because a job nulls it after 30 days. The consent version reproduces the
landing page and privacy notice revisions the visitor saw.

```sql
create table enquiry_note (
  id uuid primary key default gen_random_uuid(),
  enquiry_id uuid not null references enquiry (id) on delete cascade,
  author_id uuid not null references staff (user_id) on delete restrict,
  body text not null,
  created_at timestamptz not null default now(),

  constraint enquiry_note_body check (char_length(body) between 1 and 4000)
);

create index enquiry_note_enquiry_idx on enquiry_note (enquiry_id, created_at);
```

```sql
create table rate_limit_event (
  id bigint generated always as identity primary key,
  ip_hash text,
  email_hash text,
  created_at timestamptz not null default now(),

  constraint rate_limit_keys check (ip_hash is not null or email_hash is not null),
  constraint rate_limit_ip check (ip_hash is null or ip_hash ~ '^[0-9a-f]{64}$'),
  constraint rate_limit_email check (
    email_hash is null or email_hash ~ '^[0-9a-f]{64}$'
  )
);

create index rate_limit_ip_idx
  on rate_limit_event (ip_hash, created_at desc)
  where ip_hash is not null;

create index rate_limit_email_idx
  on rate_limit_event (email_hash, created_at desc)
  where email_hash is not null;
```

A row is written for every attempt, including honeypot hits, rejected Turnstile tokens
and validation failures, so the limit cannot be reset by a restart or bypassed by
sending invalid data. The event is written before the checks and committed on its own;
an accepted enquiry then saves in a second transaction with its outbox rows. The keys
are hashes; the raw IP and the raw email are not kept in this table. The enquiry table
keeps the email because the team must reply to it, and its `ip_hash` is nulled after
30 days. Rate-limit events are deleted after 7 days.

## Delivery

```sql
create table email_outbox (
  id uuid primary key default gen_random_uuid(),
  enquiry_id uuid not null references enquiry (id) on delete cascade,
  kind email_kind not null,
  to_email citext not null,
  reply_to citext not null,
  subject text not null,
  body_text text not null,
  body_html text not null,
  status email_status not null default 'pending',
  attempts integer not null default 0,
  next_attempt_at timestamptz not null default now(),
  last_error text,
  provider_message_id text,
  created_at timestamptz not null default now(),
  sent_at timestamptz,

  constraint email_outbox_subject check (char_length(subject) between 1 and 200),
  constraint email_outbox_text_length check (char_length(body_text) <= 20000),
  constraint email_outbox_html_length check (char_length(body_html) <= 100000),
  constraint email_outbox_attempts check (attempts >= 0),
  constraint email_outbox_sent check (
    (status = 'sent') = (sent_at is not null)
  ),
  constraint email_outbox_error check (
    last_error is null or char_length(last_error) <= 1000
  )
);

create index email_outbox_pending_idx
  on email_outbox (next_attempt_at)
  where status in ('pending', 'failed');
```

Both rows are inserted in the same transaction as the enquiry. The alert body never
contains the message. The confirmation is short: name, service, received-at, the
promise and the site email. `reply_to` is the monitored inbox. A sent row is deleted 30
days after `sent_at`, and a dead row 30 days after it was created; deleting an enquiry
cascades to its outbox rows, so erasure and the 24-month retention remove the email
bodies too.

```sql
create table revalidation (
  id bigint generated always as identity primary key,
  tags text[] not null,
  status revalidation_status not null default 'pending',
  attempts integer not null default 0,
  next_attempt_at timestamptz not null default now(),
  last_error text,
  created_at timestamptz not null default now(),
  completed_at timestamptz,

  constraint revalidation_tags check (cardinality(tags) between 1 and 50),
  constraint revalidation_attempts check (attempts >= 0),
  constraint revalidation_done check (
    (status = 'sent') = (completed_at is not null)
  )
);

create index revalidation_pending_idx
  on revalidation (next_attempt_at)
  where status in ('pending', 'failed');
```

The publish function writes one row per publish. The worker posts the tags to Next and
marks the row sent, or schedules a retry. The audit log records the publish itself;
the revalidation row is the delivery state of the cache purge.

## Audit

```sql
create table audit_log (
  id bigint generated always as identity primary key,
  actor_id uuid references staff (user_id) on delete set null,
  action text not null,
  entity_kind text,
  entity_id text,
  version_id uuid references content_version (id) on delete set null,
  page_id uuid references content_item (id) on delete set null,
  path text,
  revision integer,
  affected_rows integer,
  created_at timestamptz not null default now(),

  constraint audit_action check (char_length(action) between 1 and 80),
  constraint audit_entity_kind check (
    entity_kind is null or char_length(entity_kind) <= 40
  ),
  constraint audit_entity_id check (
    entity_id is null or char_length(entity_id) <= 100
  ),
  constraint audit_path check (
    path is null or path ~ '^/[a-z0-9-]*(/[a-z0-9-]+)*$'
  ),
  constraint audit_revision check (revision is null or revision > 0),
  constraint audit_affected_rows check (
    affected_rows is null or affected_rows >= 0
  )
);

create index audit_log_created_idx on audit_log (created_at desc);
create index audit_log_entity_idx
  on audit_log (entity_kind, entity_id, created_at desc);
create index audit_log_version_idx
  on audit_log (version_id) where version_id is not null;
create index audit_log_page_idx
  on audit_log (page_id) where page_id is not null;
```

### Sign-in events

```sql
create table sign_in_event (
  id bigint generated always as identity primary key,
  staff_id uuid references staff (user_id) on delete set null,
  occurred_at timestamptz not null default now(),
  ip_hash text,
  user_agent_hash text,
  outcome text not null,

  constraint sign_in_outcome check (outcome in ('success', 'failure')),
  constraint sign_in_ip_hash check (ip_hash is null or ip_hash ~ '^[0-9a-f]{64}$'),
  constraint sign_in_ua_hash check (
    user_agent_hash is null or user_agent_hash ~ '^[0-9a-f]{64}$'
  )
);

create index sign_in_event_occurred_idx on sign_in_event (occurred_at desc);
create index sign_in_event_staff_idx on sign_in_event (staff_id, occurred_at desc);
```

One row per sign-in attempt, written by FastAPI — successes and failures, because
AD-10's slow down of repeated failures needs the failures and AD-7 needs the
record. `staff_id` is null when the account does not exist or the address is
unknown; the row survives a staff deletion (`on delete set null`), so the 12-month
history cannot be emptied by removing the account. No password, MFA secret or
token is stored. The `purge_sign_in_events` job deletes rows older than 12 months.
Supabase Auth's own audit log is not this record, because its retention cannot be
verified from this repository and the 12-month record is a PRD §8 obligation (see
the retention table and the open questions).

Every action writes the same five columns and fills only the ones it has: a publish
records `version_id` and `revision`, a section publish adds `page_id`, an unpublish,
archive or delete records the `path`, and a retention run records `affected_rows`. A column
that is not relevant stays null. A new kind of detail is a new column and a migration,
never a free-form bag.

`audit_log` holds who did what to which item and when. It never holds an enquiry
message, a password, a token or an approval evidence file. Sign-ins are not in this
table either: they are rows in `sign_in_event`, which keeps the address and agent
hashes an audit row must not carry and purges them after 12 months. Role changes,
publishes, unpublishes, deletions, legal approvals and approval revocations are
written by the API in the same transaction as the action.

The detail columns are operational, not content: the PRD's audit fields are `actor_id`,
`action`, `entity_kind`, `entity_id` and `created_at`, and no content entity stores its
copy here. A column the action does not use stays null, so a `publish` row carries a
`version_id` and an `archive` row carries a `path`. Adding a detail means adding a
column in a migration, which keeps every audit query typed and indexable; it never
means adding a document.

## Functions and triggers

### Timestamps and the last Admin

```sql
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger staff_set_updated_at
  before update on staff
  for each row execute function set_updated_at();

create trigger content_version_set_updated_at
  before update on content_version
  for each row execute function set_updated_at();

create trigger enquiry_set_updated_at
  before update on enquiry
  for each row execute function set_updated_at();

create or replace function prevent_media_mutation()
returns trigger
language plpgsql
as $$
begin
  if new.id <> old.id
     or new.object_path <> old.object_path
     or new.mime_type <> old.mime_type
     or new.size_bytes <> old.size_bytes
     or new.width is distinct from old.width
     or new.height is distinct from old.height
     or new.alt is distinct from old.alt
     or new.checksum_sha256 <> old.checksum_sha256
     or new.uploaded_by <> old.uploaded_by
     or new.uploaded_at <> old.uploaded_at then
    raise exception 'media rows are immutable; create a new row';
  end if;

  if old.deleted_at is not null and new.deleted_at is null then
    raise exception 'media cannot be undeleted';
  end if;

  if old.deleted_at is not null and new.deleted_at is distinct from old.deleted_at then
    raise exception 'media deletion cannot be changed';
  end if;

  if old.visibility = 'public' then
    if new.visibility <> 'public'
       or new.bucket <> old.bucket
       or new.promoted_at is distinct from old.promoted_at then
      raise exception 'a public media row only changes its deleted_at';
    end if;
  elsif new.visibility = 'public' then
    if old.bucket <> 'media-staging'
       or new.bucket <> 'site-media'
       or old.promoted_at is not null
       or new.promoted_at is null
       or old.deleted_at is not null
       or new.deleted_at is not null then
      raise exception 'promotion moves one staged row to site-media';
    end if;
  elsif new.visibility <> old.visibility
     or new.bucket <> old.bucket
     or new.promoted_at is distinct from old.promoted_at then
    raise exception 'media visibility only changes on promotion';
  end if;

  return new;
end;
$$;

create trigger media_immutable
  before update on media
  for each row execute function prevent_media_mutation();
```

```sql
create or replace function lock_staff_writes()
returns trigger
language plpgsql
as $$
begin
  -- Taken before the row locks this statement will take, so two writers cannot each hold
  -- a row the other needs while one waits here. It cannot reorder a lock the caller
  -- already holds. The key is constant for the staff write path and the lock ends with
  -- the transaction.
  perform pg_advisory_xact_lock(hashtext('staff_last_admin'));
  return null;
end;
$$;

create trigger staff_lock_writes
  before insert or update or delete on staff
  for each statement execute function lock_staff_writes();

create or replace function enforce_last_admin()
returns trigger
language plpgsql
as $$
declare
  remaining integer;
begin
  if tg_op = 'DELETE' then
    if old.role = 'admin' and old.active then
      select count(*) into remaining
      from (
        select 1 from staff
        where role = 'admin' and active and user_id <> old.user_id
        for update
      ) locked;
      if remaining = 0 then
        raise exception 'the last active Admin cannot be removed';
      end if;
    end if;
    return old;
  end if;

  if old.role = 'admin' and old.active
     and not (new.role = 'admin' and new.active) then
    select count(*) into remaining
    from (
      select 1 from staff
      where role = 'admin' and active and user_id <> old.user_id
      for update
    ) locked;
    if remaining = 0 then
      raise exception 'the last active Admin cannot be removed';
    end if;
  end if;

  return new;
end;
$$;

create trigger staff_last_admin
  before update or delete on staff
  for each row execute function enforce_last_admin();
```

The statement trigger takes a transaction-scoped advisory lock before the row locks its own
statement takes, so two staff writers serialise instead of forming a lock cycle. It covers
INSERT as well: the insert's own `created_by` foreign key takes a key-share lock on an
Admin row after this trigger, so without INSERT coverage a transaction could hold that
key-share and only take the advisory lock at a later staff write, forming the cycle. The trigger cannot reorder a lock the caller
already holds: any staff service must either take
`pg_advisory_xact_lock(hashtext('staff_last_admin'))` before its first staff row lock or
retry `40P01` with a bounded backoff (Backend/docs/work/PLAN.md M15). The lock is held to commit, so a long
staff transaction blocks every other staff writer; keep staff write transactions short. The
row trigger counts active Admins other than the row being changed with a locking read: under
READ COMMITTED the statement lock already serialises, and under REPEATABLE READ or
SERIALIZABLE a concurrent committed change raises a serialization failure (`40001`) rather
than being missed by the snapshot. Demoting the last Admin, deactivating them or deleting
them all fail. A second Admin must exist first.

### Publication and immutability

```sql
create or replace function prevent_published_version_mutation()
returns trigger
language plpgsql
as $$
begin
  if old.status = 'published' then
    raise exception 'published version % is immutable', old.id;
  end if;

  if tg_op = 'DELETE' then
    return old;
  end if;
  return new;
end;
$$;

create trigger content_version_immutable
  before update or delete on content_version
  for each row execute function prevent_published_version_mutation();
```

The publish update itself is allowed: it changes a draft or in-review row to
published. Any later update or delete sees `old.status = 'published'` and fails; the
delete branch returns `old`, so a draft version can still be deleted and a published
version cannot. This also refuses an item cascade that would remove a published version.

```sql
create or replace function assert_publication_version()
returns trigger
language plpgsql
as $$
declare
  v_status version_status;
  v_archived timestamptz;
begin
  if tg_op = 'UPDATE' and new.item_id <> old.item_id then
    raise exception 'publication item cannot change';
  end if;

  select cv.status, ci.archived_at
    into v_status, v_archived
  from content_version cv
  join content_item ci on ci.id = cv.item_id
  where cv.id = new.version_id and cv.item_id = new.item_id;

  if v_status is null then
    raise exception 'version % does not belong to item %', new.version_id, new.item_id;
  end if;
  if v_status <> 'published' then
    raise exception 'publication version must be published';
  end if;
  if v_archived is not null then
    raise exception 'archived item cannot be published';
  end if;

  return new;
end;
$$;

create trigger content_publication_assert
  before insert or update on content_publication
  for each row execute function assert_publication_version();
```

A typed content row belongs to exactly one version and is immutable once that version
is published. It cannot move to another version: an update that changes `version_id`
is refused before the status check, so a published version cannot lose its typed rows
to a draft. The shared trigger reads the version status, so every table does not repeat
the rule.

```sql
create or replace function prevent_published_content_mutation()
returns trigger
language plpgsql
as $$
declare
  v_version uuid;
  v_status version_status;
begin
  if tg_op = 'UPDATE' and old.version_id is distinct from new.version_id then
    raise exception 'content rows cannot move between versions';
  end if;

  v_version := case when tg_op = 'DELETE' then old.version_id else new.version_id end;

  select status into v_status
  from content_version
  where id = v_version;

  if v_status = 'published' then
    raise exception 'published version content is immutable';
  end if;

  if tg_op = 'DELETE' then
    return old;
  end if;
  return new;
end;
$$;
```

```sql
create trigger content_seo_immutable
  before insert or update or delete on content_seo
  for each row execute function prevent_published_content_mutation();

create trigger section_version_immutable
  before insert or update or delete on section_version
  for each row execute function prevent_published_content_mutation();

create trigger section_paragraph_immutable
  before insert or update or delete on section_paragraph
  for each row execute function prevent_published_content_mutation();

create trigger process_stage_immutable
  before insert or update or delete on process_stage
  for each row execute function prevent_published_content_mutation();

create trigger process_assurance_immutable
  before insert or update or delete on process_assurance
  for each row execute function prevent_published_content_mutation();

create trigger faq_item_immutable
  before insert or update or delete on faq_item
  for each row execute function prevent_published_content_mutation();

create trigger contact_next_step_immutable
  before insert or update or delete on contact_next_step
  for each row execute function prevent_published_content_mutation();

create trigger section_version_item_immutable
  before insert or update or delete on section_version_item
  for each row execute function prevent_published_content_mutation();

create trigger service_group_version_immutable
  before insert or update or delete on service_group_version
  for each row execute function prevent_published_content_mutation();

create trigger service_version_immutable
  before insert or update or delete on service_version
  for each row execute function prevent_published_content_mutation();

create trigger project_version_immutable
  before insert or update or delete on project_version
  for each row execute function prevent_published_content_mutation();

create trigger project_image_immutable
  before insert or update or delete on project_image
  for each row execute function prevent_published_content_mutation();

create trigger project_technology_immutable
  before insert or update or delete on project_technology
  for each row execute function prevent_published_content_mutation();

create trigger proof_figure_version_immutable
  before insert or update or delete on proof_figure_version
  for each row execute function prevent_published_content_mutation();

create trigger testimonial_version_immutable
  before insert or update or delete on testimonial_version
  for each row execute function prevent_published_content_mutation();

create trigger client_logo_version_immutable
  before insert or update or delete on client_logo_version
  for each row execute function prevent_published_content_mutation();

create trigger legal_page_version_immutable
  before insert or update or delete on legal_page_version
  for each row execute function prevent_published_content_mutation();

create trigger legal_block_immutable
  before insert or update or delete on legal_block
  for each row execute function prevent_published_content_mutation();

create trigger legal_block_item_immutable
  before insert or update or delete on legal_block_item
  for each row execute function prevent_published_content_mutation();

create trigger legal_block_column_immutable
  before insert or update or delete on legal_block_column
  for each row execute function prevent_published_content_mutation();

create trigger legal_block_row_immutable
  before insert or update or delete on legal_block_row
  for each row execute function prevent_published_content_mutation();

create trigger legal_block_cell_immutable
  before insert or update or delete on legal_block_cell
  for each row execute function prevent_published_content_mutation();

create trigger settings_version_immutable
  before insert or update or delete on settings_version
  for each row execute function prevent_published_content_mutation();

create trigger settings_address_line_immutable
  before insert or update or delete on settings_address_line
  for each row execute function prevent_published_content_mutation();

create trigger settings_location_immutable
  before insert or update or delete on settings_location
  for each row execute function prevent_published_content_mutation();

create trigger settings_location_address_line_immutable
  before insert or update or delete on settings_location_address_line
  for each row execute function prevent_published_content_mutation();

create trigger settings_footer_link_immutable
  before insert or update or delete on settings_footer_link
  for each row execute function prevent_published_content_mutation();

create trigger settings_working_hour_immutable
  before insert or update or delete on settings_working_hour
  for each row execute function prevent_published_content_mutation();
```

### Section counts and publish gates

```sql
create or replace function assert_section_counts(p_version_id uuid)
returns void
language plpgsql
as $$
declare
  v_key page_section_key;
  n integer;
begin
  select section_key into v_key
  from section_version
  where version_id = p_version_id;

  if v_key is null then
    raise exception 'version % is not a page section', p_version_id;
  end if;

  if exists (
    select 1 from section_version_item svi
    where svi.version_id = p_version_id
      and not exists (
        select 1 from content_publication cp where cp.item_id = svi.item_id
      )
  ) then
    raise exception 'every referenced record must be published before its section';
  end if;

  if v_key = 'services' then
    select count(*) into n
    from section_version_item
    where version_id = p_version_id and item_kind = 'service_group';
    if n < 3 or n > 4 then
      raise exception 'services needs three or four groups, found %', n;
    end if;
  elsif v_key = 'work' then
    select count(*) into n
    from section_version_item
    where version_id = p_version_id and item_kind = 'project';
    if n < 3 or n > 6 then
      raise exception 'featured work needs three to six projects, found %', n;
    end if;
  elsif v_key = 'proof' then
    select count(*) into n
    from section_version_item
    where version_id = p_version_id and item_kind = 'proof_figure';
    if n > 4 then
      raise exception 'proof figures allows at most four figures, found %', n;
    end if;
  elsif v_key = 'about' then
    select count(*) into n
    from section_paragraph
    where version_id = p_version_id;
    if n < 1 then
      raise exception 'about needs at least one paragraph, found %', n;
    end if;
  elsif v_key = 'testimonials' then
    select count(*) into n
    from section_version_item
    where version_id = p_version_id and item_kind = 'testimonial';
    if n > 6 then
      raise exception 'testimonials allows at most six quotes, found %', n;
    end if;
  end if;
end;
$$;

create or replace function assert_publishable_version()
returns trigger
language plpgsql
as $$
declare
  v_kind content_kind;
  n integer;
begin
  if new.status = 'published' and old.status <> 'published' then
    select kind into v_kind from content_item where id = new.item_id;

    if v_kind = 'landing_page' then
      if exists (
        select 1 from page_section ps
        where ps.page_id = new.item_id
          and not exists (
            select 1 from content_publication cp where cp.item_id = ps.item_id
          )
      ) then
        raise exception 'every page section must be published before the page';
      end if;
    elsif v_kind = 'page_section' then
      perform assert_section_counts(new.id);
    elsif v_kind in ('project', 'proof_figure', 'testimonial', 'client_logo') then
      if not exists (
        select 1 from approval
        where version_id = new.id
          and revoked_at is null
          and approved_on <= (now() at time zone 'Europe/London')::date
          and (expires_on is null or expires_on >= (now() at time zone 'Europe/London')::date)
      ) then
        raise exception 'an unexpired approval is required to publish this version';
      end if;

      if v_kind = 'project'
         and exists (select 1 from project_image where version_id = new.id)
         and not exists (
           select 1 from approval
           where version_id = new.id
             and revoked_at is null
             and approved_on <= (now() at time zone 'Europe/London')::date
             and (expires_on is null or expires_on >= (now() at time zone 'Europe/London')::date)
             and 'screenshots' = any(scopes)
         ) then
        raise exception 'the approval must cover the screenshots';
      end if;
    elsif v_kind = 'legal_page' then
      if not exists (
        select 1 from legal_approval where version_id = new.id
      ) then
        raise exception 'a legal approver is required to publish this version';
      end if;

      if exists (
        select 1
        from legal_block b
        where b.version_id = new.id
          and b.kind = 'ul'
          and not exists (
            select 1 from legal_block_item i
            where i.version_id = b.version_id
              and i.block_sort_order = b.sort_order
          )
      ) then
        raise exception 'a legal list needs at least one item';
      end if;

      if exists (
        select 1
        from legal_block b
        where b.version_id = new.id
          and b.kind = 'table'
          and not exists (
            select 1 from legal_block_column c
            where c.version_id = b.version_id
              and c.block_sort_order = b.sort_order
          )
      ) then
        raise exception 'a legal table needs at least one column';
      end if;

      if exists (
        select 1
        from legal_block_row r
        where r.version_id = new.id
          and (
            select count(*) from legal_block_cell c
            where c.version_id = r.version_id
              and c.block_sort_order = r.block_sort_order
              and c.row_sort_order = r.sort_order
          ) <> (
            select count(*) from legal_block_column c
            where c.version_id = r.version_id
              and c.block_sort_order = r.block_sort_order
          )
      ) then
        raise exception 'every legal table row needs one cell per column';
      end if;
    elsif v_kind = 'settings' then
      if exists (
        select 1 from settings_version
        where version_id = new.id
          and (legal_name is null or country is null or contact_email is null)
      ) then
        raise exception 'the legal identity needs a legal name, country and working email';
      end if;

      select count(*) into n
      from settings_address_line
      where version_id = new.id;
      if n < 2 then
        raise exception 'the legal identity needs at least two address lines';
      end if;

      if (select uk_establishment from settings_version where version_id = new.id) then
        if exists (
          select 1 from settings_version
          where version_id = new.id
            and (country is null or home_registry is null
              or registration_number is null or head_office_location is null
              or legal_form is null or limited_liability is null
              or insolvency_information is null)
        ) then
          raise exception 'a UK establishment needs its regulation 63 details';
        end if;
      end if;

      if exists (
        select 1
        from settings_location l
        where l.version_id = new.id
          and (
            select count(*) from settings_location_address_line a
            where a.version_id = l.version_id
              and a.location_sort_order = l.sort_order
          ) < 2
      ) then
        raise exception 'a location needs at least two address lines';
      end if;
    end if;

    if v_kind in ('landing_page', 'legal_page') then
      if not exists (
        select 1 from content_seo
        where version_id = new.id
          and seo_title is not null
          and seo_description is not null
      ) then
        raise exception 'a page needs an SEO title and description';
      end if;
    end if;

    if v_kind in ('landing_page', 'page_section', 'project', 'client_logo', 'settings') then
      if exists (
        select 1
        from version_media vm
        join media m on m.id = vm.media_id
        where vm.version_id = new.id
          and (m.visibility <> 'public' or m.deleted_at is not null)
      ) then
        raise exception 'promote every site image before publishing';
      end if;
    end if;
  end if;

  return new;
end;
$$;

create trigger content_version_publish_assert
  before update on content_version
  for each row execute function assert_publishable_version();
```

A page version publishes only after every one of its sections has a live version. That
is what keeps the live page whole: a section left in draft keeps its previous published
version, and a section that has never published blocks the page until it is ready.

The content gates that need copy knowledge — the hero's two CTAs, the five nav
labels, the privacy note, unique SEO titles, the cookies table against
`cookies.json`, and the FAQ five-to-eight warning (LP-5 is a Should, PRD §5) —
are Pydantic and FastAPI rules, not SQL. The database enforces the
counts, the references, the approvals, the legal approver and the presence of a page's
SEO title and description; uniqueness across live pages stays in FastAPI, because a
unique index cannot span a view. Duplicating copy checks in SQL would make the schema
the second place to change a rule.

The FAQ count is a FastAPI/Pydantic CMS warning on `published` rows, not a database
gate. PRD §5 lists 5–8 questions and LP-5 is a Should, so the database publishes an
FAQ section at any count — recorded here as a decision, not a PRD rule.

### Child references

```sql
create or replace function assert_section_version_item()
returns trigger
language plpgsql
as $$
declare
  v_status version_status;
  v_kind content_kind;
  v_key page_section_key;
  v_version uuid;
  v_item_kind content_kind;
begin
  v_version := case when tg_op = 'DELETE' then old.version_id else new.version_id end;
  v_item_kind := case when tg_op = 'DELETE' then old.item_kind else new.item_kind end;

  if tg_op = 'UPDATE'
     and (old.version_id <> new.version_id or old.item_id <> new.item_id) then
    raise exception 'a section reference cannot move between versions or items';
  end if;

  select cv.status, ci.kind, ps.section_key
    into v_status, v_kind, v_key
  from content_version cv
  join content_item ci on ci.id = cv.item_id
  left join page_section ps on ps.item_id = cv.item_id
  where cv.id = v_version;

  if v_kind is null then
    if tg_op = 'DELETE' then
      return old;
    end if;
    raise exception 'references belong to a page section version';
  end if;
  if v_kind <> 'page_section' then
    raise exception 'references belong to a page section version';
  end if;
  if v_status = 'published' then
    raise exception 'published section version is immutable';
  end if;

  if tg_op = 'DELETE' then
    return old;
  end if;

  if v_key is null then
    raise exception 'section item has no page_section row';
  end if;
  if v_key = 'services' and v_item_kind = 'service_group' then
    return new;
  elsif v_key = 'work' and v_item_kind = 'project' then
    return new;
  elsif v_key = 'proof' and v_item_kind = 'proof_figure' then
    return new;
  elsif v_key = 'testimonials' and v_item_kind = 'testimonial' then
    return new;
  else
    raise exception 'section % cannot reference a %', v_key, v_item_kind;
  end if;
end;
$$;

create trigger section_version_item_assert
  before insert or update or delete on section_version_item
  for each row execute function assert_section_version_item();
```

### Legal and client approvals

```sql
create or replace function assert_legal_approval()
returns trigger
language plpgsql
as $$
declare
  v_status version_status;
  v_kind content_kind;
  v_author uuid;
begin
  select cv.status, ci.kind, cv.created_by
    into v_status, v_kind, v_author
  from content_version cv
  join content_item ci on ci.id = cv.item_id
  where cv.id = new.version_id;

  if v_kind is null or v_kind <> 'legal_page' then
    raise exception 'legal approval belongs to a legal page version';
  end if;
  if v_status = 'published' then
    raise exception 'published legal approval is immutable';
  end if;
  if new.author_id <> v_author then
    raise exception 'legal approval author must be the version author';
  end if;
  if not exists (
    select 1 from staff
    where user_id = new.approver_id and role = 'admin' and active
  ) then
    raise exception 'legal approver must be an active Admin';
  end if;

  return new;
end;
$$;

create trigger legal_approval_assert
  before insert or update on legal_approval
  for each row execute function assert_legal_approval();

create or replace function assert_legal_approval_delete()
returns trigger
language plpgsql
as $$
declare
  v_status version_status;
begin
  select status into v_status
  from content_version
  where id = old.version_id;

  if v_status = 'published' then
    raise exception 'a published legal approval cannot be deleted';
  end if;

  return old;
end;
$$;

create trigger legal_approval_no_delete
  before delete on legal_approval
  for each row execute function assert_legal_approval_delete();
```

```sql
create or replace function assert_approval()
returns trigger
language plpgsql
as $$
declare
  v_kind content_kind;
  v_bucket text;
  v_status version_status;
  v_deleted_at timestamptz;
begin
  select ci.kind, cv.status
    into v_kind, v_status
  from content_version cv
  join content_item ci on ci.id = cv.item_id
  where cv.id = new.version_id;

  if v_kind is null or v_kind <> new.subject_kind then
    raise exception 'approval subject does not match the version kind';
  end if;
  if v_kind not in ('project', 'proof_figure', 'testimonial', 'client_logo') then
    raise exception 'approvals cover projects, figures, testimonials and logos';
  end if;

  if tg_op = 'INSERT' and v_status = 'published' then
    raise exception 'approve a version before it is published';
  end if;

  if tg_op = 'UPDATE' and old.revoked_at is not null and new.revoked_at is null then
    raise exception 'a revoked approval cannot be reactivated';
  end if;

  if tg_op = 'UPDATE' and v_status = 'published' then
    if new.version_id <> old.version_id
       or new.subject_kind <> old.subject_kind
       or new.scopes <> old.scopes
       or new.approved_by_name <> old.approved_by_name
       or new.approved_by_email is distinct from old.approved_by_email
       or new.approved_on <> old.approved_on
       or new.expires_on is distinct from old.expires_on
       or new.evidence_media_id is distinct from old.evidence_media_id
       or new.recorded_by <> old.recorded_by then
      raise exception 'a published approval can only be revoked';
    end if;
  end if;

  if v_kind = 'project' then
    if not (new.scopes <@ array['client_name', 'result', 'mark', 'screenshots']::approval_scope[]) then
      raise exception 'invalid project approval scope';
    end if;
  elsif v_kind = 'proof_figure' then
    if new.scopes <> array['figure']::approval_scope[] then
      raise exception 'a figure approval covers the figure only';
    end if;
  elsif v_kind = 'testimonial' then
    if not (
      new.scopes <@ array['quote', 'client_name']::approval_scope[]
      and 'quote' = any(new.scopes)
    ) then
      raise exception 'a testimonial approval carries the quote and may carry the name';
    end if;
  elsif v_kind = 'client_logo' then
    if not (
      new.scopes <@ array['mark', 'client_name']::approval_scope[]
      and 'mark' = any(new.scopes)
    ) then
      raise exception 'a client logo approval carries the mark and may carry the name';
    end if;
  end if;

  if new.approved_on > (now() at time zone 'Europe/London')::date then
    raise exception 'an approval cannot be dated in the future';
  end if;

  if new.evidence_media_id is not null then
    select bucket, deleted_at
      into v_bucket, v_deleted_at
    from media where id = new.evidence_media_id;

    if v_bucket is null or v_bucket <> 'evidence' then
      raise exception 'approval evidence must be in the evidence bucket';
    end if;
    if v_deleted_at is not null then
      raise exception 'deleted evidence cannot be attached';
    end if;
  end if;

  return new;
end;
$$;

create trigger approval_assert
  before insert or update on approval
  for each row execute function assert_approval();

create or replace function assert_approval_delete()
returns trigger
language plpgsql
as $$
declare
  v_status version_status;
begin
  select status into v_status
  from content_version
  where id = old.version_id;

  if v_status = 'published' then
    raise exception 'revoke a published approval instead of deleting it';
  end if;

  return old;
end;
$$;

create trigger approval_no_delete
  before delete on approval
  for each row execute function assert_approval_delete();
```

The API checks that a project's approval covers every claim it makes: a non-null
`client` needs `client_name`, a non-null `result` needs `result`, any `project_image`
needs `screenshots`, and a client logo's `client_name` needs `client_name`. The
database checks that the scopes are legal for the subject, requires `screenshots` when
a `project_image` row exists, and leaves the claim coverage to the API.

### Live projections

```sql
create or replace function sync_live_projection()
returns trigger
language plpgsql
as $$
declare
  v_item uuid;
  v_kind content_kind;
  v_group uuid;
  v_title text;
  v_sort integer;
begin
  if tg_op = 'DELETE' then
    v_item := old.item_id;
  else
    v_item := new.item_id;
  end if;

  select kind into v_kind from content_item where id = v_item;

  if v_kind = 'service' then
    if tg_op = 'DELETE' then
      delete from service where item_id = old.item_id;
      return null;
    end if;

    select group_item_id, title, sort_order
      into v_group, v_title, v_sort
    from service_version
    where version_id = new.version_id;

    if v_group is null or v_title is null then
      raise exception 'service version needs a group and a title';
    end if;
    if not exists (
      select 1 from content_publication where item_id = v_group
    ) then
      raise exception 'service group must be published before its services';
    end if;

    insert into service (item_id, group_item_id, live_title, live_sort_order, published_at)
    values (new.item_id, v_group, v_title, coalesce(v_sort, 0), now())
    on conflict (item_id) do update
      set group_item_id = excluded.group_item_id,
          live_title = excluded.live_title,
          live_sort_order = excluded.live_sort_order,
          published_at = excluded.published_at;

    return null;
  end if;

  if v_kind = 'project' then
    if tg_op = 'DELETE' then
      return null;
    end if;

    select sort_order into v_sort
    from project_version
    where version_id = new.version_id;

    update project
      set live_sort_order = coalesce(v_sort, 0),
          published_at = now()
    where item_id = new.item_id;

    return null;
  end if;

  return null;
end;
$$;

create trigger content_publication_live_sync
  after insert or update or delete on content_publication
  for each row execute function sync_live_projection();
```

Unpublishing a project leaves its typed row and last live order; the project is simply
absent from `published_content`. A service is different: its typed row is the enquiry
chip and only exists while the service is live, so an unpublish deletes it.

```sql
create or replace function guard_group_unpublish()
returns trigger
language plpgsql
as $$
declare
  v_kind content_kind;
begin
  select kind into v_kind from content_item where id = old.item_id;
  if v_kind = 'service_group' and exists (
    select 1 from service where group_item_id = old.item_id
  ) then
    raise exception 'unpublish the group services before the group';
  end if;

  return old;
end;
$$;

create trigger group_unpublish_guard
  before delete on content_publication
  for each row execute function guard_group_unpublish();
```

A site image can only be a media row from a site bucket, never evidence. The columns
already carry the foreign key; this trigger checks the bucket and the mime type when an
image is attached. One helper does the check; each table has a small trigger that names
its own column, so nothing is looked up by a string at runtime.

```sql
create or replace function assert_site_image(p_media uuid)
returns void
language plpgsql
as $$
declare
  v_bucket text;
  v_mime text;
begin
  if p_media is null then
    return;
  end if;

  select bucket, mime_type
    into v_bucket, v_mime
  from media where id = p_media;

  if v_bucket is null then
    raise exception 'media % not found', p_media;
  end if;
  if v_bucket = 'evidence' then
    raise exception 'evidence cannot be a site image';
  end if;
  if v_mime not like 'image/%' then
    raise exception 'site images must be images';
  end if;
end;
$$;

create or replace function content_seo_site_image()
returns trigger
language plpgsql
as $$
begin
  perform assert_site_image(new.og_image_id);
  return new;
end;
$$;

create or replace function section_version_site_image()
returns trigger
language plpgsql
as $$
begin
  perform assert_site_image(new.image_id);
  return new;
end;
$$;

create or replace function client_logo_version_site_image()
returns trigger
language plpgsql
as $$
begin
  perform assert_site_image(new.image_id);
  return new;
end;
$$;

create or replace function project_image_site_image()
returns trigger
language plpgsql
as $$
begin
  perform assert_site_image(new.media_id);
  return new;
end;
$$;

create or replace function settings_version_site_image()
returns trigger
language plpgsql
as $$
begin
  perform assert_site_image(new.seo_og_image_id);
  perform assert_site_image(new.site_logo_id);
  return new;
end;
$$;

create trigger content_seo_site_image
  before insert or update on content_seo
  for each row execute function content_seo_site_image();

create trigger section_version_site_image
  before insert or update on section_version
  for each row execute function section_version_site_image();

create trigger client_logo_version_site_image
  before insert or update on client_logo_version
  for each row execute function client_logo_version_site_image();

create trigger project_image_site_image
  before insert or update on project_image
  for each row execute function project_image_site_image();

create trigger settings_version_site_image
  before insert or update on settings_version
  for each row execute function settings_version_site_image();
```

### Enquiries and audit

```sql
create or replace function enquiry_status_flow()
returns trigger
language plpgsql
as $$
begin
  if new.status = old.status then
    return new;
  end if;

  if not (
    (old.status = 'new' and new.status = 'in_progress')
    or (old.status = 'in_progress' and new.status = 'closed')
  ) then
    raise exception 'enquiries move new to in progress to closed';
  end if;

  if new.status = 'closed' then
    new.closed_at := coalesce(new.closed_at, now());
  end if;

  return new;
end;
$$;

create trigger enquiry_status_flow
  before update on enquiry
  for each row execute function enquiry_status_flow();

create or replace function guard_first_reply()
returns trigger
language plpgsql
as $$
begin
  if old.first_replied_at is not null
     and new.first_replied_at is distinct from old.first_replied_at then
    raise exception 'the first reply time is recorded once';
  end if;

  return new;
end;
$$;

create trigger enquiry_first_reply_once
  before update on enquiry
  for each row execute function guard_first_reply();
```

`first_replied_at` is not stamped by triage. Moving an enquiry to `in_progress` records
that an Admin has picked it up; the API sets `first_replied_at` once, when a human reply
is actually sent, and the trigger refuses a second value. SM-3 measures from
`created_at` to `first_replied_at`, so triaging early cannot improve the number.

```sql
create or replace function prevent_audit_mutation()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'DELETE' and current_setting('app.audit_retention', true) = 'on' then
    return old;
  end if;
  raise exception 'audit_log is append-only';
end;
$$;

create trigger audit_log_append_only
  before update or delete on audit_log
  for each row execute function prevent_audit_mutation();
```

### Publish, unpublish, delete and drafts

Publishing a page or a project has two parts. FastAPI first copies every staged image
attached to the winning version to `site-media` and flips those media rows; then it
calls the publish function. The SQL gate refuses the publish while any attached image
is still staged or has been deleted, so the pointer cannot move ahead of the files. If
the second part fails, FastAPI deletes the copies it just made and marks those rows
deleted, so no unreferenced file stays public; the draft then reports the images as
needing re-upload. A retry copies and promotes the replacement rows. A copy whose draft
is later discarded is reclaimed by `mark_orphan_media` after 24 hours.

A landing page is published with `publish_page`, not `publish_content`. It takes the
page version and the section versions the Admin is publishing; each section flips its
own pointer, then the page flips last. A section the Admin leaves in draft keeps its
previous published version, and a section that has never been published blocks the page.
The whole call is one transaction: if any section fails its gate, no pointer moves.

```sql
create or replace function _publish_version(
  p_item_id uuid,
  p_version_id uuid,
  p_actor uuid
)
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_revision integer;
begin
  perform 1 from content_item where id = p_item_id for update;
  if not found then
    raise exception 'item % not found', p_item_id;
  end if;

  select version_number
    into v_revision
  from content_version
  where id = p_version_id
    and item_id = p_item_id
    and status in ('draft', 'in_review');

  if v_revision is null then
    raise exception 'version % is not publishable', p_version_id;
  end if;

  update content_version
    set status = 'published',
        published_at = now(),
        published_by = p_actor
  where id = p_version_id;

  insert into content_publication (item_id, version_id, published_at, published_by)
  values (p_item_id, p_version_id, now(), p_actor)
  on conflict (item_id) do update
    set version_id = excluded.version_id,
        published_at = excluded.published_at,
        published_by = excluded.published_by;

  return v_revision;
end;
$$;

create or replace function publish_content(
  p_item_id uuid,
  p_version_id uuid,
  p_actor uuid
)
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_kind content_kind;
  v_path text;
  v_page_path text;
  v_revision integer;
  v_tags text[];
begin
  select kind, path
    into v_kind, v_path
  from content_item
  where id = p_item_id
  for update;

  if v_kind is null then
    raise exception 'item % not found', p_item_id;
  end if;
  if v_kind = 'landing_page' then
    raise exception 'a landing page is published with publish_page';
  end if;

  v_revision := _publish_version(p_item_id, p_version_id, p_actor);

  if v_kind = 'settings' then
    select array['settings', 'page:/'] || coalesce(
      array_agg(distinct 'page:' || ci.path),
      '{}'::text[]
    )
    into v_tags
    from content_item ci
    join content_publication cp on cp.item_id = ci.id
    where ci.kind = 'legal_page' and ci.archived_at is null;
  elsif v_kind = 'legal_page' then
    v_tags := array['page:' || v_path, 'routes'];
  elsif v_kind = 'page_section' then
    select ci.path into v_page_path
    from page_section ps
    join content_item ci on ci.id = ps.page_id
    where ps.item_id = p_item_id;

    v_tags := array['page:' || v_page_path, 'routes'];
  else
    v_tags := array['page:/'];
  end if;

  insert into revalidation (tags) values (v_tags);

  insert into audit_log (
    actor_id, action, entity_kind, entity_id, version_id, revision
  )
  values (
    p_actor, 'publish', v_kind::text, p_item_id::text, p_version_id, v_revision
  );

  return v_revision;
end;
$$;

create or replace function publish_page(
  p_page_id uuid,
  p_page_version_id uuid,
  p_section_versions uuid[],
  p_actor uuid
)
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_kind content_kind;
  v_path text;
  v_revision integer;
  r record;
begin
  select kind, path
    into v_kind, v_path
  from content_item
  where id = p_page_id
  for update;

  if v_kind is null then
    raise exception 'item % not found', p_page_id;
  end if;
  if v_kind <> 'landing_page' then
    raise exception 'item % is not a landing page', p_page_id;
  end if;

  if exists (
    select 1
    from unnest(p_section_versions) as u(version_id)
    left join content_version cv on cv.id = u.version_id
    left join page_section ps on ps.item_id = cv.item_id
    where cv.id is null or ps.page_id is distinct from p_page_id
  ) then
    raise exception 'a section version does not belong to this page';
  end if;

  for r in
    select distinct cv.id as version_id, cv.item_id, cv.version_number
    from unnest(p_section_versions) as u(version_id)
    join content_version cv on cv.id = u.version_id
    join page_section ps on ps.item_id = cv.item_id
    where ps.page_id = p_page_id
    order by cv.item_id
  loop
    perform _publish_version(r.item_id, r.version_id, p_actor);

    insert into audit_log (
      actor_id, action, entity_kind, entity_id, version_id, revision, page_id
    )
    values (
      p_actor,
      'publish',
      'page_section',
      r.item_id::text,
      r.version_id,
      r.version_number,
      p_page_id
    );
  end loop;

  if exists (
    select 1 from page_section ps
    where ps.page_id = p_page_id
      and not exists (
        select 1 from content_publication cp where cp.item_id = ps.item_id
      )
  ) then
    raise exception 'every page section must be published before the page';
  end if;

  v_revision := _publish_version(p_page_id, p_page_version_id, p_actor);

  insert into revalidation (tags) values (array['page:' || v_path, 'routes']);

  insert into audit_log (
    actor_id, action, entity_kind, entity_id, version_id, revision
  )
  values (
    p_actor,
    'publish',
    'landing_page',
    p_page_id::text,
    p_page_version_id,
    v_revision
  );

  return v_revision;
end;
$$;
```

```sql
create or replace function _unpublish_internal(
  p_item_id uuid,
  p_actor uuid,
  p_create_draft boolean
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_kind content_kind;
  v_path text;
  v_page_path text;
  v_tags text[];
  v_ids uuid[];
  v_id uuid;
  v_unpublished uuid[] := '{}';
begin
  select kind, path
    into v_kind, v_path
  from content_item
  where id = p_item_id
  for update;

  if v_kind is null then
    raise exception 'item % not found', p_item_id;
  end if;

  if v_kind = 'landing_page' then
    with removed as (
      delete from content_publication
      where item_id in (
        select item_id from page_section where page_id = p_item_id
      )
      returning item_id
    )
    select coalesce(array_agg(item_id), '{}'::uuid[]) into v_ids from removed;

    v_unpublished := v_unpublished || v_ids;
  end if;

  with removed as (
    delete from content_publication
    where item_id = p_item_id
    returning item_id
  )
  select coalesce(array_agg(item_id), '{}'::uuid[]) into v_ids from removed;

  v_unpublished := v_unpublished || v_ids;

  if v_kind = 'settings' then
    select array['settings', 'page:/'] || coalesce(
      array_agg(distinct 'page:' || ci.path),
      '{}'::text[]
    )
    into v_tags
    from content_item ci
    join content_publication cp on cp.item_id = ci.id
    where ci.kind = 'legal_page' and ci.archived_at is null;
  elsif v_kind = 'legal_page' then
    v_tags := array['page:' || v_path, 'routes'];
  elsif v_kind = 'landing_page' then
    v_tags := array['page:' || v_path, 'routes'];
  elsif v_kind = 'page_section' then
    select ci.path into v_page_path
    from page_section ps
    join content_item ci on ci.id = ps.page_id
    where ps.item_id = p_item_id;

    v_tags := array['page:' || v_page_path, 'routes'];
  else
    v_tags := array['page:/'];
  end if;

  insert into revalidation (tags) values (v_tags);

  insert into audit_log (actor_id, action, entity_kind, entity_id, path)
  values (p_actor, 'unpublish', v_kind::text, p_item_id::text, v_path);

  if p_create_draft then
    foreach v_id in array v_unpublished loop
      if exists (
        select 1 from content_item
        where id = v_id and archived_at is null
      ) then
        perform create_draft(v_id, p_actor);
      end if;
    end loop;
  end if;
end;
$$;

create or replace function unpublish_content(
  p_item_id uuid,
  p_actor uuid
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  perform _unpublish_internal(p_item_id, p_actor, true);
end;
$$;
```

```sql
create or replace function archive_content(
  p_item_id uuid,
  p_actor uuid
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_kind content_kind;
  v_path text;
  v_archived timestamptz;
begin
  select kind, path, archived_at
    into v_kind, v_path, v_archived
  from content_item
  where id = p_item_id
  for update;

  if v_kind is null then
    raise exception 'item % not found', p_item_id;
  end if;
  if v_archived is not null then
    raise exception 'item % is already archived', p_item_id;
  end if;

  if exists (select 1 from content_publication where item_id = p_item_id)
     or (
       v_kind = 'landing_page'
       and exists (
         select 1
         from page_section ps
         join content_publication cp on cp.item_id = ps.item_id
         where ps.page_id = p_item_id
       )
     ) then
    perform _unpublish_internal(p_item_id, p_actor, false);
  end if;

  update content_item
    set archived_at = now(),
        archived_by = p_actor
  where id = p_item_id;

  if v_kind = 'landing_page' then
    update content_item
      set archived_at = now(),
          archived_by = p_actor
    where id in (
      select item_id from page_section where page_id = p_item_id
    )
      and archived_at is null;
  end if;

  insert into audit_log (actor_id, action, entity_kind, entity_id, path)
  values (p_actor, 'archive', v_kind::text, p_item_id::text, v_path);
end;
$$;

create or replace function restore_content(
  p_item_id uuid,
  p_actor uuid
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_kind content_kind;
begin
  update content_item
    set archived_at = null,
        archived_by = null
  where id = p_item_id
    and archived_at is not null
  returning kind into v_kind;

  if v_kind is null then
    raise exception 'archived item % not found', p_item_id;
  end if;

  if v_kind = 'landing_page' then
    update content_item
      set archived_at = null,
          archived_by = null
    where id in (
      select item_id from page_section where page_id = p_item_id
    )
      and archived_at is not null;
  end if;

  insert into audit_log (actor_id, action, entity_kind, entity_id)
  values (p_actor, 'restore', v_kind::text, p_item_id::text);
end;
$$;
```

```sql
create or replace function delete_content(
  p_item_id uuid,
  p_actor uuid
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_kind content_kind;
  v_path text;
begin
  select kind, path
    into v_kind, v_path
  from content_item
  where id = p_item_id
  for update;

  if v_kind is null then
    raise exception 'item % not found', p_item_id;
  end if;

  if v_kind in ('landing_page', 'page_section', 'settings') then
    raise exception 'fixed item % cannot be deleted', p_item_id;
  end if;

  if exists (
    select 1 from content_version
    where item_id = p_item_id and status = 'published'
  ) then
    raise exception 'item % has been published and cannot be deleted', p_item_id;
  end if;

  if exists (
    select 1
    from approval a
    join content_version cv on cv.id = a.version_id
    where cv.item_id = p_item_id
  ) or exists (
    select 1
    from legal_approval la
    join content_version cv on cv.id = la.version_id
    where cv.item_id = p_item_id
  ) then
    raise exception 'item % has approval evidence and cannot be deleted', p_item_id;
  end if;

  if exists (
    select 1 from section_version_item where item_id = p_item_id
  ) then
    raise exception 'item % is referenced by a section version', p_item_id;
  end if;

  if v_kind = 'service_group' and (
    exists (select 1 from service_version where group_item_id = p_item_id)
    or exists (select 1 from service where group_item_id = p_item_id)
  ) then
    raise exception 'item % is referenced by a service or service version', p_item_id;
  end if;

  delete from content_item where id = p_item_id;

  insert into audit_log (actor_id, action, entity_kind, entity_id, path)
  values (p_actor, 'delete', v_kind::text, p_item_id::text, v_path);
end;
$$;
```

Archive is the normal delete: it unpublishes a live item, or a landing page's live
section, and then marks the item archived in one transaction, so the public change is an
unpublish with its `page:<path>` and `routes` tags; the `unpublish` row names the
archived item. It creates no draft; a restored item returns to `unpublished`, or to the
open draft that survived the archive, and the next `create_draft` copies the latest
published version when no draft is open. Restore only clears the flags; the item is not
live again until an Admin publishes it, and that publish writes its own revalidation
row. A restored item is therefore not a public change, and restore writes no cache tag.
Unpublish and archive share `_unpublish_internal`: unpublish passes drafts on (decision
69), archive passes them off. `delete_content` permanently removes an item that was never
published, carries no approval, is not one of the three fixed kinds that are never
created from the UI (the landing page, its sections and settings) and is referenced by
nothing; a legal page is creatable, so a never-published legal draft may be deleted. It
writes one `delete` audit row and no revalidation row. Historical audit rows survive the
delete, but their `version_id` and `page_id` become null (`on delete set null`);
`entity_id`, `path` and `revision` remain.

```sql
create or replace function revoke_approval(
  p_approval_id uuid,
  p_actor uuid,
  p_note text
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_version uuid;
begin
  update approval
    set revoked_at = now(),
        revoked_by = p_actor,
        revocation_note = p_note
  where id = p_approval_id and revoked_at is null
  returning version_id into v_version;

  if v_version is null then
    raise exception 'approval % not found or already revoked', p_approval_id;
  end if;

  insert into revalidation (tags)
  select distinct array['page:' || page.path]
  from section_version_item svi
  join content_version sv on sv.id = svi.version_id
  join content_publication scp on scp.version_id = sv.id
  join page_section ps on ps.item_id = sv.item_id
  join content_item page on page.id = ps.page_id
  where svi.item_id = (select item_id from content_version where id = v_version);

  insert into audit_log (actor_id, action, entity_kind, entity_id, version_id)
  values (
    p_actor, 'approval.revoke', 'approval', p_approval_id::text, v_version
  );
end;
$$;
```

A revoked approval does not unpublish a version; the public read stops returning the record
because its approval is no longer live. The function therefore revalidates every page
whose live section version references the record. In Phase 1 that is the landing page;
with more composed pages the same join queues each of them, and a record's own page in
Phase 2 adds its `page:<slug>` tag through the same pattern.

### Drafts

```sql
create or replace function create_draft(
  p_item_id uuid,
  p_actor uuid
)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_open uuid;
  v_live uuid;
  v_next integer;
  v_new uuid;
  v_archived timestamptz;
  v_kind content_kind;
  v_key page_section_key;
begin
  select archived_at, kind
    into v_archived, v_kind
  from content_item
  where id = p_item_id
  for update;

  if not found then
    raise exception 'item % not found', p_item_id;
  end if;
  if v_archived is not null then
    raise exception 'archived item % cannot be drafted', p_item_id;
  end if;

  select id into v_open
  from content_version
  where item_id = p_item_id and status in ('draft', 'in_review');

  if v_open is not null then
    return v_open;
  end if;

  select version_id into v_live
  from content_publication
  where item_id = p_item_id;

  if v_live is null then
    select id into v_live
    from content_version
    where item_id = p_item_id and status = 'published'
    order by version_number desc
    limit 1;
  end if;

  update content_item
    set next_version = next_version + 1
  where id = p_item_id
  returning next_version - 1 into v_next;

  if v_next is null then
    raise exception 'item % not found', p_item_id;
  end if;

  insert into content_version (item_id, version_number, status, created_by)
  values (p_item_id, v_next, 'draft', p_actor)
  returning id into v_new;

  if v_kind = 'landing_page' then
    if v_live is null then
      insert into content_seo (version_id) values (v_new);
    else
      insert into content_seo (
        version_id, seo_title, seo_description, seo_noindex, og_image_id
      )
      select v_new, seo_title, seo_description, seo_noindex, og_image_id
      from content_seo where version_id = v_live;
    end if;

  elsif v_kind = 'page_section' then
    select section_key into v_key
    from page_section where item_id = p_item_id;

    if v_key is null then
      raise exception 'section item % has no page_section row', p_item_id;
    end if;

    if v_live is null then
      insert into section_version (version_id, section_key)
      values (v_new, v_key);
    else
      insert into section_version (
        version_id, section_key, heading, intro, body, nav_label,
        eyebrow, primary_label, primary_href, secondary_label, secondary_href,
        cta_label, cta_href, privacy_text, privacy_link_label, image_id
      )
      select v_new, section_key, heading, intro, body, nav_label,
        eyebrow, primary_label, primary_href, secondary_label, secondary_href,
        cta_label, cta_href, privacy_text, privacy_link_label, image_id
      from section_version where version_id = v_live;

      insert into section_paragraph (version_id, sort_order, text)
      select v_new, sort_order, text
      from section_paragraph where version_id = v_live;

      insert into process_stage (version_id, sort_order, title, body)
      select v_new, sort_order, title, body
      from process_stage where version_id = v_live;

      insert into process_assurance (version_id, sort_order, title, body)
      select v_new, sort_order, title, body
      from process_assurance where version_id = v_live;

      insert into faq_item (version_id, sort_order, question, answer, status)
      select v_new, sort_order, question, answer, status
      from faq_item where version_id = v_live;

      insert into contact_next_step (version_id, sort_order, title, body)
      select v_new, sort_order, title, body
      from contact_next_step where version_id = v_live;

      insert into section_version_item (version_id, item_id, item_kind, sort_order)
      select v_new, item_id, item_kind, sort_order
      from section_version_item where version_id = v_live;
    end if;

  elsif v_kind = 'service_group' then
    if v_live is null then
      insert into service_group_version (version_id) values (v_new);
    else
      insert into service_group_version (version_id, title)
      select v_new, title
      from service_group_version where version_id = v_live;
    end if;

  elsif v_kind = 'service' then
    if v_live is null then
      insert into service_version (version_id) values (v_new);
    else
      insert into service_version (
        version_id, group_item_id, title, summary, long_description, sort_order
      )
      select v_new, group_item_id, title, summary, long_description, sort_order
      from service_version where version_id = v_live;
    end if;

  elsif v_kind = 'project' then
    if v_live is null then
      insert into project_version (version_id) values (v_new);
    else
      insert into project_version (
        version_id, title, client, client_need, built, result, category, sort_order
      )
      select v_new, title, client, client_need, built, result, category, sort_order
      from project_version where version_id = v_live;

      insert into project_technology (version_id, sort_order, name)
      select v_new, sort_order, name
      from project_technology where version_id = v_live;

      insert into project_image (version_id, sort_order, media_id)
      select v_new, sort_order, media_id
      from project_image where version_id = v_live;
    end if;

  elsif v_kind = 'proof_figure' then
    if v_live is null then
      insert into proof_figure_version (version_id) values (v_new);
    else
      insert into proof_figure_version (version_id, label, value, prefix, suffix)
      select v_new, label, value, prefix, suffix
      from proof_figure_version where version_id = v_live;
    end if;

  elsif v_kind = 'testimonial' then
    if v_live is null then
      insert into testimonial_version (version_id) values (v_new);
    else
      insert into testimonial_version (version_id, quote, name, role, company)
      select v_new, quote, name, role, company
      from testimonial_version where version_id = v_live;
    end if;

  elsif v_kind = 'client_logo' then
    if v_live is null then
      insert into client_logo_version (version_id) values (v_new);
    else
      insert into client_logo_version (version_id, client_name, image_id)
      select v_new, client_name, image_id
      from client_logo_version where version_id = v_live;
    end if;

  elsif v_kind = 'legal_page' then
    if v_live is null then
      insert into legal_page_version (version_id) values (v_new);
      insert into content_seo (version_id) values (v_new);
    else
      insert into legal_page_version (version_id, label, title, effective_on)
      select v_new, label, title, effective_on
      from legal_page_version where version_id = v_live;

      insert into content_seo (
        version_id, seo_title, seo_description, seo_noindex, og_image_id
      )
      select v_new, seo_title, seo_description, seo_noindex, og_image_id
      from content_seo where version_id = v_live;

      insert into legal_block (version_id, sort_order, kind, text)
      select v_new, sort_order, kind, text
      from legal_block where version_id = v_live;

      insert into legal_block_item (version_id, block_sort_order, sort_order, text)
      select v_new, block_sort_order, sort_order, text
      from legal_block_item where version_id = v_live;

      insert into legal_block_column (version_id, block_sort_order, sort_order, label)
      select v_new, block_sort_order, sort_order, label
      from legal_block_column where version_id = v_live;

      insert into legal_block_row (version_id, block_sort_order, sort_order)
      select v_new, block_sort_order, sort_order
      from legal_block_row where version_id = v_live;

      insert into legal_block_cell (
        version_id, block_sort_order, row_sort_order, column_sort_order, text
      )
      select v_new, block_sort_order, row_sort_order, column_sort_order, text
      from legal_block_cell where version_id = v_live;
    end if;

  elsif v_kind = 'settings' then
    if v_live is null then
      insert into settings_version (version_id) values (v_new);
    else
      insert into settings_version (
        version_id, legal_name, trading_name, country,
        contact_email, contact_phone, contact_phone_hours,
        hours_summary, hours_timezone, footer_note,
        seo_title_suffix, seo_description, seo_og_image_id,
        cta_label, cta_href, site_logo_id,
        nepal_site_url, booking_url, booking_label,
        uk_establishment, home_registry, registration_number,
        head_office_location, legal_form, limited_liability,
        insolvency_information, vat_number
      )
      select v_new, legal_name, trading_name, country,
        contact_email, contact_phone, contact_phone_hours,
        hours_summary, hours_timezone, footer_note,
        seo_title_suffix, seo_description, seo_og_image_id,
        cta_label, cta_href, site_logo_id,
        nepal_site_url, booking_url, booking_label,
        uk_establishment, home_registry, registration_number,
        head_office_location, legal_form, limited_liability,
        insolvency_information, vat_number
      from settings_version where version_id = v_live;

      insert into settings_address_line (version_id, sort_order, line)
      select v_new, sort_order, line
      from settings_address_line where version_id = v_live;

      insert into settings_location (
        version_id, sort_order, name, country, phone, phone_hours
      )
      select v_new, sort_order, name, country, phone, phone_hours
      from settings_location where version_id = v_live;

      insert into settings_location_address_line (
        version_id, location_sort_order, sort_order, line
      )
      select v_new, location_sort_order, sort_order, line
      from settings_location_address_line where version_id = v_live;

      insert into settings_footer_link (version_id, sort_order, label, href)
      select v_new, sort_order, label, href
      from settings_footer_link where version_id = v_live;

      insert into settings_working_hour (
        version_id, day_of_week, sort_order, opens_at, closes_at, is_closed
      )
      select v_new, day_of_week, sort_order, opens_at, closes_at, is_closed
      from settings_working_hour where version_id = v_live;
    end if;

  else
    raise exception 'unknown content kind %', v_kind;
  end if;

  return v_new;
end;
$$;
```

The draft copies the live version's typed row and its child rows. When the item has no
live pointer (after an unpublish, or on a restored item), it copies the latest published
version instead, so unpublishing does not lose the content. A new item with no version gets an empty typed row of the
right kind, which the editor fills; the publish gates refuse it until the required
fields exist. It deliberately does not copy approvals or legal approvals: a new version
needs a new permission.

### Retention helpers

```sql
create or replace function purge_expired_enquiries()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  delete from enquiry
  where created_at < now() - interval '24 months';
  get diagnostics n = row_count;

  insert into audit_log (actor_id, action, entity_kind, affected_rows)
  values (null, 'retention.delete', 'enquiry', n);

  return n;
end;
$$;

create or replace function purge_rate_limit_events()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  delete from rate_limit_event where created_at < now() - interval '7 days';
  get diagnostics n = row_count;
  return n;
end;
$$;

create or replace function purge_enquiry_ip_hashes()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  update enquiry
  set ip_hash = null
  where ip_hash is not null
    and created_at < now() - interval '30 days';
  get diagnostics n = row_count;
  return n;
end;
$$;

create or replace function purge_email_outbox()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  delete from email_outbox
  where (status = 'sent' and sent_at < now() - interval '30 days')
     or (status = 'dead' and created_at < now() - interval '30 days');
  get diagnostics n = row_count;
  return n;
end;
$$;

create or replace function purge_revalidation_rows()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  delete from revalidation
  where status = 'sent' and completed_at < now() - interval '30 days';
  get diagnostics n = row_count;
  return n;
end;
$$;

create or replace function purge_audit_log()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  perform set_config('app.audit_retention', 'on', true);
  delete from audit_log where created_at < now() - interval '12 months';
  get diagnostics n = row_count;
  return n;
end;
$$;

create or replace function purge_sign_in_events()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  delete from sign_in_event where occurred_at < now() - interval '12 months';
  get diagnostics n = row_count;
  return n;
end;
$$;

create or replace function mark_orphan_media()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  update media m
  set deleted_at = now()
  where m.deleted_at is null
    and m.uploaded_at < now() - interval '24 hours'
    and not exists (select 1 from version_media vm where vm.media_id = m.id)
    and not exists (select 1 from approval a where a.evidence_media_id = m.id);

  get diagnostics n = row_count;
  return n;
end;
$$;
```

`purge_audit_log` is the only path that may delete audit rows; the trigger recognises
the transaction-local setting and allows that delete. Every other delete or update
fails. The 24-month enquiry period and 12-month audit period are the PRD's proposals;
D-8's legal answer confirms them. The shorter periods are Leafclutch proposals that D-8
must also confirm: 30 days for the enquiry's `ip_hash` and for outbox rows, 7 days for
rate-limit events.

Content versions are not purged in Phase 1. Published versions are immutable and kept,
so an image referenced by any version is never orphaned and `mark_orphan_media` cannot
delete it. The function only reclaims uploads that no version ever referenced, or that
were detached from a draft before it published. The one exception is the failed-publish
compensation, which marks the promoted rows deleted and removes their copies; those
rows stay until the draft drops the reference. Storage growth is accepted in exchange
for version history that PRD §7 requires.

### Approval expiry

```sql
create or replace function enqueue_expiring_approvals()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  n integer;
begin
  insert into revalidation (tags)
  select distinct array['page:' || page.path]
  from approval a
  join content_version cv on cv.id = a.version_id
  join section_version_item svi on svi.item_id = cv.item_id
  join content_version sv on sv.id = svi.version_id
  join page_section ps on ps.item_id = sv.item_id
  join content_publication scp
    on scp.item_id = ps.item_id and scp.version_id = sv.id
  join content_item page on page.id = ps.page_id
  join content_publication pcp on pcp.item_id = page.id
  where a.expires_on = ((now() at time zone 'Europe/London')::date - 1)
    and a.revoked_at is null
    and page.kind = 'landing_page'
    and page.archived_at is null;

  get diagnostics n = row_count;
  return n;
end;
$$;
```

The two schedules that call this function are an hour apart. One of them is on time;
the other can queue the same page again on the first day the item is hidden. A
duplicate cache purge is harmless, and it is better than a guard that a recent publish
row could suppress.

The read filters `expires_on >= today`, so the item stops being visible the day after
its expiry date. The job runs just after midnight and purges the pages holding it, and
a cache miss alone never keeps an expired quote visible.

## Views

`version_media` unifies every place a site image can attach to a version. The
source columns are the real foreign keys; the view exists so the publish gate,
`mark_orphan_media` and the media worker have one list. Adding an image slot in Phase 2
means adding its source to this view; the gate and the orphan job then cover it without
another change.

```sql
create view version_media as
select version_id, og_image_id as media_id, 'og_image'::media_role as role
from content_seo
where og_image_id is not null
union all
select version_id, image_id, 'about_image'::media_role
from section_version
where image_id is not null
union all
select version_id, image_id, 'client_logo'::media_role
from client_logo_version
where image_id is not null
union all
select version_id, site_logo_id, 'site_logo'::media_role
from settings_version
where site_logo_id is not null
union all
select version_id, media_id, 'project_image'::media_role
from project_image
union all
select version_id, seo_og_image_id, 'og_image'::media_role
from settings_version
where seo_og_image_id is not null;
```

```sql
create view published_content as
select
  ci.id as item_id,
  ci.kind,
  ci.path,
  ci.slug,
  cp.version_id,
  cv.version_number as revision,
  cp.published_at,
  cp.published_by
from content_item ci
join content_publication cp on cp.item_id = ci.id
join content_version cv on cv.id = cp.version_id
where ci.archived_at is null;

create view published_page as
select * from published_content
where kind in ('landing_page', 'legal_page');

create view published_page_seo as
select
  p.item_id, p.kind, p.path, p.version_id, p.revision, p.published_at,
  v.seo_title, v.seo_description, v.seo_noindex, v.og_image_id
from published_page p
join content_seo v on v.version_id = p.version_id;

create view published_legal as
select
  p.item_id, p.path, p.version_id, p.revision, p.published_at,
  v.label, v.title, v.effective_on,
  s.seo_title, s.seo_description, s.seo_noindex, s.og_image_id
from published_page p
join legal_page_version v on v.version_id = p.version_id
join content_seo s on s.version_id = p.version_id
where p.kind = 'legal_page';

create view published_section as
select
  pc.item_id,
  ps.page_id,
  ps.section_key,
  ps.sort_order,
  pc.version_id,
  pc.revision,
  pc.published_at,
  v.heading, v.intro, v.body, v.nav_label,
  v.eyebrow, v.primary_label, v.primary_href,
  v.secondary_label, v.secondary_href,
  v.cta_label, v.cta_href,
  v.privacy_text, v.privacy_link_label, v.image_id
from published_content pc
join page_section ps on ps.item_id = pc.item_id
join section_version v on v.version_id = pc.version_id
where pc.kind = 'page_section';

create view published_service as
select
  s.item_id,
  s.group_item_id,
  s.live_title,
  s.live_sort_order,
  pc.version_id,
  pc.revision,
  v.summary,
  v.long_description,
  v.sort_order
from service s
join published_content pc on pc.item_id = s.item_id
join service_version v on v.version_id = pc.version_id;

create view published_project as
select
  p.item_id,
  p.live_sort_order,
  pc.version_id,
  pc.revision,
  v.title,
  v.client,
  v.client_need,
  v.built,
  v.result,
  v.category,
  v.sort_order
from project p
join published_content pc on pc.item_id = p.item_id
join project_version v on v.version_id = pc.version_id;

create view published_proof_figure as
select pc.item_id, pc.version_id, pc.revision, v.label, v.value, v.prefix, v.suffix
from published_content pc
join proof_figure_version v on v.version_id = pc.version_id
where pc.kind = 'proof_figure';

create view published_testimonial as
select pc.item_id, pc.version_id, pc.revision, v.quote, v.name, v.role, v.company
from published_content pc
join testimonial_version v on v.version_id = pc.version_id
where pc.kind = 'testimonial';

create view published_client_logo as
select pc.item_id, pc.version_id, pc.revision, v.client_name, v.image_id
from published_content pc
join client_logo_version v on v.version_id = pc.version_id
where pc.kind = 'client_logo';

create view published_settings as
select
  pc.version_id,
  pc.revision,
  v.legal_name, v.trading_name, v.country,
  v.contact_email, v.contact_phone, v.contact_phone_hours,
  v.hours_summary, v.hours_timezone, v.footer_note,
  v.seo_title_suffix, v.seo_description, v.seo_og_image_id,
  v.cta_label, v.cta_href, v.site_logo_id,
  v.nepal_site_url,
  v.uk_establishment, v.home_registry, v.registration_number,
  v.head_office_location, v.legal_form, v.limited_liability,
  v.insolvency_information, v.vat_number
from published_content pc
join settings_version v on v.version_id = pc.version_id
where pc.kind = 'settings';

create view published_settings_hours as
select
  h.version_id,
  h.day_of_week,
  h.sort_order,
  h.opens_at,
  h.closes_at,
  h.is_closed
from published_settings p
join settings_working_hour h on h.version_id = p.version_id;

create view media_usage as
select media_id, count(*) as reference_count
from (
  select media_id from version_media
  union all
  select evidence_media_id from approval where evidence_media_id is not null
) refs
group by media_id;

create view orphan_media as
select m.*
from media m
left join media_usage u on u.media_id = m.id
where u.media_id is null and m.deleted_at is null;
```

A public page read is a query on `published_page_seo` and `published_legal` for the
path, followed by `published_section` for that page ordered by `sort_order`. Each
section version is then resolved through `section_version_item`: service groups,
projects, figures and testimonials come from the typed published views, and the
section's images come from `version_media`. The child rows — paragraphs,
stages, assurances, FAQs, next steps, technologies, address lines, and a legal page's
list items, columns, rows and cells — are read by version id and assembled in order.
The API filters expired or revoked approvals and
assembles the contract payload. It never selects from `content_version` without the
publication join.

## RLS, roles and storage

```sql
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'api_runner') then
    create role api_runner login;
  end if;
end;
$$;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'scheduler_runner') then
    create role scheduler_runner login;
  end if;
end;
$$;

grant usage on schema public to api_runner;
grant usage on schema public to scheduler_runner;
grant select, insert, update, delete on all tables in schema public to api_runner;
grant usage, select on all sequences in schema public to api_runner;
alter role api_runner bypassrls;

revoke update, delete on audit_log from api_runner;
revoke update, delete on sign_in_event from api_runner;

revoke all on function publish_content(uuid, uuid, uuid) from public;
revoke all on function publish_page(uuid, uuid, uuid[], uuid) from public;
revoke all on function _publish_version(uuid, uuid, uuid) from public;
revoke all on function unpublish_content(uuid, uuid) from public;
revoke all on function _unpublish_internal(uuid, uuid, boolean) from public;
revoke all on function archive_content(uuid, uuid) from public;
revoke all on function restore_content(uuid, uuid) from public;
revoke all on function delete_content(uuid, uuid) from public;
revoke all on function create_draft(uuid, uuid) from public;
revoke all on function revoke_approval(uuid, uuid, text) from public;
revoke all on function purge_expired_enquiries() from public;
revoke all on function purge_enquiry_ip_hashes() from public;
revoke all on function purge_email_outbox() from public;
revoke all on function purge_rate_limit_events() from public;
revoke all on function purge_revalidation_rows() from public;
revoke all on function purge_audit_log() from public;
revoke all on function purge_sign_in_events() from public;
revoke all on function mark_orphan_media() from public;
revoke all on function enqueue_expiring_approvals() from public;

grant execute on function publish_content(uuid, uuid, uuid) to api_runner;
grant execute on function publish_page(uuid, uuid, uuid[], uuid) to api_runner;
grant execute on function unpublish_content(uuid, uuid) to api_runner;
grant execute on function archive_content(uuid, uuid) to api_runner;
grant execute on function restore_content(uuid, uuid) to api_runner;
grant execute on function delete_content(uuid, uuid) to api_runner;
grant execute on function create_draft(uuid, uuid) to api_runner;
grant execute on function revoke_approval(uuid, uuid, text) to api_runner;

grant execute on function purge_expired_enquiries() to scheduler_runner;
grant execute on function purge_rate_limit_events() to scheduler_runner;
grant execute on function purge_revalidation_rows() to scheduler_runner;
grant execute on function purge_audit_log() to scheduler_runner;
grant execute on function purge_enquiry_ip_hashes() to scheduler_runner;
grant execute on function purge_sign_in_events() to scheduler_runner;
grant execute on function purge_email_outbox() to scheduler_runner;
grant execute on function mark_orphan_media() to scheduler_runner;
grant execute on function enqueue_expiring_approvals() to scheduler_runner;

revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on schema public from anon, authenticated;

alter default privileges in schema public
  revoke all on tables from anon, authenticated;
alter default privileges in schema public
  revoke all on sequences from anon, authenticated;
alter default privileges in schema public
  grant select, insert, update, delete on tables to api_runner;
alter default privileges in schema public
  grant usage, select on sequences to api_runner;

alter table staff enable row level security;
alter table media enable row level security;
alter table content_item enable row level security;
alter table content_version enable row level security;
alter table content_publication enable row level security;
alter table content_seo enable row level security;
alter table page_section enable row level security;
alter table section_version enable row level security;
alter table section_paragraph enable row level security;
alter table process_stage enable row level security;
alter table process_assurance enable row level security;
alter table faq_item enable row level security;
alter table contact_next_step enable row level security;
alter table section_version_item enable row level security;
alter table service_group enable row level security;
alter table service_group_version enable row level security;
alter table service_version enable row level security;
alter table service enable row level security;
alter table project_version enable row level security;
alter table project_image enable row level security;
alter table project_technology enable row level security;
alter table project enable row level security;
alter table proof_figure_version enable row level security;
alter table testimonial_version enable row level security;
alter table client_logo_version enable row level security;
alter table legal_page_version enable row level security;
alter table legal_block enable row level security;
alter table legal_block_item enable row level security;
alter table legal_block_column enable row level security;
alter table legal_block_row enable row level security;
alter table legal_block_cell enable row level security;
alter table settings_version enable row level security;
alter table settings_address_line enable row level security;
alter table settings_location enable row level security;
alter table settings_location_address_line enable row level security;
alter table settings_footer_link enable row level security;
alter table settings_working_hour enable row level security;
alter table legal_approval enable row level security;
alter table approval enable row level security;
alter table enquiry enable row level security;
alter table enquiry_note enable row level security;
alter table rate_limit_event enable row level security;
alter table email_outbox enable row level security;
alter table revalidation enable row level security;
alter table audit_log enable row level security;
alter table sign_in_event enable row level security;
```

There are deliberately no policies for `anon` or `authenticated`. The Supabase Data
API stays off for these tables. `api_runner` is FastAPI's direct connection role and
bypasses RLS; only the FastAPI environment holds its password. The second guard is
therefore that a leaked anon key or a misconfigured Data API cannot read a row.

The role is created here without a password. The password is set outside the
migration, per environment, and stored in the FastAPI secret store.

`scheduler_runner` is the FastAPI scheduler's own role for the `pg_cron`
fallback: it holds usage on the `public` schema plus execute on the nine
retention and expiry functions and nothing else — no table grants at all.
That is enough because every one of those
functions is security definer and deletes as its owner. Its password is set
outside the migration, per environment, like `api_runner`'s. `api_runner` keeps
no execute grant on those functions, so a request-serving connection cannot run
a purge even if it is compromised.

### Storage buckets

```sql
insert into storage.buckets (id, name, public, file_size_limit)
values
  ('media-staging', 'media-staging', false, 4194304),
  ('site-media', 'site-media', true, 4194304),
  ('evidence', 'evidence', false, 4194304)
on conflict (id) do nothing;

create policy "site media public read"
  on storage.objects
  for select
  to anon, authenticated
  using (bucket_id = 'site-media');
```

Only `site-media` has an anon read policy. `media-staging` and `evidence` have none:
FastAPI uploads with the service role and reads them through short-lived signed URLs.
An upload starts in `media-staging`; publishing copies the object to `site-media` and
flips the row, so a draft file has no public URL at all. The three buckets each have a
4MB object limit, matching the request limit the BFF can carry. The bucket insert is
Supabase-specific; the test harness either runs Supabase local or skips this migration.

## Publish invariants and where they live

| Invariant                                                                                                                      | Enforced by                                                        |
| ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| One open draft or in-review version per item                                                                                   | `content_version_one_open` unique index                          |
| Published versions are never updated or deleted                                                                                | `content_version_immutable` trigger                              |
| A published version's typed rows and child rows never change or move to another version                                        | `prevent_published_content_mutation` on every content table      |
| The publication points at a published version of the same item, and its item cannot change                                     | `content_publication_assert` trigger                             |
| An archived item has no publication pointer                                                                                    | `content_item_archive_guard` trigger                             |
| Every page section has its own status, versions and pointer                                                                    | `page_section` and `content_publication` rows                  |
| A page publishes only when every section has a live version                                                                    | `publish_page` and `assert_publishable_version`                |
| A project, figure, testimonial or client logo has an unexpired approval                                                        | `assert_publishable_version` trigger plus API scope checks       |
| A project with images has an approval covering screenshots                                                                     | `assert_publishable_version` trigger                             |
| A client logo's approval covers the mark, and the name when named                                                              | `assert_approval` trigger plus API scope checks                  |
| A legal page has a non-author Admin approver                                                                                   | `legal_approval_assert` and `assert_publishable_version`       |
| A services section has 3–4 groups and a work section 3–6 projects                                                            | `assert_section_counts` trigger plus API                         |
| A proof section has at most 4 figures and testimonials at most 6                                                               | `assert_section_counts` plus API                                 |
| An about section has at least one paragraph                                                                                    | `assert_section_counts` plus `section_paragraph` sort range      |
| An FAQ section outside five to eight published questions warns in the CMS (LP-5 is a Should, PRD §5) | FastAPI/Pydantic warning; the database no longer refuses         |
| A legal list or table block has its items, columns and one cell per column                                                     | `assert_publishable_version` trigger                             |
| The legal identity always carries its legal name, country and working email (PRD §12), with 2–4 address lines for itself and every location; a UK establishment carries its regulation 63 details; the VAT line is absent without a VAT number | `settings_*_address_line` sort range, `assert_publishable_version`, and the read (null renders nothing) |
| A set site logo is promoted before publish; a null logo renders the repository asset                                           | `version_media`, the settings image gate, Next fallback          |
| A project has 0–3 images; about, OG and logo images 0–1                                                                      | `project_image` sort range and the image columns                 |
| A section row uses only the columns its key allows                                                                             | `section_version` key checks and the child-table triggers        |
| Media type, size, alt, bucket and pixel guard                                                                                  | `media` checks plus upload validation                            |
| A site image is public only when a published version references it                                                             | promotion gate in `assert_publishable_version` plus media checks |
| Media referenced by any version is never deleted                                                                               | the four image foreign keys and `mark_orphan_media`              |
| Live service titles are unique                                                                                                 | `service_live_title_key` unique index                            |
| A service group is live before its services                                                                                    | `sync_live_projection` trigger                                   |
| A project's live order is the published version's order                                                                        | `sync_live_projection` trigger                                   |
| A group with live services cannot be unpublished                                                                               | `guard_group_unpublish` trigger                                  |
| The last active Admin cannot be removed                                                                                        | `staff_lock_writes` and `staff_last_admin` triggers              |
| Enquiries move new → in progress → closed                                                                                    | `enquiry_status_flow` trigger                                    |
| Every enquiry attempt is rate limited                                                                                          | API writes `rate_limit_event` before the checks                  |
| Enquiry field limits and consent format                                                                                        | `enquiry` checks plus Pydantic                                   |
| Expired approvals leave the cache within five minutes, or a day at worst                                                       | expiry job plus a 24-hour maximum age                              |
| Audit rows are append-only                                                                                                     | `audit_log_append_only` trigger                                  |
| Sign-in attempts are kept 12 months                                                                                            | `purge_sign_in_events` plus the 12-month retention; `api_runner` has no update or delete, and only the security-definer purge deletes |
| The `pg_cron` fallback runs every retention and expiry function                                                              | `scheduler_runner` execute grants; each function is security definer |
| Hero has both CTAs; five nav labels; About non-empty; unique SEO; privacy note and live notice; cookies match `cookies.json` | FastAPI/Pydantic and the publish service                           |
| Contact phone has staffed hours; locations real                                                                                | FastAPI/Pydantic and the column checks                             |

The split is deliberate: SQL keeps the structural rules that must survive any client,
and FastAPI keeps the rules that need copy, cross-item checks or the current page.

## Retention and scheduled jobs

| Job                            | Cadence                   | Action                                                                                                   |
| ------------------------------ | ------------------------- | -------------------------------------------------------------------------------------------------------- |
| `enqueue_expiring_approvals` | 23:05 and 00:05 UTC daily | Revalidate pages whose approval expired yesterday, within five minutes of London midnight in GMT and BST |
| `purge_expired_enquiries`    | 02:05 UTC daily           | Delete enquiries older than 24 months; notes and outbox cascade                                          |
| `purge_rate_limit_events`    | 02:15 UTC daily           | Delete rate limit events older than 7 days                                                               |
| `purge_revalidation_rows`    | 02:25 UTC daily           | Delete sent revalidation rows older than 30 days                                                         |
| `purge_audit_log`            | 02:35 UTC daily           | Delete audit rows older than 12 months, through the retention setting                                    |
| `purge_enquiry_ip_hashes`    | 02:45 UTC daily           | Null the enquiry `ip_hash` after 30 days                                                               |
| `purge_sign_in_events`       | 02:50 UTC daily           | Delete sign-in attempts older than 12 months                                                             |
| `purge_email_outbox`         | 02:55 UTC daily           | Delete sent and dead outbox rows after 30 days                                                           |
| `mark_orphan_media`          | 03:05 UTC daily           | Mark media with no references for object deletion                                                        |

```sql
select cron.schedule(
  'expiring-approvals-bst', '5 23 * * *',
  $$select enqueue_expiring_approvals();$$
);
select cron.schedule(
  'expiring-approvals-gmt', '5 0 * * *',
  $$select enqueue_expiring_approvals();$$
);
select cron.schedule(
  'purge-expired-enquiries', '5 2 * * *',
  $$select purge_expired_enquiries();$$
);
select cron.schedule(
  'purge-rate-limits', '15 2 * * *',
  $$select purge_rate_limit_events();$$
);
select cron.schedule(
  'purge-revalidation', '25 2 * * *',
  $$select purge_revalidation_rows();$$
);
select cron.schedule(
  'purge-audit', '35 2 * * *',
  $$select purge_audit_log();$$
);
select cron.schedule(
  'purge-enquiry-ip-hashes', '45 2 * * *',
  $$select purge_enquiry_ip_hashes();$$
);
select cron.schedule(
  'purge-sign-in-events', '50 2 * * *',
  $$select purge_sign_in_events();$$
);
select cron.schedule(
  'purge-email-outbox', '55 2 * * *',
  $$select purge_email_outbox();$$
);
select cron.schedule(
  'mark-orphan-media', '5 3 * * *',
  $$select mark_orphan_media();$$
);
```

`pg_cron` runs in UTC on Supabase, and its `cron.timezone` is a postmaster setting the
project cannot rely on changing. The two expiry schedules solve the BST shift without
it: at 23:05 UTC it is 00:05 in BST, and at 00:05 UTC it is 00:05 in GMT. One run is
always on time; the other may queue the same page again, and a duplicate cache purge is
harmless.

If `pg_cron` is not enabled on the Supabase plan, the `0017_jobs` revision is skipped
and the same functions run from a FastAPI scheduler connecting as
`scheduler_runner`. The cadence and the SQL stay the same; only the caller changes.

The email and revalidation workers are FastAPI processes, not `pg_cron` jobs. They
claim rows with `for update skip locked`, so several workers can run without taking
the same email twice:

```sql
select id
from email_outbox
where status in ('pending', 'failed')
  and next_attempt_at <= now()
order by next_attempt_at
limit 20
for update skip locked;
```

The revalidation worker uses the same pattern. A dead row stops retrying after the
configured attempts and alerts the named owner.

The media object deletion worker reads rows with `deleted_at` set and no references,
removes the object from the bucket, then deletes the row. It is separate from the
database because storage deletion is an HTTP call, not SQL. A 404 from storage counts as
success: a failed-publish compensation may already have removed the object while the
row waited for its draft to drop the reference. The worker deletes the row only when
`version_media` and `approval` no longer reference it.

## Fitting the rest of the site

Phase 1 builds one composed page, the legal pages and the records behind them. The
schema is shaped so the Phase 2 features extend it instead of replacing it. The
extension points are the version spine (`content_item` → `content_version` →
`content_publication`), `content_seo` for anything that renders as a page, one typed
version table per kind, and `version_media` for images.

| Phase 2 feature | What it adds | What it does not need |
| --- | --- | --- |
| Service and project pages | A `path` on each record (for example `/services/<slug>`), a `content_seo` row per version, their kinds in `published_page` and `/routes` | A new table, or a change to the spine or the publish functions |
| Blog posts and careers listings (AD-12) | New `content_kind` values and their version tables, paths, `content_seo`, image slots in `version_media` | A second content system; the state machine, approvals and cache tags are shared |
| Scheduled publishing (AD-12) | `content_version.scheduled_for` and a worker that calls the publish function | A new status value; the version waits in `in_review` |
| A second composed page | A `page_kind` value and any new `page_section_key` values; sections, versions, order and publishing are already per page | A change to `page_section` or `publish_page` |
| A header nav beyond the five section labels | A `nav_item` table, or a nav section read from settings | A change to `section_version.nav_label`; Phase 1 keeps the labels on sections |
| Careers applications | Their own tables | Reusing `enquiry`; an application is not an enquiry |
| A new approval subject or scope | Enum values | A change to `approval` or the publish gate |
| Another image slot | A column or child table, plus one line in `version_media` | A change to the publish gate or the orphan job |

Two changes are not additive, and both are outside Phase 1:

- **Locales.** `content_item.path` is unique on its own. A second language makes the key
  `(path, locale)` and every read filters by locale. The PRD leaves multi-language out
  of scope; if it is ever approved, that is a deliberate migration, not a surprise.
- **A composed page with a different section vocabulary** still needs
  `page_section_key` values, so the enum grows. It is a migration, but the data model
  does not change.

The tables for blog posts, careers, taxonomy, navigation and scheduling do not exist on
purpose: the PRD names those features without naming their fields, and inventing columns
now would lock in a guess. What Phase 1 owes them is the shape above, not a placeholder.

> `AGENTS.md` confirms FastAPI, SQLAlchemy and Pydantic for this build. They replace
> the PRD §9 recommendation of Next.js route handlers, Prisma and Zod. Server-only
> database access, RLS, published-only reads, Supabase Storage and on-demand
> revalidation still match PRD §9.

Backups, the three environments, monitoring, DNS and email deliverability are outside
`DATABASE.md` and belong in requirements/runbook.

## Migrations

Alembic is the source of truth. The SQL above is split into these revisions:

| Revision                  | Contents                                                                                                                                                                                                   | Downgrade                            |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `0001_extensions_enums` | Extensions and all enum types, including the `site_logo` role                                                                                                                                                                              | Drop enums only; extensions stay |
| `0002_staff`            | `staff`, last-Admin statement and row triggers, timestamp trigger                                                                                                                                                           | Drop table and functions             |
| `0003_media`            | `media`, media immutability trigger                                                                                                                                                                      | Drop table and trigger               |
| `0004_content_core`     | `content_item`, `content_version`, `content_publication`, `content_seo`, their six indexes, and the version, publication, archive and content-immutability functions and triggers                                                                                                             | Drop tables and functions            |
| `0005_page_sections`    | `page_section`, `section_version`, `section_paragraph`, the four section child tables and their triggers, `section_version_item`                                                                        | Drop tables and triggers             |
| `0006_services`         | `service_group`, `service_group_version`, `service_version`, `service`, their triggers and indexes                                                                                                 | Drop tables and triggers             |
| `0007_projects`         | `project_version`, `project_image`, `project_technology`, `project`, their triggers and indexes                                                                                                                            | Drop tables and triggers             |
| `0008_proof`            | `proof_figure_version`, `testimonial_version`, `client_logo_version`, their triggers                                                                                                                 | Drop tables and triggers             |
| `0009_legal`            | `legal_page_version`, `legal_block`, its item, column, row and cell tables, their triggers                                                                                                                               | Drop tables and triggers             |
| `0010_settings`         | `settings_version` (with legal-identity, booking, hreflang and logo columns), `settings_address_line`, `settings_location`, `settings_location_address_line`, `settings_footer_link`, `settings_working_hour`, their triggers                                                                                                                      | Drop tables and triggers             |
| `0011_approvals`        | `legal_approval`, `approval`, approval triggers                                                                                                                                                        | Drop tables and triggers             |
| `0012_enquiries`        | `enquiry`, `enquiry_note`, `rate_limit_event`, status triggers                                                                                                                                       | Drop tables and triggers             |
| `0013_delivery`         | `email_outbox`, `revalidation`                                                                                                                                                                         | Drop tables                          |
| `0014_audit`            | `audit_log`, `sign_in_event`, the `audit_log` append-only trigger, and the sign-in purge                                                                                                                                                                         | Drop table and trigger               |
| `0015_publish`          | Publish, page publish, unpublish (public wrapper and internal helper), archive, restore, delete, draft, projection, approval, section-item, site-image, enquiry, audit, retention and expiry functions and triggers; views, including `staff_account` and `published_settings_hours`; regulation 63 gates (the FAQ 5–8 rule is a CMS warning, not a gate) | Drop functions, triggers and views   |
| `0016_rls_storage`      | Roles, grants (including schema usage for `api_runner` and `scheduler_runner`), RLS (including the working-hour and sign-in tables), three buckets and the public read policy                                                                                                                                               | Revoke and drop policies (dev only)  |
| `0017_jobs`             | `pg_cron` schedules, including the two London-midnight expiry runs and the sign-in purge                                                                                                                                       | Unschedule jobs                      |

The order matters because the table triggers call functions created in their own
revision or earlier, and the publish functions read `revalidation` and `audit_log`.
`prevent_published_content_mutation` lives in `0004`; each table revision attaches it.
The migration files use `op.execute` for functions, triggers, views, RLS and storage;
plain tables use SQLAlchemy operations so `alembic check` can compare the models.

```bash
cd api
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

Rules for every migration:

- One logical change per revision. A revision that adds a column and backfills it is
  two revisions when the table is large.
- Additive first: add nullable columns, backfill, then set `not null` and add the
  constraint. Drop only after the API no longer reads the field.
- Enums are extended with `alter type ... add value` in their own migration. A new
  value is not used in the same transaction that adds it. Nothing here has migrated
  yet, so `0001` carries the known value (`site_logo`) directly; the
  rule bites on the next value after scaffolding.
- Long indexes use `create index concurrently` in an `autocommit_block`; the initial
  greenfield indexes do not need it.
- Destructive changes never run automatically in production. Take a backup, run
  forward, and keep the rollback plan outside the migration.
- The production database is migrated before the new API deploy, and the API must
  still read the previous shape during the deploy window.
- Development, staging and production each run their own migrations against their own
  Supabase project. Production data is never copied to development or previews.
- `auth.users` and `storage` schemas belong to Supabase. Alembic only manages
  `public`; the test harness creates the minimal `auth.users` and `storage.buckets`
  objects or uses Supabase local.

### Migration tests

- `upgrade head` on an empty database, `downgrade base`, `upgrade head` again.
- `alembic check` reports no model drift.
- The publish function tests run inside a transaction and roll back.
- The anonymous test connects as `anon` and as `authenticated` and gets a permission
  error or zero rows for every table and view.
- `api_runner` can read a published page and cannot see a draft through the views
  (the view's `published_content` join is the filter, not RLS).
- Publishing without an approval fails; publishing a legal page without an approver
  fails; demoting the last Admin fails; a published version cannot be edited.
- `publish_page` publishes ten section versions and the page in one transaction; a
  section left in draft keeps its previous published version, and a page whose section
  has never published is refused.
- `unpublish_content` deletes the pointer and creates a draft for the item, reusing an
  existing open draft; a landing-page unpublish leaves drafts for the page and its ten
  sections (created or reused), so `publish_page` can publish the page again. A plain
  unpublish on an item with no pointer creates no draft.
- `archive_content` creates no draft; a restored item is `unpublished`, or the open draft
  that survived the archive, until an Admin publishes it. `delete_content` removes a
  never-published item with one `delete` audit row and no revalidation row, and refuses
  an item of one of the three fixed kinds, a published or approved item, and an item
  referenced by a section version or a service (or its version), each with a distinct
  message.
- `publish_content` refuses a landing page; a draft copies the section row, its
  paragraphs, technologies, address lines and legal block children, plus its references;
  a published section version cannot gain a reference or edit its copy.
- A new item's first draft has an empty typed row; the publish gate refuses it until
  the required fields exist.
- A client logo publishes with an approval carrying `mark`, and is refused without one;
  a `client_name` claim needs the name scope.
- A project's published `sort_order` becomes `project.live_sort_order`, and the work
  section reads that order rather than the reference.
- A legal page with `effective_on` null resolves to the London publish date; a set date
  is returned unchanged.
- A legal list or table block publishes only when its items, columns and one cell per
  column are present; a table row cannot be attached to a list block, and a paragraph
  cannot be attached to a section other than About.
- A settings version publishes only with its legal name, country and working email
  (PRD §12) plus two address lines for the legal identity, and a location with
  two of its own; each of the three identity fields is refused null in turn.
- A settings version with `uk_establishment` true is refused without its regulation
  63 details and publishes with them; a null `vat_number` stays a null VAT field.
  `nepal_site_url`, `booking_url` and `booking_label` store values while staying
  out of `published_settings`.
- A settings version accepts a split Monday and a closed day, and refuses a reversed
  interval and both half-open intervals under one shape check; `create_draft`
  copies the rows and `published_settings_hours` reads the live ones. A set `site_logo_id` appears in
  `version_media` as `site_logo` and the publish gate refuses it staged; an
  evidence row is refused as the logo.
- An FAQ marked `draft` is absent from the published FAQ list, and its neighbours keep
  their `sort_order`.
- An FAQ section publishes with four, five, eight and nine published questions alike;
  the database refuses none of them, and a `draft` question does not count. The
  five-to-eight rule is a FastAPI/Pydantic CMS warning (LP-5 stays a Should).
- A project with a staged image fails to publish until the image is promoted, and the
  same project publishes once it is. An evidence row cannot be attached to a version,
  and a site image cannot point at the evidence bucket.
- A live service titled `__other__` fails the `service_title_reserved` check; the API
  rejects it earlier with a field error.
- Moving an enquiry to `in_progress` leaves `first_replied_at` null; setting it once
  succeeds and a second value is refused.
- `/routes` and the legal `updated_on` use `(published_at at time zone 'Europe/London')::date`;
  a 23:30 UTC publish in BST returns the next UK day.
- Archive unpublishes a live item, or a landing page whose section pointer is live while
  its own is not, and queues its page tag; `docs/runbooks/database-validation.sql` covers
  the page-pointer-absent case. Restore clears the flags and publishes nothing.
- Unpublish deletes the pointer and creates a draft; a landing-page unpublish leaves
  eleven drafts (created or reused). A permanent delete removes only a never-published
  item and writes one `delete` audit row.
- The expiry job queues a page whose approval expired yesterday; a second schedule may
  queue it again, a duplicate that the 24-hour cache ceiling makes harmless.
- `purge_enquiry_ip_hashes` nulls only the old hash, `purge_email_outbox` deletes only
  sent or dead rows older than 30 days, and both leave the enquiry itself intact.
- Retention functions delete only the intended rows; the audit purge bypasses the
  append-only trigger only through the retention setting. `scheduler_runner`
  executes the retention and expiry functions while `api_runner` cannot.
- The scheduler fallback survives `public` losing schema usage: inside a transaction that
  is rolled back, `revoke usage on schema public from public`, then `set role
  scheduler_runner` still executes one retention function through its own explicit
  schema-usage grant, while `set role api_runner` is refused the same function. The
  test connects as a superuser, which bypasses privilege checks, so both attempts must
  use `set role`. `api_runner` keeps its own explicit usage grant, so its refusal proves
  the missing EXECUTE grant — the privilege separation — rather than schema resolution.
- A success and a failure `sign_in_event` are stored; a row older than 12 months is
  purged and a fresh one stays. `api_runner` can insert a sign-in row but cannot
  update or delete one, while the security-definer purge still deletes. No `preview_token` table exists.

## Bootstrap

Migrations create structures, not content. After the first Admin is invited in
Supabase Auth, a one-off command creates the staff row and the empty content items:

1. Find the `auth.users` row by email; fail if it does not exist.
2. Insert `staff` with `role = 'admin'` if no staff row exists. The last-Admin trigger
   permits the first one.
3. Insert the settings singleton and its first draft.
4. Insert the landing page at `/` and its first draft.
5. Insert the ten section items and their `page_section` rows in PRD §5 order: hero,
   proof, services, not sure, work, process, about, testimonials, FAQs, contact. Each
   gets a first draft through `create_draft`; the `page_section` row must exist first.
6. Insert legal page drafts at `/privacy`, `/cookies`, `/accessibility` and `/terms`.
7. Insert no services, projects, figures, testimonials or client logos, and no copy.

The command is idempotent and uses `on conflict` on paths and the settings singleton.
It publishes nothing: the privacy notice and the legal pages go live when their copy
and approval exist, and the landing page waits for every section and the content gates.
The empty drafts are the editor's starting point, not placeholder copy.

Each first draft is created through `create_draft`, which inserts an empty typed row of
the right kind. If a bootstrap inserts a version directly, the after-insert trigger
bumps `content_item.next_version`, so the next draft cannot reuse the number.

```bash
cd api
uv run python -m app.cli bootstrap --admin-email hello@example.com
```

The bootstrap is a CLI, not a migration, because it needs a real `auth.users` row and
an actor for `created_by`. A migration that invented a system user would put a fake
staff member in the audit trail.

## Reading a page

The public read is deliberately boring:

1. `select * from published_page_seo where path = $1;` for the landing page, or
   `published_legal` for a legal page.
2. Read `published_section` for the page, ordered by `sort_order`.
3. For each record-backed section, read `section_version_item` for the section version:
   service groups, projects, figures and testimonials. Resolve each through the typed
   published views; drop archived, unpublished, expired-approval and revoked-approval
   rows. Work is ordered by `published_project.live_sort_order`; services are grouped
   and ordered by `published_service.live_sort_order`.
4. Read `version_media` for the page's OG image, the about section's image, the
   site logo and each client logo. Every one is `visibility = 'public'`, because
   the publish gate refuses the version otherwise; the returned URL is
   `/media/<object_path>`.
5. For the process section, read `process_stage` and `process_assurance` by version id.
   For the about section, read `section_paragraph`. For the contact
   section, read `contact_next_step`. For the FAQ section, return only `faq_item` rows
   whose `status` is `published`, in `sort_order`. A project's `project_technology`
   rows and a legal page's block children are read the same way, by version id.
6. Assemble the contract payload; compute `form.services` from `published_service`
   joined to a published group.

The `/routes` call reads `published_legal` and `published_page` and returns `path`,
`kind`, the legal `label` from `legal_page_version`, `(published_at at time zone 'Europe/London')::date` as `lastmod`, and the page's `seo_noindex`. The legal
`updated_on` uses the same expression, so both are UK calendar dates regardless of the
server's session timezone. The `/settings` call reads `published_settings` and its
locations, footer links, working hours and logo. No public query touches `content_version` without
`content_publication`, `enquiry`, `approval`, `audit_log` or `media` rows outside
`site-media`. A preview is the one read that uses a signed URL from `media-staging`;
that read is staff-only and `no-store` (see Preview below).

### Preview is authenticated-only

There is no `preview_token` table (SE-12). A preview is the public payload shape
with drafts in place of published versions, served `no-store` with an
`X-Robots-Tag: noindex` header to a staff session only: the Next `/preview` route
reads the session cookie, forwards the bearer, and FastAPI checks the staff role
on every request. The reason for the path taken: every approver is already staff
under invite-only MFA with a 12-hour idle expiry, so a shareable bearer would add
issuance, revocation and cleanup for no Phase 1 reader, and a leaked link would
outlive the session that created it. SE-12's private, not-cached and not-indexed
demands are met by that session plus the headers, not by a token lifecycle.
Staged media inside a preview is a short-lived signed URL scoped to that session,
never a public path. `CONTRACT.md` already describes this shape, so it is
unchanged.

## Notes for requirements.md

- `first_replied_at` is an explicit "reply sent" action, not a status change. Moving an
  enquiry to `in_progress` is triage only; SM-3 measures from `created_at` to
  `first_replied_at`, which is write-once.
- The media deletion worker treats a storage 404 as already deleted. A failed-publish
  tombstone waits until its draft drops the image reference, then the row is removed; a
  missing object must not stop that cleanup.
- The admin must not offer `__other__` as a service title. The API rejects it and the
  live `service` table has a check.
- A page publish takes the section versions the Admin is publishing. A section left in
  draft keeps its last published version live; a section that has never published blocks
  the page. Section status `in_review` means ready to publish; an Admin publishing their
  own draft may include it under the PRD's skip-review rule (decision 51 is reversed).
- A legal page's `effective_on` null means the London publish date; a set date is shown
  as written and may be in the future.
- An FAQ's `status` is visibility (`published` or `draft`), not a workflow state. Draft
  FAQs stay in the published FAQ section and are filtered from the public read. The
  5–8 published-question rule (LP-5, PRD §5) is a Should, so it is a FastAPI/Pydantic
  CMS warning, not a database gate.
- `footer_links` and the SEO default fields are real settings columns: static footer
  links are stored, legal links still come from `/routes`, and SEO defaults fill only
  fields a page omits. A page's own values win.
- A client logo is a content kind with an approval; D-9 decides whether any page shows
  one. A page with no logo slot does not reference it.
- Products (SV-2, PRD §7) are out of scope by explicit decision: no product kind,
  table, view, slot or approval subject is modelled. Reintroducing products requires
  a new `content_kind`, a typed table, a PRD/D-3 decision and a migration.
- Preview is staff-session-only; there is no token to issue, expire or revoke.
- Sign-in attempts live in `sign_in_event` for 12 months; the admin audit surface
  reads both that table and `audit_log`.
- The version row has no content. Every read and write of a draft or a published
  version must go through the kind's typed table and its child rows, in the same
  transaction as the version row. A version insert without its typed row is a bug, not
  a valid empty draft; the first draft is created by `create_draft`, which inserts the
  empty typed row.
- `content_seo` is the one home for a page's SEO title, description, noindex and OG
  image, for the landing page and every legal page now, and for service, project and
  blog pages in Phase 2. A page version without it fails the publish trigger. The
  unique title across live pages is a FastAPI rule; the API must check it before it
  calls the publish function.
- Cache tags are `page:<path>`, never a fixed `/`. A section publish or unpublish
  resolves its owning page's path, and an approval revoke queues every live page whose
  live section version references the record.
- The admin's "last changed by" for a content item is
  `coalesce(updated_by, created_by)` on the open version, or `published_by` and
  `published_at` when there is no open version. Media has `uploaded_by`/`uploaded_at`;
  deletion and promotion write an audit row. Enquiry triage and reply write audit rows;
  the enquiry table does not store an actor.
- The PRD data model is §8. §12 is UK legal and compliance; cite it only for the legal
  identity rules, not for the data model.
- Table count. 46 base tables against the PRD's "about 10" rationale (PRD §9):
  typed storage is deliberate — every list is a child table, so no column holds a
  document — and the cost is more migrations, more joins and a longer schema
  document. That trade-off is recorded here for sign-off before scaffolding.

## Validation performed

The SQL in this document as it stood before decisions 69 and 70 was applied to a scratch
PostgreSQL 18 database on 27 November 2026, with minimal `auth.users`, `auth.mfa_factors`
and `storage` stubs. The run:

- read `mfa_status` and `last_sign_in_at` from `staff_account` and refused to demote the
  last active Admin;
- published settings from typed columns and read them back through `published_settings`;
- created the page and ten section items, published all ten with `publish_page`, and
  read the hero heading from `section_version`;
- copied a section's row, its four process stages and its three references into a new
  draft;
- changed the hero draft and published the page without it, leaving the old hero live;
  then published the hero draft and moved only its own pointer;
- returned one published FAQ from a section holding a published and a draft item;
- refused an edit to a published `section_version`;
- refused a process stage attached to the hero section, and a hero row carrying the
  contact privacy fields;
- published a client logo with a `mark` approval and refused one carrying only the name;
- refused a legal page without a non-author approver, then refused one without SEO, then
  stored a null effective date and a named future one; both legal pages appeared in
  `published_page_seo` with their own titles;
- refused to publish a project with a staged image until it was promoted, and projected
  its `sort_order` into `project.live_sort_order`;
- refused an evidence file as a site image;
- refused the reserved service title `__other__` on a draft, and a group unpublish while
  it had live services;
- refused a `page_section` item committed without its `page_section` row;
- left `first_replied_at` null on triage, recorded it once on a reply, and refused an
  overwrite; nulled a 40-day-old `ip_hash` and deleted a 40-day-old sent outbox row;
- queued the page once from an approval that expired yesterday, through the section
  version join, and queued the page again when an approval was revoked;
- published two composed pages at `/` and `/about`, each with its own `hero`, `about`
  and `faqs`, and saw the cache tags `page:/` and `page:/about`;
- archived the page, saw all ten sections archived and unpublished, and restored them;
- denied `anon` and `authenticated` a read, and allowed `api_runner` to read
  `published_content`, `staff_account` and `version_media`.

The unpublish split (`_unpublish_internal` and the `unpublish_content` wrapper),
`archive_content`, `restore_content` and `delete_content` were applied to a fresh scratch
PostgreSQL 18.7 database on 27 November 2026, with the runbook's auth/storage stubs and block
56 (`cron.schedule`) skipped because the image has no `pg_cron`; 46 base tables were
created. The run:

- published the page and ten sections through `publish_page`, unpublished it, and saw
  the 11 live pointers removed, 11 drafts left and one revalidation row tagged `page:/`
  and `routes`; then republished it from those drafts;
- unpublished a service, removing the pointer, keeping the published version, leaving one
  draft and writing the audit row; unpublished it again, which wrote a second audit row
  without a new draft; and reused an existing open draft instead of creating another,
  removing the pointer and writing a third audit row;
- archived a service and the page with no draft created, `archived_at` and `archived_by`
  set, the pointer gone, one audit row and one `page:/` cache tag each; restored both,
  clearing the flags and leaving nothing live, no new draft, no pointer and no new cache
  tag;
- deleted a never-published service, removing the row and its versions, writing one
  audit row and no revalidation row; deleted a legal-page draft twice, reusing the path
  in between;
- refused a delete of a published item, each of the three fixed kinds (landing page,
  section, settings), an item with approval evidence, an item referenced by a section
  version, and a group with a service version, each with its named message and the row
  still present.

The commands and expected output are in `docs/runbooks/database-validation.md`; the
fixture and assertions are in `docs/runbooks/database-validation.sql`.

The broader fixture behind the first list is still uncommitted. The unpublish, archive
and delete harness is committed in `docs/runbooks/`, so that half can be re-run before
`api/` is scaffolded.

The Supabase `storage` schema, the `pg_cron` schedules and the real `auth.users` are
stubbed or skipped. They need a Supabase local or staging run before the first deploy.
The FastAPI side still has to implement the object copy that promotes a staged image;
this run exercises the database half only.

The 27 November gap-closure run regenerated `schema.sql` from the document as it then
stood, before decisions 69 and 70 (56 blocks then, the `pg_cron` block skipped as
before), applied it with `stubs.sql` to fresh scratch databases, and ran both suites to a
pass. The document now has 57 blocks; the unpublish split and `delete_content` are
covered by the later run above, not by that gap-closure run. `test-cols.sql` ends `ALL
TESTS PASSED`, covering the product scope exclusion (no `product` enum value, table or
view, and an approval with a `product` subject refused), the legal identity gate (a
null `legal_name`, `country` and
`contact_email` each refused, all three publishing) and the regulation 63 gate
both ways with a null VAT field, the hreflang field,
a split Monday and a closed day with four refused intervals (one reversed, two
half-open), the `site_logo` role with a staged-logo
refusal and an evidence-bucket refusal, stored-but-unpublished booking fields, FAQ
publishes at 4, 5, 8 and 9 with a draft excluded (the 5–8 rule now a CMS warning),
a 13-month-old sign-in purged with the fresh
row kept, `api_runner` refused update, delete and purge execution on
`sign_in_event` while the security-definer purge still deletes, `scheduler_runner`
executing the retention functions that `api_runner` cannot, no `preview_token` table, 46 base tables, zero `jsonb` columns and two
array columns; `test-multi.sql` passes on two composed pages with five FAQs each
and refuses a `product` content item. A direct query confirmed 46 tables, 0
`jsonb` columns and 2 array columns, and `git diff --check` is clean.

## PRD items outside the schema

These PRD requirements are app, ops or legal-copy responsibilities, so this document
does not imply full PRD coverage for them and no tables are added for them:

- AD-10 sign-in slowdown/lock: `sign_in_event` records failures; Supabase Auth or
  FastAPI enforces the lock.
- AD-8 "last changed by" for enquiries and staff: audit-derived, not a column.
- Privacy notice live before the form collects data: publish/launch check.
- Cookie consent and GA4 consent: app-level; D-4 open. The Cookies footer link
  follows decision 52: no optional cookies exist, so there is no preferences
  control.
- Legal block links: `legal_block` supports `h2`, `p`, `ul` and `table` only; URLs
  are plain text unless a link block is approved.
- Accessibility, performance, browser and Lighthouse checks.
- Backups, three environments, monitoring, DNS and email deliverability.
- Analytics events and Search Console.

## Open questions

1. **Data layer confirmation.** SQLAlchemy 2.0 sync + Alembic + psycopg 3 is the
   proposal. The alternative is async SQLAlchemy with asyncpg; it changes the FastAPI
   endpoint style, not the schema. Confirm before scaffolding.
2. **`auth.users` in CI.** The FK is right for Supabase. The test harness must create
   a minimal `auth.users` or run Supabase local; a plain Postgres container does not
   have the schema.
3. **`pg_cron` on the plan.** If the Supabase plan does not include it, the same
   functions run from a FastAPI scheduler connecting as `scheduler_runner`; the
   SQL and cadence stay.
4. **Retention.** 24 months for enquiries and 12 for audit and sign-in attempts are
   the PRD's proposals; D-8's legal answer confirms them. The schema also proposes
   30 days for `ip_hash` and outbox rows and 7 days for rate-limit events; D-8 must
   confirm those, and the privacy notice must state all five periods.
5. **D-7 and D-8 fields.** The settings columns now carry the regulation 63 details
   and the VAT number, with the publish gate and the null-VAT rule, but no values
   are seeded: D-7's answer fills them. The Nepal transfer safeguard and
   representative/DPO fields are still undecided with no columns; adding them is a
   migration and a Pydantic change.
6. **Service group order for Phase 2.** The services section version owns group order in
   Phase 1. If Phase 2 needs a global service-page order, add `sort_order` to
   `service_group_version` rather than a column now.
7. **Approval scope granularity.** One approval can carry several scopes. If clients
   routinely approve the name and the screenshots separately, the API can store two
   rows; the publish gate already accepts any live row covering each claim.
8. **Media object paths.** `<id>.<extension>` keeps paths opaque and stable. If the
   storage provider needs a different layout, only the upload path changes; the media
   row and the `/media/*` rewrite do not.
9. **Screenshot minimum.** `project_image` allows 0–3 images. If `CONTRACT.md` open
   question 5 resolves to 1–3, tighten the count trigger; no table change is needed.
10. **Client logos (D-9).** The schema carries `client_logo` as a content kind, a
    media column and an approval subject, so D-9's data model exists. D-9 still decides
    whether a logo is shown; a render slot means adding it to a section's references and
    to the public payload, not a table change.
11. **Sign-in audit retention.** Resolved: `sign_in_event` carries one row per
    sign-in attempt with a 12-month purge, because Supabase's retention cannot be
    verified from this repository and the 12-month record is a PRD §8 obligation.
    The admin audit surface reads that table alongside `audit_log`.
12. **Products (D-3, SV-2).** Out of scope by explicit decision: no product kind,
    table, view, slot or approval subject is modelled. Reintroducing products
    requires a new `content_kind`, a typed table, a PRD/D-3 decision and a
    migration.
13. **Hreflang locale codes (NF-8).** The hreflang locale codes are unconfirmed
    and not guessed — neither `en-NP` nor `ne-NP` is stored; `nepal_site_url`
    stays the only hreflang field.

Decisions, not open questions: D-12 answered 26 November: no budget field and no
booking link (decision 46). `booking_url` and `booking_label` remain unpublished
placeholders; EN-10 is a Should left undelivered by decision, not an open
decision.

## PRD gap closure

Eight items addressed, plus the product scope exclusion, on 27 November 2026
against `PRD.md`, reusing the typed-storage rules: no JSONB, no second content store, the publication pointer as the only
switch, approvals attach to versions, RLS stays a second guard. Nothing below
invents a value for an open decision; nullable fields, publish gates and comments
carry those instead. Every affected requirement cites its PRD ID or section. The
product scope exclusion is recorded alongside them, not as an addressed item.

Products (SV-2) are out of scope by explicit decision. No product kind, table,
view, slot or approval subject is modelled. Reintroducing products requires a new
`content_kind`, a typed table, a PRD/D-3 decision and a migration.

1. **UK legal identity (PRD §12, D-7).** Nullable `uk_establishment` (not null,
   default false), `home_registry`, `registration_number`,
   `head_office_location`, `legal_form`, `limited_liability`,
   `insolvency_information` and `vat_number` on `settings_version`. Publish gate:
   the legal name, country and working email are always required; when
   `uk_establishment` is true the regulation 63 fields are required too; when
   `vat_number` is null the VAT line is absent. No values seeded. Exposed
   through `published_settings`, copied by `create_draft`, listed in the
   model-at-a-glance, and tested both ways.
2. **Nepal hreflang (NF-8).** Addressed, not closed: nullable `nepal_site_url` on
   the settings version,
   exposed through `published_settings`. The locale codes still need confirmation
   and are not guessed — neither `en-NP` nor `ne-NP` is stored.
3. **Structured working hours (EN-9, PRD §5 and §12).** Version-scoped
   `settings_working_hour` child table: ISO `day_of_week` 1–7, `opens_at`,
   `closes_at`, `is_closed`; split intervals allowed; one shape check requires
   either a closed day with both times null or an open day with both times set
   and `closes_at > opens_at`, so half-open intervals are refused. `hours_summary` stays the display string the contract needs, so
   nothing derived breaks the wire; the rows are additive detail. `create_draft`
   copies them, `published_settings_hours` reads the live ones, and the open
   question of whether EN-9 needs a structured-hours gate is answered no: the
   phone rule stays on the `contact_phone_hours` text.
4. **Header/footer editability (LP-2, PRD §5).** `site_logo_id` media slot on the
   settings version, `site_logo` in `media_role`, included in `version_media`,
   `assert_site_image`, `create_draft`, the promotion gate and
   `published_settings`. Footer details, footer links and the Enquire CTA stay
   editable as before; the PRD names no other footer text field, so none is
   added. `CONTRACT.md` records the slot (logo `0–1`, null renders the
   repository asset).
5. **Booking link (EN-10, D-12).** Addressed as a schema placeholder, not closed:
   `booking_url` and `booking_label` as nullable columns on `settings_version`,
   but unpublished: no publish gate, no seeded value, absent from
   `published_settings`. Decision 46 stays accurate — D-12 was answered on
   26 November with no booking link, so the columns are a placeholder that D-12
   has not approved and the link stays off. EN-10 is a Should left undelivered
   by decision 46, not an open decision; showing
   the link would mean exposing the fields through `published_settings` and
   `CONTRACT.md` at that point. No embed; the link would open in a new tab.
   The budget field is not added. `CONTRACT.md` unchanged.
6. **FAQ count (LP-5, PRD §5).** Addressed, not closed: `assert_section_counts`
   no longer refuses an FAQ section outside five to eight `published`
   `faq_item` rows — LP-5 stays a Should, so the 5–8 rule is a FastAPI/Pydantic
   CMS warning instead of a database gate (see the invariants table). The tests
   publish at 4, 5, 8 and 9 with a draft excluded. If the team separately
   decides LP-5 is a Must, the gate can return; that decision is not made here.
7. **Sign-in audit (AD-7, retention).** `sign_in_event` (`staff_id`,
   `occurred_at`, `ip_hash`, `user_agent_hash`, `outcome`) with a 12-month
   purge, RLS enabled, append-only to `api_runner` (only the security-definer
   purge deletes), and tests for store, access and purge. No passwords, MFA secrets
   or tokens. The alternative — relying on Supabase Auth's audit log — was
   rejected because its retention cannot be verified from this repository and
   the 12-month record is a PRD §8 obligation.
8. **Preview tokens (SE-12).** Decided: authenticated-only, no `preview_token`
   table. Every approver is already staff under invite-only MFA with a 12-hour
   idle expiry, so a shareable bearer would add issuance, revocation and cleanup
   for no Phase 1 reader; SE-12's private, not-cached and not-indexed demands
   are met by the staff session plus `no-store`/`noindex`. Documented under
   Reading a page; `CONTRACT.md` already describes this shape and is unchanged.

No new Alembic revision: everything folds into the existing revisions, whose
table says where. No existing revision was renumbered.

The eight items above were addressed; the product scope exclusion is recorded
separately: products (SV-2) are out of scope by explicit decision, so D-3 no longer covers a
product catalogue or any page slot; reintroducing products requires a new
`content_kind`, a typed table, a PRD/D-3 decision and a migration. Decisions still
open: D-7 (Companies House and VAT values), D-8 (retention sign-off, including the
30-day, 7-day and sign-in periods), D-9 (which proof may be shown, including the
logo slot), D-10 (prices), the hreflang URL and locale codes, the Nepal transfer
safeguard and representative/DPO fields, and LP-5 staying a Should (the 5–8 rule is
a CMS warning unless the team separately decides LP-5 is a Must). D-12 is answered
(no booking link, decision 46): `booking_url` and `booking_label` are unpublished
placeholders; EN-10 is a Should left undelivered by decision 46, not an open
decision.
