"""Store catalog-backed revision topics selected during report review.

Revision ID: 20260831_0014
Revises: 20260831_0013
"""

import sqlalchemy as sa

from alembic import op

revision = "20260831_0014"
down_revision = "20260831_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "report_knowledge_links" in set(inspector.get_table_names()):
        return
    op.create_table(
        "report_knowledge_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("point_code", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "point_code", name="uq_report_knowledge_link"),
    )
    op.create_index("ix_report_knowledge_links_report_id", "report_knowledge_links", ["report_id"], unique=False)
    op.create_index("ix_report_knowledge_links_point", "report_knowledge_links", ["point_code"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "report_knowledge_links" not in set(inspector.get_table_names()):
        return
    indexes = {item["name"] for item in inspector.get_indexes("report_knowledge_links")}
    if "ix_report_knowledge_links_point" in indexes:
        op.drop_index("ix_report_knowledge_links_point", table_name="report_knowledge_links")
    if "ix_report_knowledge_links_report_id" in indexes:
        op.drop_index("ix_report_knowledge_links_report_id", table_name="report_knowledge_links")
    op.drop_table("report_knowledge_links")
