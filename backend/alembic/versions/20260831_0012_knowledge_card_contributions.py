"""Add teacher knowledge-card contributions beneath the fixed T08 catalog."""

import sqlalchemy as sa

from alembic import op

revision = "20260831_0012"
down_revision = "20260831_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "knowledge_card_contributions" in set(inspector.get_table_names()):
        return
    op.create_table(
        "knowledge_card_contributions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("point_code", sa.String(length=120), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_code", sa.String(length=80), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("card_type", sa.String(length=20), nullable=False, server_default="single_choice"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("correct_option", sa.Integer(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_knowledge_card_contributions_point_code", "knowledge_card_contributions", ["point_code"])
    op.create_index("ix_knowledge_card_contributions_owner_id", "knowledge_card_contributions", ["owner_id"])
    op.create_index("ix_knowledge_card_contributions_class_code", "knowledge_card_contributions", ["class_code"])
    op.create_index("ix_knowledge_card_contributions_status", "knowledge_card_contributions", ["status"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "knowledge_card_contributions" not in set(inspector.get_table_names()):
        return
    indexes = {item["name"] for item in inspector.get_indexes("knowledge_card_contributions")}
    for name in (
        "ix_knowledge_card_contributions_status",
        "ix_knowledge_card_contributions_class_code",
        "ix_knowledge_card_contributions_owner_id",
        "ix_knowledge_card_contributions_point_code",
    ):
        if name in indexes:
            op.drop_index(name, table_name="knowledge_card_contributions")
    op.drop_table("knowledge_card_contributions")
