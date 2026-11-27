"""The media table's constraints, promotion rules and immutability, against real PostgreSQL.

Every test runs inside the ``db`` transaction and is rolled back by the fixture. The
immutability trigger is ``before update`` only, so an insert is governed by the table
constraints alone; each fixture inserts the auth user and the staff row that ``uploaded_by``
references.
"""

import uuid
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import auth_users, media, staff

IMMUTABLE = "media rows are immutable; create a new row"
UNDELETED = "media cannot be undeleted"
PUBLIC_ONLY_DELETED = "a public media row only changes its deleted_at"
ONE_PROMOTION = "promotion moves one staged row to site-media"
VISIBILITY_ONLY_ON_PROMOTION = "media visibility only changes on promotion"


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


def test_every_documented_constraint_is_installed(db: Connection) -> None:
    # Alembic 1.20 does not compare CHECK constraints (task 0002's `alembic check` note),
    # so the installed set is pinned by name here and every check is exercised by the
    # tests above. The document's fifteen are the primary key, the unique pair and thirteen
    # checks; the foreign key is the one PostgreSQL names itself.
    constraints = {
        (name, kind)
        for name, kind in db.execute(
            sa.text(
                "select conname, contype from pg_constraint "
                "where conrelid = 'media'::regclass and contype in ('p', 'u', 'c', 'f')"
            )
        ).all()
    }

    assert constraints == {
        ("media_pkey", "p"),
        ("media_object_unique", "u"),
        ("media_uploaded_by_fkey", "f"),
        ("media_alt_length", "c"),
        ("media_alt_required", "c"),
        ("media_bucket", "c"),
        ("media_checksum", "c"),
        ("media_height", "c"),
        ("media_image_dimensions", "c"),
        ("media_mime_length", "c"),
        ("media_object_path", "c"),
        ("media_promotion", "c"),
        ("media_size", "c"),
        ("media_types", "c"),
        ("media_visibility_bucket", "c"),
        ("media_width", "c"),
    }


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
        "old.visibility = 'public'",
        "old.bucket <> 'media-staging'",
        "new.bucket <> 'site-media'",
        "raise exception 'media rows are immutable; create a new row'",
        "raise exception 'media cannot be undeleted'",
        "raise exception 'a public media row only changes its deleted_at'",
        "raise exception 'promotion moves one staged row to site-media'",
        "raise exception 'media visibility only changes on promotion'",
    ]
    for fragment in fragments:
        assert fragment in normalised, f"the installed function is missing: {fragment}"
