"""The content spine: items, versions, publication pointers, page SEO and their guards.

The tables use SQLAlchemy operations so `alembic check` compares them with app/models.py.

The functions and triggers are copied from Backend/docs/DATABASE.md §Content items and
versions, §Page SEO, §Publication and immutability and §Timestamps and the last Admin.
`prevent_published_content_mutation` is created here but attached only to `content_seo`;
the typed content tables it also guards arrive in later revisions and attach it there.
`content_item_archive_guard` refuses an archive that leaves a publication pointer.
`content_version_set_updated_at` reuses the `set_updated_at` function from `0002_staff`.

Revision ID: 0004_content_core
Revises: 0003_media
Create Date: 2026-11-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_content_core"
down_revision: str | None = "0003_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTENT_KIND = postgresql.ENUM(
    "landing_page",
    "page_section",
    "legal_page",
    "service_group",
    "service",
    "project",
    "proof_figure",
    "testimonial",
    "client_logo",
    "settings",
    name="content_kind",
    create_type=False,
)

VERSION_STATUS = postgresql.ENUM(
    "draft", "in_review", "published", name="version_status", create_type=False
)

BUMP_NEXT_VERSION_SQL = """
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
"""

CONTENT_VERSION_BUMP_NEXT_TRIGGER_SQL = """
create trigger content_version_bump_next
  after insert on content_version
  for each row execute function bump_next_version();
"""

PREVENT_ARCHIVED_WITH_PUBLICATION_SQL = """
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
"""

CONTENT_ITEM_ARCHIVE_GUARD_TRIGGER_SQL = """
create trigger content_item_archive_guard
  before update on content_item
  for each row execute function prevent_archived_with_publication();
"""

PREVENT_PUBLISHED_VERSION_MUTATION_SQL = """
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
"""

CONTENT_VERSION_IMMUTABLE_TRIGGER_SQL = """
create trigger content_version_immutable
  before update or delete on content_version
  for each row execute function prevent_published_version_mutation();
"""

ASSERT_PUBLICATION_VERSION_SQL = """
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
"""

CONTENT_PUBLICATION_ASSERT_TRIGGER_SQL = """
create trigger content_publication_assert
  before insert or update on content_publication
  for each row execute function assert_publication_version();
"""

PREVENT_PUBLISHED_CONTENT_MUTATION_SQL = """
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
"""

CONTENT_SEO_IMMUTABLE_TRIGGER_SQL = """
create trigger content_seo_immutable
  before insert or update or delete on content_seo
  for each row execute function prevent_published_content_mutation();
"""

CONTENT_VERSION_SET_UPDATED_AT_TRIGGER_SQL = """
create trigger content_version_set_updated_at
  before update on content_version
  for each row execute function set_updated_at();
"""


def upgrade() -> None:
    op.create_table(
        "content_item",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("kind", CONTENT_KIND, nullable=False),
        sa.Column("path", sa.Text()),
        sa.Column("slug", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("staff.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "next_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column(
            "archived_by",
            sa.Uuid(),
            sa.ForeignKey("staff.user_id", ondelete="RESTRICT"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "kind", name="content_item_id_kind_key"),
        sa.CheckConstraint("next_version > 0", name="content_item_next_version"),
        sa.CheckConstraint(
            "path is null or path ~ '^/([a-z0-9-]+(/[a-z0-9-]+)*)?$'",
            name="content_item_path_format",
        ),
        sa.CheckConstraint(
            "slug is null or slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="content_item_slug_format",
        ),
        sa.CheckConstraint(
            "kind not in ('landing_page', 'legal_page') or path is not null",
            name="content_item_path_required",
        ),
        sa.CheckConstraint(
            "kind not in ('service', 'project') or slug is not null",
            name="content_item_slug_required",
        ),
        sa.CheckConstraint(
            "kind <> 'settings' or (path is null and slug is null)",
            name="content_item_settings_shape",
        ),
        sa.CheckConstraint(
            "kind <> 'page_section' or (path is null and slug is null)",
            name="content_item_section_shape",
        ),
        sa.CheckConstraint(
            "(archived_at is null) = (archived_by is null)",
            name="content_item_archive",
        ),
    )
    op.create_table(
        "content_version",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "item_id",
            sa.Uuid(),
            sa.ForeignKey("content_item.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            VERSION_STATUS,
            nullable=False,
            server_default=sa.text("'draft'::version_status"),
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("staff.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            sa.Uuid(),
            sa.ForeignKey("staff.user_id", ondelete="RESTRICT"),
        ),
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
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "published_by",
            sa.Uuid(),
            sa.ForeignKey("staff.user_id", ondelete="RESTRICT"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "item_id",
            "version_number",
            name="content_version_item_id_version_number_key",
        ),
        sa.UniqueConstraint("item_id", "id", name="content_version_item_id_id_key"),
        sa.CheckConstraint("version_number > 0", name="content_version_number"),
        sa.CheckConstraint(
            "(status = 'published') = (published_at is not null)",
            name="content_version_published",
        ),
        sa.CheckConstraint(
            "(status = 'published') = (published_by is not null)",
            name="content_version_publisher",
        ),
        sa.CheckConstraint(
            "status <> 'in_review' or submitted_at is not null",
            name="content_version_review",
        ),
    )
    op.create_table(
        "content_publication",
        sa.Column(
            "item_id",
            sa.Uuid(),
            sa.ForeignKey("content_item.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "published_by",
            sa.Uuid(),
            sa.ForeignKey("staff.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("item_id"),
        sa.ForeignKeyConstraint(
            ["item_id", "version_id"],
            ["content_version.item_id", "content_version.id"],
            name="content_publication_version_fk",
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "content_seo",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("content_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seo_title", sa.Text()),
        sa.Column("seo_description", sa.Text()),
        sa.Column(
            "seo_noindex",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "og_image_id",
            sa.Uuid(),
            sa.ForeignKey("media.id", ondelete="RESTRICT"),
        ),
        sa.PrimaryKeyConstraint("version_id"),
        sa.CheckConstraint(
            "seo_title is null or char_length(seo_title) between 1 and 60",
            name="content_seo_title_length",
        ),
        sa.CheckConstraint(
            "seo_description is null or char_length(seo_description) between 1 and 160",
            name="content_seo_description_length",
        ),
    )

    op.create_index(
        "content_item_path_key",
        "content_item",
        ["path"],
        unique=True,
        postgresql_where=sa.text("path is not null"),
    )
    op.create_index(
        "content_item_kind_slug_key",
        "content_item",
        ["kind", "slug"],
        unique=True,
        postgresql_where=sa.text("slug is not null"),
    )
    op.create_index(
        "content_item_settings_singleton",
        "content_item",
        ["kind"],
        unique=True,
        postgresql_where=sa.text("kind = 'settings'"),
    )
    op.create_index(
        "content_item_kind_idx",
        "content_item",
        ["kind"],
        postgresql_where=sa.text("archived_at is null"),
    )
    op.create_index(
        "content_version_one_open",
        "content_version",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("status in ('draft', 'in_review')"),
    )
    op.create_index(
        "content_version_item_status_idx",
        "content_version",
        ["item_id", "status"],
    )

    op.execute(BUMP_NEXT_VERSION_SQL)
    op.execute(CONTENT_VERSION_BUMP_NEXT_TRIGGER_SQL)
    op.execute(PREVENT_ARCHIVED_WITH_PUBLICATION_SQL)
    op.execute(CONTENT_ITEM_ARCHIVE_GUARD_TRIGGER_SQL)
    op.execute(PREVENT_PUBLISHED_VERSION_MUTATION_SQL)
    op.execute(CONTENT_VERSION_IMMUTABLE_TRIGGER_SQL)
    op.execute(ASSERT_PUBLICATION_VERSION_SQL)
    op.execute(CONTENT_PUBLICATION_ASSERT_TRIGGER_SQL)
    op.execute(PREVENT_PUBLISHED_CONTENT_MUTATION_SQL)
    op.execute(CONTENT_SEO_IMMUTABLE_TRIGGER_SQL)
    op.execute(CONTENT_VERSION_SET_UPDATED_AT_TRIGGER_SQL)


def downgrade() -> None:
    # The explicit trigger drops document the pairs; dropping a table also removes its
    # indexes. Functions go after their triggers and before the tables in reverse
    # dependency order.
    op.execute("drop trigger content_seo_immutable on content_seo")
    op.execute("drop trigger content_publication_assert on content_publication")
    op.execute("drop trigger content_version_set_updated_at on content_version")
    op.execute("drop trigger content_version_immutable on content_version")
    op.execute("drop trigger content_version_bump_next on content_version")
    op.execute("drop trigger content_item_archive_guard on content_item")
    op.execute("drop function prevent_published_content_mutation()")
    op.execute("drop function assert_publication_version()")
    op.execute("drop function prevent_published_version_mutation()")
    op.execute("drop function prevent_archived_with_publication()")
    op.execute("drop function bump_next_version()")
    op.drop_table("content_seo")
    op.drop_table("content_publication")
    op.drop_table("content_version")
    op.drop_table("content_item")
