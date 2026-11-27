"""The migration history and ``Base.metadata`` agree.

``alembic check`` is also run from the command line; this keeps the property in the suite
so a model change that forgets a revision fails a test, not a later review.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine


def test_alembic_check_finds_no_drift(database_engine: Engine, alembic_config: Config) -> None:
    # database_engine applies the bootstrap and `upgrade head` before the comparison.
    command.check(alembic_config)
