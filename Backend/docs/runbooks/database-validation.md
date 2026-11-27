# Database validation on a scratch PostgreSQL 18

## Purpose

Run the SQL in `docs/DATABASE.md` against a scratch PostgreSQL 18 database and prove the
unpublish, archive and delete behaviour task 0002 added: the `_unpublish_internal` helper
and `unpublish_content` wrapper, `archive_content`, `restore_content` and
`delete_content`, including its five refusals. It also proves that archiving a landing
page removes a live section pointer when the page has no pointer of its own. This is the
only way to execute those functions before `api/` exists.

`database-validation.sql` beside this page holds the fixtures and assertions. This page
holds the commands. The run covers the unpublish/archive/delete half of the validation;
the first list in `DATABASE.md` `## Validation performed` comes from a broader fixture
that is still uncommitted.

## Prerequisites

- Docker with the `postgres:18` image.
- Python 3 (the extraction step in section 3 uses `python3`).
- Either a `psql` client, or the container's own client through `docker exec`. The
  commands below use `docker exec`, so no host `psql` is needed.
- Run everything from the repository root.

## 1. Start a scratch database

Remove a leftover container of the same name first, then start a fresh one:

```bash
docker rm -f lc-pg18-validate 2>/dev/null || true

docker run -d --name lc-pg18-validate \
  -p 55432:5432 \
  -e POSTGRES_PASSWORD=pg \
  -e POSTGRES_DB=lc \
  postgres:18

for i in $(seq 1 60); do
  docker exec lc-pg18-validate pg_isready -U postgres -d lc >/dev/null 2>&1 && break
  sleep 1
done
```

Port 55432 and the name `lc-pg18-validate` are the runbook's convention; any free port
and name work if the later commands are changed to match.

## 2. Apply the auth and storage stubs

The image has no Supabase schemas. These minimal stubs satisfy the foreign keys and
grants the document's SQL expects: an `auth.users` row per staff member, optional MFA
factors, and the two storage tables with the bucket limits block 55 inserts into.

```bash
docker exec -i lc-pg18-validate psql -U postgres -d lc -v ON_ERROR_STOP=1 <<'SQL'
create schema auth;
create schema storage;
create table auth.users (
  id uuid primary key,
  email text unique,
  last_sign_in_at timestamptz
);
create table auth.mfa_factors (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  status text not null
);
create table storage.buckets (
  id text primary key,
  name text not null,
  public boolean not null default false,
  file_size_limit bigint
);
create table storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text not null,
  name text not null,
  owner uuid
);
create role anon nologin;
create role authenticated nologin;
SQL
```

## 3. Extract the document's SQL blocks

Extract every fenced ```sql block from `docs/DATABASE.md`, in document order:

```bash
rm -rf /tmp/lc-blocks
mkdir -p /tmp/lc-blocks
python3 - <<'PY'
import re
from pathlib import Path

blocks = re.findall(r"```sql\n(.*?)```", Path("docs/DATABASE.md").read_text(), re.S)
for i, block in enumerate(blocks, 1):
    Path("/tmp/lc-blocks", f"{i:02d}.sql").write_text(block)
print(f"{len(blocks)} SQL blocks")
PY
```

At the time of the recorded run this prints `58 SQL blocks`.

## 4. Apply the blocks

Copy the extracted blocks into the container and apply them one at a time with
`ON_ERROR_STOP`. Block 57 is the `cron.schedule` block; the image has no `pg_cron`, so it
is skipped by content rather than by number.

```bash
docker cp /tmp/lc-blocks lc-pg18-validate:/tmp/lc-blocks

for f in $(docker exec lc-pg18-validate sh -c 'ls /tmp/lc-blocks/*.sql | sort'); do
  if docker exec lc-pg18-validate grep -q 'cron.schedule' "$f"; then
    echo "skip $f (no pg_cron)"
    continue
  fi
  docker exec lc-pg18-validate psql -U postgres -d lc -v ON_ERROR_STOP=1 -q -f "$f" \
    || { echo "failed $f"; exit 1; }
done
```

The run prints `skip /tmp/lc-blocks/57.sql (no pg_cron)` once. Confirm the base tables:

```bash
docker exec lc-pg18-validate psql -U postgres -d lc -tAc \
  "select count(*) from pg_tables where schemaname = 'public'"
```

This prints `46`.

## 5. Run the harness

```bash
docker cp docs/runbooks/database-validation.sql \
  lc-pg18-validate:/tmp/database-validation.sql
docker exec lc-pg18-validate psql -U postgres -d lc \
  -f /tmp/database-validation.sql
```

The script sets `ON_ERROR_STOP` itself, so any failed assertion exits non-zero.

## Expected output

A fresh run applies cleanly. The notices below are the recorded output of the third
27 November 2026 run (line numbers depend on the script; the messages do not):

```
## admin fixture
INSERT 0 1
INSERT 0 1
## page, sections, unpublish, republish
psql:/tmp/database-validation.sql:105: NOTICE:  PASS fixture: page and ten sections published
psql:/tmp/database-validation.sql:105: NOTICE:  PASS unpublish landing page: 11 pointers removed, 11 drafts exist
psql:/tmp/database-validation.sql:105: NOTICE:  PASS publish_page republished the page from the 11 drafts
DO
## service lifecycle
psql:/tmp/database-validation.sql:197: NOTICE:  PASS unpublish service: pointer gone, one draft, published version kept, audit written
psql:/tmp/database-validation.sql:197: NOTICE:  PASS second unpublish: no new draft, audit row still written (documented)
psql:/tmp/database-validation.sql:197: NOTICE:  PASS unpublish reuses an existing open draft: pointer gone, third audit row
psql:/tmp/database-validation.sql:197: NOTICE:  PASS archive: no draft, archived flag, audit row, one page:/ cache tag
psql:/tmp/database-validation.sql:197: NOTICE:  PASS restore: flags cleared, unpublished, no draft, no pointer, no cache tag
DO
## delete and refusals
psql:/tmp/database-validation.sql:338: NOTICE:  PASS delete never-published service: row and versions gone, one audit row, no cache tag
psql:/tmp/database-validation.sql:338: NOTICE:  PASS legal page draft deleted twice and its path reused
psql:/tmp/database-validation.sql:338: NOTICE:  PASS delete refuses a published item
psql:/tmp/database-validation.sql:338: NOTICE:  PASS delete refuses the fixed kinds: landing page, section, settings
psql:/tmp/database-validation.sql:338: NOTICE:  PASS delete refuses an approved item
psql:/tmp/database-validation.sql:338: NOTICE:  PASS delete refuses an item referenced by a section version
psql:/tmp/database-validation.sql:338: NOTICE:  PASS delete refuses a group with a service version
DO
## archive and restore the page
psql:/tmp/database-validation.sql:409: NOTICE:  PASS archive page: 11 items archived, no drafts created, pointer gone, audit row, page:/ and routes cache tag
psql:/tmp/database-validation.sql:409: NOTICE:  PASS restore page: all 11 flags cleared, nothing live, no new draft, no cache tag
DO
## archive page with a live section and no page pointer
psql:/tmp/database-validation.sql:500: NOTICE:  PASS archive page with a live section and no page pointer: 11 archived, pointers gone, one page unpublish audit row, page:/ and routes cache tag, no draft
DO
```

That is 18 `PASS` notices, two `INSERT 0 1` lines and five `DO` blocks, and psql exits
0. A fresh database is required: the fixture inserts fixed ids and slugs, so a second run
on the same database fails on those inserts.

## Clean up

```bash
docker rm -f lc-pg18-validate
```

## What this does not cover

- **Supabase `storage` objects.** `storage.buckets` and `storage.objects` are stub tables.
  No file is uploaded, copied between buckets or removed.
- **`pg_cron`.** The image has no `pg_cron`, so the `cron.schedule` block is skipped. The
  schedules and the retention jobs still need a Supabase local or staging run.
- **Real `auth.users`.** The staff fixture is one stub row; MFA status defaults, sign-in
  timestamps and Auth triggers are not exercised.
- **FastAPI object promotion.** This run exercises the database half only; the API still
  has to implement the copy that promotes a staged image to `site-media`.
- **The publish gates beyond this fixture.** The broader checks reviewed in `DATABASE.md`
  (publish approvals, legal identity, project approvals, FAQ counts, grants and so on) are
  not repeated here. This harness only builds enough published state to exercise
  unpublish, archive and delete.
