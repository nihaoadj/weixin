"""Create the pilot schema and add class membership support."""

import sqlalchemy as sa

from alembic import op
from app import models  # noqa: F401
from app.db import Base

revision = "20260820_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
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
