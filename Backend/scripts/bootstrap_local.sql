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
do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'auth' and table_name = 'users' and column_name = 'email'
  ) then
    alter table auth.users add column email text;
  end if;

  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'auth' and table_name = 'users' and column_name = 'last_sign_in_at'
  ) then
    alter table auth.users add column last_sign_in_at timestamptz;
  end if;
end
$$;
