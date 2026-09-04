"""Append-only PBL learning-plan evaluation history for student reports."""

import sqlalchemy as sa

from alembic import op

revision = "20260904_0019"
down_revision = "20260903_0018"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "learning_plan_evaluations" in inspector.get_table_names():
        return
    op.create_table(
        "learning_plan_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("failed_targets", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("automation_exhausted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("record_source", sa.String(20), nullable=False, server_default="runtime"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["plan_id"], ["learning_plans.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("plan_id", "cycle_number", name="uq_learning_plan_evaluation_cycle"),
    )
    op.create_index("ix_learning_plan_evaluations_plan_id", "learning_plan_evaluations", ["plan_id"])


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM learning_plan_evaluations")):
        raise RuntimeError("Restore the pre-T15 backup before removing PBL evaluation history")
    op.drop_index("ix_learning_plan_evaluations_plan_id", table_name="learning_plan_evaluations")
    op.drop_table("learning_plan_evaluations")
