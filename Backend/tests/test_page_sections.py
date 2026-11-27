"""The page section, list and reference tables' constraints, guards and cascade rules.

Every test runs inside the ``db`` transaction and is rolled back by the fixture. The
fixtures insert the auth user and staff rows the foreign keys reference, then the items,
versions, section and child rows the case needs. No row is committed.

The deferred constraint trigger is exercised by switching it to immediate inside a
savepoint: the savepoint's rollback keeps the outer test transaction clean, and the raised
``DBAPIError`` is the failure a real commit would produce.

The SQL is pinned twice: behaviour is exercised through inserts, updates and deletes, and
the installed constraint, index, trigger and function definitions are compared with
Backend/docs/DATABASE.md so a weakened expression fails a test even where a behaviour case
happens not to reach it.
"""

import uuid
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import (
    auth_users,
    contact_next_step,
    content_item,
    content_version,
    faq_item,
    media,
    page_section,
    process_assurance,
    process_stage,
    section_paragraph,
    section_version,
    section_version_item,
    staff,
)

PAGE_SECTION_NEEDS_ROW = "page section item .* needs a page_section row"
IMMUTABLE_CONTENT = "published version content is immutable"
ROW_BELONGS = "row belongs to section .*"
REFERENCE_MOVE = "a section reference cannot move between versions or items"
REFERENCE_NOT_SECTION = "references belong to a page section version"
PUBLISHED_SECTION = "published section version is immutable"
SECTION_ITEM_MISSING = "section item has no page_section row"
PAGE_SECTION_LOST = "page section item .* lost its page_section row"
PAGE_SECTION_CHANGED = "page section item .* changed its page_section row"
PAGE_SECTION_POSITION = "page_section identity and position cannot change"
SECTION_VERSION_KEY_MOVED = "section version key cannot change"
VERSION_MOVE = "a version cannot move between items"
SECTION_VERSION_WRONG_ITEM = "section version belongs to a page section"
SECTION_VERSION_KEY_MISMATCH = "section version key .* does not match its section .*"
SECTION_ITEM_WITH_VERSIONS = "a section item with versions cannot change kind"

# The ten keys in the order PRD §5 lists them. This is the landing page's reading order.
PRD_SECTIONS = [
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
]

# The five list tables, the section key that owns each, a valid row and the column an edit
# changes. `section_version_item` is a reference table and is exercised separately.
SECTION_CHILD_TABLES: dict[str, sa.Table] = {
    "contact_next_step": contact_next_step,
    "faq_item": faq_item,
    "process_assurance": process_assurance,
    "process_stage": process_stage,
    "section_paragraph": section_paragraph,
}

CHILD_SECTION_KEY: dict[str, str] = {
    "contact_next_step": "contact",
    "faq_item": "faqs",
    "process_assurance": "process",
    "process_stage": "process",
    "section_paragraph": "about",
}

CHILD_ROW: dict[str, dict[str, object]] = {
    "contact_next_step": {"title": "Start a conversation", "body": "Send us the brief"},
    "faq_item": {"question": "How long does it take?", "answer": "It depends."},
    "process_assurance": {"title": "Fixed price", "body": "Agreed before work starts"},
    "process_stage": {"title": "Discovery", "body": "We read the brief"},
    "section_paragraph": {"text": "We are a small studio."},
}

CHILD_EDIT: dict[str, dict[str, object]] = {
    "contact_next_step": {"title": "Edited next step"},
    "faq_item": {"question": "Edited question?"},
    "process_assurance": {"title": "Edited assurance"},
    "process_stage": {"title": "Edited stage"},
    "section_paragraph": {"text": "Edited paragraph"},
}

# The four record-backed section keys and the item kind each renders.
REFERENCE_KIND: dict[str, str] = {
    "proof": "proof_figure",
    "services": "service_group",
    "testimonials": "testimonial",
    "work": "project",
}

# The primary keys, unique constraints, checks and foreign keys as PostgreSQL renders
# them. The definitions are normalised by ``normalise_constraint`` before the comparison,
# so PostgreSQL's whitespace and decorative parentheses do not matter.
EXPECTED_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "contact_next_step_body_length": (
        "c",
        "CHECK (((body IS NULL) OR (char_length(body) <= 160)))",
    ),
    "contact_next_step_pkey": ("p", "PRIMARY KEY (version_id, sort_order)"),
    "contact_next_step_sort": (
        "c",
        "CHECK (((sort_order >= 0) AND (sort_order <= 3)))",
    ),
    "contact_next_step_title_length": (
        "c",
        "CHECK (((title IS NULL) OR (char_length(title) <= 40)))",
    ),
    "contact_next_step_version_id_fkey": (
        "f",
        "FOREIGN KEY (version_id) REFERENCES content_version(id) ON DELETE CASCADE",
    ),
    "faq_answer_length": (
        "c",
        "CHECK (((answer IS NULL) OR (char_length(answer) <= 600)))",
    ),
    "faq_item_pkey": ("p", "PRIMARY KEY (version_id, sort_order)"),
    "faq_item_version_id_fkey": (
        "f",
        "FOREIGN KEY (version_id) REFERENCES content_version(id) ON DELETE CASCADE",
    ),
    "faq_question_length": (
        "c",
        "CHECK (((question IS NULL) OR (char_length(question) <= 120)))",
    ),
    "page_section_item_fk": (
        "f",
        "FOREIGN KEY (item_id, kind) REFERENCES content_item(id, kind) ON DELETE CASCADE",
    ),
    "page_section_key_unique": ("u", "UNIQUE (page_id, section_key)"),
    "page_section_kind": ("c", "CHECK ((kind = 'page_section'::content_kind))"),
    "page_section_order_unique": ("u", "UNIQUE (page_id, sort_order)"),
    "page_section_page_fk": (
        "f",
        "FOREIGN KEY (page_id, page_kind) REFERENCES content_item(id, kind) "
        "ON DELETE CASCADE",
    ),
    "page_section_page_kind": (
        "c",
        "CHECK ((page_kind = 'landing_page'::content_kind))",
    ),
    "page_section_pkey": ("p", "PRIMARY KEY (item_id)"),
    "page_section_sort": ("c", "CHECK ((sort_order >= 0))"),
    "process_assurance_body_length": (
        "c",
        "CHECK (((body IS NULL) OR (char_length(body) <= 160)))",
    ),
    "process_assurance_pkey": ("p", "PRIMARY KEY (version_id, sort_order)"),
    "process_assurance_sort": (
        "c",
        "CHECK (((sort_order >= 0) AND (sort_order <= 2)))",
    ),
    "process_assurance_title_length": (
        "c",
        "CHECK (((title IS NULL) OR (char_length(title) <= 40)))",
    ),
    "process_assurance_version_id_fkey": (
        "f",
        "FOREIGN KEY (version_id) REFERENCES content_version(id) ON DELETE CASCADE",
    ),
    "process_stage_body_length": (
        "c",
        "CHECK (((body IS NULL) OR (char_length(body) <= 160)))",
    ),
    "process_stage_pkey": ("p", "PRIMARY KEY (version_id, sort_order)"),
    "process_stage_sort": (
        "c",
        "CHECK (((sort_order >= 0) AND (sort_order <= 3)))",
    ),
    "process_stage_title_length": (
        "c",
        "CHECK (((title IS NULL) OR (char_length(title) <= 40)))",
    ),
    "process_stage_version_id_fkey": (
        "f",
        "FOREIGN KEY (version_id) REFERENCES content_version(id) ON DELETE CASCADE",
    ),
    "section_paragraph_length": (
        "c",
        "CHECK (((char_length(text) >= 1) AND (char_length(text) <= 600)))",
    ),
    "section_paragraph_pkey": ("p", "PRIMARY KEY (version_id, sort_order)"),
    "section_paragraph_sort": (
        "c",
        "CHECK (((sort_order >= 0) AND (sort_order <= 3)))",
    ),
    "section_paragraph_version_id_fkey": (
        "f",
        "FOREIGN KEY (version_id) REFERENCES content_version(id) ON DELETE CASCADE",
    ),
    "section_version_body_key": (
        "c",
        "CHECK (((section_key = ANY (ARRAY['hero'::page_section_key, "
        "'not-sure'::page_section_key, 'contact'::page_section_key])) OR "
        "(body IS NULL)))",
    ),
    "section_version_cta_key": (
        "c",
        "CHECK (((section_key = 'not-sure'::page_section_key) OR ((cta_label IS NULL) "
        "AND (cta_href IS NULL))))",
    ),
    "section_version_cta_label_length": (
        "c",
        "CHECK ((((primary_label IS NULL) OR (char_length(primary_label) <= 30)) AND "
        "((secondary_label IS NULL) OR (char_length(secondary_label) <= 30)) AND "
        "((cta_label IS NULL) OR (char_length(cta_label) <= 30))))",
    ),
    "section_version_eyebrow_key": (
        "c",
        "CHECK (((section_key = 'hero'::page_section_key) OR (eyebrow IS NULL)))",
    ),
    "section_version_heading_key": (
        "c",
        "CHECK (((section_key <> 'proof'::page_section_key) OR (heading IS NULL)))",
    ),
    "section_version_heading_length": (
        "c",
        "CHECK (((heading IS NULL) OR (char_length(heading) <= 70)))",
    ),
    "section_version_hero_ctas": (
        "c",
        "CHECK (((section_key = 'hero'::page_section_key) OR ((primary_label IS NULL) "
        "AND (primary_href IS NULL) AND (secondary_label IS NULL) AND "
        "(secondary_href IS NULL))))",
    ),
    "section_version_href_length": (
        "c",
        "CHECK ((((primary_href IS NULL) OR (char_length(primary_href) <= 200)) AND "
        "((secondary_href IS NULL) OR (char_length(secondary_href) <= 200)) AND "
        "((cta_href IS NULL) OR (char_length(cta_href) <= 200))))",
    ),
    "section_version_image_id_fkey": (
        "f",
        "FOREIGN KEY (image_id) REFERENCES media(id) ON DELETE RESTRICT",
    ),
    "section_version_image_key": (
        "c",
        "CHECK (((section_key = 'about'::page_section_key) OR (image_id IS NULL)))",
    ),
    "section_version_intro_key": (
        "c",
        "CHECK (((section_key = ANY (ARRAY['services'::page_section_key, "
        "'work'::page_section_key, 'process'::page_section_key])) OR (intro IS NULL)))",
    ),
    "section_version_item_fk": (
        "f",
        "FOREIGN KEY (item_id, item_kind) REFERENCES content_item(id, kind) "
        "ON DELETE RESTRICT",
    ),
    "section_version_item_kind": (
        "c",
        "CHECK ((item_kind = ANY (ARRAY['service_group'::content_kind, "
        "'project'::content_kind, 'proof_figure'::content_kind, "
        "'testimonial'::content_kind])))",
    ),
    "section_version_item_order": (
        "c",
        "CHECK (((item_kind = 'project'::content_kind) = (sort_order IS NULL)))",
    ),
    "section_version_item_pk": ("p", "PRIMARY KEY (version_id, item_id)"),
    "section_version_item_sort": (
        "c",
        "CHECK (((sort_order IS NULL) OR (sort_order >= 0)))",
    ),
    "section_version_item_version_id_fkey": (
        "f",
        "FOREIGN KEY (version_id) REFERENCES content_version(id) ON DELETE CASCADE",
    ),
    "section_version_nav_key": (
        "c",
        "CHECK (((section_key = ANY (ARRAY['services'::page_section_key, "
        "'work'::page_section_key, 'process'::page_section_key, "
        "'about'::page_section_key, 'contact'::page_section_key])) OR "
        "(nav_label IS NULL)))",
    ),
    "section_version_pkey": ("p", "PRIMARY KEY (version_id)"),
    "section_version_privacy_key": (
        "c",
        "CHECK (((section_key = 'contact'::page_section_key) OR ((privacy_text IS NULL) "
        "AND (privacy_link_label IS NULL))))",
    ),
    "section_version_version_id_fkey": (
        "f",
        "FOREIGN KEY (version_id) REFERENCES content_version(id) ON DELETE CASCADE",
    ),
}

# Every index on the eight tables, including the ones backing a constraint, so an extra
# index fails the comparison as well as a changed expression or predicate.
EXPECTED_INDEXES: dict[str, str] = {
    "contact_next_step_pkey": (
        "CREATE UNIQUE INDEX contact_next_step_pkey ON public.contact_next_step USING "
        "btree (version_id, sort_order)"
    ),
    "faq_item_pkey": (
        "CREATE UNIQUE INDEX faq_item_pkey ON public.faq_item USING btree "
        "(version_id, sort_order)"
    ),
    "page_section_key_unique": (
        "CREATE UNIQUE INDEX page_section_key_unique ON public.page_section USING btree "
        "(page_id, section_key)"
    ),
    "page_section_order_unique": (
        "CREATE UNIQUE INDEX page_section_order_unique ON public.page_section USING "
        "btree (page_id, sort_order)"
    ),
    "page_section_page_idx": (
        "CREATE INDEX page_section_page_idx ON public.page_section USING btree "
        "(page_id, sort_order)"
    ),
    "page_section_pkey": (
        "CREATE UNIQUE INDEX page_section_pkey ON public.page_section USING btree "
        "(item_id)"
    ),
    "process_assurance_pkey": (
        "CREATE UNIQUE INDEX process_assurance_pkey ON public.process_assurance USING "
        "btree (version_id, sort_order)"
    ),
    "process_stage_pkey": (
        "CREATE UNIQUE INDEX process_stage_pkey ON public.process_stage USING btree "
        "(version_id, sort_order)"
    ),
    "section_paragraph_pkey": (
        "CREATE UNIQUE INDEX section_paragraph_pkey ON public.section_paragraph USING "
        "btree (version_id, sort_order)"
    ),
    "section_version_item_lookup_idx": (
        "CREATE INDEX section_version_item_lookup_idx ON public.section_version_item "
        "USING btree (item_id)"
    ),
    "section_version_item_order_key": (
        "CREATE UNIQUE INDEX section_version_item_order_key ON "
        "public.section_version_item USING btree (version_id, sort_order) "
        "WHERE (sort_order IS NOT NULL)"
    ),
    "section_version_item_pk": (
        "CREATE UNIQUE INDEX section_version_item_pk ON public.section_version_item "
        "USING btree (version_id, item_id)"
    ),
    "section_version_pkey": (
        "CREATE UNIQUE INDEX section_version_pkey ON public.section_version USING btree "
        "(version_id)"
    ),
}

# ``tgtype`` bits: 1 row, 2 before, 4 insert, 8 delete, 16 update. The tuple adds the
# constraint-trigger flags, which the content spine's triggers do not carry.
EXPECTED_TRIGGERS: dict[str, tuple[str, bool, bool, bool, bool, bool, bool, bool]] = {
    "contact_next_step_immutable": (
        "contact_next_step",
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ),
    "contact_next_step_section": (
        "contact_next_step",
        True,
        True,
        True,
        False,
        True,
        False,
        False,
    ),
    "content_item_page_section_row": (
        "content_item",
        True,
        False,
        True,
        False,
        True,
        True,
        True,
    ),
    "content_version_item_frozen": (
        "content_version",
        True,
        True,
        False,
        False,
        True,
        False,
        False,
    ),
    "faq_item_immutable": (
        "faq_item",
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ),
    "faq_item_section": (
        "faq_item",
        True,
        True,
        True,
        False,
        True,
        False,
        False,
    ),
    "page_section_immutable": (
        "page_section",
        True,
        True,
        False,
        False,
        True,
        False,
        False,
    ),
    "page_section_row_kept": (
        "page_section",
        True,
        False,
        False,
        True,
        False,
        True,
        True,
    ),
    "process_assurance_immutable": (
        "process_assurance",
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ),
    "process_assurance_section": (
        "process_assurance",
        True,
        True,
        True,
        False,
        True,
        False,
        False,
    ),
    "process_stage_immutable": (
        "process_stage",
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ),
    "process_stage_section": (
        "process_stage",
        True,
        True,
        True,
        False,
        True,
        False,
        False,
    ),
    "section_paragraph_immutable": (
        "section_paragraph",
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ),
    "section_paragraph_section": (
        "section_paragraph",
        True,
        True,
        True,
        False,
        True,
        False,
        False,
    ),
    "section_version_immutable": (
        "section_version",
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ),
    "section_version_item_assert": (
        "section_version_item",
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ),
    "section_version_item_immutable": (
        "section_version_item",
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ),
    "section_version_key_guard": (
        "section_version",
        True,
        True,
        True,
        False,
        True,
        False,
        False,
    ),
}

# Every section key with a row that uses only the columns its key allows. About also needs
# a media row, inserted by the test.
SECTION_COPY: list[tuple[str, dict[str, str], bool]] = [
    (
        "hero",
        {
            "heading": "Hero heading",
            "body": "Hero body",
            "eyebrow": "Eyebrow",
            "primary_label": "Start a project",
            "primary_href": "/contact",
            "secondary_label": "See our work",
            "secondary_href": "/work",
        },
        False,
    ),
    ("proof", {}, False),
    (
        "services",
        {"heading": "Services", "intro": "What we do", "nav_label": "Services"},
        False,
    ),
    (
        "not-sure",
        {
            "heading": "Not sure",
            "body": "Where to start",
            "cta_label": "Talk to us",
            "cta_href": "/contact",
        },
        False,
    ),
    (
        "work",
        {"heading": "Work", "intro": "Selected projects", "nav_label": "Work"},
        False,
    ),
    (
        "process",
        {"heading": "Process", "intro": "How we work", "nav_label": "Process"},
        False,
    ),
    ("about", {"heading": "About", "nav_label": "About"}, True),
    ("testimonials", {"heading": "Testimonials"}, False),
    ("faqs", {"heading": "FAQs"}, False),
    (
        "contact",
        {
            "heading": "Contact",
            "body": "Tell us about the project",
            "nav_label": "Contact",
            "privacy_text": "We use this to reply.",
            "privacy_link_label": "Privacy notice",
        },
        False,
    ),
]


def normalise(definition: str) -> str:
    """Lower-case and collapse whitespace so only the meaning is compared."""
    return " ".join(definition.lower().split())


def normalise_constraint(definition: str) -> str:
    """Lower-case and collapse whitespace; PostgreSQL's parentheses are part of the pin."""
    return " ".join(definition.lower().split())


def add_staff(db: Connection) -> uuid.UUID:
    """Insert the auth user and staff row that the created_by and uploaded_by FKs need."""
    user_id = uuid.uuid4()
    db.execute(sa.insert(auth_users).values(id=user_id))
    db.execute(
        sa.insert(staff).values(
            user_id=user_id,
            email=f"{user_id}@example.com",
            display_name="Section editor",
            role="editor",
        )
    )
    return user_id


def item_values(created_by: uuid.UUID, **overrides: object) -> dict[str, object]:
    """A valid item for its kind, with ``overrides`` applied."""
    kind = overrides.get("kind", "landing_page")
    values: dict[str, object] = {
        "kind": kind,
        "path": "/" if kind in ("landing_page", "legal_page") else None,
        "created_by": created_by,
    }
    values.update(overrides)
    return values


def add_item(db: Connection, created_by: uuid.UUID, **overrides: object) -> uuid.UUID:
    return db.execute(
        sa.insert(content_item)
        .values(**item_values(created_by, **overrides))
        .returning(content_item.c.id)
    ).scalar_one()


def version_values(
    item_id: uuid.UUID, created_by: uuid.UUID, **overrides: object
) -> dict[str, object]:
    """A valid draft version, with ``overrides`` applied."""
    values: dict[str, object] = {
        "item_id": item_id,
        "version_number": 1,
        "created_by": created_by,
    }
    values.update(overrides)
    return values


def add_version(
    db: Connection, item_id: uuid.UUID, created_by: uuid.UUID, **overrides: object
) -> uuid.UUID:
    return db.execute(
        sa.insert(content_version)
        .values(**version_values(item_id, created_by, **overrides))
        .returning(content_version.c.id)
    ).scalar_one()


def publish_version(db: Connection, version_id: uuid.UUID, published_by: uuid.UUID) -> None:
    """The publish update: draft or in-review to published, with both publish fields."""
    db.execute(
        sa.update(content_version)
        .where(content_version.c.id == version_id)
        .values(status="published", published_at=datetime.now(UTC), published_by=published_by)
    )


def add_page(db: Connection, editor: uuid.UUID) -> uuid.UUID:
    """A landing page with a unique path so two pages can coexist in one test."""
    return add_item(db, editor, kind="landing_page", path=f"/page-{uuid.uuid4()}")


def add_section(
    db: Connection,
    editor: uuid.UUID,
    section_key: str = "hero",
    sort_order: int = 0,
    page_id: uuid.UUID | None = None,
    **overrides: object,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert a page (unless given), a page_section item and its page_section row."""
    page_id = page_id if page_id is not None else add_page(db, editor)
    item_id = add_item(db, editor, kind="page_section")
    values: dict[str, object] = {
        "item_id": item_id,
        "page_id": page_id,
        "section_key": section_key,
        "sort_order": sort_order,
    }
    values.update(overrides)
    db.execute(sa.insert(page_section).values(**values))
    return page_id, item_id


def add_section_version(
    db: Connection,
    editor: uuid.UUID,
    section_key: str = "hero",
    sort_order: int = 0,
    page_id: uuid.UUID | None = None,
    **overrides: object,
) -> uuid.UUID:
    """Insert a section item, its draft version and the section_version row."""
    _, item_id = add_section(db, editor, section_key, sort_order, page_id)
    version_id = add_version(db, item_id, editor)
    values: dict[str, object] = {"version_id": version_id, "section_key": section_key}
    values.update(overrides)
    db.execute(sa.insert(section_version).values(**values))
    return version_id


def add_child_row(
    db: Connection, version_id: uuid.UUID, table_name: str, **overrides: object
) -> None:
    """Insert a valid list row of ``table_name`` on ``version_id``, with overrides."""
    values: dict[str, object] = {
        "version_id": version_id,
        "sort_order": 0,
        **CHILD_ROW[table_name],
    }
    values.update(overrides)
    db.execute(sa.insert(SECTION_CHILD_TABLES[table_name]).values(**values))


def add_child_version(
    db: Connection, editor: uuid.UUID, table_name: str, **overrides: object
) -> uuid.UUID:
    """Insert the owning section's version and one valid list row on it."""
    version_id = add_section_version(db, editor, CHILD_SECTION_KEY[table_name])
    add_child_row(db, version_id, table_name, **overrides)
    return version_id


def add_record_item(db: Connection, editor: uuid.UUID, item_kind: str) -> uuid.UUID:
    """A record item the sections can reference; projects and services need a slug."""
    overrides: dict[str, object] = {}
    if item_kind in ("service", "project"):
        overrides["slug"] = f"{item_kind}-{uuid.uuid4()}"
    return add_item(db, editor, kind=item_kind, **overrides)


def add_reference(
    db: Connection,
    version_id: uuid.UUID,
    item_id: uuid.UUID,
    item_kind: str,
    sort_order: int | None,
) -> None:
    db.execute(
        sa.insert(section_version_item).values(
            version_id=version_id,
            item_id=item_id,
            item_kind=item_kind,
            sort_order=sort_order,
        )
    )


def media_values(uploaded_by: uuid.UUID, **overrides: object) -> dict[str, object]:
    """A valid staged image row, with ``overrides`` applied."""
    values: dict[str, object] = {
        "visibility": "private",
        "bucket": "media-staging",
        "object_path": f"{uuid.uuid4()}.webp",
        "mime_type": "image/webp",
        "size_bytes": 1024,
        "width": 800,
        "height": 600,
        "alt": "A descriptive alt",
        "checksum_sha256": bytes(32),
        "uploaded_by": uploaded_by,
    }
    values.update(overrides)
    return values


def add_media(db: Connection, uploaded_by: uuid.UUID) -> uuid.UUID:
    return db.execute(
        sa.insert(media).values(**media_values(uploaded_by)).returning(media.c.id)
    ).scalar_one()


def select_section_version(db: Connection, version_id: uuid.UUID) -> sa.Row:
    return db.execute(
        sa.select(section_version).where(section_version.c.version_id == version_id)
    ).one()


def count_rows(db: Connection, table: sa.Table, *conditions: object) -> int:
    statement = sa.select(sa.func.count()).select_from(table)
    if conditions:
        statement = statement.where(*conditions)
    return db.execute(statement).scalar_one()


def test_the_section_tables_start_empty(db: Connection) -> None:
    tables = [
        *SECTION_CHILD_TABLES.values(),
        section_version_item,
        section_version,
        page_section,
    ]
    for table in tables:
        rows = db.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()
        assert rows == 0, (
            f"stale committed rows in {table.name} from an earlier run; delete them before "
            "rerunning the suite"
        )


def test_a_page_section_item_without_its_row_fails_when_the_constraint_is_checked(
    db: Connection,
) -> None:
    editor = add_staff(db)

    with pytest.raises(DBAPIError, match=PAGE_SECTION_NEEDS_ROW):
        with db.begin_nested():
            add_item(db, editor, kind="page_section")
            db.execute(
                sa.text("set constraints content_item_page_section_row immediate")
            )


def test_a_page_section_item_with_its_row_passes_the_immediate_check(db: Connection) -> None:
    editor = add_staff(db)

    with db.begin_nested():
        _, item_id = add_section(db, editor)
        db.execute(sa.text("set constraints content_item_page_section_row immediate"))

    assert count_rows(db, page_section, page_section.c.item_id == item_id) == 1


def test_a_page_section_row_takes_the_kind_defaults(db: Connection) -> None:
    editor = add_staff(db)
    _, item_id = add_section(db, editor)

    row = db.execute(
        sa.select(page_section).where(page_section.c.item_id == item_id)
    ).one()
    assert row.kind == "page_section"
    assert row.page_kind == "landing_page"
    assert row.sort_order == 0


def test_two_sections_of_one_page_cannot_share_a_key(db: Connection) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    add_section(db, editor, "hero", 0, page_id)

    with pytest.raises(IntegrityError, match="page_section_key_unique"):
        with db.begin_nested():
            add_section(db, editor, "hero", 1, page_id)

    # Another page may use the same key.
    add_section(db, editor, "hero", 0)


def test_two_sections_of_one_page_cannot_share_a_place(db: Connection) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    add_section(db, editor, "hero", 0, page_id)

    with pytest.raises(IntegrityError, match="page_section_order_unique"):
        with db.begin_nested():
            add_section(db, editor, "proof", 0, page_id)

    # Another page may use the same place.
    add_section(db, editor, "proof", 0)


def test_a_section_sort_order_cannot_be_negative(db: Connection) -> None:
    editor = add_staff(db)

    with pytest.raises(IntegrityError, match="page_section_sort"):
        with db.begin_nested():
            add_section(db, editor, "hero", -1)


def test_the_page_section_kind_is_pinned(db: Connection) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    item_id = add_item(db, editor, kind="page_section")

    with pytest.raises(IntegrityError, match="page_section_kind"):
        with db.begin_nested():
            db.execute(
                sa.insert(page_section).values(
                    item_id=item_id,
                    page_id=page_id,
                    kind="landing_page",
                    section_key="hero",
                    sort_order=0,
                )
            )


def test_the_page_kind_is_pinned(db: Connection) -> None:
    editor = add_staff(db)
    other_section = add_item(db, editor, kind="page_section")
    item_id = add_item(db, editor, kind="page_section")

    with pytest.raises(IntegrityError, match="page_section_page_kind"):
        with db.begin_nested():
            db.execute(
                sa.insert(page_section).values(
                    item_id=item_id,
                    page_id=other_section,
                    page_kind="page_section",
                    section_key="hero",
                    sort_order=0,
                )
            )


def test_a_section_item_must_be_a_page_section(db: Connection) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    other_page = add_page(db, editor)

    with pytest.raises(IntegrityError, match="page_section_item_fk"):
        with db.begin_nested():
            db.execute(
                sa.insert(page_section).values(
                    item_id=other_page,
                    page_id=page_id,
                    section_key="hero",
                    sort_order=0,
                )
            )


def test_a_section_page_must_be_a_landing_page(db: Connection) -> None:
    editor = add_staff(db)
    service_id = add_item(db, editor, kind="service", slug="branding")
    item_id = add_item(db, editor, kind="page_section")

    with pytest.raises(IntegrityError, match="page_section_page_fk"):
        with db.begin_nested():
            db.execute(
                sa.insert(page_section).values(
                    item_id=item_id,
                    page_id=service_id,
                    section_key="hero",
                    sort_order=0,
                )
            )


def test_deleting_a_landing_page_with_sections_is_refused(db: Connection) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    add_section(db, editor, "hero", 0, page_id)
    add_section(db, editor, "proof", 1, page_id)

    with pytest.raises(DBAPIError, match=PAGE_SECTION_LOST):
        with db.begin_nested():
            db.execute(sa.delete(content_item).where(content_item.c.id == page_id))
            db.execute(sa.text("set constraints page_section_row_kept immediate"))

    assert count_rows(db, content_item, content_item.c.id == page_id) == 1
    assert count_rows(db, page_section, page_section.c.page_id == page_id) == 2


def test_deleting_the_sections_then_the_landing_page_succeeds(db: Connection) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    _, hero_id = add_section(db, editor, "hero", 0, page_id)
    _, proof_id = add_section(db, editor, "proof", 1, page_id)

    for item_id in (hero_id, proof_id):
        db.execute(sa.delete(content_item).where(content_item.c.id == item_id))

    db.execute(sa.delete(content_item).where(content_item.c.id == page_id))
    db.execute(
        sa.text(
            "set constraints content_item_page_section_row, "
            "page_section_row_kept immediate"
        )
    )

    assert count_rows(db, content_item, content_item.c.id == page_id) == 0
    assert count_rows(db, page_section, page_section.c.page_id == page_id) == 0


def test_a_page_section_item_created_and_deleted_in_one_transaction_passes(
    db: Connection,
) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    item_id = add_item(db, editor, kind="page_section")
    db.execute(
        sa.insert(page_section).values(
            item_id=item_id,
            page_id=page_id,
            section_key="hero",
            sort_order=0,
        )
    )

    db.execute(sa.delete(content_item).where(content_item.c.id == item_id))
    db.execute(sa.text("set constraints content_item_page_section_row immediate"))

    assert count_rows(db, content_item, content_item.c.id == item_id) == 0
    assert count_rows(db, page_section, page_section.c.item_id == item_id) == 0


def test_deleting_a_section_item_cascades_its_row(db: Connection) -> None:
    editor = add_staff(db)
    page_id, item_id = add_section(db, editor)

    db.execute(sa.delete(content_item).where(content_item.c.id == item_id))
    db.execute(sa.text("set constraints page_section_row_kept immediate"))

    assert count_rows(db, page_section, page_section.c.item_id == item_id) == 0
    assert count_rows(db, page_section, page_section.c.page_id == page_id) == 0


def test_a_live_page_section_row_cannot_be_deleted(db: Connection) -> None:
    editor = add_staff(db)
    _, item_id = add_section(db, editor)

    with pytest.raises(DBAPIError, match=PAGE_SECTION_LOST):
        with db.begin_nested():
            db.execute(sa.delete(page_section).where(page_section.c.item_id == item_id))
            db.execute(sa.text("set constraints page_section_row_kept immediate"))

    assert count_rows(db, page_section, page_section.c.item_id == item_id) == 1


def test_a_page_section_row_can_be_deleted_and_recreated_in_one_transaction(
    db: Connection,
) -> None:
    editor = add_staff(db)
    page_id, item_id = add_section(db, editor)

    db.execute(sa.delete(page_section).where(page_section.c.item_id == item_id))
    db.execute(
        sa.insert(page_section).values(
            item_id=item_id,
            page_id=page_id,
            section_key="hero",
            sort_order=0,
        )
    )
    db.execute(sa.text("set constraints page_section_row_kept immediate"))

    assert count_rows(db, page_section, page_section.c.item_id == item_id) == 1


@pytest.mark.parametrize("column", ["page_id", "section_key", "sort_order"])
def test_a_page_section_row_cannot_be_recreated_with_different_values(
    db: Connection, column: str
) -> None:
    editor = add_staff(db)
    page_id, item_id = add_section(db, editor, "hero", 0)
    row: dict[str, object] = {
        "item_id": item_id,
        "page_id": page_id,
        "section_key": "hero",
        "sort_order": 0,
    }
    row[column] = {
        "page_id": add_page(db, editor),
        "section_key": "contact",
        "sort_order": 1,
    }[column]

    with pytest.raises(DBAPIError, match=PAGE_SECTION_CHANGED):
        with db.begin_nested():
            db.execute(sa.delete(page_section).where(page_section.c.item_id == item_id))
            db.execute(sa.insert(page_section).values(**row))
            db.execute(sa.text("set constraints page_section_row_kept immediate"))

    stored = db.execute(
        sa.select(
            page_section.c.page_id,
            page_section.c.section_key,
            page_section.c.sort_order,
        ).where(page_section.c.item_id == item_id)
    ).one()
    assert stored == (page_id, "hero", 0)


def test_an_item_cannot_become_a_page_section_without_a_row(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor, kind="service_group")

    with pytest.raises(DBAPIError, match=PAGE_SECTION_NEEDS_ROW):
        with db.begin_nested():
            db.execute(
                sa.update(content_item)
                .where(content_item.c.id == item_id)
                .values(kind="page_section")
            )
            db.execute(
                sa.text("set constraints content_item_page_section_row immediate")
            )

    assert (
        db.execute(
            sa.select(content_item.c.kind).where(content_item.c.id == item_id)
        ).scalar_one()
        == "service_group"
    )


@pytest.mark.parametrize("column", ["item_id", "page_id", "section_key", "sort_order"])
def test_a_page_section_identity_or_position_cannot_change(
    db: Connection, column: str
) -> None:
    editor = add_staff(db)
    page_id, item_id = add_section(db, editor, "hero", 0)
    replacements: dict[str, object] = {
        "item_id": add_item(db, editor, kind="page_section"),
        "page_id": add_page(db, editor),
        "section_key": "proof",
        "sort_order": 1,
    }

    with pytest.raises(DBAPIError, match=PAGE_SECTION_POSITION):
        with db.begin_nested():
            db.execute(
                sa.update(page_section)
                .where(page_section.c.item_id == item_id)
                .values(**{column: replacements[column]})
            )

    stored = db.execute(
        sa.select(page_section.c[column]).where(page_section.c.item_id == item_id)
    ).scalar_one()
    original: dict[str, object] = {
        "item_id": item_id,
        "page_id": page_id,
        "section_key": "hero",
        "sort_order": 0,
    }
    assert stored == original[column]


def test_a_no_op_page_section_update_is_allowed(db: Connection) -> None:
    editor = add_staff(db)
    _, item_id = add_section(db, editor, "hero", 0)

    result = db.execute(
        sa.update(page_section)
        .where(page_section.c.item_id == item_id)
        .values(section_key="hero", sort_order=0)
    )

    assert result.rowcount == 1


@pytest.mark.parametrize(
    ("section_key", "copy", "uses_image"),
    SECTION_COPY,
    ids=[case[0] for case in SECTION_COPY],
)
def test_each_section_key_accepts_its_columns(
    db: Connection,
    section_key: str,
    copy: dict[str, str],
    uses_image: bool,
) -> None:
    editor = add_staff(db)
    values: dict[str, object] = dict(copy)
    if uses_image:
        values["image_id"] = add_media(db, editor)

    version_id = add_section_version(db, editor, section_key, **values)

    row = select_section_version(db, version_id)
    assert row.section_key == section_key
    for column, value in values.items():
        assert getattr(row, column) == value


@pytest.mark.parametrize(
    ("section_key", "overrides", "constraint"),
    [
        ("hero", {"heading": "h" * 71}, "section_version_heading_length"),
        ("proof", {"heading": "Heading"}, "section_version_heading_key"),
        ("hero", {"intro": "Intro"}, "section_version_intro_key"),
        ("about", {"body": "Body"}, "section_version_body_key"),
        ("hero", {"nav_label": "Nav"}, "section_version_nav_key"),
        ("not-sure", {"eyebrow": "Eyebrow"}, "section_version_eyebrow_key"),
        (
            "not-sure",
            {"primary_label": "Start", "primary_href": "/contact"},
            "section_version_hero_ctas",
        ),
        (
            "about",
            {"primary_label": "Start", "primary_href": "/contact"},
            "section_version_hero_ctas",
        ),
        ("hero", {"cta_label": "Talk", "cta_href": "/contact"}, "section_version_cta_key"),
        ("services", {"privacy_text": "Privacy"}, "section_version_privacy_key"),
        ("services", {"image_id": "media"}, "section_version_image_key"),
        (
            "hero",
            {"primary_label": "l" * 31},
            "section_version_cta_label_length",
        ),
        ("not-sure", {"cta_label": "l" * 31}, "section_version_cta_label_length"),
        (
            "hero",
            {"primary_href": "/" + "h" * 200},
            "section_version_href_length",
        ),
        ("not-sure", {"cta_href": "/" + "h" * 200}, "section_version_href_length"),
    ],
    ids=[
        "long-heading",
        "heading-on-proof",
        "intro-off-its-keys",
        "body-off-its-keys",
        "nav-off-its-keys",
        "eyebrow-off-hero",
        "hero-ctas-off-hero",
        "about-ctas-off-about",
        "cta-off-not-sure",
        "privacy-off-contact",
        "image-off-about",
        "long-primary-label",
        "long-cta-label",
        "long-primary-href",
        "long-cta-href",
    ],
)
def test_a_section_version_check_refuses_the_row(
    db: Connection,
    section_key: str,
    overrides: dict[str, object],
    constraint: str,
) -> None:
    editor = add_staff(db)
    values = dict(overrides)
    if values.get("image_id") == "media":
        values["image_id"] = add_media(db, editor)

    with pytest.raises(IntegrityError, match=constraint):
        with db.begin_nested():
            add_section_version(db, editor, section_key, **values)


def test_a_section_version_accepts_the_length_bounds(db: Connection) -> None:
    editor = add_staff(db)

    version_id = add_section_version(
        db,
        editor,
        "hero",
        heading="h" * 70,
        primary_label="l" * 30,
        primary_href="/" + "h" * 199,
        secondary_label="l" * 30,
        secondary_href="/" + "h" * 199,
    )

    row = select_section_version(db, version_id)
    assert row.heading == "h" * 70
    assert row.primary_label == "l" * 30
    assert len(row.primary_href) == 200
    assert len(row.secondary_href) == 200


def test_an_image_used_by_a_section_cannot_be_deleted(db: Connection) -> None:
    editor = add_staff(db)
    image_id = add_media(db, editor)
    add_section_version(db, editor, "about", image_id=image_id)

    with pytest.raises(IntegrityError, match="section_version_image_id_fkey"):
        with db.begin_nested():
            db.execute(sa.delete(media).where(media.c.id == image_id))

    assert count_rows(db, media, media.c.id == image_id) == 1


def test_a_draft_section_version_can_be_edited(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "hero", heading="Before")

    db.execute(
        sa.update(section_version)
        .where(section_version.c.version_id == version_id)
        .values(heading="After")
    )

    assert select_section_version(db, version_id).heading == "After"


def test_a_published_section_version_is_frozen(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "hero", heading="Before")
    publish_version(db, version_id, editor)

    with pytest.raises(DBAPIError, match=IMMUTABLE_CONTENT):
        with db.begin_nested():
            db.execute(
                sa.update(section_version)
                .where(section_version.c.version_id == version_id)
                .values(heading="After")
            )

    with pytest.raises(DBAPIError, match=IMMUTABLE_CONTENT):
        with db.begin_nested():
            db.execute(
                sa.delete(section_version).where(
                    section_version.c.version_id == version_id
                )
            )

    assert select_section_version(db, version_id).heading == "Before"


def test_a_section_version_key_must_match_its_section(db: Connection) -> None:
    editor = add_staff(db)
    _, item_id = add_section(db, editor, "hero")
    version_id = add_version(db, item_id, editor)

    with pytest.raises(DBAPIError, match=SECTION_VERSION_KEY_MISMATCH):
        with db.begin_nested():
            db.execute(
                sa.insert(section_version).values(
                    version_id=version_id, section_key="contact"
                )
            )


def test_a_section_version_needs_its_page_section_row(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor, kind="page_section")
    version_id = add_version(db, item_id, editor)

    with pytest.raises(DBAPIError, match=SECTION_ITEM_MISSING):
        with db.begin_nested():
            db.execute(
                sa.insert(section_version).values(
                    version_id=version_id, section_key="hero"
                )
            )


def test_a_project_version_cannot_gain_a_section_version(db: Connection) -> None:
    editor = add_staff(db)
    project_id = add_item(db, editor, kind="project", slug=f"project-{uuid.uuid4()}")
    version_id = add_version(db, project_id, editor)

    with pytest.raises(DBAPIError, match=SECTION_VERSION_WRONG_ITEM):
        with db.begin_nested():
            db.execute(
                sa.insert(section_version).values(
                    version_id=version_id, section_key="hero"
                )
            )


def test_a_section_version_key_cannot_change(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "hero")

    with pytest.raises(DBAPIError, match=SECTION_VERSION_KEY_MOVED):
        with db.begin_nested():
            db.execute(
                sa.update(section_version)
                .where(section_version.c.version_id == version_id)
                .values(section_key="contact")
            )

    assert select_section_version(db, version_id).section_key == "hero"


def test_a_version_cannot_move_to_another_item(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "about")
    project_id = add_item(db, editor, kind="project", slug=f"project-{uuid.uuid4()}")

    with pytest.raises(DBAPIError, match=VERSION_MOVE):
        with db.begin_nested():
            db.execute(
                sa.update(content_version)
                .where(content_version.c.id == version_id)
                .values(item_id=project_id)
            )


def test_a_refused_version_move_leaves_the_section_version_with_its_item(
    db: Connection,
) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "about")
    project_id = add_item(db, editor, kind="project", slug=f"project-{uuid.uuid4()}")

    with pytest.raises(DBAPIError, match=VERSION_MOVE):
        with db.begin_nested():
            db.execute(
                sa.update(content_version)
                .where(content_version.c.id == version_id)
                .values(item_id=project_id)
            )

    owner = db.execute(
        sa.select(content_version.c.item_id).where(content_version.c.id == version_id)
    ).scalar_one()
    assert owner != project_id
    assert count_rows(db, page_section, page_section.c.item_id == owner) == 1
    assert select_section_version(db, version_id).section_key == "about"

    db.execute(
        sa.insert(section_paragraph).values(
            version_id=version_id, sort_order=0, text="Still about."
        )
    )
    assert (
        count_rows(db, section_paragraph, section_paragraph.c.version_id == version_id)
        == 1
    )


def test_a_section_item_with_versions_cannot_change_kind(db: Connection) -> None:
    editor = add_staff(db)
    _, item_id = add_section(db, editor, "hero")
    # Consume the insert event while the page row exists, so the case reaches the update.
    db.execute(sa.text("set constraints content_item_page_section_row immediate"))
    version_id = add_version(db, item_id, editor)
    db.execute(
        sa.insert(section_version).values(version_id=version_id, section_key="hero")
    )
    db.execute(sa.delete(page_section).where(page_section.c.item_id == item_id))

    with pytest.raises(DBAPIError, match=SECTION_ITEM_WITH_VERSIONS):
        with db.begin_nested():
            db.execute(
                sa.update(content_item)
                .where(content_item.c.id == item_id)
                .values(kind="service_group")
            )


def test_a_section_item_without_versions_can_change_kind(db: Connection) -> None:
    editor = add_staff(db)
    _, item_id = add_section(db, editor, "hero")
    db.execute(sa.text("set constraints content_item_page_section_row immediate"))
    db.execute(sa.delete(page_section).where(page_section.c.item_id == item_id))

    db.execute(
        sa.update(content_item)
        .where(content_item.c.id == item_id)
        .values(kind="service_group")
    )
    db.execute(sa.text("set constraints all immediate"))

    assert (
        db.execute(
            sa.select(content_item.c.kind).where(content_item.c.id == item_id)
        ).scalar_one()
        == "service_group"
    )


def test_deleting_a_draft_content_version_cascades_its_section_version(
    db: Connection,
) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "hero")

    db.execute(sa.delete(content_version).where(content_version.c.id == version_id))

    assert count_rows(db, section_version, section_version.c.version_id == version_id) == 0


def test_the_ten_prd_sections_read_back_in_their_order(db: Connection) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    for sort_order, section_key in enumerate(PRD_SECTIONS):
        add_section(db, editor, section_key, sort_order, page_id)

    rows = db.execute(
        sa.select(page_section.c.section_key, page_section.c.sort_order)
        .where(page_section.c.page_id == page_id)
        .order_by(page_section.c.sort_order)
    ).all()

    assert [row.section_key for row in rows] == PRD_SECTIONS
    assert [row.sort_order for row in rows] == list(range(10))


@pytest.mark.parametrize(
    ("table_name", "wrong_key"),
    [
        ("section_paragraph", "contact"),
        ("process_stage", "about"),
        ("process_assurance", "services"),
        ("faq_item", "process"),
        ("contact_next_step", "faqs"),
    ],
    ids=[
        "paragraph-on-contact",
        "stage-on-about",
        "assurance-on-services",
        "faq-on-process",
        "next-step-on-faqs",
    ],
)
def test_a_child_row_is_refused_on_the_wrong_section(
    db: Connection, table_name: str, wrong_key: str
) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, wrong_key)

    with pytest.raises(DBAPIError, match=ROW_BELONGS):
        with db.begin_nested():
            add_child_row(db, version_id, table_name)

    assert count_rows(db, SECTION_CHILD_TABLES[table_name]) == 0


@pytest.mark.parametrize("table_name", list(CHILD_SECTION_KEY), ids=list(CHILD_SECTION_KEY))
def test_a_child_row_is_accepted_by_its_owning_section(
    db: Connection, table_name: str
) -> None:
    editor = add_staff(db)
    version_id = add_child_version(db, editor, table_name)

    table = SECTION_CHILD_TABLES[table_name]
    assert count_rows(db, table, table.c.version_id == version_id) == 1


def test_an_faq_item_defaults_to_published(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_child_version(db, editor, "faq_item")

    status = db.execute(
        sa.select(faq_item.c.status).where(faq_item.c.version_id == version_id)
    ).scalar_one()

    assert status == "published"


@pytest.mark.parametrize("section_key", list(REFERENCE_KIND), ids=list(REFERENCE_KIND))
def test_each_record_section_accepts_its_item_kind(
    db: Connection, section_key: str
) -> None:
    editor = add_staff(db)
    item_kind = REFERENCE_KIND[section_key]
    version_id = add_section_version(db, editor, section_key)
    item_id = add_record_item(db, editor, item_kind)

    add_reference(
        db,
        version_id,
        item_id,
        item_kind,
        None if item_kind == "project" else 0,
    )

    assert (
        count_rows(
            db,
            section_version_item,
            section_version_item.c.version_id == version_id,
        )
        == 1
    )


@pytest.mark.parametrize(
    ("section_key", "item_kind"),
    [
        ("services", "project"),
        ("work", "service_group"),
        ("proof", "testimonial"),
        ("testimonials", "proof_figure"),
    ],
    ids=["services-project", "work-service-group", "proof-testimonial", "testimonials-figure"],
)
def test_a_section_refuses_another_item_kind(
    db: Connection, section_key: str, item_kind: str
) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, section_key)
    item_id = add_record_item(db, editor, item_kind)
    sort_order = None if item_kind == "project" else 0

    with pytest.raises(
        DBAPIError, match=f"section {section_key} cannot reference a {item_kind}"
    ):
        with db.begin_nested():
            add_reference(db, version_id, item_id, item_kind, sort_order)

    assert count_rows(db, section_version_item) == 0


def test_a_reference_cannot_be_added_to_a_published_version(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "services")
    add_reference(
        db, version_id, add_record_item(db, editor, "service_group"), "service_group", 0
    )
    publish_version(db, version_id, editor)

    with pytest.raises(DBAPIError, match=PUBLISHED_SECTION):
        with db.begin_nested():
            add_reference(
                db,
                version_id,
                add_record_item(db, editor, "service_group"),
                "service_group",
                1,
            )

    assert (
        count_rows(
            db,
            section_version_item,
            section_version_item.c.version_id == version_id,
        )
        == 1
    )


def test_a_reference_cannot_move_between_versions(db: Connection) -> None:
    editor = add_staff(db)
    first_version = add_section_version(db, editor, "services")
    second_version = add_section_version(db, editor, "services")
    item_id = add_record_item(db, editor, "service_group")
    add_reference(db, first_version, item_id, "service_group", 0)

    with pytest.raises(DBAPIError, match=REFERENCE_MOVE):
        with db.begin_nested():
            db.execute(
                sa.update(section_version_item)
                .where(section_version_item.c.version_id == first_version)
                .values(version_id=second_version)
            )


def test_a_reference_cannot_move_between_items(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "services")
    item_id = add_record_item(db, editor, "service_group")
    other_id = add_record_item(db, editor, "service_group")
    add_reference(db, version_id, item_id, "service_group", 0)

    with pytest.raises(DBAPIError, match=REFERENCE_MOVE):
        with db.begin_nested():
            db.execute(
                sa.update(section_version_item)
                .where(section_version_item.c.item_id == item_id)
                .values(item_id=other_id)
            )


def test_a_reference_must_belong_to_a_page_section_version(db: Connection) -> None:
    editor = add_staff(db)
    project_id = add_record_item(db, editor, "project")
    version_id = add_version(db, project_id, editor)
    group_id = add_record_item(db, editor, "service_group")

    with pytest.raises(DBAPIError, match=REFERENCE_NOT_SECTION):
        with db.begin_nested():
            add_reference(db, version_id, group_id, "service_group", 0)


def test_a_section_item_without_its_row_cannot_take_references(db: Connection) -> None:
    editor = add_staff(db)
    _, item_id = add_section(db, editor, "services")
    version_id = add_version(db, item_id, editor)
    db.execute(
        sa.insert(section_version).values(version_id=version_id, section_key="services")
    )
    # The section_version cannot exist without the row, so the row goes afterwards; the
    # reference guard still has to refuse a version whose page_section row has vanished.
    db.execute(sa.delete(page_section).where(page_section.c.item_id == item_id))
    group_id = add_record_item(db, editor, "service_group")

    with pytest.raises(DBAPIError, match=SECTION_ITEM_MISSING):
        with db.begin_nested():
            add_reference(db, version_id, group_id, "service_group", 0)


def test_a_project_reference_carries_no_order(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "work")
    project_id = add_record_item(db, editor, "project")

    with pytest.raises(IntegrityError, match="section_version_item_order"):
        with db.begin_nested():
            add_reference(db, version_id, project_id, "project", 0)


def test_a_non_project_reference_carries_an_order(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "services")
    group_id = add_record_item(db, editor, "service_group")

    with pytest.raises(IntegrityError, match="section_version_item_order"):
        with db.begin_nested():
            add_reference(db, version_id, group_id, "service_group", None)


def test_a_version_cannot_place_two_references_alike(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "proof")
    add_reference(
        db,
        version_id,
        add_record_item(db, editor, "proof_figure"),
        "proof_figure",
        0,
    )

    with pytest.raises(IntegrityError, match="section_version_item_order_key"):
        with db.begin_nested():
            add_reference(
                db,
                version_id,
                add_record_item(db, editor, "proof_figure"),
                "proof_figure",
                0,
            )


def test_unordered_references_can_share_a_version(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "work")
    for _ in range(2):
        add_reference(
            db, version_id, add_record_item(db, editor, "project"), "project", None
        )

    assert (
        count_rows(
            db,
            section_version_item,
            section_version_item.c.version_id == version_id,
        )
        == 2
    )


def test_a_referenced_item_cannot_be_deleted(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "work")
    project_id = add_record_item(db, editor, "project")
    add_reference(db, version_id, project_id, "project", None)

    with pytest.raises(IntegrityError, match="section_version_item_fk"):
        with db.begin_nested():
            db.execute(sa.delete(content_item).where(content_item.c.id == project_id))

    assert count_rows(db, content_item, content_item.c.id == project_id) == 1


@pytest.mark.parametrize("table_name", list(CHILD_SECTION_KEY), ids=list(CHILD_SECTION_KEY))
def test_a_child_row_is_editable_until_its_version_publishes(
    db: Connection, table_name: str
) -> None:
    editor = add_staff(db)
    table = SECTION_CHILD_TABLES[table_name]
    version_id = add_child_version(db, editor, table_name)
    column, value = next(iter(CHILD_EDIT[table_name].items()))

    db.execute(
        sa.update(table)
        .where(table.c.version_id == version_id)
        .values(**CHILD_EDIT[table_name])
    )
    edited = db.execute(
        sa.select(table.c[column]).where(table.c.version_id == version_id)
    ).scalar_one()
    assert edited == value

    publish_version(db, version_id, editor)

    with pytest.raises(DBAPIError, match=IMMUTABLE_CONTENT):
        with db.begin_nested():
            db.execute(
                sa.update(table)
                .where(table.c.version_id == version_id)
                .values(**CHILD_EDIT[table_name])
            )

    with pytest.raises(DBAPIError, match=IMMUTABLE_CONTENT):
        with db.begin_nested():
            db.execute(sa.delete(table).where(table.c.version_id == version_id))

    assert count_rows(db, table, table.c.version_id == version_id) == 1


def test_a_reference_is_editable_until_its_version_publishes(db: Connection) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "services")
    item_id = add_record_item(db, editor, "service_group")
    add_reference(db, version_id, item_id, "service_group", 0)

    db.execute(
        sa.update(section_version_item)
        .where(section_version_item.c.version_id == version_id)
        .values(sort_order=1)
    )

    publish_version(db, version_id, editor)

    with pytest.raises(DBAPIError, match=PUBLISHED_SECTION):
        with db.begin_nested():
            db.execute(
                sa.update(section_version_item)
                .where(section_version_item.c.version_id == version_id)
                .values(sort_order=0)
            )

    with pytest.raises(DBAPIError, match=PUBLISHED_SECTION):
        with db.begin_nested():
            db.execute(
                sa.delete(section_version_item).where(
                    section_version_item.c.version_id == version_id
                )
            )

    assert (
        count_rows(
            db,
            section_version_item,
            section_version_item.c.version_id == version_id,
        )
        == 1
    )


def test_deleting_a_draft_version_cascades_every_child_row(db: Connection) -> None:
    editor = add_staff(db)
    versions: list[tuple[str, uuid.UUID]] = [
        (table_name, add_child_version(db, editor, table_name))
        for table_name in CHILD_SECTION_KEY
    ]
    reference_version = add_section_version(db, editor, "services")
    add_reference(
        db,
        reference_version,
        add_record_item(db, editor, "service_group"),
        "service_group",
        0,
    )

    for table_name, version_id in versions:
        db.execute(sa.delete(content_version).where(content_version.c.id == version_id))
        table = SECTION_CHILD_TABLES[table_name]
        assert count_rows(db, table, table.c.version_id == version_id) == 0

    db.execute(
        sa.delete(content_version).where(content_version.c.id == reference_version)
    )
    assert (
        count_rows(
            db,
            section_version_item,
            section_version_item.c.version_id == reference_version,
        )
        == 0
    )


def test_every_documented_constraint_matches_its_definition(db: Connection) -> None:
    # Alembic 1.20 does not compare CHECK constraints, so the installed definitions are
    # compared here instead. Whitespace and the parentheses PostgreSQL adds are
    # normalised; a changed bound or operator still fails.
    installed = {
        name: (kind, normalise_constraint(definition))
        for name, kind, definition in db.execute(
            sa.text(
                "select conname, contype, pg_get_constraintdef(oid) from pg_constraint "
                "where conrelid in ('page_section'::regclass, "
                "'section_version'::regclass, 'section_paragraph'::regclass, "
                "'process_stage'::regclass, 'process_assurance'::regclass, "
                "'faq_item'::regclass, 'contact_next_step'::regclass, "
                "'section_version_item'::regclass) "
                "and contype in ('p', 'u', 'c', 'f')"
            )
        ).all()
    }

    assert installed == {
        name: (kind, normalise_constraint(definition))
        for name, (kind, definition) in EXPECTED_CONSTRAINTS.items()
    }


def test_the_documented_indexes_and_predicates_are_installed(db: Connection) -> None:
    installed = {
        name: normalise(definition)
        for name, definition in db.execute(
            sa.text(
                "select indexname, indexdef from pg_indexes where tablename in "
                "('page_section', 'section_version', 'section_paragraph', "
                "'process_stage', 'process_assurance', 'faq_item', "
                "'contact_next_step', 'section_version_item')"
            )
        ).all()
    }

    assert installed == {
        name: normalise(definition) for name, definition in EXPECTED_INDEXES.items()
    }


def test_the_installed_triggers_fire_on_the_documented_events(db: Connection) -> None:
    installed = {
        name: (
            table,
            (tgtype & 1) == 1,  # row level
            (tgtype & 2) == 2,  # before
            (tgtype & 4) == 4,  # insert
            (tgtype & 8) == 8,  # delete
            (tgtype & 16) == 16,  # update
            deferrable,
            initially_deferred,
        )
        for name, table, tgtype, deferrable, initially_deferred in db.execute(
            sa.text(
                "select tgname, tgrelid::regclass::text, tgtype, tgdeferrable, "
                "tginitdeferred from pg_trigger where not tgisinternal and tgname in "
                "('content_item_page_section_row', 'content_version_item_frozen', "
                "'section_version_immutable', 'section_paragraph_section', "
                "'process_stage_section', "
                "'process_assurance_section', 'faq_item_section', "
                "'contact_next_step_section', 'section_version_item_assert', "
                "'section_paragraph_immutable', 'process_stage_immutable', "
                "'process_assurance_immutable', 'faq_item_immutable', "
                "'contact_next_step_immutable', 'section_version_item_immutable', "
                "'page_section_row_kept', 'page_section_immutable', "
                "'section_version_key_guard')"
            )
        ).all()
    }

    assert installed == EXPECTED_TRIGGERS


def test_the_column_scoped_triggers_watch_the_documented_columns(db: Connection) -> None:
    watched = {
        name: columns
        for name, columns in db.execute(
            sa.text(
                "select t.tgname, coalesce(("
                "select string_agg(a.attname, ',' order by a.attnum) "
                "from pg_attribute a "
                "where a.attrelid = t.tgrelid "
                "and a.attnum = any (t.tgattr::int2[])), '') "
                "from pg_trigger t where not t.tgisinternal and t.tgname in "
                "('content_item_page_section_row', 'content_version_item_frozen', "
                "'section_version_immutable', 'section_paragraph_section', "
                "'process_stage_section', "
                "'process_assurance_section', 'faq_item_section', "
                "'contact_next_step_section', 'section_version_item_assert', "
                "'section_paragraph_immutable', 'process_stage_immutable', "
                "'process_assurance_immutable', 'faq_item_immutable', "
                "'contact_next_step_immutable', 'section_version_item_immutable', "
                "'page_section_row_kept', 'page_section_immutable', "
                "'section_version_key_guard')"
            )
        ).all()
    }

    assert watched == {
        name: {
            "content_item_page_section_row": "kind",
            "content_version_item_frozen": "item_id",
            "section_version_key_guard": "section_key",
        }.get(name, "")
        for name in EXPECTED_TRIGGERS
    }


def test_the_installed_assert_page_section_row_pins_its_message(db: Connection) -> None:
    definition = db.execute(
        sa.text("select pg_get_functiondef(cast(:function as regprocedure))"),
        {"function": "assert_page_section_row()"},
    ).scalar_one()
    normalised = normalise(definition)

    for fragment in [
        "if exists (",
        "select 1 from content_item where id = new.id and kind = 'page_section'",
        "and not exists (",
        "select 1 from page_section where item_id = new.id",
        "raise exception 'page section item % needs a page_section row', new.id",
        "if tg_op = 'update'",
        "and old.kind = 'page_section'",
        "and new.kind <> 'page_section'",
        "join section_version sv on sv.version_id = cv.id",
        "raise exception 'a section item with versions cannot change kind'",
        "return null",
    ]:
        assert fragment in normalised, (
            f"the installed assert_page_section_row() is missing: {fragment}"
        )


@pytest.mark.parametrize(
    ("function", "fragments"),
    [
        (
            "assert_section_child()",
            [
                "select section_key into v_key",
                "from section_version",
                "where version_id = new.version_id",
                "if v_key is null or v_key::text <> tg_argv[0] then",
                "raise exception 'row belongs to section %, not %', v_key, tg_argv[0]",
                "return new",
            ],
        ),
        (
            "assert_page_section_item_kept()",
            [
                "if not exists (",
                "select 1 from content_item where id = old.item_id "
                "and kind = 'page_section'",
                "select page_id, section_key, sort_order",
                "if not found then",
                "raise exception 'page section item % lost its page_section row', "
                "old.item_id",
                "if v_page_id is not distinct from old.page_id",
                "and v_section_key is not distinct from old.section_key",
                "and v_sort_order is not distinct from old.sort_order then",
                "raise exception 'page section item % changed its page_section row', "
                "old.item_id",
            ],
        ),
        (
            "assert_page_section_position()",
            [
                "if new.item_id is distinct from old.item_id",
                "or new.page_id is distinct from old.page_id",
                "or new.section_key is distinct from old.section_key",
                "or new.sort_order is distinct from old.sort_order then",
                "raise exception 'page_section identity and position cannot change'",
                "return new",
            ],
        ),
        (
            "assert_section_version_key()",
            [
                "if tg_op = 'update' and new.section_key <> old.section_key then",
                "raise exception 'section version key cannot change'",
                "select ci.kind, ps.section_key",
                "left join page_section ps on ps.item_id = cv.item_id",
                "if v_kind is null or v_kind <> 'page_section' then",
                "raise exception 'section version belongs to a page section'",
                "raise exception 'section item has no page_section row'",
                "if v_key <> new.section_key then",
                "raise exception 'section version key % does not match its section %',",
                "new.section_key, v_key",
                "return new",
            ],
        ),
        (
            "prevent_version_item_move()",
            [
                "if new.item_id <> old.item_id then",
                "raise exception 'a version cannot move between items'",
                "return new",
            ],
        ),
        (
            "assert_section_version_item()",
            [
                "v_version := case when tg_op = 'delete' then old.version_id else "
                "new.version_id end",
                "v_item_kind := case when tg_op = 'delete' then old.item_kind else "
                "new.item_kind end",
                "if tg_op = 'update' and (old.version_id <> new.version_id or "
                "old.item_id <> new.item_id) then",
                "raise exception 'a section reference cannot move between versions or "
                "items'",
                "select cv.status, ci.kind, ps.section_key",
                "left join page_section ps on ps.item_id = cv.item_id",
                "raise exception 'references belong to a page section version'",
                "raise exception 'published section version is immutable'",
                "raise exception 'section item has no page_section row'",
                "if v_key = 'services' and v_item_kind = 'service_group' then",
                "elsif v_key = 'work' and v_item_kind = 'project' then",
                "elsif v_key = 'proof' and v_item_kind = 'proof_figure' then",
                "elsif v_key = 'testimonials' and v_item_kind = 'testimonial' then",
                "raise exception 'section % cannot reference a %', v_key, v_item_kind",
            ],
        ),
    ],
    ids=[
        "assert_section_child",
        "assert_page_section_item_kept",
        "assert_page_section_position",
        "assert_section_version_key",
        "prevent_version_item_move",
        "assert_section_version_item",
    ],
)
def test_the_installed_section_functions_pin_their_bodies(
    db: Connection, function: str, fragments: list[str]
) -> None:
    definition = db.execute(
        sa.text("select pg_get_functiondef(cast(:function as regprocedure))"),
        {"function": function},
    ).scalar_one()
    normalised = normalise(definition)

    for fragment in fragments:
        assert normalise(fragment) in normalised, (
            f"the installed {function} is missing: {fragment}"
        )
