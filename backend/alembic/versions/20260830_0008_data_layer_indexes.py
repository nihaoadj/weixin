"""Add stable pagination indexes for data summaries."""

import sqlalchemy as sa

from alembic import op

revision = "20260830_0008"
down_revision = "20260828_0007"
branch_labels = None
depends_on = None


def _create_index_if_missing(name: str, table: str, columns: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return
    if name not in {item["name"] for item in inspector.get_indexes(table)}:
        op.create_index(name, table, columns)


def upgrade() -> None:
    _create_index_if_missing("ix_conversations_updated_id", "conversations", ["updated_at", "id"])
    _create_index_if_missing("ix_reports_updated_id", "reports", ["updated_at", "id"])
    _create_index_if_missing("ix_conversations_student_updated_id", "conversations", ["student_id", "updated_at", "id"])
    _create_index_if_missing("ix_reports_student_updated_id", "reports", ["student_id", "updated_at", "id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for name, table in (
        ("ix_reports_student_updated_id", "reports"),
        ("ix_conversations_student_updated_id", "conversations"),
        ("ix_reports_updated_id", "reports"),
        ("ix_conversations_updated_id", "conversations"),
    ):
        if table in inspector.get_table_names() and name in {item["name"] for item in inspector.get_indexes(table)}:
            op.drop_index(name, table_name=table)
