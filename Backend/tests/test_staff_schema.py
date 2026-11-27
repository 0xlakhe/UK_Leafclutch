"""The staff table's constraints and the last-Admin guard, against real PostgreSQL.

Every test runs inside the ``db`` transaction and is rolled back by the fixture.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import auth_users, staff

LAST_ADMIN = "the last active Admin cannot be removed"


def add_staff(
    db: Connection,
    *,
    role: str = "admin",
    active: bool = True,
    email: str | None = None,
    display_name: str = "Staff Member",
    created_at: datetime | None = None,
) -> uuid.UUID:
    """Insert one staff row, with the auth user it references, and return its ``user_id``."""
    user_id = uuid.uuid4()
    db.execute(sa.insert(auth_users).values(id=user_id))
    values: dict[str, object] = {
        "user_id": user_id,
        "email": email if email is not None else f"{user_id}@example.com",
        "display_name": display_name,
        "role": role,
        "active": active,
    }
    if created_at is not None:
        values["created_at"] = created_at
        values["updated_at"] = created_at
    db.execute(sa.insert(staff).values(**values))
    return user_id


def count_staff(db: Connection) -> int:
    return db.execute(sa.select(sa.func.count()).select_from(staff)).scalar_one()


def role_of(db: Connection, user_id: uuid.UUID) -> str:
    return db.execute(sa.select(staff.c.role).where(staff.c.user_id == user_id)).scalar_one()


def is_active(db: Connection, user_id: uuid.UUID) -> bool:
    return db.execute(sa.select(staff.c.active).where(staff.c.user_id == user_id)).scalar_one()


def test_the_staff_table_starts_empty(db: Connection) -> None:
    assert count_staff(db) == 0


def test_defaults_apply_on_insert(db: Connection) -> None:
    user_id = add_staff(db, role="editor")

    row = db.execute(
        sa.select(staff.c.active, staff.c.created_at, staff.c.updated_at).where(
            staff.c.user_id == user_id
        )
    ).one()
    assert row.active is True
    assert row.created_at == row.updated_at


def test_deleting_a_missing_staff_row_is_a_no_op(db: Connection) -> None:
    db.execute(sa.delete(staff).where(staff.c.user_id == uuid.uuid4()))

    assert count_staff(db) == 0


def test_staff_requires_an_existing_auth_user(db: Connection) -> None:
    with pytest.raises(IntegrityError, match="staff_user_id_fkey"):
        with db.begin_nested():
            db.execute(
                sa.insert(staff).values(
                    user_id=uuid.uuid4(),
                    email="orphan@example.com",
                    display_name="Orphan",
                    role="admin",
                )
            )


def test_deleting_a_staffed_auth_user_is_refused(db: Connection) -> None:
    admin_id = add_staff(db)

    with pytest.raises(IntegrityError, match="staff_user_id_fkey"):
        with db.begin_nested():
            db.execute(sa.delete(auth_users).where(auth_users.c.id == admin_id))


def test_deleting_the_last_active_admin_is_refused(db: Connection) -> None:
    admin_id = add_staff(db, role="admin")

    with pytest.raises(DBAPIError, match=LAST_ADMIN):
        with db.begin_nested():
            db.execute(sa.delete(staff).where(staff.c.user_id == admin_id))

    assert count_staff(db) == 1


def test_demoting_the_last_active_admin_is_refused(db: Connection) -> None:
    admin_id = add_staff(db, role="admin")

    with pytest.raises(DBAPIError, match=LAST_ADMIN):
        with db.begin_nested():
            db.execute(
                sa.update(staff).where(staff.c.user_id == admin_id).values(role="editor")
            )

    assert role_of(db, admin_id) == "admin"


def test_deactivating_the_last_active_admin_is_refused(db: Connection) -> None:
    admin_id = add_staff(db, role="admin")

    with pytest.raises(DBAPIError, match=LAST_ADMIN):
        with db.begin_nested():
            db.execute(
                sa.update(staff).where(staff.c.user_id == admin_id).values(active=False)
            )

    assert is_active(db, admin_id) is True


def test_a_second_active_admin_allows_deleting_the_first(db: Connection) -> None:
    first = add_staff(db, role="admin")
    add_staff(db, role="admin")

    db.execute(sa.delete(staff).where(staff.c.user_id == first))

    assert count_staff(db) == 1


def test_a_second_active_admin_allows_demoting_the_first(db: Connection) -> None:
    first = add_staff(db, role="admin")
    add_staff(db, role="admin")

    db.execute(sa.update(staff).where(staff.c.user_id == first).values(role="editor"))

    assert role_of(db, first) == "editor"


def test_a_second_active_admin_allows_deactivating_the_first(db: Connection) -> None:
    first = add_staff(db, role="admin")
    add_staff(db, role="admin")

    db.execute(sa.update(staff).where(staff.c.user_id == first).values(active=False))

    assert is_active(db, first) is False


def test_an_editor_is_not_protected(db: Connection) -> None:
    editor_id = add_staff(db, role="editor")

    db.execute(sa.delete(staff).where(staff.c.user_id == editor_id))

    assert count_staff(db) == 0


def test_an_inactive_admin_is_not_protected(db: Connection) -> None:
    admin_id = add_staff(db, role="admin", active=False)

    db.execute(sa.delete(staff).where(staff.c.user_id == admin_id))

    assert count_staff(db) == 0


def test_a_duplicate_email_is_refused(db: Connection) -> None:
    add_staff(db, email="admin@example.com")

    with pytest.raises(IntegrityError, match="staff_email_unique"):
        with db.begin_nested():
            add_staff(db, email="admin@example.com")


def test_a_duplicate_email_is_refused_regardless_of_case(db: Connection) -> None:
    add_staff(db, email="admin@example.com")

    with pytest.raises(IntegrityError, match="staff_email_unique"):
        with db.begin_nested():
            add_staff(db, email="Admin@Example.com")


@pytest.mark.parametrize(
    ("display_name", "accepted"),
    [
        ("A", True),
        ("A" * 100, True),
        ("", False),
        ("A" * 101, False),
    ],
    ids=["one-character", "hundred-characters", "empty", "hundred-and-one-characters"],
)
def test_display_name_length_bounds(
    db: Connection, display_name: str, accepted: bool
) -> None:
    if accepted:
        add_staff(db, display_name=display_name)
        assert count_staff(db) == 1
        return

    with pytest.raises(IntegrityError, match="staff_display_name_length"):
        with db.begin_nested():
            add_staff(db, display_name=display_name)


def test_an_update_moves_updated_at_but_not_created_at(db: Connection) -> None:
    # now() is constant for a transaction, so the row starts an hour in the past and the
    # update supplies an even older updated_at: only the trigger can move it forward.
    old = datetime.now(UTC) - timedelta(hours=1)
    admin_id = add_staff(db, created_at=old)

    db.execute(
        sa.update(staff)
        .where(staff.c.user_id == admin_id)
        .values(display_name="Renamed", updated_at=old - timedelta(days=1))
    )

    created_at, updated_at = db.execute(
        sa.select(staff.c.created_at, staff.c.updated_at).where(staff.c.user_id == admin_id)
    ).one()
    assert created_at == old
    assert updated_at > old
