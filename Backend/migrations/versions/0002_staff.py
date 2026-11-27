"""The staff table, the last-Admin guard and the timestamp trigger.

The table uses SQLAlchemy operations so `alembic check` compares it with app/models.py.

The trigger SQL follows Backend/docs/DATABASE.md §Timestamps and the last Admin, with
deliberate changes dated 27 November 2026: a statement-level `staff_lock_writes` trigger
takes a transaction-scoped advisory lock before any row lock, and `enforce_last_admin`
counts with a locking read so REPEATABLE READ and SERIALIZABLE cannot let a concurrent
removal through. Both changes are in DATABASE.md.

Revision ID: 0002_staff
Revises: 0001_extensions_enums
Create Date: 2026-11-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_staff"
down_revision: str | None = "0001_extensions_enums"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SET_UPDATED_AT_SQL = """
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;
"""

LOCK_STAFF_WRITES_SQL = """
create or replace function lock_staff_writes()
returns trigger
language plpgsql
as $$
begin
  -- Taken before any row lock: two writers cannot each hold a row the other needs while
  -- one waits here. The key is constant for the staff write path and the lock ends with
  -- the transaction.
  perform pg_advisory_xact_lock(hashtext('staff_last_admin'));
  return null;
end;
$$;
"""

ENFORCE_LAST_ADMIN_SQL = """
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
"""


STAFF_SET_UPDATED_AT_TRIGGER_SQL = """
create trigger staff_set_updated_at
  before update on staff
  for each row execute function set_updated_at();
"""

STAFF_LOCK_WRITES_TRIGGER_SQL = """
create trigger staff_lock_writes
  before update or delete on staff
  for each statement execute function lock_staff_writes();
"""

STAFF_LAST_ADMIN_TRIGGER_SQL = """
create trigger staff_last_admin
  before update or delete on staff
  for each row execute function enforce_last_admin();
"""


def upgrade() -> None:
    op.create_table(
        "staff",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("auth.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        # The type itself is created by 0001; this must not try to create it again.
        sa.Column(
            "role",
            postgresql.ENUM("admin", "editor", name="staff_role", create_type=False),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("staff.user_id", ondelete="SET NULL"),
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email", name="staff_email_unique"),
        sa.CheckConstraint(
            "char_length(display_name) between 1 and 100",
            name="staff_display_name_length",
        ),
    )
    op.create_index(
        "staff_active_role_idx",
        "staff",
        ["role"],
        postgresql_where=sa.text("active"),
    )

    op.execute(SET_UPDATED_AT_SQL)
    op.execute(STAFF_SET_UPDATED_AT_TRIGGER_SQL)
    op.execute(LOCK_STAFF_WRITES_SQL)
    op.execute(STAFF_LOCK_WRITES_TRIGGER_SQL)
    op.execute(ENFORCE_LAST_ADMIN_SQL)
    op.execute(STAFF_LAST_ADMIN_TRIGGER_SQL)


def downgrade() -> None:
    # The explicit trigger drops document the pair; dropping the table also removes the
    # timestamp trigger and the index.
    op.execute("drop trigger staff_last_admin on staff")
    op.execute("drop trigger staff_lock_writes on staff")
    op.drop_table("staff")
    op.execute("drop function enforce_last_admin()")
    op.execute("drop function lock_staff_writes()")
    op.execute("drop function set_updated_at()")
