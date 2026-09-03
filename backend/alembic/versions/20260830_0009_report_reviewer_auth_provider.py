"""Report reviewer audit trail and account provider isolation."""

import sqlalchemy as sa

from alembic import op

revision = "20260830_0009"
down_revision = "20260830_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    report_columns = {item["name"] for item in inspector.get_columns("reports")}
    if "reviewer_id" not in report_columns:
        with op.batch_alter_table("reports") as batch:
            batch.add_column(sa.Column("reviewer_id", sa.Integer(), nullable=True))
            batch.create_index("ix_reports_reviewer_id", ["reviewer_id"])
    user_columns = {item["name"] for item in inspector.get_columns("users")}
    if "auth_provider" not in user_columns:
        with op.batch_alter_table("users") as batch:
            batch.add_column(
                sa.Column("auth_provider", sa.String(length=20), nullable=False, server_default="demo")
            )
            batch.create_index("ix_users_auth_provider", ["auth_provider"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    report_columns = {item["name"] for item in inspector.get_columns("reports")}
    if "reviewer_id" in report_columns:
        with op.batch_alter_table("reports") as batch:
            batch.drop_index("ix_reports_reviewer_id")
            batch.drop_column("reviewer_id")
    user_columns = {item["name"] for item in inspector.get_columns("users")}
    if "auth_provider" in user_columns:
        with op.batch_alter_table("users") as batch:
            batch.drop_index("ix_users_auth_provider")
            batch.drop_column("auth_provider")
