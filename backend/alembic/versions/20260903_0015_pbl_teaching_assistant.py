"""Add the pathology PBL teaching-assistant persistence.

Revision ID: 20260903_0015
Revises: 20260831_0014
"""
import sqlalchemy as sa

from alembic import op

revision="20260903_0015"
down_revision="20260831_0014"
branch_labels=None
depends_on=None

def upgrade() -> None:
    # Test bootstrap may have created current metadata before Alembic exercises
    # an older revision.  Mirror prior migrations by making this additive.
    if "pbl_sessions" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table("pbl_sessions",sa.Column("id",sa.Integer,primary_key=True),sa.Column("class_id",sa.Integer,sa.ForeignKey("classes.id"),nullable=False),sa.Column("teacher_id",sa.Integer,sa.ForeignKey("users.id"),nullable=False),sa.Column("topic_code",sa.String(120),nullable=False),sa.Column("provider",sa.String(40),nullable=False),sa.Column("invocation_mode",sa.String(40)),sa.Column("status",sa.String(20),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("CURRENT_TIMESTAMP")),sa.Column("closed_at",sa.DateTime(timezone=True)))
    op.create_index("ix_pbl_sessions_class_status","pbl_sessions",["class_id","status"])
    op.create_table("pbl_participations",sa.Column("id",sa.Integer,primary_key=True),sa.Column("session_id",sa.Integer,sa.ForeignKey("pbl_sessions.id",ondelete="CASCADE"),nullable=False),sa.Column("student_id",sa.Integer,sa.ForeignKey("users.id"),nullable=False),sa.Column("coze_user_ref",sa.String(100)),sa.Column("coze_conversation_ref",sa.String(120)),sa.Column("messages",sa.JSON,nullable=False),sa.Column("revision",sa.Integer,nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("CURRENT_TIMESTAMP")),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.text("CURRENT_TIMESTAMP")),sa.UniqueConstraint("session_id","student_id",name="uq_pbl_participation_student"))
    op.create_table("pbl_diagnostic_snapshots",sa.Column("id",sa.Integer,primary_key=True),sa.Column("participation_id",sa.Integer,sa.ForeignKey("pbl_participations.id",ondelete="CASCADE"),nullable=False),sa.Column("revision",sa.Integer,nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("assistant_reply",sa.Text,nullable=False),sa.Column("follow_up_question",sa.Text),sa.Column("knowledge_gaps",sa.JSON,nullable=False),sa.Column("reasoning_issues",sa.JSON,nullable=False),sa.Column("provider_metadata",sa.JSON,nullable=False),sa.Column("failure_reason",sa.String(100)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("CURRENT_TIMESTAMP")),sa.UniqueConstraint("participation_id","revision",name="uq_pbl_snapshot_revision"))
    op.create_table("pbl_question_suggestions",sa.Column("id",sa.Integer,primary_key=True),sa.Column("snapshot_id",sa.Integer,sa.ForeignKey("pbl_diagnostic_snapshots.id",ondelete="CASCADE"),nullable=False),sa.Column("title",sa.String(200),nullable=False),sa.Column("prompt",sa.Text,nullable=False),sa.Column("linked_findings",sa.JSON,nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("version",sa.Integer,nullable=False),sa.Column("problem_id",sa.Integer,sa.ForeignKey("problems.id"),unique=True))
    op.create_table("problem_origins",sa.Column("id",sa.Integer,primary_key=True),sa.Column("problem_id",sa.Integer,sa.ForeignKey("problems.id",ondelete="CASCADE"),nullable=False,unique=True),sa.Column("source_type",sa.String(40),nullable=False),sa.Column("source_id",sa.Integer,nullable=False),sa.UniqueConstraint("source_type","source_id",name="uq_problem_origin_source"))

def downgrade() -> None:
    if "pbl_sessions" not in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.drop_table("problem_origins")
    op.drop_table("pbl_question_suggestions")
    op.drop_table("pbl_diagnostic_snapshots")
    op.drop_table("pbl_participations")
    op.drop_index("ix_pbl_sessions_class_status", table_name="pbl_sessions")
    op.drop_table("pbl_sessions")
