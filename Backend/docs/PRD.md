# Leafclutch UK Website — Product Requirements Document

Extracted text of `Leafclutch UK Website — Product Requirements Document (1).pdf`
(29 pages, 24 November 2026). It lives here so no session has to extract the PDF
again.

- The PDF is the source. This file is its text, not a summary or a paraphrase.
- `[[page N]]` marks where page N began in the PDF, so citations to a section or
  a page still resolve.
- Running headers and footers were removed; nothing else changed. Line wrapping
  and table layout are the PDF's, not Markdown's, so read it as text: a table is
  rows of plain lines, not a pipe table.
- PRD §18 holds the open decisions. Read it before choosing a stack, domain,
  analytics, pricing or legal identity.

## Text

```text
Leafclutch UK Website — Product
Requirements Document
Nov 24, 2026 · Sandesh Thapa
Phase 1 launches a single-page UK website with a secure admin panel. The timeline for
each phase is to be planned. Per-service pages, project pages, the blog and careers follow
in Phase 2, and an AI assistant in Phase 3. This document merges the three drafts by
Susan, Rakesh and the shared Google Doc into one plan. Where they disagreed, the
choice and the reason are stated.
1. Goals and success measures
A UK business owner should understand what Leafclutch does within a few seconds, see
real proof of its work, and get in touch easily. Staff must be able to keep the site up to date
without a developer.
Objectives
1. Present the UK branch clearly and professionally, in the existing Leafclutch brand.
2. Explain approved services by the business problems they solve, not by the tools we
use.
3. Show real projects and verified proof only.
4. Make it easy to discuss a project, request a consultation or send an enquiry.
5. Give authorised staff a simple, secure admin panel.
6. Deliver a responsive, accessible, fast and maintainable site that later phases can build
on.
Success measures (targets are proposals until management confirms them)
ID Measure How we measure it Proposed target
SM-1 Qualified
enquiries
Enquiries in the admin panel that match
the target audience, after removing
spam
8 per month after 3
months
SM-
2
Form
completion
Form submissions ÷ visitors who start
the form
8%
[[page 1]]
2. Audience and positioning
The site targets direct UK business clients. Agency white-label partnerships are not part
of this website's positioning.
Who visits (assumption, to confirm). Owners, managers and marketers at UK startups
and small to mid-sized businesses. They need a website, software, an app or some
automation. Many are not technical and some are outsourcing for the first time. Whether
mid-market and larger organisations are also a priority is an open decision (section 18).
What they need to see. Buyers working with a team based in Nepal want proof that it is
safe to do so:
what we build and the result they get, in plain words;
real work and real people behind it;
who owns the code and how handover works;
how their data is protected;
when we are reachable in UK hours, and how fast we reply.
How we talk. Lead with the client's problem and the outcome, then the service, and only
then the technology. British English throughout. No generic agency slogans and no claim
we can't back up.
Proposed positioning line (to confirm): experienced software and product engineering
from Nepal, with UK-standard accountability, a named team and full client ownership of
the code.
ID Measure How we measure it Proposed target
SM-
3
Response time First human reply, from the enquiry
timestamp
Within 1 UK working
day
SM-
4
Honest proof Every published name, logo, quote,
figure and screenshot has written
approval
100% at launch and
after
SM-
5
Quality Lighthouse and accessibility checks in
section 13
All pass before
launch
[[page 2]]
3. Scope and phases
Phase 1 keeps the public site to one landing page, but the backend and admin panel are
built properly, so later phases add pages without rework.
Not included unless separately agreed: client accounts or portals; payments,
subscriptions or checkout; a CRM or applicant-tracking system built from scratch; multi-
language content; marketing automation or personalisation; price calculators; AI-written
or auto-published content; paid-media landing pages.
Why a single page first. Susan's and Rakesh's drafts both start with one page; the Google
Doc launches 8 page types. One page ships sooner and needs less approved copy. The
admin panel and data model are still designed for separate service and project pages, so
Phase 2 is mostly new templates.
Phase What's in it Estimate
Phase 1 — Launch One responsive landing page (section 5).
Privacy notice, cookie information,
website terms and accessibility
statement. Enquiry form with secure
storage and email alerts. Admin panel for
page text, services, projects, media,
enquiries, legal pages and site settings.
SEO, analytics, monitoring, backups.
To be
planned
Phase 2 — Content and
recruitment
Services overview and one page per
service. Work page and one page per
project. Full About page. Blog / Insights
with categories. Careers pages, and on-
site job applications only if privacy and
retention are approved. Scheduled
publishing. CRM or calendar integrations
if a real workflow needs them.
To be
planned
Phase 3 — AI assistant Chat assistant that answers only from
approved company content, says when it
doesn't know, and hands over to a person.
Comes with an AI use policy, privacy and
retention rules, usage limits and cost
controls. The rest of the site must work if
it is down.
To be
planned
[[page 3]]
4. Research: what we take from UK websites
The three drafts reviewed about 40 UK sites between them: Xapner, 123Digi, SMART5 and
IISAW (Susan); KOTA, Cyber-Duck, Blue Frontier, CreativeWeb, WE-DEV, FocusReactive,
Visuable, Digimpact and Madcraft (Rakesh); and a 30-site sample (Google Doc appendix).
We study their approach, not copy their design, prices or claims.
What we take
Grouped services. All of Susan's four sites group services (3–4 groups) instead of one
long list.
Short navigation. 4–8 menu items plus an enquiry button; the footer repeats the main
links, contact details and legal pages.
Proof early. Real figures, work and testimonials near the top (123Digi, IISAW).
Many ways to get in touch. Enquiry buttons in several places, a short form, and a
stated reply time (123Digi promises one working day).
A prompt for unsure visitors.
"Describe your problem" for people who don't know
which service they need (IISAW).
Consistency. The same headings, buttons, cards and spacing everywhere. We copy
that habit, not their colours.
Clear service packaging. Defined deliverables and ongoing care plans (WE-DEV),
outcome-led service explanations (Cyber-Duck, CreativeWeb).
What we avoid
A thin portfolio with only names and one-line descriptions (SMART5).
White-label agency positioning (WE-DEV).
Copying competitor prices. Any package price comes from our own costs.
Promising blanket legal compliance or new services (for example answer-engine
optimisation) before we can deliver and prove them.
Accessibility gaps: 22 of the 28 core UK sites in the Google Doc sample had at least
one serious automated accessibility finding.
5. Landing page structure
The page runs in this order, top to bottom. Every section's text, images and buttons come
from the admin panel.
1. Header — logo, menu, and an "Enquire" button. Sticky on scroll.
[[page 4]]
2. Hero — what Leafclutch does and who it's for, in one headline and one or two lines.
Two buttons:
"Discuss your project" (to the form) and "See our work"
.
3. Proof figures — years, projects delivered, clients. Real numbers only; the row is
hidden if none are approved.
4. Services — in 3–4 categories, each service with a short outcome-led description.
5. Not sure what you need? — a short prompt that takes the visitor to the form to
describe their problem.
6. Featured work — 3–6 approved projects, each with the client need, what we built, the
result (only if real) and screenshots.
7. How we work — 4 stages from first call to handover, plus code ownership, security
and UK-hours contact.
8. About — the company, where it is based, how UK clients are served, and the team (if
approved).
9. Testimonials — only with written client permission; hidden if there are none.
10. FAQs — 5–8 short questions (cost, timeline, ownership, communication, support).
11. Contact — enquiry form, email, UK phone (if staffed), working hours in UK time, and
what happens after you send.
12. Footer — service and section links, contact details, legal company details (section 12),
legal pages, cookie preferences.
Menu (Phase 1): Services, Work, How we work, About, Contact, plus the Enquire button.
Each item scrolls to its section. Blog and Careers join the menu in Phase 2, when those
pages exist.
Separate pages at launch: Privacy notice, Cookie information, Website terms,
Accessibility statement, and a 404 page.
6. Public website requirements
Must = launch blocker. Should = in Phase 1 if time allows, otherwise first update after
launch. Phase 2/3 = later. Every requirement has a pass/fail check.
[[page 5]]
Landing page and navigation
ID Requirement Priority How we check
LP-1 Hero says what Leafclutch does and
who it's for, with two buttons
(enquire, see work)
Must Both visible without scrolling at
375px and 1366px
LP-2 Sections in the order of section 5,
all editable from the admin panel
Must Changing a section in admin and
publishing updates the live page
within 1 minute
LP-3 Proof figures row with real,
approved numbers only
Should Each figure has an approval record;
row hides when empty
LP-4 "Not sure what you need?" prompt
leading to the form
Should Prompt opens the form with the
message field focused
LP-5 FAQs section Should FAQs editable in admin; accessible
accordion (keyboard and screen
reader)
NV-
1
Sticky header with the Phase 1
menu and Enquire button; scrolls to
sections
Must Works with mouse, touch and
keyboard; current section is shown
NV-
2
Mobile menu Must Opens and closes with keyboard
and touch; tap targets at least
44px
NV-
3
Footer with section links, contact
details, legal company details, legal
pages and cookie preferences
Must All links resolve; details match the
privacy notice and Contact section
NV-
4
Clear hover, focus, loading, success
and error states on all controls
Must Visible focus ring on every
interactive element
[[page 6]]
Services and work
Contact and enquiries
ID Requirement Priority How we check
SV-1 Services grouped in 3–4 categories,
each with a short outcome-led
description
Must Menu, section and Phase 2 pages
use the same categories
SV-
2
Software products shown only if
management approves them for UK
sale or demo
Must Product entries can be switched
off in admin
SV-
3
Featured work: client need, what we
built, result (only if real),
technologies, screenshots
Must Every published project has an
approval record (section 7)
SV-
4
If a project has no measurable
result, say what was built instead;
no invented numbers
Must Content review before publish
SV-
5
Testimonials with written
permission only
Should Each quote links to a permission
record
SV-
6
Services overview and one page per
service (problem, what's included,
how we work, timeline, FAQs,
related work, enquiry button)
Phase
2
—
SV-
7
Work page and one page per
project
Phase
2
—
ID Requirement Priority How we check
EN-1 Enquiry buttons in the header,
hero, after services and in the
footer
Must All four go to the form
EN-
2
Short form: name, email, company
(optional), service needed,
message
Must No other required fields; service
list comes from the Services
content
[[page 7]]
Design
ID Requirement Priority How we check
EN-3 Short privacy note beside the form,
linking to the privacy notice. No
marketing opt-in required to send
Must Form can be sent without any
marketing tick box
EN-
4
Validation in the browser and again
on the server, with clear field errors
Must Bad input is rejected by the API
even with browser checks
bypassed
EN-5 Spam protection: honeypot field,
Cloudflare Turnstile and a server
rate limit
Must Bot submissions and floods are
blocked; real users see no puzzle in
normal use
EN-6 On success, say what happens next
and when they'll hear back ("within
1 UK working day")
Must Message shown on screen
EN-7 Confirmation email to the visitor Should Arrives in inbox (not spam) from
the sending subdomain
EN-8 If sending fails, show a clear error
and the direct email address
Must Tested by forcing a server error
EN-9 Contact section shows email, UK
phone (only if staffed), working
hours in UK time
Must Phone hidden in admin if UK hours
are not staffed
EN-
10
"Book a call" link to a calendar
booking page
Should Opens the booking page in a new
tab; no embed before consent
ID Requirement Priority How we check
DS-1 Use the existing Leafclutch logo,
colours, typography and brand
assets; no separate UK brand
Must Design tokens match the current
brand guide
DS-
2
One set of heading, button, card
and spacing styles across all pages
Must All UI built from one component
library
DS-
3
Real screenshots and project
images over generic stock
Should No stock images in Featured work
[[page 8]]
7. Admin panel and content management
The admin panel is part of Phase 1. It lives at /admin in the same app, is not linked from
the public site, is hidden from search engines, and is for Leafclutch staff only.
Access and roles
There is no public sign-up. An Admin invites each person by email and role; the invite link
expires after 7 days and the person sets their own password. Every staff account uses
MFA (an authenticator app). Sessions end after 12 hours of inactivity. Google Workspace
sign-in can replace passwords later if the company approves it.
ID Requirement Priority How we check
DS-
4
Subtle hover and scroll effects only;
nothing important depends on
them; respects reduced motion
Should With reduced motion on, all
content shows without animation
DS-
5
Designed for phones, not shrunk
from desktop
Must Checked at 320, 375, 768, 1024, 1366
and 1440px; no sideways scroll
Action Admin Editor
Sign in Yes Yes
Create and edit drafts (page text, services,
projects, media)
Yes Yes
Preview drafts Yes Yes
Publish, unpublish Yes No
Delete content Yes No
Edit legal pages and approval records Yes No
View and manage enquiries Yes No
Invite, change or remove users Yes No
Site settings (contact details, footer, SEO defaults) Yes No
[[page 9]]
Enquiries are Admin-only because they hold personal data. If sales staff need them, add a
third "Sales" role later. The Google Doc proposed four roles; two are enough for a small
team, and more can be added when the workflow needs them.
What staff can manage
Publishing workflow
1. Any change is saved as a Draft. The live site does not change.
2. An Editor marks it In review when ready. Admins can skip this for their own changes.
3. An Admin checks it in Preview and clicks Publish. The live page updates within 1
minute.
Content What they can do
Page sections Edit text, images, links and buttons for each
landing-page section
Services and products Create, edit, reorder, publish, unpublish
Projects Client need, work done, result, technologies,
screenshots, category, order, approval record
Proof (figures, testimonials, client
logos)
Each item has an approval record: who approved,
when, and an expiry date if the permission has
one
FAQs Create, edit, reorder
Media Upload, replace and remove images; alt text is
required; type and size limits
Legal pages Edit the privacy notice, cookie information, terms
and accessibility statement, with version and
effective date
Enquiries View, change status, add internal notes, export,
delete
Site settings Contact details, working hours, legal company
details, footer links, SEO defaults
[[page 10]]
4. While a published item is being edited, the live version stays exactly as it was until the
new draft is published.
5. Unpublish removes an item from the site and returns it to Draft. Nothing is deleted,
and previous versions are kept.
The public site only reads published content. Projects, testimonials and figures can't be
published without an approval record, and an expired approval hides the item
automatically. Legal pages need an approver who is not the author.
Enquiry workflow
Enquiries move through New → In progress → Closed. The team gets an email for each
new enquiry (without the full message, section 8). The first reply time is recorded for SM-
3. Admins can export or delete one person's enquiries to answer a UK GDPR request.
Admin requirements
ID Requirement Priority
AD-1 Invite-only staff accounts, email + password +
MFA, password reset by email
Must
AD-2 Admin and Editor roles, checked on the server for
every action, not only hidden in the UI
Must
AD-3 Manage page sections, services, projects, FAQs,
media, legal pages and settings
Must
AD-4 Draft → In review → Published, with preview and
version history
Must
AD-5 Approval records for proof items; publishing
blocked without one; expired items hidden
Must
AD-6 Enquiry list with status, notes, export and delete Must
AD-7 Audit log of sign-ins, publish and unpublish, role
changes and deletions
Must
AD-8 "Last changed by" and "when" on every item Must
AD-9 Image upload with required alt text, type and size
limits
Must
[[page 11]]
8. Backend, data and enquiry flow
The backend serves published content, runs the admin panel, stores media and handles
enquiries. It returns useful errors without exposing secrets or internal details.
Data model
ID Requirement Priority
AD-10 Lock or slow down sign-in after repeated failures;
the last Admin can't be removed
Must
AD-11 Google Workspace sign-in for staff Should (if approved)
AD-12 Blog posts, careers listings, scheduled publishing Phase 2
Entity Main fields
Users name, email, role, MFA status, active, last sign-in
Page sections section key, order, text, images, buttons, status,
draft and published versions
Services category, title, slug, short and long description,
order, status
Projects title, slug, category, client need, work done, result,
technologies, images, order, status, approval
record
Proof items type (figure, testimonial, logo), content, approved
by, approved on, expires on, evidence file (private)
FAQs question, answer, order, status
Media file, type, size, alt text, uploaded by, uploaded on
Legal pages title, body, version, effective date, author, approver
Enquiries name, email, company, service, message, source
page, consent notice version, status, notes,
created on, first replied on
[[page 12]]
Slugs on services and projects let Phase 2 add their own pages without a data change.
Separate tables for team profiles, careers or AI conversations are added only when those
features are approved.
Enquiry flow
1. The server validates the form, checks the honeypot and Turnstile, and applies the rate
limit.
2. The enquiry is saved to the database first.
3. Then an internal email goes to the enquiry inbox (for example hello@ ). It holds the
name, service and a link to the admin record, not the full message.
4. The visitor gets a short confirmation from the sending subdomain, with replies going
to hello@.
5. If an email fails, the enquiry is not lost: the failure is logged and retried.
Data retention
Proposed: enquiries are kept for 24 months, then deleted automatically, and audit logs for
12 months. Legal confirms both, and they go in the privacy notice.
9. Technical architecture and hosting
Recommended stack: one Next.js app on Vercel (London) with Supabase (London) for the
database, staff sign-in and file storage. First, in week 1, audit the existing Nepal website
and infrastructure. If its backend, database or admin panel can be reused safely, we reuse
it rather than build a duplicate.
Entity Main fields
Site settings contact details, hours, legal company details,
footer links, SEO defaults
Audit log who, what, which item, when (append only)
[[page 13]]
Layer Choice Why
Website and
admin
Next.js (App Router) with
TypeScript and Tailwind CSS
Server-rendered pages are fast and
good for SEO. Brand colours set
once as design tokens. Admin lives
in the same app under /admin.
Server logic Next.js route handlers and server
actions. No separate API server
One codebase and one deploy is
enough for this site. A separate API
can be split out later if needed.
Database PostgreSQL on Supabase, London
region (eu-west-2), accessed with
Prisma
Content is relational (services,
projects, images) and enquiries
need a fixed structure. Region is
hard to change later, so it's set at
creation.
Staff sign-in Supabase Auth: invite-only, email +
password, TOTP MFA, secure
HTTP-only cookies
Invites, MFA and password reset
come ready-made. No custom
cryptography.
Media Supabase Storage: public bucket
for site images, private bucket for
proof evidence (signed, short-
lived links)
Simple for Phase 1. Cloudinary only
if we need advanced image
processing.
Hosting Vercel, server functions pinned to
London ( lhr1 )
Close to UK visitors and to the
database. Simple deploys from
GitHub.
DNS Cloudflare DNS with DNSSEC Central domain control. We don't
add a second CDN/proxy in front of
Vercel unless it's deliberately set
up and tested.
Email Google Workspace for staff
mailboxes; Resend for website
emails
Workspace is already confirmed.
Website emails go from a separate
sending subdomain.
Validation Zod, same rules in the browser and
on the server
The server check is the one that
counts.
Monitoring Sentry, uptime checks, Vercel and
Supabase logs
Errors and downtime alert a named
owner.
[[page 14]]
Rules for the build
Server-only data access. The browser never talks to the database. Supabase's public
Data API is switched off for the app's tables, and Row Level Security is on as a second
guard.
Public pages read published content only. A test proves that a visitor can never get
drafts, users, enquiries, proof evidence or the audit log.
Secrets stay on the server (service keys, email and AI keys) in environment variables,
never in the repository.
Three environments: development, staging and production, each with its own
Supabase project and buckets. Production data is never copied to development or
previews.
Caching: public pages and images are cached; admin pages, signed-in responses and
enquiries never are. Publishing triggers on-demand revalidation.
Backups: daily database backups, plus point-in-time recovery if the plan supports it;
media bucket copied to a second location. Target: lose at most 24 hours of data and be
back within 4 hours. A full restore to staging is tested before launch.
Accounts: domain, DNS, Vercel, Supabase and GitHub are owned by company
accounts, with MFA and at least two company administrators each.
Alternative considered: Payload CMS
The Google Doc proposed Payload CMS 3 on Fly.io. Payload gives drafts, versions and an
admin UI out of the box. We recommend against it for Phase 1: the content model is small
(about 10 tables), invites and MFA already come from Supabase Auth, and Payload adds a
framework the team must learn plus a second hosting provider. We revisit it in Phase 2,
when the blog and careers make the content model bigger (decision D-5).
Layer Choice Why
Code Company-owned GitHub
organisation; protected main ; lint,
type-check, build and tests on
every pull request
Broken builds never reach
production.
[[page 15]]
Architecture at a glance
Visitors and staff reach the same Next.js app; only its server code talks to Supabase and
the outside services.
10. Domain, email and third-party tools
We use what the company already has first and add a tool only when there is a clear need
and an owner.
Domain and email
Domain: leafclutch.co.uk if it is available and approved; otherwise an approved
subdomain such as uk.leafclutchtech.com.np. Nothing is assumed until
registration and ownership are confirmed.
￼
Phase 1 architecture · one app, one database region
[[page 16]]
Mailboxes: stay on Google Workspace. Use group addresses routed to named staff
rather than new paid mailboxes: hello@ for enquiries, website-alerts@ for system
alerts, and careers@ only in Phase 2.
Website emails: sent from a separate subdomain, for example no-reply@updates.
<domain>
, with replies going to hello@.
Deliverability: SPF, DKIM and DMARC set up for Workspace and the sending
subdomain, with one SPF record per hostname. DMARC starts in monitoring mode,
then moves to enforcement.
Tools
Need Choice Phase Notes
Spam protection Cloudflare Turnstile +
honeypot
1 Mostly invisible to real
users; avoids
reCAPTCHA's tracking
concerns
Website email Resend (or Postmark) 1 Check for an existing
provider first
Analytics Plausible (cookieless) +
Google Search Console
1 See section 14; GA4 only if
the company insists, and
then only after consent
Cookie banner None needed if only
essential cookies are
used; CookieYes or
Cookiebot if not
1 Don't install a consent
platform for cookies the
site doesn't set
Booking Google Calendar
appointment schedule
(Workspace), linked not
embedded
1
(Should)
Calendly only if we need
more features; no embed
before consent
Error and uptime
monitoring
Sentry + an uptime
checker
1 Alerts go to website-
alerts@ and a named
owner
[[page 17]]
Every tool that handles visitor data is named in the privacy notice, with its data location.
Prices and free-tier limits are checked before anything is bought.
11. Security and privacy
All of these are Must for launch.
Need Choice Phase Notes
CRM None at launch; the admin
panel is the enquiry log
2 HubSpot free CRM or
Zoho if volume or several
sales users justify it; we
always keep our own copy
of each enquiry
Newsletter Brevo, if wanted 2 Explicit opt-in and
unsubscribe; contact-form
senders are never added
automatically
Accounting, project
tools, video calls
Existing company tools — No website integration
ID Requirement How we check
SE-1 HTTPS only, with HSTS and security
headers (Content Security Policy, no
framing by other sites, no MIME sniffing,
strict referrer policy)
Header scan scores A or better
SE-2 Admin is invite-only with MFA;
passwords hashed by Supabase Auth;
repeated failed sign-ins are slowed or
locked
Tested with a test account on staging
SE-3 Every protected action checks the user's
role on the server
API tests call each admin action as
Editor and as a signed-out visitor
SE-4 Public reads return published content
only
Test proves no draft, user, enquiry, proof
evidence or audit row is reachable
without signing in
[[page 18]]
12. UK legal and compliance
The UK operation is a branch of the Nepal-incorporated parent company, not a separate
UK limited company. Its exact Companies House status must be verified before launch.
This section is an implementation summary, not legal advice; whoever handles legal for
Leafclutch signs off the final wording.
ID Requirement How we check
SE-5 All input validated and cleaned on the
server; database queries parameterised
through Prisma, never built from strings
Invalid and malicious inputs are rejected
in tests
SE-6 Enquiry form protected by honeypot,
Turnstile and a rate limit
Automated flood test is blocked
SE-7 Uploads checked for type and size;
stored in Supabase Storage, not on the
app server; proof evidence only through
short-lived signed links
Unsupported files are rejected; an
anonymous request for an evidence file
fails
SE-8 Secrets in environment variables only;
none in the repository or browser code
Secret scanning on the repository
SE-9 Dependencies updated regularly, with
automatic alerts for known
vulnerabilities
Dependabot (or similar) enabled
SE-
10
No passwords, tokens or enquiry
contents in logs, analytics or notification
emails
Log review on staging
SE-11 Data breach plan: a named owner who
knows serious breaches must be
reported to the ICO within 72 hours
Plan written and owner named before
launch
SE-
12
Preview links are private, not cached and
not indexed
Preview URL returns noindex and no-
store
[[page 19]]
Company details on the site
Show the parent company's exact legal name and country of incorporation, a
geographic address and a working email. Put them in the footer and the Contact
section, always visible.
If the branch is registered with Companies House as a UK establishment, also show
the details required by regulation 63 of the Overseas Companies Regulations 2009:
country of incorporation, home registry and registration number, head-office location,
legal form, limited-liability status and any insolvency information.
Never invent a UK company number, VAT number, UK registered office, local staff or
certification. Show a VAT number only if the company is VAT-registered.
Keep identity and contact details identical across the footer, Contact section, privacy
notice and terms.
A UK phone number is labelled as a contact line, not a UK office, unless an office
exists.
Privacy (UK GDPR)
Publish the privacy notice before the form collects any data.
It explains: who the data controller is, what we collect and why, the lawful basis, who
receives it, how long we keep it, individual rights, how to contact us and how to
complain to the ICO.
It explains international access and transfers: which staff in Nepal can see UK
enquiries, why, how access is secured, and the safeguard used (for example the UK
IDTA or the UK Addendum to the EU SCCs). Hosting in London does not remove this
assessment.
It lists every processor (Vercel, Supabase, Resend, Cloudflare, analytics) and its data
location.
Legal confirms whether a UK representative or a Data Protection Officer is needed.
Cookies and tracking (PECR)
Non-essential cookies or similar tracking need consent first: a clear positive action, no
pre-ticked boxes,
"Reject all" as easy and visible as "Accept all"
, and consent that can
be withdrawn as easily as it was given. If someone rejects, no non-essential cookie is
set.
[[page 20]]
Some basic analytics may be exempt under the Data (Use and Access) Act 2025 and
the ICO's 2026 guidance, but not all analytics. Legal confirms which tools qualify
before launch.
The cookie information page lists only what the site actually sets, based on a real scan
of the finished site.
Accessibility and content accuracy
WCAG 2.2 AA is our design and testing target. The public-sector accessibility
regulations are not described as applying to us; we meet our Equality Act 2010 duty to
make reasonable adjustments.
An accessibility statement gives a way to report barriers.
British English, UK date format, UK phone format and opening hours in UK time.
Prices, if ever shown, in GBP (£) and saying whether VAT is included.
No pricing, client logos, testimonials, figures or certifications unless verified and
approved.
Pages and documents at launch
Privacy notice, cookie information and preferences, website terms (if approved) and
accessibility statement. Other corporate policies or reports are published only if a legal
duty applies to the UK branch and the right person approves them. We don't build a large
"Policies and reports" library just because other companies have one.
13. SEO, accessibility and performance
All Must for launch, measured on the landing page and one legal page.
ID Target How we check
NF-1 Accessibility: WCAG 2.2 AA; zero
serious or critical automated findings;
full keyboard use with visible focus;
works with a screen reader; form errors
announced
axe scan + manual keyboard and screen-
reader pass (VoiceOver and NVDA)
[[page 21]]
If Leafclutch gets a UK address, set up a Google Business Profile. Most long-term search
growth comes from the Phase 2 blog and service pages; Phase 1 gets the basics right.
14. Analytics and monitoring
We want to know how many people visit, where they come from, how many click Enquire
and how many send the form. One analytics tool only.
Recommendation: start with Plausible (cookieless) plus Google Search Console. It
answers those questions and likely needs no cookie banner (legal to confirm), which
keeps the page fast and the legal work simple. If the company prefers Google Analytics 4,
ID Target How we check
NF-
2
Performance (lab, mobile 4G): LCP
under 2.5s, CLS under 0.1, TBT 200ms or
less. After launch, INP under 200ms from
real users
Lighthouse, median of 5 runs at 375px
and 1366px
NF-
3
Responsive: no sideways scroll, no cut-
off text, tap targets at least 44px
Checked at 320, 375, 768, 1024, 1366 and
1440px
NF-
4
Browsers: current and previous versions
of Chrome, Edge, Firefox and Safari; iOS
Safari; Android Chrome
Browser matrix signed off in testing
NF-
5
SEO basics: server-rendered HTML, one
H1, unique title and meta description,
semantic headings, Open Graph tags
Lighthouse SEO 100; manual check of
social previews
NF-
6
Structured data: Organization, Service
and FAQ JSON-LD
Google Rich Results Test passes
NF-
7
Indexing: sitemap.xml and robots.txt;
/admin and previews set to noindex;
site added to Google Search Console
Search Console shows the sitemap
processed
NF-
8
Language: lang="en-GB"
, British
spelling; hreflang links between the UK
and Nepal sites
hreflang validator passes on both sites
NF-
9
Images: compressed modern formats,
correct sizes, descriptive alt text
No Lighthouse image warnings
[[page 22]]
it loads only after the visitor accepts, through a consent banner with Consent Mode
denied by default (decision D-4). The three drafts disagreed here: Susan proposed
cookieless first, Rakesh GA4, the Google Doc GA4 with GTM and Cookiebot.
Events tracked: Enquire button clicks (by location), form starts, form submissions, form
errors,
"Book a call" clicks, traffic source. Nothing personal.
Monitoring
15. Delivery plan
The Phase 1 timeline is to be planned. The stages below assume three people full time
(assumed: two developers and one designer/content person, to confirm) using AI coding
tools for scaffolding, routine code and tests. Every piece of generated code is still
reviewed, security-checked and tested by a developer.
What Tool Alert goes to
Frontend and backend errors Sentry Named owner + website-
alerts@
Site, admin sign-in and form
availability
Uptime checker, every 5
minutes
Named owner
Failed enquiry emails, failed
backups
App logs + Sentry alerts Named owner
Search visibility and indexing Google Search Console Content owner, monthly
Core Web Vitals, accessibility,
dependencies
Monthly check Tech owner
Step Stage What happens Done when
1 Sign-off and
audit
PRD approved; open decisions
D-1 to D-6 answered; Nepal
website and infrastructure
audit (1–2 days); domain,
accounts and Workspace setup
confirmed
Stack, hosting and domain
agreed in writing
[[page 23]]
Runs alongside the build (company side, before the build ends): approved copy, project
details and screenshots, client permissions, real figures, legal company details, privacy
notice and terms, brand assets.
Timeline. To be planned with the team once D-1 to D-6 are decided. Legal review and
content are the two things most likely to slow it down. If they slip, launch moves; we don't
publish placeholders or unverified claims.
Phase 2 timeline is to be planned after launch, based on what the first weeks of enquiries
show.
16. Launch checklist
The site goes live only when every item is ticked. If one can't be met, launch moves; we
don't ship a workaround.
Legal and content
Step Stage What happens Done when
2 Design and setup Landing page design in the
Leafclutch brand; design
tokens and components; data
model; repository, CI, staging
Design approved; staging
deploys from GitHub
3 Build: site and
backend
All landing-page sections;
enquiry form, storage and
emails; staff sign-in, MFA and
roles
Form works end to end on
staging
4 Build: admin
panel
Content editing; draft, review,
publish; approval records;
media; enquiries; audit log
Staff can change every
section without a developer
5 Integrations and
quality
Analytics, monitoring, SEO and
structured data, cookie setup,
backups, restore test
All checks in sections 11 and
13 run on staging
6 Testing and
launch
Responsive, browser,
accessibility and security
testing; real content loaded;
legal pages signed off; DNS
cutover with a rollback plan
Launch checklist (section 16)
all ticked
[[page 24]]
Product
Quality and security
Operations
17. Risks and fallbacks
Legal company details verified and shown in the footer and Contact section
Privacy notice, cookie information, terms and accessibility statement approved by
someone other than the author
International access and transfer safeguard for Nepal staff documented
Every project, figure, testimonial and logo has an approval record
No placeholder text, broken links or unapproved claims
UK phone shown only if UK hours are staffed; reply-time promise agreed
All Must requirements in sections 6 and 7 pass their checks
Enquiry form tested end to end: stored, team alerted, visitor confirmed, email failure
retried
Staff accounts created with MFA; at least two Admins
Staff trained to edit, publish and handle enquiries
Accessibility, performance, responsive and browser checks in section 13 pass
Security checks in section 11 pass, including the anonymous-read test
Cookie scan done; no non-essential script runs before consent
Backup restored to staging successfully
Domain, DNS, SPF, DKIM and DMARC verified; HTTPS and HSTS live
Sentry and uptime alerts reach a named owner
Analytics and Search Console receiving data
Rollback plan tested; owners named for content, enquiries, privacy and alerts
ID Risk Likelihood Fallback
R-1 Legal review or company details
not ready before testing starts
High Launch moves. Form stays off and
direct email is used only if legal
approves that as an interim step
[[page 25]]
18. Open decisions
D-1 to D-6 are needed in week 1, before the build starts. The rest are needed before the
content or legal pages they affect.
ID Risk Likelihood Fallback
R-2 Too few approved projects or
figures
Medium Featured work shows what was
built without client names or
numbers; figures row stays
hidden. No placeholders
R-3 The Nepal infrastructure audit
finds a reusable backend that
changes the stack
Medium Decided in week 1, before the
build starts; the timeline is re-
checked then
R-4 Nobody can answer the phone or
enquiries in UK hours
Medium Phone hidden; the reply promise is
"within 1 UK working day" by email
only
R-5 Drafts or private data leak through
public pages
Low Server-only data access, Data API
off, RLS on, and the anonymous-
read test in CI
R-6 An approval for a testimonial, logo
or figure expires or is withdrawn
Low Expiry hides the item
automatically; Admins can
unpublish at once
R-7 Spam floods the enquiry inbox Medium Honeypot, Turnstile, rate limit;
thresholds tuned after launch
R-8 Phase 2 asks for much bigger
content needs than planned
Low Slugs and the content model are
ready for separate pages; Payload
is reconsidered then (D-5)
ID Decision Recommendation Owner Needed
by
D-1 Final stack and hosting,
after the Nepal website
and infrastructure audit
Next.js on Vercel +
Supabase London (section
9), unless the audit finds
something safe to reuse
Tech lead End of
week 1
[[page 26]]
ID Decision Recommendation Owner Needed
by
D-2 Website domain and
Google Workspace
domain setup
leafclutch.co.uk if
available, else an approved
subdomain
Management Week 1
D-3 UK audience priority,
service catalogue, and
whether software
products are included
Startups and SMEs first; 3–
4 service categories
Management Week 1
D-4 Analytics tool Plausible + Search Console;
GA4 only with consent
Management
+ legal
Week 1
D-5 Admin build approach Custom admin in the
Next.js app; reconsider
Payload CMS in Phase 2
Tech lead Week 1
D-6 Team size and budget;
launch target date
Three people full time;
timeline to be planned
Management Week 1
D-7 Legal company identity:
parent's registered
details, Companies
House status and
number, VAT status,
address to show
— Founder / legal Week 3
D-8 Data controller, Nepal
staff access, transfer
safeguard, UK
representative or DPO,
retention periods
24 months for enquiries, to
confirm
Legal Week 3
D-9 Which projects, figures,
testimonials and client
logos can be shown
Start with 3–6 projects with
written approval
Commercial
lead
Week 3
D-
10
Prices or packages on
the site; free
consultation offer
No prices in Phase 1; offer a
free first call if the
company will honour it
Management Week 2
[[page 27]]
19. Source documents and references
Merged drafts
Susan Jati — PRD: Leafclutch UK Website (Word document, 23 Nov 2026): research
on four UK sites, landing page structure, requirement tables, UK tools, timeline.
Rakesh Patel — UK Branch Website – PRD (Notion): phases 1–3, Nepal infrastructure
audit, Supabase/Vercel London, domain and email, UK branch legal requirements.
LeafClutch UK Website — Product Requirements Document (Google Doc): success
measures, acceptance criteria, proof approval model, security and backup targets. Its
research appendix ( uk-website-similarity-report-single.html ) was not
attached to the doc.
What came from where
ID Decision Recommendation Owner Needed
by
D-11 UK-hours cover: phone
or WhatsApp staffing
and the reply-time
promise
Email-only with a 1 UK
working day promise until
hours are staffed
Management Week 2
D-
12
Booking link and an
optional budget field on
the form
Booking link: yes (Google
Calendar). Budget field:
optional, with "Prefer not to
say"
Management Week 2
D-
13
Owners for website
content, enquiries,
privacy and cookie
reviews, document
approval, and
production alerts
— Management Week 4
Topic Taken from
Single landing page first, section order,
requirement tables
Susan, Rakesh
Phase 2 and 3 scope, out-of-scope list Rakesh
[[page 28]]
Legal and guidance sources cited in the drafts (not re-checked for this merge; legal
should confirm they are current)
Companies House — Overseas companies registered in the UK
Overseas Companies Regulations 2009, regulations 62 and 63
Electronic Commerce (EC Directive) Regulations 2002, regulation 6
ICO — Right to be informed; What privacy information should we provide?; A guide to
international transfers
ICO — Guidance on the use of storage and access technologies (PECR); Data (Use
and Access) Act 2025 guidance
W3C — Web Content Accessibility Guidelines 2.2
Equality and Human Rights Commission — Equality Act 2010 guidance for services
Department for Business and Trade — Longitudinal Small Business Survey 2025
Topic Taken from
Nepal infrastructure audit before choosing the
stack
Rakesh
Next.js + Supabase London + Vercel lhr1 Rakesh, Susan
Admin and Editor roles, draft and publish All three
Approval records for proof, pass/fail checks,
success measures, backup targets, Data API off
Google Doc
Cookieless analytics first Susan
UK branch legal details (Overseas Companies
Regulations)
Rakesh
Cookie consent rules, ICO 72-hour breach rule,
newsletter opt-in
Susan
Domain, Workspace groups, sending subdomain,
enquiry saved before email
Rakesh
[[page 29]]
```
