"""The page sections, their copy rows, lists and references.

The tables use SQLAlchemy operations so `alembic check` compares them with app/models.py.

The guards are copied from Backend/docs/DATABASE.md §Section items, §Lists inside a
section, §Section references, §Child references and §Publication and immutability.
`assert_page_section_row` is attached as a deferrable constraint trigger: the API inserts a
section's item and its page_section row in one transaction, and the trigger fails the
commit if it forgets the row. `assert_section_child` keeps each list on the section key
that owns it, and `assert_section_version_item` keeps a reference on the record kind its
section renders. The seven immutability triggers reuse `prevent_published_content_mutation`
from 0004; the function is not recreated here.

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

ASSERT_SECTION_CHILD_SQL = """
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
"""

SECTION_CHILD_TRIGGERS_SQL = """
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
"""

ASSERT_SECTION_VERSION_ITEM_SQL = """
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
"""

SECTION_VERSION_ITEM_ASSERT_TRIGGER_SQL = """
create trigger section_version_item_assert
  before insert or update or delete on section_version_item
  for each row execute function assert_section_version_item();
"""

CHILD_IMMUTABLE_TRIGGERS_SQL = """
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
"""

FAQ_STATUS = postgresql.ENUM(
    "published", "draft", name="faq_status", create_type=False
)


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

    op.create_table(
        "section_paragraph",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("content_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("version_id", "sort_order"),
        sa.CheckConstraint("sort_order between 0 and 3", name="section_paragraph_sort"),
        sa.CheckConstraint(
            "char_length(text) between 1 and 600", name="section_paragraph_length"
        ),
    )
    op.create_table(
        "process_stage",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("content_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("body", sa.Text()),
        sa.PrimaryKeyConstraint("version_id", "sort_order"),
        sa.CheckConstraint("sort_order between 0 and 3", name="process_stage_sort"),
        sa.CheckConstraint(
            "title is null or char_length(title) <= 40",
            name="process_stage_title_length",
        ),
        sa.CheckConstraint(
            "body is null or char_length(body) <= 160",
            name="process_stage_body_length",
        ),
    )
    op.create_table(
        "process_assurance",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("content_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("body", sa.Text()),
        sa.PrimaryKeyConstraint("version_id", "sort_order"),
        sa.CheckConstraint("sort_order between 0 and 2", name="process_assurance_sort"),
        sa.CheckConstraint(
            "title is null or char_length(title) <= 40",
            name="process_assurance_title_length",
        ),
        sa.CheckConstraint(
            "body is null or char_length(body) <= 160",
            name="process_assurance_body_length",
        ),
    )
    op.create_table(
        "faq_item",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("content_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text()),
        sa.Column("answer", sa.Text()),
        sa.Column(
            "status",
            FAQ_STATUS,
            nullable=False,
            server_default=sa.text("'published'::faq_status"),
        ),
        sa.PrimaryKeyConstraint("version_id", "sort_order"),
        sa.CheckConstraint(
            "question is null or char_length(question) <= 120",
            name="faq_question_length",
        ),
        sa.CheckConstraint(
            "answer is null or char_length(answer) <= 600", name="faq_answer_length"
        ),
    )
    op.create_table(
        "contact_next_step",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("content_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("body", sa.Text()),
        sa.PrimaryKeyConstraint("version_id", "sort_order"),
        sa.CheckConstraint("sort_order between 0 and 3", name="contact_next_step_sort"),
        sa.CheckConstraint(
            "title is null or char_length(title) <= 40",
            name="contact_next_step_title_length",
        ),
        sa.CheckConstraint(
            "body is null or char_length(body) <= 160",
            name="contact_next_step_body_length",
        ),
    )
    op.create_table(
        "section_version_item",
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("content_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("item_kind", CONTENT_KIND, nullable=False),
        sa.Column("sort_order", sa.Integer()),
        sa.PrimaryKeyConstraint("version_id", "item_id", name="section_version_item_pk"),
        sa.ForeignKeyConstraint(
            ["item_id", "item_kind"],
            ["content_item.id", "content_item.kind"],
            name="section_version_item_fk",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "item_kind in ('service_group', 'project', 'proof_figure', 'testimonial')",
            name="section_version_item_kind",
        ),
        sa.CheckConstraint(
            "sort_order is null or sort_order >= 0", name="section_version_item_sort"
        ),
        sa.CheckConstraint(
            "(item_kind = 'project') = (sort_order is null)",
            name="section_version_item_order",
        ),
    )

    op.create_index(
        "section_version_item_order_key",
        "section_version_item",
        ["version_id", "sort_order"],
        unique=True,
        postgresql_where=sa.text("sort_order is not null"),
    )
    op.create_index(
        "section_version_item_lookup_idx", "section_version_item", ["item_id"]
    )

    op.execute(ASSERT_PAGE_SECTION_ROW_SQL)
    op.execute(CONTENT_ITEM_PAGE_SECTION_ROW_TRIGGER_SQL)
    op.execute(SECTION_VERSION_IMMUTABLE_TRIGGER_SQL)
    op.execute(ASSERT_SECTION_CHILD_SQL)
    op.execute(SECTION_CHILD_TRIGGERS_SQL)
    op.execute(ASSERT_SECTION_VERSION_ITEM_SQL)
    op.execute(SECTION_VERSION_ITEM_ASSERT_TRIGGER_SQL)
    op.execute(CHILD_IMMUTABLE_TRIGGERS_SQL)


def downgrade() -> None:
    # The explicit trigger drops document the pairs. `assert_page_section_row` goes after
    # its trigger and before the table it reads; `prevent_published_content_mutation`
    # belongs to 0004 and stays. The child guards go before their functions, and the
    # children before `section_version`, which they read.
    op.execute("drop trigger section_version_item_immutable on section_version_item")
    op.execute("drop trigger contact_next_step_immutable on contact_next_step")
    op.execute("drop trigger faq_item_immutable on faq_item")
    op.execute("drop trigger process_assurance_immutable on process_assurance")
    op.execute("drop trigger process_stage_immutable on process_stage")
    op.execute("drop trigger section_paragraph_immutable on section_paragraph")
    op.execute("drop trigger section_version_item_assert on section_version_item")
    op.execute("drop trigger contact_next_step_section on contact_next_step")
    op.execute("drop trigger faq_item_section on faq_item")
    op.execute("drop trigger process_assurance_section on process_assurance")
    op.execute("drop trigger process_stage_section on process_stage")
    op.execute("drop trigger section_paragraph_section on section_paragraph")
    op.execute("drop function assert_section_version_item()")
    op.execute("drop function assert_section_child()")
    op.drop_table("section_version_item")
    op.drop_table("contact_next_step")
    op.drop_table("faq_item")
    op.drop_table("process_assurance")
    op.drop_table("process_stage")
    op.drop_table("section_paragraph")
    op.execute("drop trigger content_item_page_section_row on content_item")
    op.execute("drop trigger section_version_immutable on section_version")
    op.execute("drop function assert_page_section_row()")
    op.drop_table("section_version")
    op.drop_table("page_section")
