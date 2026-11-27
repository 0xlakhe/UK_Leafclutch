"""The media table and the immutability trigger.

The table uses SQLAlchemy operations so `alembic check` compares it with app/models.py.

The trigger and its function are copied verbatim from Backend/docs/DATABASE.md §Media.
`prevent_media_mutation` is `before update` only: a staged row may be promoted once and a
public row may only receive `deleted_at`, and nothing may be undeleted. Insert and delete
are intentionally not guarded here; the publish gate and the reference checks own those.

Revision ID: 0003_media
Revises: 0002_staff
Create Date: 2026-11-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_media"
down_revision: str | None = "0002_staff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVENT_MEDIA_MUTATION_SQL = """
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
       or new.promoted_at is null then
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
"""

MEDIA_IMMUTABLE_TRIGGER_SQL = """
create trigger media_immutable
  before update on media
  for each row execute function prevent_media_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "media",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # The type itself is created by 0001; this must not try to create it again.
        sa.Column(
            "visibility",
            postgresql.ENUM(
                "public", "private", name="media_visibility", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("object_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("alt", sa.Text()),
        sa.Column("checksum_sha256", sa.LargeBinary(), nullable=False),
        sa.Column(
            "uploaded_by",
            sa.Uuid(),
            sa.ForeignKey("staff.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("promoted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bucket", "object_path", name="media_object_unique"),
        sa.CheckConstraint(
            "bucket in ('media-staging', 'site-media', 'evidence')",
            name="media_bucket",
        ),
        sa.CheckConstraint(
            "(visibility = 'public' and bucket = 'site-media') or\n"
            "(visibility = 'private' and bucket in ('media-staging', 'evidence'))",
            name="media_visibility_bucket",
        ),
        sa.CheckConstraint(
            "(visibility = 'public') = (promoted_at is not null)",
            name="media_promotion",
        ),
        sa.CheckConstraint(
            "char_length(object_path) between 1 and 300 and object_path !~ '^/'",
            name="media_object_path",
        ),
        sa.CheckConstraint(
            "char_length(mime_type) between 1 and 100",
            name="media_mime_length",
        ),
        sa.CheckConstraint(
            "size_bytes > 0 and size_bytes <= 4194304",
            name="media_size",
        ),
        sa.CheckConstraint(
            "octet_length(checksum_sha256) = 32",
            name="media_checksum",
        ),
        sa.CheckConstraint(
            "alt is null or char_length(alt) <= 120",
            name="media_alt_length",
        ),
        sa.CheckConstraint(
            "bucket = 'evidence' or alt is not null",
            name="media_alt_required",
        ),
        sa.CheckConstraint(
            "(bucket = 'evidence'\n"
            "  and mime_type in ('application/pdf', 'image/jpeg', 'image/png', "
            "'image/webp'))\n"
            "or (bucket <> 'evidence'\n"
            "  and mime_type in ('image/jpeg', 'image/png', 'image/webp'))",
            name="media_types",
        ),
        sa.CheckConstraint(
            "width is null or width > 0",
            name="media_width",
        ),
        sa.CheckConstraint(
            "height is null or height > 0",
            name="media_height",
        ),
        sa.CheckConstraint(
            "mime_type not like 'image/%' or (width is not null and height is not null)",
            name="media_image_dimensions",
        ),
    )

    op.execute(PREVENT_MEDIA_MUTATION_SQL)
    op.execute(MEDIA_IMMUTABLE_TRIGGER_SQL)


def downgrade() -> None:
    # The explicit drops document the pair; dropping the table also removes the trigger.
    op.execute("drop trigger media_immutable on media")
    op.execute("drop function prevent_media_mutation()")
    op.drop_table("media")
