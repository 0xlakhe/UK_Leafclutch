"""The media table's constraints, promotion rules and immutability, against real PostgreSQL.

Every test runs inside the ``db`` transaction and is rolled back by the fixture. The
immutability trigger is ``before update`` only, so an insert is governed by the table
constraints alone; each fixture inserts the auth user and the staff row that ``uploaded_by``
references.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import auth_users, media, staff

IMMUTABLE = "media rows are immutable; create a new row"
UNDELETED = "media cannot be undeleted"
DELETION_FROZEN = "media deletion cannot be changed"
PUBLIC_ONLY_DELETED = "a public media row only changes its deleted_at"
ONE_PROMOTION = "promotion moves one staged row to site-media"
VISIBILITY_ONLY_ON_PROMOTION = "media visibility only changes on promotion"

# The fifteen checks, the unique pair and the foreign key as PostgreSQL renders them, plus
# the primary key. ``normalise_constraint`` folds case and collapses whitespace only: the
# parentheses are kept because grouping changes the rule, and a pure regrouping must fail.
EXPECTED_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "media_pkey": ("p", "PRIMARY KEY (id)"),
    "media_object_unique": ("u", "UNIQUE (bucket, object_path)"),
    "media_uploaded_by_fkey": (
        "f",
        "FOREIGN KEY (uploaded_by) REFERENCES staff(user_id) ON DELETE RESTRICT",
    ),
    "media_alt_length": (
        "c",
        "CHECK (((alt IS NULL) OR ((char_length(alt) >= 1) AND "
        "(char_length(alt) <= 120))))",
    ),
    "media_alt_required": (
        "c",
        "CHECK (((bucket = 'evidence'::text) OR (alt IS NOT NULL)))",
    ),
    "media_bucket": (
        "c",
        "CHECK ((bucket = ANY (ARRAY['media-staging'::text, 'site-media'::text, "
        "'evidence'::text])))",
    ),
    "media_checksum": ("c", "CHECK ((octet_length(checksum_sha256) = 32))"),
    "media_deleted_after_upload": (
        "c",
        "CHECK (((deleted_at IS NULL) OR (deleted_at >= uploaded_at)))",
    ),
    "media_height": ("c", "CHECK (((height IS NULL) OR (height > 0)))"),
    "media_image_dimensions": (
        "c",
        "CHECK (((mime_type !~~ 'image/%'::text) OR ((width IS NOT NULL) AND "
        "(height IS NOT NULL))))",
    ),
    "media_mime_length": (
        "c",
        "CHECK (((char_length(mime_type) >= 1) AND (char_length(mime_type) <= 100)))",
    ),
    "media_object_path": (
        "c",
        "CHECK ((((char_length(object_path) >= 1) AND "
        "(char_length(object_path) <= 300)) AND (object_path !~ '^/'::text)))",
    ),
    "media_promoted_after_upload": (
        "c",
        "CHECK (((promoted_at IS NULL) OR (promoted_at >= uploaded_at)))",
    ),
    "media_promotion": (
        "c",
        "CHECK (((visibility = 'public'::media_visibility) = (promoted_at IS NOT NULL)))",
    ),
    "media_size": ("c", "CHECK (((size_bytes > 0) AND (size_bytes <= 4194304)))"),
    "media_types": (
        "c",
        "CHECK ((((bucket = 'evidence'::text) AND (mime_type = ANY "
        "(ARRAY['application/pdf'::text, 'image/jpeg'::text, 'image/png'::text, "
        "'image/webp'::text]))) OR ((bucket <> 'evidence'::text) AND (mime_type = "
        "ANY (ARRAY['image/jpeg'::text, 'image/png'::text, 'image/webp'::text])))))",
    ),
    "media_visibility_bucket": (
        "c",
        "CHECK ((((visibility = 'public'::media_visibility) AND "
        "(bucket = 'site-media'::text)) OR ((visibility = 'private'::media_visibility) "
        "AND (bucket = ANY (ARRAY['media-staging'::text, 'evidence'::text])))))",
    ),
    "media_width": ("c", "CHECK (((width IS NULL) OR (width > 0)))"),
}

EXPECTED_ENUMS: dict[str, list[str]] = {
    "staff_role": ["admin", "editor"],
    "content_kind": [
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
    ],
    "page_section_key": [
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
    ],
    "version_status": ["draft", "in_review", "published"],
    "approval_scope": ["client_name", "result", "mark", "screenshots", "quote", "figure"],
    "media_visibility": ["public", "private"],
    "media_role": [
        "project_image",
        "about_image",
        "og_image",
        "client_logo",
        "site_logo",
    ],
    "enquiry_status": ["new", "in_progress", "closed"],
    "faq_status": ["published", "draft"],
    "legal_block_kind": ["h2", "p", "ul", "table"],
    "email_kind": ["enquiry_alert", "enquiry_confirmation"],
    "email_status": ["pending", "sent", "failed", "dead"],
    "revalidation_status": ["pending", "sent", "failed", "dead"],
}


def normalise_constraint(definition: str) -> str:
    """Lower-case and collapse whitespace; PostgreSQL's parentheses stay significant."""
    return " ".join(definition.lower().split())


def add_uploader(db: Connection) -> uuid.UUID:
    """Insert the auth user and staff row that ``uploaded_by`` references."""
    user_id = uuid.uuid4()
    db.execute(sa.insert(auth_users).values(id=user_id))
    db.execute(
        sa.insert(staff).values(
            user_id=user_id,
            email=f"{user_id}@example.com",
            display_name="Uploader",
            role="editor",
        )
    )
    return user_id


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


def add_media(db: Connection, uploaded_by: uuid.UUID, **overrides: object) -> uuid.UUID:
    """Insert one media row and return its id."""
    return db.execute(
        sa.insert(media)
        .values(**media_values(uploaded_by, **overrides))
        .returning(media.c.id)
    ).scalar_one()


def add_evidence_pdf(db: Connection, uploaded_by: uuid.UUID) -> uuid.UUID:
    """Insert a private evidence PDF: no dimensions and no alt text."""
    return add_media(
        db,
        uploaded_by,
        bucket="evidence",
        mime_type="application/pdf",
        width=None,
        height=None,
        alt=None,
    )


def promote(db: Connection, media_id: uuid.UUID) -> None:
    """Move one staged row to ``site-media`` and make it public."""
    db.execute(
        sa.update(media)
        .where(media.c.id == media_id)
        .values(
            visibility="public",
            bucket="site-media",
            promoted_at=datetime.now(UTC),
        )
    )


def select_media(db: Connection, media_id: uuid.UUID) -> sa.Row:
    return db.execute(sa.select(media).where(media.c.id == media_id)).one()


def test_the_media_table_starts_empty(db: Connection) -> None:
    rows = db.execute(sa.select(media.c.id, media.c.object_path)).all()
    assert rows == [], (
        "stale committed media rows from an earlier run; delete them before rerunning the "
        f"suite: {rows}"
    )


def test_a_staged_image_is_accepted_with_the_server_defaults(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_media(db, uploaded_by)

    row = select_media(db, media_id)
    assert row.visibility == "private"
    assert row.bucket == "media-staging"
    assert row.promoted_at is None
    assert row.deleted_at is None
    assert row.uploaded_at is not None
    assert isinstance(row.id, uuid.UUID)


def test_evidence_accepts_a_pdf_without_dimensions_or_alt(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_evidence_pdf(db, uploaded_by)

    row = select_media(db, media_id)
    assert row.bucket == "evidence"
    assert row.mime_type == "application/pdf"
    assert row.width is None
    assert row.height is None
    assert row.alt is None


def test_the_bucket_and_object_path_are_unique(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    path = f"{uuid.uuid4()}.webp"
    add_media(db, uploaded_by, object_path=path)

    with pytest.raises(IntegrityError, match="media_object_unique"):
        with db.begin_nested():
            add_media(db, uploaded_by, object_path=path)

    # The unique constraint is on the pair, not the path alone.
    add_media(db, uploaded_by, bucket="evidence", object_path=path, alt=None)


@pytest.mark.parametrize("bucket", ["media-staging", "evidence"])
def test_a_public_row_must_be_in_site_media(db: Connection, bucket: str) -> None:
    uploaded_by = add_uploader(db)

    with pytest.raises(IntegrityError, match="media_visibility_bucket"):
        with db.begin_nested():
            add_media(
                db,
                uploaded_by,
                visibility="public",
                bucket=bucket,
                promoted_at=datetime.now(UTC),
            )


def test_a_private_row_must_be_staged_or_evidence(db: Connection) -> None:
    uploaded_by = add_uploader(db)

    with pytest.raises(IntegrityError, match="media_visibility_bucket"):
        with db.begin_nested():
            add_media(db, uploaded_by, visibility="private", bucket="site-media")


def test_promoted_at_is_set_exactly_when_the_row_is_public(db: Connection) -> None:
    uploaded_by = add_uploader(db)

    with pytest.raises(IntegrityError, match="media_promotion"):
        with db.begin_nested():
            add_media(
                db,
                uploaded_by,
                visibility="public",
                bucket="site-media",
            )

    with pytest.raises(IntegrityError, match="media_promotion"):
        with db.begin_nested():
            add_media(
                db,
                uploaded_by,
                visibility="private",
                promoted_at=datetime.now(UTC),
            )


@pytest.mark.parametrize(
    ("bucket", "visibility", "promoted_at"),
    [
        ("media-staging", "private", None),
        ("site-media", "public", "now"),
    ],
    ids=["staged", "public"],
)
def test_alt_is_required_outside_evidence(
    db: Connection,
    bucket: str,
    visibility: str,
    promoted_at: str | None,
) -> None:
    uploaded_by = add_uploader(db)
    values: dict[str, object] = {"bucket": bucket, "visibility": visibility, "alt": None}
    if promoted_at is not None:
        values["promoted_at"] = datetime.now(UTC)

    with pytest.raises(IntegrityError, match="media_alt_required"):
        with db.begin_nested():
            add_media(db, uploaded_by, **values)


def test_alt_is_limited_to_120_characters(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    add_media(db, uploaded_by, alt="a" * 120)

    with pytest.raises(IntegrityError, match="media_alt_length"):
        with db.begin_nested():
            add_media(db, uploaded_by, alt="a" * 121)


def test_an_empty_alt_is_refused_outside_evidence(db: Connection) -> None:
    uploaded_by = add_uploader(db)

    with pytest.raises(IntegrityError, match="media_alt_length"):
        with db.begin_nested():
            add_media(db, uploaded_by, alt="")


def test_an_empty_alt_is_refused_in_evidence(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    # `null` is the evidence omission (proved in the happy path above); `''` is not.
    add_evidence_pdf(db, uploaded_by)

    with pytest.raises(IntegrityError, match="media_alt_length"):
        with db.begin_nested():
            add_media(
                db,
                uploaded_by,
                bucket="evidence",
                mime_type="application/pdf",
                width=None,
                height=None,
                alt="",
            )


def test_pdf_is_accepted_in_evidence_and_refused_elsewhere(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    add_evidence_pdf(db, uploaded_by)
    pdf: dict[str, object] = {
        "mime_type": "application/pdf",
        "width": None,
        "height": None,
    }

    with pytest.raises(IntegrityError, match="media_types"):
        with db.begin_nested():
            add_media(db, uploaded_by, **pdf)

    with pytest.raises(IntegrityError, match="media_types"):
        with db.begin_nested():
            add_media(
                db,
                uploaded_by,
                visibility="public",
                bucket="site-media",
                promoted_at=datetime.now(UTC),
                **pdf,
            )


def test_an_unknown_mime_type_is_refused(db: Connection) -> None:
    uploaded_by = add_uploader(db)

    with pytest.raises(IntegrityError, match="media_types"):
        with db.begin_nested():
            add_media(
                db,
                uploaded_by,
                bucket="evidence",
                mime_type="application/zip",
                width=None,
                height=None,
                alt=None,
            )


@pytest.mark.parametrize(
    ("size_bytes", "accepted"),
    [
        (1, True),
        (4194304, True),
        (0, False),
        (-1, False),
        (4194305, False),
    ],
    ids=["one-byte", "four-megabytes", "zero", "negative", "over-four-megabytes"],
)
def test_size_must_be_positive_and_at_most_four_megabytes(
    db: Connection, size_bytes: int, accepted: bool
) -> None:
    uploaded_by = add_uploader(db)

    if accepted:
        add_media(db, uploaded_by, size_bytes=size_bytes)
        return

    with pytest.raises(IntegrityError, match="media_size"):
        with db.begin_nested():
            add_media(db, uploaded_by, size_bytes=size_bytes)


@pytest.mark.parametrize("length", [31, 33])
def test_the_checksum_must_be_32_bytes(db: Connection, length: int) -> None:
    uploaded_by = add_uploader(db)

    with pytest.raises(IntegrityError, match="media_checksum"):
        with db.begin_nested():
            add_media(db, uploaded_by, checksum_sha256=b"\x00" * length)


@pytest.mark.parametrize(
    "object_path",
    ["", "/absolute.webp", "a" * 301],
    ids=["empty", "absolute", "over-300-characters"],
)
def test_the_object_path_must_be_relative_and_within_bounds(
    db: Connection, object_path: str
) -> None:
    uploaded_by = add_uploader(db)

    with pytest.raises(IntegrityError, match="media_object_path"):
        with db.begin_nested():
            add_media(db, uploaded_by, object_path=object_path)


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"width": None}, "media_image_dimensions"),
        ({"height": None}, "media_image_dimensions"),
        ({"width": 0}, "media_width"),
        ({"width": -1}, "media_width"),
        ({"height": 0}, "media_height"),
        ({"height": -1}, "media_height"),
    ],
    ids=[
        "no-width",
        "no-height",
        "zero-width",
        "negative-width",
        "zero-height",
        "negative-height",
    ],
)
def test_an_image_requires_positive_dimensions(
    db: Connection, overrides: dict[str, object], constraint: str
) -> None:
    uploaded_by = add_uploader(db)

    with pytest.raises(IntegrityError, match=constraint):
        with db.begin_nested():
            add_media(db, uploaded_by, **overrides)


@pytest.mark.parametrize(
    "column",
    [
        "id",
        "object_path",
        "mime_type",
        "size_bytes",
        "width",
        "height",
        "alt",
        "checksum_sha256",
        "uploaded_by",
        "uploaded_at",
    ],
)
def test_editing_a_pinned_column_is_refused(db: Connection, column: str) -> None:
    uploaded_by = add_uploader(db)
    other_uploader = add_uploader(db)
    media_id = add_media(db, uploaded_by)
    replacement: dict[str, object] = {
        "id": uuid.uuid4(),
        "object_path": f"{uuid.uuid4()}.webp",
        "mime_type": "image/png",
        "size_bytes": 2048,
        "width": 1024,
        "height": 768,
        "alt": "A different alt",
        "checksum_sha256": b"\x01" * 32,
        "uploaded_by": other_uploader,
        "uploaded_at": datetime(2000, 1, 1, tzinfo=UTC),
    }

    with pytest.raises(DBAPIError, match=IMMUTABLE):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(**{column: replacement[column]})
            )


def test_a_staged_row_can_be_promoted_once(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_media(db, uploaded_by)

    promote(db, media_id)

    row = select_media(db, media_id)
    assert row.visibility == "public"
    assert row.bucket == "site-media"
    assert row.promoted_at is not None

    with pytest.raises(DBAPIError, match=PUBLIC_ONLY_DELETED):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(promoted_at=datetime.now(UTC))
            )


def test_a_soft_deleted_staged_row_cannot_be_promoted(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_media(db, uploaded_by)
    db.execute(
        sa.update(media).where(media.c.id == media_id).values(deleted_at=sa.func.now())
    )
    assert select_media(db, media_id).deleted_at is not None

    with pytest.raises(DBAPIError, match=ONE_PROMOTION):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(
                    visibility="public",
                    bucket="site-media",
                    promoted_at=datetime.now(UTC),
                )
            )


def test_promoting_while_deleting_in_the_same_statement_is_refused(
    db: Connection,
) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_media(db, uploaded_by)

    with pytest.raises(DBAPIError, match=ONE_PROMOTION):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(
                    visibility="public",
                    bucket="site-media",
                    promoted_at=sa.func.now(),
                    deleted_at=sa.func.now(),
                )
            )

    assert select_media(db, media_id).visibility == "private"


def test_a_public_row_cannot_return_to_private_or_change_bucket(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_media(db, uploaded_by)
    promote(db, media_id)

    with pytest.raises(DBAPIError, match=PUBLIC_ONLY_DELETED):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(visibility="private")
            )

    with pytest.raises(DBAPIError, match=PUBLIC_ONLY_DELETED):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(bucket="media-staging")
            )

    row = select_media(db, media_id)
    assert row.visibility == "public"
    assert row.bucket == "site-media"


def test_an_evidence_row_cannot_become_public(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_evidence_pdf(db, uploaded_by)

    with pytest.raises(DBAPIError, match=ONE_PROMOTION):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(
                    visibility="public",
                    bucket="site-media",
                    promoted_at=datetime.now(UTC),
                )
            )

    assert select_media(db, media_id).visibility == "private"


def test_a_private_row_cannot_change_bucket(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_media(db, uploaded_by)

    with pytest.raises(DBAPIError, match=VISIBILITY_ONLY_ON_PROMOTION):
        with db.begin_nested():
            db.execute(
                sa.update(media).where(media.c.id == media_id).values(bucket="evidence")
            )

    assert select_media(db, media_id).bucket == "media-staging"


def test_deleted_at_is_the_only_change_a_public_row_accepts(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_media(db, uploaded_by)
    promote(db, media_id)

    db.execute(
        sa.update(media)
        .where(media.c.id == media_id)
        .values(deleted_at=datetime.now(UTC))
    )
    assert select_media(db, media_id).deleted_at is not None

    with pytest.raises(DBAPIError, match=UNDELETED):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(deleted_at=None)
            )

    with pytest.raises(DBAPIError, match=IMMUTABLE):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(alt="A corrected alt")
            )


def test_a_second_deleted_at_value_is_refused(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    media_id = add_media(db, uploaded_by)
    promote(db, media_id)
    db.execute(
        sa.update(media).where(media.c.id == media_id).values(deleted_at=sa.func.now())
    )

    with pytest.raises(DBAPIError, match=DELETION_FROZEN):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(deleted_at=datetime.now(UTC) + timedelta(seconds=1))
            )

    assert select_media(db, media_id).deleted_at is not None


def test_deleted_at_cannot_precede_uploaded_at(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    uploaded_at = datetime(2026, 1, 2, tzinfo=UTC)

    with pytest.raises(IntegrityError, match="media_deleted_after_upload"):
        with db.begin_nested():
            add_media(
                db,
                uploaded_by,
                uploaded_at=uploaded_at,
                deleted_at=uploaded_at - timedelta(days=1),
            )


def test_promoted_at_cannot_precede_uploaded_at(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    uploaded_at = datetime(2026, 1, 2, tzinfo=UTC)

    with pytest.raises(IntegrityError, match="media_promoted_after_upload"):
        with db.begin_nested():
            add_media(
                db,
                uploaded_by,
                visibility="public",
                bucket="site-media",
                uploaded_at=uploaded_at,
                promoted_at=uploaded_at - timedelta(days=1),
            )


def test_deleted_at_cannot_precede_uploaded_at_on_a_public_row(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    uploaded_at = datetime(2026, 1, 2, tzinfo=UTC)
    media_id = add_media(db, uploaded_by, uploaded_at=uploaded_at)
    promote(db, media_id)

    with pytest.raises(IntegrityError, match="media_deleted_after_upload"):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(deleted_at=uploaded_at - timedelta(days=1))
            )

    assert select_media(db, media_id).deleted_at is None


def test_promoted_at_cannot_precede_uploaded_at_on_promotion(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    uploaded_at = datetime(2026, 1, 2, tzinfo=UTC)
    media_id = add_media(db, uploaded_by, uploaded_at=uploaded_at)

    with pytest.raises(IntegrityError, match="media_promoted_after_upload"):
        with db.begin_nested():
            db.execute(
                sa.update(media)
                .where(media.c.id == media_id)
                .values(
                    visibility="public",
                    bucket="site-media",
                    promoted_at=uploaded_at - timedelta(days=1),
                )
            )

    row = select_media(db, media_id)
    assert row.visibility == "private"
    assert row.bucket == "media-staging"
    assert row.promoted_at is None


def test_equal_timestamps_are_accepted(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    uploaded_at = datetime(2026, 1, 2, tzinfo=UTC)

    add_media(db, uploaded_by, uploaded_at=uploaded_at, deleted_at=uploaded_at)
    add_media(
        db,
        uploaded_by,
        visibility="public",
        bucket="site-media",
        uploaded_at=uploaded_at,
        promoted_at=uploaded_at,
    )


def test_equal_timestamps_are_accepted_on_update_and_promotion(db: Connection) -> None:
    uploaded_by = add_uploader(db)
    uploaded_at = datetime(2026, 1, 2, tzinfo=UTC)

    public_id = add_media(db, uploaded_by, uploaded_at=uploaded_at)
    promote(db, public_id)
    db.execute(
        sa.update(media).where(media.c.id == public_id).values(deleted_at=uploaded_at)
    )
    assert select_media(db, public_id).deleted_at == uploaded_at

    staged_id = add_media(db, uploaded_by, uploaded_at=uploaded_at)
    db.execute(
        sa.update(media)
        .where(media.c.id == staged_id)
        .values(visibility="public", bucket="site-media", promoted_at=uploaded_at)
    )
    row = select_media(db, staged_id)
    assert row.visibility == "public"
    assert row.promoted_at == uploaded_at


def test_every_documented_constraint_matches_its_definition(db: Connection) -> None:
    # Alembic 1.20 does not compare CHECK constraints (task 0002's `alembic check` note),
    # so the installed definitions are compared here instead. Case and whitespace are
    # normalised; parentheses and operators are compared exactly, so a changed bound, a
    # changed operator or a pure regrouping fails.
    installed = {
        name: (kind, normalise_constraint(definition))
        for name, kind, definition in db.execute(
            sa.text(
                "select conname, contype, pg_get_constraintdef(oid) from pg_constraint "
                "where conrelid = 'media'::regclass and contype in ('p', 'u', 'c', 'f')"
            )
        ).all()
    }

    assert installed == {
        name: (kind, normalise_constraint(definition))
        for name, (kind, definition) in EXPECTED_CONSTRAINTS.items()
    }


def test_the_enum_labels_are_pinned(db: Connection) -> None:
    labels: dict[str, list[str]] = {}
    for type_name, label in db.execute(
        sa.text(
            "select t.typname, e.enumlabel "
            "from pg_type t "
            "join pg_enum e on e.enumtypid = t.oid "
            "join pg_namespace n on n.oid = t.typnamespace "
            "where n.nspname = 'public' "
            "order by t.typname, e.enumsortorder"
        )
    ).all():
        labels.setdefault(type_name, []).append(label)

    assert labels == EXPECTED_ENUMS


def test_the_installed_trigger_is_before_update_only(db: Connection) -> None:
    triggers = {
        name: (
            (tgtype & 1) == 1,  # row level
            (tgtype & 2) == 2,  # before
            (tgtype & 4) == 4,  # insert
            (tgtype & 8) == 8,  # delete
            (tgtype & 16) == 16,  # update
        )
        for name, tgtype in db.execute(
            sa.text(
                "select tgname, tgtype from pg_trigger "
                "where tgrelid = 'media'::regclass and not tgisinternal"
            )
        ).all()
    }

    assert triggers == {"media_immutable": (True, True, False, False, True)}


def test_the_installed_function_pins_every_column_and_message(db: Connection) -> None:
    definition = db.execute(
        sa.text("select pg_get_functiondef('prevent_media_mutation()'::regprocedure)")
    ).scalar_one()
    normalised = " ".join(definition.lower().split())

    fragments = [
        "new.id <> old.id",
        "new.object_path <> old.object_path",
        "new.mime_type <> old.mime_type",
        "new.size_bytes <> old.size_bytes",
        "new.width is distinct from old.width",
        "new.height is distinct from old.height",
        "new.alt is distinct from old.alt",
        "new.checksum_sha256 <> old.checksum_sha256",
        "new.uploaded_by <> old.uploaded_by",
        "new.uploaded_at <> old.uploaded_at",
        "old.deleted_at is not null and new.deleted_at is null",
        "old.deleted_at is not null and new.deleted_at is distinct from old.deleted_at",
        "old.visibility = 'public'",
        "old.bucket <> 'media-staging'",
        "new.bucket <> 'site-media'",
        "or old.deleted_at is not null",
        "or new.deleted_at is not null",
        "raise exception 'media rows are immutable; create a new row'",
        "raise exception 'media cannot be undeleted'",
        "raise exception 'media deletion cannot be changed'",
        "raise exception 'a public media row only changes its deleted_at'",
        "raise exception 'promotion moves one staged row to site-media'",
        "raise exception 'media visibility only changes on promotion'",
    ]
    for fragment in fragments:
        assert fragment in normalised, f"the installed function is missing: {fragment}"
