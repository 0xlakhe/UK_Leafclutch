"""Extensions and every enum type.

The SQL is copied from Backend/docs/DATABASE.md §Enums, including the `site_logo` role.
Revision ID: 0001_extensions_enums
Revises:
Create Date: 2026-11-27

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_extensions_enums"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS_SQL = """
create extension if not exists pgcrypto;
create extension if not exists citext;

create type staff_role as enum ('admin', 'editor');

create type content_kind as enum (
  'landing_page',
  'page_section',
  'legal_page',
  'service_group',
  'service',
  'project',
  'proof_figure',
  'testimonial',
  'client_logo',
  'settings'
);

create type page_section_key as enum (
  'hero',
  'proof',
  'services',
  'not-sure',
  'work',
  'process',
  'about',
  'testimonials',
  'faqs',
  'contact'
);

create type version_status as enum ('draft', 'in_review', 'published');

create type approval_scope as enum (
  'client_name',
  'result',
  'mark',
  'screenshots',
  'quote',
  'figure'
);

create type media_visibility as enum ('public', 'private');

create type media_role as enum (
  'project_image',
  'about_image',
  'og_image',
  'client_logo',
  'site_logo'
);

create type enquiry_status as enum ('new', 'in_progress', 'closed');

create type faq_status as enum ('published', 'draft');

create type legal_block_kind as enum ('h2', 'p', 'ul', 'table');

create type email_kind as enum ('enquiry_alert', 'enquiry_confirmation');

create type email_status as enum ('pending', 'sent', 'failed', 'dead');

create type revalidation_status as enum ('pending', 'sent', 'failed', 'dead');
"""


def upgrade() -> None:
    op.execute(ENUMS_SQL)


def downgrade() -> None:
    # Drop the enum types only. Extensions are shared database objects: they may predate
    # this revision or be used by another schema, so removing them on downgrade would fail
    # or break that schema. The upgrade's "if not exists" makes re-applying them safe.
    op.execute("drop type revalidation_status")
    op.execute("drop type email_status")
    op.execute("drop type email_kind")
    op.execute("drop type legal_block_kind")
    op.execute("drop type faq_status")
    op.execute("drop type enquiry_status")
    op.execute("drop type media_role")
    op.execute("drop type media_visibility")
    op.execute("drop type approval_scope")
    op.execute("drop type version_status")
    op.execute("drop type page_section_key")
    op.execute("drop type content_kind")
    op.execute("drop type staff_role")
