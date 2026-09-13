"""T21 immutable teacher PBL feedback."""

import sqlalchemy as sa

from alembic import op

revision = "20260909_0023"
down_revision = "20260908_0022"
branch_labels = None
depends_on = None


def upgrade():
    if "pbl_teacher_feedbacks" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "pbl_teacher_feedbacks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("pbl_diagnostic_snapshots.id"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("learning_plans.id"), nullable=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("suggestion_id", sa.Integer(), sa.ForeignKey("pbl_question_suggestions.id"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("client_feedback_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("teacher_id", "client_feedback_id", name="uq_pbl_teacher_feedback_client"),
        sa.CheckConstraint(
            "action_type IN ('feedback_only', 'task_published', 'closed', 'follow_up')",
            name="ck_pbl_teacher_feedback_action",
        ),
    )
    op.create_index("ix_pbl_teacher_feedback_snapshot_created", "pbl_teacher_feedbacks", ["snapshot_id", "created_at"])
    op.create_index("ix_pbl_teacher_feedback_student_created", "pbl_teacher_feedbacks", ["student_id", "created_at"])
    op.create_index(
        "ix_pbl_teacher_feedback_class_action_created",
        "pbl_teacher_feedbacks",
        ["class_id", "action_type", "created_at"],
    )


def downgrade():
    bind = op.get_bind()
    if "pbl_teacher_feedbacks" not in sa.inspect(bind).get_table_names():
        return
    if bind.scalar(sa.text("SELECT count(*) FROM pbl_teacher_feedbacks")):
        raise RuntimeError(
            "T21 teacher feedback exists; restore a verified backup instead of removing feedback history"
        )
    op.drop_table("pbl_teacher_feedbacks")
