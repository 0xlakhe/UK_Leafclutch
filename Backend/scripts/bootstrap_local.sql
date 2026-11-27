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
