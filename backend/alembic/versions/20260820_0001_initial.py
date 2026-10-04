"""Create the pilot schema and add class membership support."""

import sqlalchemy as sa

from alembic import op
from app import models  # noqa: F401
from app.db import Base

revision = "20260820_0001"
down_revision = None
branch_labels = None
depends_on = None


# This is the pilot's original table set.  Do not replace it with all current
# runtime metadata: later revisions own their DDL, especially PBL (0015) and
# single-round learning (0033).  Keeping this allowlist prevents a fresh
# upgrade from silently creating future-schema tables at revision 0001.
PILOT_TABLE_NAMES = (
    "users",
    "problems",
    "conversations",
    "messages",
    "question_threads",
    "question_thread_messages",
    "reports",
)


def upgrade() -> None:
    bind = op.get_bind()
    missing = [name for name in PILOT_TABLE_NAMES if name not in Base.metadata.tables]
    if missing:
        raise RuntimeError(f"pilot schema metadata is missing required tables: {', '.join(missing)}")
    Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables[name] for name in PILOT_TABLE_NAMES])
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "class_ids" not in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("class_ids", sa.JSON(), nullable=True))
        op.execute("UPDATE users SET class_ids = '[]' WHERE class_ids IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "class_ids" in user_columns:
            with op.batch_alter_table("users") as batch_op:
                batch_op.drop_column("class_ids")
