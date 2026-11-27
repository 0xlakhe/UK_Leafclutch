-- Minimal stand-in for Supabase's auth schema on a plain PostgreSQL.
--
-- Supabase owns this schema and its rows; running this script against Supabase is a
-- no-op. It exists so a fresh local or test database can satisfy
-- staff.user_id references auth.users (id) and run the validation runbook's admin fixture,
-- which needs email and last_sign_in_at, before `alembic upgrade head`.
create schema if not exists auth;

create table if not exists auth.users (
  id uuid primary key,
  email text,
  last_sign_in_at timestamptz
);

-- An existing volume may hold the first stub, with only id. Add the later columns only
-- when they are missing; on Supabase both exist, so the block changes nothing.
-- pg_catalog, not information_schema: that view hides columns from a role without
-- privileges, which would make this block try to ALTER a table it does not own.
do $$
begin
  if not exists (
    select 1
    from pg_catalog.pg_attribute a
    join pg_catalog.pg_class c on c.oid = a.attrelid
    join pg_catalog.pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'auth'
      and c.relname = 'users'
      and a.attname = 'email'
      and not a.attisdropped
  ) then
    alter table auth.users add column email text;
  end if;

  if not exists (
    select 1
    from pg_catalog.pg_attribute a
    join pg_catalog.pg_class c on c.oid = a.attrelid
    join pg_catalog.pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'auth'
      and c.relname = 'users'
      and a.attname = 'last_sign_in_at'
      and not a.attisdropped
  ) then
    alter table auth.users add column last_sign_in_at timestamptz;
  end if;
end
$$;
