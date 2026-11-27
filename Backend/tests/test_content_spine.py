"""The content spine's constraints, guards and cascade rules, against real PostgreSQL.

Every test runs inside the ``db`` transaction and is rolled back by the fixture. The
fixtures insert the auth user and staff rows the foreign keys reference, then the item and
version rows the case needs. No row is committed.

The SQL is pinned twice: behaviour is exercised through inserts and updates, and the
installed constraint, index, trigger and function definitions are compared with
Backend/docs/DATABASE.md so a weakened expression fails a test even where a behaviour
case happens not to reach it.
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
    content_publication,
    content_seo,
    content_version,
    staff,
)

IMMUTABLE_VERSION = "published version .* is immutable"
PUBLICATION_NOT_PUBLISHED = "publication version must be published"
PUBLICATION_OTHER_ITEM = "version .* does not belong to item"
PUBLICATION_ARCHIVED = "archived item cannot be published"
IMMUTABLE_CONTENT = "published version content is immutable"

CONTENT_TABLES = (content_item, content_version, content_publication, content_seo)

# The primary keys, unique constraints, checks and foreign keys as PostgreSQL renders
# them. The definitions are normalised by ``normalise_constraint`` before the comparison,
# so PostgreSQL's whitespace and decorative parentheses do not matter.
EXPECTED_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "content_item_archive": (
        "c",
        "CHECK (((archived_at IS NULL) OR (archived_by IS NOT NULL)))",
    ),
    "content_item_archived_by_fkey": (
        "f",
        "FOREIGN KEY (archived_by) REFERENCES staff(user_id) ON DELETE SET NULL",
    ),
    "content_item_created_by_fkey": (
        "f",
        "FOREIGN KEY (created_by) REFERENCES staff(user_id) ON DELETE RESTRICT",
    ),
    "content_item_id_kind_key": ("u", "UNIQUE (id, kind)"),
    "content_item_next_version": ("c", "CHECK ((next_version > 0))"),
    "content_item_path_format": (
        "c",
        "CHECK (((path IS NULL) OR (path ~ '^/[a-z0-9-]*(/[a-z0-9-]+)*$'::text)))",
    ),
    "content_item_path_required": (
        "c",
        "CHECK (((kind <> ALL (ARRAY['landing_page'::content_kind, "
        "'legal_page'::content_kind])) OR (path IS NOT NULL)))",
    ),
    "content_item_pkey": ("p", "PRIMARY KEY (id)"),
    "content_item_section_shape": (
        "c",
        "CHECK (((kind <> 'page_section'::content_kind) OR ((path IS NULL) AND "
        "(slug IS NULL))))",
    ),
    "content_item_settings_shape": (
        "c",
        "CHECK (((kind <> 'settings'::content_kind) OR ((path IS NULL) AND "
        "(slug IS NULL))))",
    ),
    "content_item_slug_format": (
        "c",
        "CHECK (((slug IS NULL) OR (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'::text)))",
    ),
    "content_item_slug_required": (
        "c",
        "CHECK (((kind <> ALL (ARRAY['service'::content_kind, 'project'::content_kind])) "
        "OR (slug IS NOT NULL)))",
    ),
    "content_publication_item_id_fkey": (
        "f",
        "FOREIGN KEY (item_id) REFERENCES content_item(id) ON DELETE CASCADE",
    ),
    "content_publication_pkey": ("p", "PRIMARY KEY (item_id)"),
    "content_publication_published_by_fkey": (
        "f",
        "FOREIGN KEY (published_by) REFERENCES staff(user_id) ON DELETE RESTRICT",
    ),
    "content_publication_version_fk": (
        "f",
        "FOREIGN KEY (item_id, version_id) REFERENCES content_version(item_id, id) "
        "ON DELETE RESTRICT",
    ),
    "content_seo_description_length": (
        "c",
        "CHECK (((seo_description IS NULL) OR ((char_length(seo_description) >= 1) AND "
        "(char_length(seo_description) <= 160))))",
    ),
    "content_seo_og_image_id_fkey": (
        "f",
        "FOREIGN KEY (og_image_id) REFERENCES media(id) ON DELETE RESTRICT",
    ),
    "content_seo_pkey": ("p", "PRIMARY KEY (version_id)"),
    "content_seo_title_length": (
        "c",
        "CHECK (((seo_title IS NULL) OR ((char_length(seo_title) >= 1) AND "
        "(char_length(seo_title) <= 60))))",
    ),
    "content_seo_version_id_fkey": (
        "f",
        "FOREIGN KEY (version_id) REFERENCES content_version(id) ON DELETE CASCADE",
    ),
    "content_version_created_by_fkey": (
        "f",
        "FOREIGN KEY (created_by) REFERENCES staff(user_id) ON DELETE RESTRICT",
    ),
    "content_version_item_id_fkey": (
        "f",
        "FOREIGN KEY (item_id) REFERENCES content_item(id) ON DELETE CASCADE",
    ),
    "content_version_item_id_id_key": ("u", "UNIQUE (item_id, id)"),
    "content_version_item_id_version_number_key": (
        "u",
        "UNIQUE (item_id, version_number)",
    ),
    "content_version_number": ("c", "CHECK ((version_number > 0))"),
    "content_version_pkey": ("p", "PRIMARY KEY (id)"),
    "content_version_published": (
        "c",
        "CHECK (((status = 'published'::version_status) = (published_at IS NOT NULL)))",
    ),
    "content_version_published_by_fkey": (
        "f",
        "FOREIGN KEY (published_by) REFERENCES staff(user_id) ON DELETE RESTRICT",
    ),
    "content_version_publisher": (
        "c",
        "CHECK (((status = 'published'::version_status) = (published_by IS NOT NULL)))",
    ),
    "content_version_review": (
        "c",
        "CHECK (((status <> 'in_review'::version_status) OR (submitted_at IS NOT NULL)))",
    ),
    "content_version_updated_by_fkey": (
        "f",
        "FOREIGN KEY (updated_by) REFERENCES staff(user_id) ON DELETE RESTRICT",
    ),
}

# The six indexes in DATABASE.md, with their predicates. The primary key and the two
# composite uniques are constraints above, not indexes here.
EXPECTED_INDEXES: dict[str, str] = {
    "content_item_path_key": (
        "CREATE UNIQUE INDEX content_item_path_key ON public.content_item USING btree "
        "(path) WHERE (path IS NOT NULL)"
    ),
    "content_item_kind_slug_key": (
        "CREATE UNIQUE INDEX content_item_kind_slug_key ON public.content_item USING "
        "btree (kind, slug) WHERE (slug IS NOT NULL)"
    ),
    "content_item_settings_singleton": (
        "CREATE UNIQUE INDEX content_item_settings_singleton ON public.content_item "
        "USING btree (kind) WHERE (kind = 'settings'::content_kind)"
    ),
    "content_item_kind_idx": (
        "CREATE INDEX content_item_kind_idx ON public.content_item USING btree (kind) "
        "WHERE (archived_at IS NULL)"
    ),
    "content_version_one_open": (
        "CREATE UNIQUE INDEX content_version_one_open ON public.content_version USING "
        "btree (item_id) WHERE (status = ANY (ARRAY['draft'::version_status, "
        "'in_review'::version_status]))"
    ),
    "content_version_item_status_idx": (
        "CREATE INDEX content_version_item_status_idx ON public.content_version USING "
        "btree (item_id, status)"
    ),
}

# ``tgtype`` bits: 1 row, 2 before, 4 insert, 8 delete, 16 update.
EXPECTED_TRIGGERS: dict[str, tuple[str, bool, bool, bool, bool, bool]] = {
    "content_version_bump_next": (
        "content_version",
        True,
        False,
        True,
        False,
        False,
    ),
    "content_version_immutable": (
        "content_version",
        True,
        True,
        False,
        False,
        True,
    ),
    "content_version_set_updated_at": (
        "content_version",
        True,
        True,
        False,
        False,
        True,
    ),
    "content_publication_assert": (
        "content_publication",
        True,
        True,
        True,
        False,
        True,
    ),
    "content_seo_immutable": (
        "content_seo",
        True,
        True,
        True,
        True,
        True,
    ),
}


def normalise(definition: str) -> str:
    """Lower-case and collapse whitespace so only the meaning is compared."""
    return " ".join(definition.lower().split())


def normalise_constraint(definition: str) -> str:
    """Lower-case, drop PostgreSQL's decorative parentheses and collapse whitespace."""
    return " ".join(definition.lower().replace("(", "").replace(")", "").split())


def add_staff(db: Connection) -> uuid.UUID:
    """Insert the auth user and staff row that the created_by and published_by FKs need."""
    user_id = uuid.uuid4()
    db.execute(sa.insert(auth_users).values(id=user_id))
    db.execute(
        sa.insert(staff).values(
            user_id=user_id,
            email=f"{user_id}@example.com",
            display_name="Content editor",
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


def add_publication(
    db: Connection, item_id: uuid.UUID, version_id: uuid.UUID, published_by: uuid.UUID
) -> None:
    db.execute(
        sa.insert(content_publication).values(
            item_id=item_id,
            version_id=version_id,
            published_by=published_by,
        )
    )


def add_seo(db: Connection, version_id: uuid.UUID, **overrides: object) -> None:
    values: dict[str, object] = {"version_id": version_id}
    values.update(overrides)
    db.execute(sa.insert(content_seo).values(**values))


def select_item(db: Connection, item_id: uuid.UUID) -> sa.Row:
    return db.execute(sa.select(content_item).where(content_item.c.id == item_id)).one()


def select_version(db: Connection, version_id: uuid.UUID) -> sa.Row:
    return db.execute(
        sa.select(content_version).where(content_version.c.id == version_id)
    ).one()


def count_rows(db: Connection, table: sa.Table, *conditions: object) -> int:
    statement = sa.select(sa.func.count()).select_from(table)
    if conditions:
        statement = statement.where(*conditions)
    return db.execute(statement).scalar_one()


def test_the_content_tables_start_empty(db: Connection) -> None:
    for table in CONTENT_TABLES:
        rows = db.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()
        assert rows == 0, (
            f"stale committed rows in {table.name} from an earlier run; delete them before "
            "rerunning the suite"
        )


def test_a_content_item_and_a_draft_version_take_the_server_defaults(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    assert select_item(db, item_id).next_version == 1
    version_id = add_version(db, item_id, editor)

    item = select_item(db, item_id)
    assert isinstance(item.id, uuid.UUID)
    assert item.next_version == 2
    assert item.created_at is not None
    assert item.archived_at is None
    assert item.archived_by is None

    version = select_version(db, version_id)
    assert version.status == "draft"
    assert version.version_number == 1
    assert version.created_at is not None
    assert version.updated_at is not None
    assert version.submitted_at is None
    assert version.published_at is None
    assert version.published_by is None


def test_an_in_review_version_records_its_submission(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)

    version_id = add_version(
        db,
        item_id,
        editor,
        status="in_review",
        submitted_at=datetime.now(UTC),
    )

    assert select_version(db, version_id).status == "in_review"


@pytest.mark.parametrize("next_version", [0, -1])
def test_next_version_must_be_positive(db: Connection, next_version: int) -> None:
    editor = add_staff(db)

    with pytest.raises(IntegrityError, match="content_item_next_version"):
        with db.begin_nested():
            add_item(db, editor, next_version=next_version)


def test_bump_next_version_raises_the_counter_past_an_inserted_version(
    db: Connection,
) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    assert select_item(db, item_id).next_version == 1

    add_version(db, item_id, editor, version_number=5)

    assert select_item(db, item_id).next_version == 6


def test_bump_next_version_never_lowers_the_counter(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor, next_version=10)

    add_version(db, item_id, editor, version_number=2)

    assert select_item(db, item_id).next_version == 10


def test_a_second_open_version_is_refused(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    add_version(db, item_id, editor, version_number=1)

    with pytest.raises(IntegrityError, match="content_version_one_open"):
        with db.begin_nested():
            add_version(db, item_id, editor, version_number=2)


def test_an_in_review_version_is_open_too(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    add_version(db, item_id, editor, version_number=1)

    with pytest.raises(IntegrityError, match="content_version_one_open"):
        with db.begin_nested():
            add_version(
                db,
                item_id,
                editor,
                version_number=2,
                status="in_review",
                submitted_at=datetime.now(UTC),
            )


def test_a_new_version_is_allowed_once_the_first_is_published(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    first_id = add_version(db, item_id, editor, version_number=1)
    publish_version(db, first_id, editor)

    second_id = add_version(db, item_id, editor, version_number=2)

    assert select_version(db, second_id).status == "draft"
    assert select_item(db, item_id).next_version == 3


@pytest.mark.parametrize("version_number", [0, -1])
def test_a_version_number_must_be_positive(db: Connection, version_number: int) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)

    with pytest.raises(IntegrityError, match="content_version_number"):
        with db.begin_nested():
            add_version(db, item_id, editor, version_number=version_number)


def test_a_version_number_is_unique_per_item(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    first_id = add_version(db, item_id, editor, version_number=1)
    publish_version(db, first_id, editor)

    with pytest.raises(IntegrityError, match="content_version_item_id_version_number_key"):
        with db.begin_nested():
            add_version(db, item_id, editor, version_number=1)

    # The pair is unique, not the number across items.
    other_item_id = add_item(db, editor, path="/other")
    add_version(db, other_item_id, editor, version_number=1)


def test_the_publish_update_succeeds(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)

    publish_version(db, version_id, editor)

    version = select_version(db, version_id)
    assert version.status == "published"
    assert version.published_at is not None
    assert version.published_by == editor


def test_the_publish_update_sets_updated_at(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    # An insert does not run the timestamp trigger, so this pins a stale value first.
    version_id = add_version(
        db, item_id, editor, updated_at=datetime(2000, 1, 1, tzinfo=UTC)
    )

    db.execute(
        sa.update(content_version)
        .where(content_version.c.id == version_id)
        .values(updated_by=editor)
    )

    assert select_version(db, version_id).updated_at.year != 2000


@pytest.mark.parametrize(
    "change",
    [
        {"status": "draft", "published_at": None, "published_by": None},
        {"version_number": 99},
        {"published_at": datetime(2026, 1, 1, tzinfo=UTC)},
    ],
    ids=["back-to-draft", "renumber", "new-published-at"],
)
def test_a_published_version_cannot_be_updated(
    db: Connection, change: dict[str, object]
) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)
    publish_version(db, version_id, editor)

    with pytest.raises(DBAPIError, match=IMMUTABLE_VERSION):
        with db.begin_nested():
            db.execute(
                sa.update(content_version)
                .where(content_version.c.id == version_id)
                .values(**change)
            )

    assert select_version(db, version_id).status == "published"


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        (
            {"status": "published", "published_at": None, "published_by": "editor"},
            "content_version_published",
        ),
        (
            {"status": "draft", "published_at": datetime.now(UTC)},
            "content_version_published",
        ),
        (
            {"status": "published", "published_at": datetime.now(UTC), "published_by": None},
            "content_version_publisher",
        ),
        (
            {"status": "draft", "published_by": "editor"},
            "content_version_publisher",
        ),
        (
            {"status": "in_review", "submitted_at": None, "published_by": None},
            "content_version_review",
        ),
    ],
    ids=[
        "published-without-published-at",
        "draft-with-published-at",
        "published-without-publisher",
        "draft-with-publisher",
        "in-review-without-submitted-at",
    ],
)
def test_the_version_status_checks_refuse_incoherent_rows(
    db: Connection, overrides: dict[str, object], constraint: str
) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    values = dict(overrides)
    if values.get("published_by") == "editor":
        values["published_by"] = editor

    with pytest.raises(IntegrityError, match=constraint):
        with db.begin_nested():
            add_version(db, item_id, editor, **values)


def test_a_publication_records_the_published_version(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)
    publish_version(db, version_id, editor)

    add_publication(db, item_id, version_id, editor)

    row = db.execute(
        sa.select(content_publication).where(content_publication.c.item_id == item_id)
    ).one()
    assert row.version_id == version_id
    assert row.published_at is not None
    assert row.published_by == editor


def test_a_publication_refuses_a_draft_version(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)

    with pytest.raises(DBAPIError, match=PUBLICATION_NOT_PUBLISHED):
        with db.begin_nested():
            add_publication(db, item_id, version_id, editor)


def test_a_publication_refuses_another_items_version(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    other_item_id = add_item(db, editor, path="/other")
    other_version_id = add_version(db, other_item_id, editor)
    publish_version(db, other_version_id, editor)

    with pytest.raises(DBAPIError, match=PUBLICATION_OTHER_ITEM):
        with db.begin_nested():
            add_publication(db, item_id, other_version_id, editor)


def test_a_publication_refuses_an_archived_item(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)
    publish_version(db, version_id, editor)
    db.execute(
        sa.update(content_item)
        .where(content_item.c.id == item_id)
        .values(archived_at=datetime.now(UTC), archived_by=editor)
    )

    with pytest.raises(DBAPIError, match=PUBLICATION_ARCHIVED):
        with db.begin_nested():
            add_publication(db, item_id, version_id, editor)


def test_archived_at_without_archived_by_is_refused(db: Connection) -> None:
    editor = add_staff(db)

    with pytest.raises(IntegrityError, match="content_item_archive"):
        with db.begin_nested():
            add_item(db, editor, archived_at=datetime.now(UTC))

    item_id = add_item(db, editor, path="/live")
    assert select_item(db, item_id).archived_at is None


def test_an_archived_item_records_both_flags(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor, path="/archived")
    archived_at = datetime.now(UTC)

    db.execute(
        sa.update(content_item)
        .where(content_item.c.id == item_id)
        .values(archived_at=archived_at, archived_by=editor)
    )

    item = select_item(db, item_id)
    assert item.archived_at == archived_at
    assert item.archived_by == editor


@pytest.mark.parametrize(
    "path",
    ["/", "/about", "/legal/privacy", "/a-b/c-d"],
    ids=["root", "one-segment", "two-segments", "hyphens"],
)
def test_a_valid_path_is_accepted(db: Connection, path: str) -> None:
    editor = add_staff(db)

    item_id = add_item(db, editor, kind="legal_page", path=path)

    assert select_item(db, item_id).path == path


@pytest.mark.parametrize(
    "path",
    ["about", "/About", "/about/", "/a//b", "/about_us", "//"],
    ids=["no-slash", "uppercase", "trailing-slash", "empty-segment", "underscore", "empty"],
)
def test_an_invalid_path_is_refused(db: Connection, path: str) -> None:
    editor = add_staff(db)

    with pytest.raises(IntegrityError, match="content_item_path_format"):
        with db.begin_nested():
            add_item(db, editor, kind="legal_page", path=path)


@pytest.mark.parametrize("slug", ["about", "a-b", "a1-b2"])
def test_a_valid_slug_is_accepted(db: Connection, slug: str) -> None:
    editor = add_staff(db)

    item_id = add_item(db, editor, kind="service", slug=slug)

    assert select_item(db, item_id).slug == slug


@pytest.mark.parametrize(
    "slug",
    ["About", "a-", "-a", "a--b", "a_b", ""],
    ids=["uppercase", "trailing-hyphen", "leading-hyphen", "double-hyphen", "underscore", "empty"],
)
def test_an_invalid_slug_is_refused(db: Connection, slug: str) -> None:
    editor = add_staff(db)

    with pytest.raises(IntegrityError, match="content_item_slug_format"):
        with db.begin_nested():
            add_item(db, editor, kind="service", slug=slug)


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"kind": "landing_page"}, "content_item_path_required"),
        ({"kind": "legal_page"}, "content_item_path_required"),
        ({"kind": "service"}, "content_item_slug_required"),
        ({"kind": "project"}, "content_item_slug_required"),
        ({"kind": "settings", "path": "/settings"}, "content_item_settings_shape"),
        ({"kind": "settings", "slug": "settings"}, "content_item_settings_shape"),
        ({"kind": "page_section", "path": "/section"}, "content_item_section_shape"),
        ({"kind": "page_section", "slug": "section"}, "content_item_section_shape"),
    ],
    ids=[
        "landing-page-without-path",
        "legal-page-without-path",
        "service-without-slug",
        "project-without-slug",
        "settings-with-path",
        "settings-with-slug",
        "section-with-path",
        "section-with-slug",
    ],
)
def test_the_kind_shape_rules_refuse_incoherent_items(
    db: Connection, overrides: dict[str, object], constraint: str
) -> None:
    editor = add_staff(db)
    if "path" not in overrides:
        overrides["path"] = None

    with pytest.raises(IntegrityError, match=constraint):
        with db.begin_nested():
            add_item(db, editor, **overrides)


@pytest.mark.parametrize(
    "kind",
    ["landing_page", "legal_page", "service", "project", "settings", "page_section"],
)
def test_every_kind_accepts_a_coherent_item(db: Connection, kind: str) -> None:
    editor = add_staff(db)
    overrides: dict[str, object] = {"kind": kind}
    if kind in ("landing_page", "legal_page"):
        overrides["path"] = "/coherent"
    if kind in ("service", "project"):
        overrides["slug"] = "coherent"

    item_id = add_item(db, editor, **overrides)

    assert select_item(db, item_id).kind == kind


def test_the_settings_item_is_a_singleton(db: Connection) -> None:
    editor = add_staff(db)
    add_item(db, editor, kind="settings", path=None)

    with pytest.raises(IntegrityError, match="content_item_settings_singleton"):
        with db.begin_nested():
            add_item(db, editor, kind="settings", path=None)


def test_a_path_is_unique(db: Connection) -> None:
    editor = add_staff(db)
    add_item(db, editor, kind="legal_page", path="/privacy")

    with pytest.raises(IntegrityError, match="content_item_path_key"):
        with db.begin_nested():
            add_item(db, editor, kind="legal_page", path="/privacy")


def test_a_slug_is_unique_within_its_kind(db: Connection) -> None:
    editor = add_staff(db)
    add_item(db, editor, kind="service", slug="branding")

    with pytest.raises(IntegrityError, match="content_item_kind_slug_key"):
        with db.begin_nested():
            add_item(db, editor, kind="service", slug="branding")

    # Another kind may use the same slug.
    add_item(db, editor, kind="project", slug="branding")


def test_two_items_of_one_kind_are_allowed(db: Connection) -> None:
    # The kind index is not unique; two legal pages coexist. The definition test pins its
    # predicate.
    editor = add_staff(db)
    add_item(db, editor, kind="legal_page", path="/one")
    add_item(db, editor, kind="legal_page", path="/two")

    assert count_rows(db, content_item, content_item.c.kind == "legal_page") == 2


def test_seo_title_and_description_accept_their_upper_bounds(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)

    add_seo(db, version_id, seo_title="t" * 60, seo_description="d" * 160)

    row = db.execute(
        sa.select(content_seo).where(content_seo.c.version_id == version_id)
    ).one()
    assert row.seo_title == "t" * 60
    assert row.seo_description == "d" * 160
    assert row.seo_noindex is False
    assert row.og_image_id is None


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"seo_title": ""}, "content_seo_title_length"),
        ({"seo_title": "t" * 61}, "content_seo_title_length"),
        ({"seo_description": ""}, "content_seo_description_length"),
        ({"seo_description": "d" * 161}, "content_seo_description_length"),
    ],
    ids=["empty-title", "long-title", "empty-description", "long-description"],
)
def test_seo_lengths_are_bounded(
    db: Connection, overrides: dict[str, object], constraint: str
) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)

    with pytest.raises(IntegrityError, match=constraint):
        with db.begin_nested():
            add_seo(db, version_id, **overrides)


def test_seo_cannot_be_inserted_for_a_published_version(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)
    publish_version(db, version_id, editor)

    with pytest.raises(DBAPIError, match=IMMUTABLE_CONTENT):
        with db.begin_nested():
            add_seo(db, version_id, seo_title="Late title")


def test_seo_created_on_a_draft_is_frozen_after_publish(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)
    add_seo(db, version_id, seo_title="Before publish")

    publish_version(db, version_id, editor)

    with pytest.raises(DBAPIError, match=IMMUTABLE_CONTENT):
        with db.begin_nested():
            db.execute(
                sa.update(content_seo)
                .where(content_seo.c.version_id == version_id)
                .values(seo_title="After publish")
            )

    with pytest.raises(DBAPIError, match=IMMUTABLE_CONTENT):
        with db.begin_nested():
            db.execute(
                sa.delete(content_seo).where(content_seo.c.version_id == version_id)
            )

    assert (
        db.execute(
            sa.select(content_seo.c.seo_title).where(
                content_seo.c.version_id == version_id
            )
        ).scalar_one()
        == "Before publish"
    )


def test_seo_for_an_unknown_version_is_refused(db: Connection) -> None:
    with pytest.raises(IntegrityError, match="content_seo_version_id_fkey"):
        with db.begin_nested():
            add_seo(db, uuid.uuid4(), seo_title="Orphan")


def test_seo_is_deleted_with_its_draft_version(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)
    add_seo(db, version_id, seo_title="Draft title")

    db.execute(sa.delete(content_version).where(content_version.c.id == version_id))

    assert count_rows(db, content_seo, content_seo.c.version_id == version_id) == 0


def test_deleting_an_item_cascades_its_versions_and_seo(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)
    add_seo(db, version_id, seo_title="Draft title")

    db.execute(sa.delete(content_item).where(content_item.c.id == item_id))

    assert count_rows(db, content_item, content_item.c.id == item_id) == 0
    assert count_rows(db, content_version, content_version.c.item_id == item_id) == 0
    assert count_rows(db, content_seo, content_seo.c.version_id == version_id) == 0


def test_deleting_a_version_named_by_a_publication_is_refused(db: Connection) -> None:
    editor = add_staff(db)
    item_id = add_item(db, editor)
    version_id = add_version(db, item_id, editor)
    publish_version(db, version_id, editor)
    add_publication(db, item_id, version_id, editor)

    with pytest.raises(IntegrityError, match="content_publication_version_fk"):
        with db.begin_nested():
            db.execute(sa.delete(content_version).where(content_version.c.id == version_id))

    assert count_rows(db, content_version, content_version.c.id == version_id) == 1


def test_every_documented_constraint_matches_its_definition(db: Connection) -> None:
    # Alembic 1.20 does not compare CHECK constraints, so the installed definitions are
    # compared here instead. Whitespace and the parentheses PostgreSQL adds are
    # normalised; a changed bound or operator still fails.
    installed = {
        name: (kind, normalise_constraint(definition))
        for name, kind, definition in db.execute(
            sa.text(
                "select conname, contype, pg_get_constraintdef(oid) from pg_constraint "
                "where conrelid in ('content_item'::regclass, 'content_version'::regclass, "
                "'content_publication'::regclass, 'content_seo'::regclass) "
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
                "where tablename in ('content_item', 'content_version', "
                "'content_publication', 'content_seo')"
            )
        ).all()
        if name in EXPECTED_INDEXES
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
        )
        for name, table, tgtype in db.execute(
            sa.text(
                "select tgname, tgrelid::regclass::text, tgtype from pg_trigger "
                "where not tgisinternal and tgrelid in ('content_item'::regclass, "
                "'content_version'::regclass, 'content_publication'::regclass, "
                "'content_seo'::regclass)"
            )
        ).all()
    }

    assert installed == EXPECTED_TRIGGERS


@pytest.mark.parametrize(
    ("function", "fragments"),
    [
        (
            "bump_next_version()",
            [
                "update content_item set next_version = greatest(next_version, "
                "new.version_number + 1) where id = new.item_id",
                "return null",
            ],
        ),
        (
            "prevent_published_version_mutation()",
            [
                "if old.status = 'published' then",
                "raise exception 'published version % is immutable', old.id",
            ],
        ),
        (
            "assert_publication_version()",
            [
                "where cv.id = new.version_id and cv.item_id = new.item_id",
                "raise exception 'version % does not belong to item %', "
                "new.version_id, new.item_id",
                "raise exception 'publication version must be published'",
                "raise exception 'archived item cannot be published'",
            ],
        ),
        (
            "prevent_published_content_mutation()",
            [
                "v_version := case when tg_op = 'delete' then old.version_id "
                "else new.version_id end",
                "raise exception 'published version content is immutable'",
                "if tg_op = 'delete' then return old",
            ],
        ),
    ],
    ids=["bump", "version-immutable", "publication-assert", "content-immutable"],
)
def test_the_installed_functions_pin_their_messages(
    db: Connection, function: str, fragments: list[str]
) -> None:
    definition = db.execute(
        sa.text("select pg_get_functiondef(cast(:function as regprocedure))"),
        {"function": function},
    ).scalar_one()
    normalised = normalise(definition)

    for fragment in fragments:
        assert fragment in normalised, f"the installed {function} is missing: {fragment}"
