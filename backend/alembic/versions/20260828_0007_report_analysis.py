"""Persist formative report analysis details."""

import sqlalchemy as sa

from alembic import op

revision = "20260828_0007"
down_revision = "20260823_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("reports")}
    if "ai_analysis" not in columns:
        with op.batch_alter_table("reports") as batch:
            batch.add_column(sa.Column("ai_analysis", sa.JSON(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("reports")}
    if "ai_analysis" in columns:
        with op.batch_alter_table("reports") as batch:
            batch.drop_column("ai_analysis")
