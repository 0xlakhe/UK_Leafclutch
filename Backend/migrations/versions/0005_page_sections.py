"""The page sections and their copy rows.

The tables use SQLAlchemy operations so `alembic check` compares them with app/models.py.

The guards are copied from Backend/docs/DATABASE.md §Section items and §Publication and
immutability. `assert_page_section_row` is attached as a deferrable constraint trigger:
the API inserts a section's item and its page_section row in one transaction, and the
trigger fails the commit if it forgets the row. `section_version_immutable` reuses
`prevent_published_content_mutation` from 0004; the function is not recreated here.

Revision ID: 0005_page_sections
Revises: 0004_content_core
Create Date: 2026-11-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_page_sections"
down_revision: str | None = "0004_content_core"
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

PAGE_SECTION_KEY = postgresql.ENUM(
    "hero",
    "proof",
    "services",
    "not-sure",
    "work",
    "process",
    "about",
    "testimonials",
    "faqs",
    "contact",
    name="page_section_key",
    create_type=False,
)

ASSERT_PAGE_SECTION_ROW_SQL = """
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
"""

CONTENT_ITEM_PAGE_SECTION_ROW_TRIGGER_SQL = """
create constraint trigger content_item_page_section_row
  after insert on content_item
  deferrable initially deferred
  for each row execute function assert_page_section_row();
"""

SECTION_VERSION_IMMUTABLE_TRIGGER_SQL = """
create trigger section_version_immutable
  before insert or update or delete on section_version
  for each row execute function prevent_published_content_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "page_section",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            CONTENT_KIND,
            nullable=False,
            server_default=sa.text("'page_section'::content_kind"),
        ),
        sa.Column("page_id", sa.Uuid(), nullable=False),
        sa.Column(
            "page_kind",
            CONTENT_KIND,
            nullable=False,
            server_default=sa.text("'landing_page'::content_kind"),
        ),
        sa.Column("section_key", PAGE_SECTION_KEY, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("item_id"),
        sa.ForeignKeyConstraint(
            ["item_id", "kind"],
            ["content_item.id", "content_item.kind"],
            name="page_section_item_fk",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["page_id", "page_kind"],
            ["content_item.id", "content_item.kind"],
            name="page_section_page_fk",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("page_id", "section_key", name="page_section_key_unique"),
        sa.UniqueConstraint("page_id", "sort_order", name="page_section_order_unique"),
        sa.CheckConstraint("kind = 'page_section'", name="page_section_kind"),
        sa.CheckConstraint("page_kind = 'landing_page'", name="page_section_page_kind"),
        sa.CheckConstraint("sort_order >= 0", name="page_section_sort"),
    )
    op.create_table(
        "section_version",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("content_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_key", PAGE_SECTION_KEY, nullable=False),
        sa.Column("heading", sa.Text()),
        sa.Column("intro", sa.Text()),
        sa.Column("body", sa.Text()),
        sa.Column("nav_label", sa.Text()),
        sa.Column("eyebrow", sa.Text()),
        sa.Column("primary_label", sa.Text()),
        sa.Column("primary_href", sa.Text()),
        sa.Column("secondary_label", sa.Text()),
        sa.Column("secondary_href", sa.Text()),
        sa.Column("cta_label", sa.Text()),
        sa.Column("cta_href", sa.Text()),
        sa.Column("privacy_text", sa.Text()),
        sa.Column("privacy_link_label", sa.Text()),
        sa.Column("image_id", sa.Uuid(), sa.ForeignKey("media.id", ondelete="RESTRICT")),
        sa.PrimaryKeyConstraint("version_id"),
        sa.CheckConstraint(
            "heading is null or char_length(heading) <= 70",
            name="section_version_heading_length",
        ),
        sa.CheckConstraint(
            "section_key <> 'proof' or heading is null",
            name="section_version_heading_key",
        ),
        sa.CheckConstraint(
            "section_key in ('services', 'work', 'process') or intro is null",
            name="section_version_intro_key",
        ),
        sa.CheckConstraint(
            "section_key in ('hero', 'not-sure', 'contact') or body is null",
            name="section_version_body_key",
        ),
        sa.CheckConstraint(
            "section_key in ('services', 'work', 'process', 'about', 'contact') "
            "or nav_label is null",
            name="section_version_nav_key",
        ),
        sa.CheckConstraint(
            "section_key = 'hero' or eyebrow is null",
            name="section_version_eyebrow_key",
        ),
        sa.CheckConstraint(
            "section_key = 'hero' or (primary_label is null and primary_href is null "
            "and secondary_label is null and secondary_href is null)",
            name="section_version_hero_ctas",
        ),
        sa.CheckConstraint(
            "section_key = 'not-sure' or (cta_label is null and cta_href is null)",
            name="section_version_cta_key",
        ),
        sa.CheckConstraint(
            "section_key = 'contact' "
            "or (privacy_text is null and privacy_link_label is null)",
            name="section_version_privacy_key",
        ),
        sa.CheckConstraint(
            "section_key = 'about' or image_id is null",
            name="section_version_image_key",
        ),
        sa.CheckConstraint(
            "(primary_label is null or char_length(primary_label) <= 30) "
            "and (secondary_label is null or char_length(secondary_label) <= 30) "
            "and (cta_label is null or char_length(cta_label) <= 30)",
            name="section_version_cta_label_length",
        ),
        sa.CheckConstraint(
            "(primary_href is null or char_length(primary_href) <= 200) "
            "and (secondary_href is null or char_length(secondary_href) <= 200) "
            "and (cta_href is null or char_length(cta_href) <= 200)",
            name="section_version_href_length",
        ),
    )

    op.create_index("page_section_page_idx", "page_section", ["page_id", "sort_order"])

    op.execute(ASSERT_PAGE_SECTION_ROW_SQL)
    op.execute(CONTENT_ITEM_PAGE_SECTION_ROW_TRIGGER_SQL)
    op.execute(SECTION_VERSION_IMMUTABLE_TRIGGER_SQL)


def downgrade() -> None:
    # The explicit trigger drops document the pairs. `assert_page_section_row` goes after
    # its trigger and before the table it reads; `prevent_published_content_mutation`
    # belongs to 0004 and stays.
    op.execute("drop trigger content_item_page_section_row on content_item")
    op.execute("drop trigger section_version_immutable on section_version")
    op.execute("drop function assert_page_section_row()")
    op.drop_table("section_version")
    op.drop_table("page_section")
