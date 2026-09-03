"""Add student-confirmed learning topics to conversations."""

import sqlalchemy as sa

from alembic import op

revision = "20260831_0010"
down_revision = "20260830_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "conversation_learning_contexts" in inspector.get_table_names():
        return
    op.create_table(
        "conversation_learning_contexts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("topic_code", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="student_selected"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("conversation_id", "topic_code", name="uq_conversation_learning_topic"),
    )
    op.create_index(
        "ix_conversation_learning_contexts_conversation_id", "conversation_learning_contexts", ["conversation_id"]
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "conversation_learning_contexts" in inspector.get_table_names():
        op.drop_index("ix_conversation_learning_contexts_conversation_id", table_name="conversation_learning_contexts")
        op.drop_table("conversation_learning_contexts")
