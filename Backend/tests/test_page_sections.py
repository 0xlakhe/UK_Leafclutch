"""The page section tables' constraints, guards and cascade rules, against real PostgreSQL.

Every test runs inside the ``db`` transaction and is rolled back by the fixture. The
fixtures insert the auth user and staff rows the foreign keys reference, then the items,
versions and section rows the case needs. No row is committed.

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
    content_item,
    content_version,
    media,
    page_section,
    section_version,
    staff,
)

PAGE_SECTION_NEEDS_ROW = "page section item .* needs a page_section row"
IMMUTABLE_CONTENT = "published version content is immutable"

# The primary keys, unique constraints, checks and foreign keys as PostgreSQL renders
# them. The definitions are normalised by ``normalise_constraint`` before the comparison,
# so PostgreSQL's whitespace and decorative parentheses do not matter.
EXPECTED_CONSTRAINTS: dict[str, tuple[str, str]] = {
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

# Every index on the two tables, including the ones backing a constraint, so an extra
# index fails the comparison as well as a changed expression or predicate.
EXPECTED_INDEXES: dict[str, str] = {
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
    "section_version_pkey": (
        "CREATE UNIQUE INDEX section_version_pkey ON public.section_version USING btree "
        "(version_id)"
    ),
}

# ``tgtype`` bits: 1 row, 2 before, 4 insert, 8 delete, 16 update. The tuple adds the
# constraint-trigger flags, which the content spine's triggers do not carry.
EXPECTED_TRIGGERS: dict[str, tuple[str, bool, bool, bool, bool, bool, bool, bool]] = {
    "content_item_page_section_row": (
        "content_item",
        True,
        False,
        True,
        False,
        False,
        True,
        True,
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
    """Lower-case, drop PostgreSQL's decorative parentheses and collapse whitespace."""
    return " ".join(definition.lower().replace("(", "").replace(")", "").split())


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


def test_the_page_section_tables_start_empty(db: Connection) -> None:
    for table in (page_section, section_version):
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


def test_deleting_the_landing_page_cascades_its_section_rows(db: Connection) -> None:
    editor = add_staff(db)
    page_id = add_page(db, editor)
    add_section(db, editor, "hero", 0, page_id)
    add_section(db, editor, "proof", 1, page_id)
    assert count_rows(db, page_section, page_section.c.page_id == page_id) == 2

    db.execute(sa.delete(content_item).where(content_item.c.id == page_id))

    assert count_rows(db, page_section, page_section.c.page_id == page_id) == 0


def test_deleting_a_section_item_cascades_its_row(db: Connection) -> None:
    editor = add_staff(db)
    page_id, item_id = add_section(db, editor)

    db.execute(sa.delete(content_item).where(content_item.c.id == item_id))

    assert count_rows(db, page_section, page_section.c.item_id == item_id) == 0
    assert count_rows(db, page_section, page_section.c.page_id == page_id) == 0


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


def test_deleting_a_draft_content_version_cascades_its_section_version(
    db: Connection,
) -> None:
    editor = add_staff(db)
    version_id = add_section_version(db, editor, "hero")

    db.execute(sa.delete(content_version).where(content_version.c.id == version_id))

    assert count_rows(db, section_version, section_version.c.version_id == version_id) == 0


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
                "'section_version'::regclass) "
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
                "select indexname, indexdef from pg_indexes "
                "where tablename in ('page_section', 'section_version')"
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
                "('content_item_page_section_row', 'section_version_immutable')"
            )
        ).all()
    }

    assert installed == EXPECTED_TRIGGERS


def test_the_installed_assert_page_section_row_pins_its_message(db: Connection) -> None:
    definition = db.execute(
        sa.text("select pg_get_functiondef(cast(:function as regprocedure))"),
        {"function": "assert_page_section_row()"},
    ).scalar_one()
    normalised = normalise(definition)

    for fragment in [
        "if new.kind = 'page_section' and not exists",
        "select 1 from page_section where item_id = new.id",
        "raise exception 'page section item % needs a page_section row', new.id",
        "return null",
    ]:
        assert fragment in normalised, (
            f"the installed assert_page_section_row() is missing: {fragment}"
        )
