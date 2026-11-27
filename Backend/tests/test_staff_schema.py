"""The staff table's constraints and the last-Admin guard, against real PostgreSQL.

Every test runs inside the ``db`` transaction and is rolled back by the fixture, except the
concurrency, deadlock and isolation tests, which commit deliberately on independent
connections and clean up.
"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy import Connection, Engine
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
    rows = db.execute(sa.select(staff.c.user_id, staff.c.email, staff.c.role)).all()
    assert rows == [], (
        "stale committed staff rows from an earlier run; delete them before rerunning the "
        f"suite: {rows}"
    )


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


def test_demoting_and_deactivating_the_last_admin_together_is_refused(db: Connection) -> None:
    admin_id = add_staff(db, role="admin")

    with pytest.raises(DBAPIError, match=LAST_ADMIN):
        with db.begin_nested():
            db.execute(
                sa.update(staff)
                .where(staff.c.user_id == admin_id)
                .values(role="editor", active=False)
            )

    assert role_of(db, admin_id) == "admin"
    assert is_active(db, admin_id) is True


def test_a_second_inactive_admin_does_not_protect_the_only_active_one(db: Connection) -> None:
    active_admin = add_staff(db, role="admin")
    add_staff(db, role="admin", active=False)

    with pytest.raises(DBAPIError, match=LAST_ADMIN):
        with db.begin_nested():
            db.execute(sa.delete(staff).where(staff.c.user_id == active_admin))


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


def wait_for_an_advisory_lock_waiter(engine: Engine, timeout: float = 5.0) -> None:
    """Return once a backend in this database is queued on an advisory lock."""
    deadline = time.monotonic() + timeout
    with engine.connect() as watcher:
        while time.monotonic() < deadline:
            waiting = watcher.execute(
                sa.text(
                    "select count(*) from pg_locks "
                    "where locktype = 'advisory' and not granted "
                    "and database = "
                    "(select oid from pg_database where datname = current_database())"
                )
            ).scalar_one()
            if waiting:
                return
            time.sleep(0.01)
    raise AssertionError("the second write never blocked on the last-Admin advisory lock")


def commit_two_admins(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    """Commit two active Admins outside any test transaction and return their ids."""
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    with engine.begin() as setup:
        setup.execute(sa.insert(auth_users).values([{"id": first_id}, {"id": second_id}]))
        setup.execute(
            sa.insert(staff).values(
                [
                    {
                        "user_id": first_id,
                        "email": "concurrent-a@example.com",
                        "display_name": "Admin A",
                        "role": "admin",
                    },
                    {
                        "user_id": second_id,
                        "email": "concurrent-b@example.com",
                        "display_name": "Admin B",
                        "role": "admin",
                    },
                ]
            )
        )
    return first_id, second_id


def cleanup_committed_staff(engine: Engine, user_ids: list[uuid.UUID]) -> None:
    """Remove committed test rows; TRUNCATE is needed because the last Admin cannot be deleted."""
    with engine.begin() as cleanup:
        cleanup.execute(sa.text("truncate table staff"))
        cleanup.execute(sa.delete(auth_users).where(auth_users.c.id.in_(user_ids)))


def count_active_admins(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.execute(
            sa.select(sa.func.count())
            .select_from(staff)
            .where(staff.c.role == "admin", staff.c.active)
        ).scalar_one()


def test_the_installed_guard_is_the_locking_read_version(db: Connection) -> None:
    row_definition = db.execute(
        sa.text("select pg_get_functiondef('enforce_last_admin()'::regprocedure)")
    ).scalar_one()
    assert "for update" in row_definition.lower()

    lock_definition = db.execute(
        sa.text("select pg_get_functiondef('lock_staff_writes()'::regprocedure)")
    ).scalar_one()
    assert "pg_advisory_xact_lock" in lock_definition

    triggers = dict(
        db.execute(
            sa.text(
                "select tgname, (tgtype & 1) = 1 from pg_trigger "
                "where tgrelid = 'staff'::regclass and not tgisinternal"
            )
        ).all()
    )
    assert triggers["staff_lock_writes"] is False  # statement-level, before row locks
    assert triggers["staff_last_admin"] is True  # row-level guard


def test_concurrent_deletes_cannot_remove_both_active_admins(database_engine: Engine) -> None:
    first_id, second_id = commit_two_admins(database_engine)
    first = database_engine.connect()
    second = database_engine.connect()
    failure: Exception | None = None

    def delete_second() -> None:
        nonlocal failure
        try:
            second.begin()
            second.execute(sa.delete(staff).where(staff.c.user_id == second_id))
            second.commit()
        except Exception as exc:  # the expected refusal; asserted after the join
            failure = exc
            second.rollback()

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        first.begin()
        first.execute(sa.delete(staff).where(staff.c.user_id == first_id))
        future = pool.submit(delete_second)
        wait_for_an_advisory_lock_waiter(database_engine)
        first.commit()
        future.result(timeout=10)

        assert isinstance(failure, DBAPIError), f"the second delete did not fail: {failure!r}"
        assert LAST_ADMIN in str(failure)
        assert count_active_admins(database_engine) == 1
    finally:
        # Release the advisory lock before waiting for the worker, or a failed wait deadlocks.
        if first.in_transaction():
            first.rollback()
        first.close()
        pool.shutdown(wait=True)
        second.rollback()
        second.close()
        cleanup_committed_staff(database_engine, [first_id, second_id])


def test_a_delete_then_an_update_of_the_other_admin_does_not_deadlock(
    database_engine: Engine,
) -> None:
    first_id, second_id = commit_two_admins(database_engine)
    first = database_engine.connect()
    second = database_engine.connect()
    failure: Exception | None = None

    def update_second() -> None:
        nonlocal failure
        try:
            second.begin()
            second.execute(
                sa.update(staff)
                .where(staff.c.user_id == second_id)
                .values(display_name="from second")
            )
            second.commit()
        except Exception as exc:
            failure = exc
            second.rollback()

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        first.begin()
        first.execute(sa.delete(staff).where(staff.c.user_id == first_id))
        future = pool.submit(update_second)
        wait_for_an_advisory_lock_waiter(database_engine)
        # The second writer is waiting on the statement lock before it takes row B, so this
        # update of row B cannot wait behind it: no advisory-versus-row lock cycle exists.
        first.execute(
            sa.update(staff).where(staff.c.user_id == second_id).values(display_name="from first")
        )
        first.commit()
        future.result(timeout=10)

        assert failure is None, f"the second writer failed: {failure!r}"
        with database_engine.connect() as check:
            display_name = check.execute(
                sa.select(staff.c.display_name).where(staff.c.user_id == second_id)
            ).scalar_one()
        assert display_name == "from second"
        assert count_active_admins(database_engine) == 1
    finally:
        if first.in_transaction():
            first.rollback()
        first.close()
        pool.shutdown(wait=True)
        second.rollback()
        second.close()
        cleanup_committed_staff(database_engine, [first_id, second_id])


@pytest.mark.parametrize("isolation_level", ["REPEATABLE READ", "SERIALIZABLE"])
def test_the_guard_holds_at_stronger_isolation(
    database_engine: Engine, isolation_level: str
) -> None:
    first_id, second_id = commit_two_admins(database_engine)
    first = database_engine.connect()
    second = database_engine.connect()
    failure: Exception | None = None

    def delete_second() -> None:
        nonlocal failure
        try:
            second.begin()
            second.execute(sa.text(f"set transaction isolation level {isolation_level}"))
            second.execute(sa.delete(staff).where(staff.c.user_id == second_id))
            second.commit()
        except Exception as exc:
            failure = exc
            second.rollback()

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        first.begin()
        first.execute(sa.text(f"set transaction isolation level {isolation_level}"))
        first.execute(sa.delete(staff).where(staff.c.user_id == first_id))
        future = pool.submit(delete_second)
        wait_for_an_advisory_lock_waiter(database_engine)
        first.commit()
        future.result(timeout=10)

        assert failure is not None, "the second delete was allowed at this isolation level"
        message = str(failure)
        assert LAST_ADMIN in message or "could not serialize access" in message
        assert count_active_admins(database_engine) == 1
    finally:
        if first.in_transaction():
            first.rollback()
        first.close()
        pool.shutdown(wait=True)
        second.rollback()
        second.close()
        cleanup_committed_staff(database_engine, [first_id, second_id])
