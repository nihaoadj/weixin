"""Add PBL AI source and targeted delivery facts to knowledge cards."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260919_0030"
down_revision = "20260917_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("knowledge_card_contributions")}
    definitions = (
        sa.Column("ai_title", sa.String(length=200), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=True),
        sa.Column("source_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("source_position", sa.Integer(), nullable=True),
        sa.Column("source_finding_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("origin_student_id", sa.Integer(), nullable=True),
        sa.Column("origin_student_name", sa.String(length=120), nullable=True),
        sa.Column("target_student_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    for column in definitions:
        if column.name not in columns:
            op.add_column("knowledge_card_contributions", column)

    inspector = sa.inspect(bind)
    foreign_names = {item["name"] for item in inspector.get_foreign_keys("knowledge_card_contributions")}
    unique_names = {item["name"] for item in inspector.get_unique_constraints("knowledge_card_contributions")}
    if "fk_knowledge_card_origin_student" not in foreign_names or "uq_knowledge_card_pbl_source" not in unique_names:
        with op.batch_alter_table("knowledge_card_contributions") as batch:
            if "fk_knowledge_card_origin_student" not in foreign_names:
                batch.create_foreign_key("fk_knowledge_card_origin_student", "users", ["origin_student_id"], ["id"])
            if "uq_knowledge_card_pbl_source" not in unique_names:
                batch.create_unique_constraint(
                    "uq_knowledge_card_pbl_source", ["source_type", "source_snapshot_id", "source_position"]
                )
    index_names = {item["name"] for item in sa.inspect(bind).get_indexes("knowledge_card_contributions")}
    if "ix_knowledge_card_contributions_origin_student_id" not in index_names:
        op.create_index(
            "ix_knowledge_card_contributions_origin_student_id",
            "knowledge_card_contributions",
            ["origin_student_id"],
        )
    if "ix_knowledge_card_source_status" not in index_names:
        op.create_index(
            "ix_knowledge_card_source_status",
            "knowledge_card_contributions",
            ["source_type", "status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT COUNT(*) FROM knowledge_card_contributions WHERE source_type IS NOT NULL")):
        raise RuntimeError("T40 AI knowledge card data exists; use a forward fix or verified backup")
    inspector = sa.inspect(bind)
    index_names = {item["name"] for item in inspector.get_indexes("knowledge_card_contributions")}
    if "ix_knowledge_card_source_status" in index_names:
        op.drop_index("ix_knowledge_card_source_status", table_name="knowledge_card_contributions")
    if "ix_knowledge_card_contributions_origin_student_id" in index_names:
        op.drop_index("ix_knowledge_card_contributions_origin_student_id", table_name="knowledge_card_contributions")
    foreign_names = {item["name"] for item in sa.inspect(bind).get_foreign_keys("knowledge_card_contributions")}
    unique_names = {item["name"] for item in sa.inspect(bind).get_unique_constraints("knowledge_card_contributions")}
    with op.batch_alter_table("knowledge_card_contributions") as batch:
        if "uq_knowledge_card_pbl_source" in unique_names:
            batch.drop_constraint("uq_knowledge_card_pbl_source", type_="unique")
        if "fk_knowledge_card_origin_student" in foreign_names:
            batch.drop_constraint("fk_knowledge_card_origin_student", type_="foreignkey")
        columns = {column["name"] for column in sa.inspect(bind).get_columns("knowledge_card_contributions")}
        for name in (
            "target_student_ids",
            "origin_student_name",
            "origin_student_id",
            "source_finding_ids",
            "source_position",
            "source_snapshot_id",
            "source_type",
            "ai_title",
        ):
            if name in columns:
                batch.drop_column(name)
