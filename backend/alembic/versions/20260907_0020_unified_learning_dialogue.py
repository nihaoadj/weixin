"""Unify student-initiated dialogue with the PBL learning loop."""

import sqlalchemy as sa

from alembic import op

revision = "20260907_0020"
down_revision = "20260904_0019"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session_columns = {column["name"] for column in sa.inspect(bind).get_columns("pbl_sessions")}
    with op.batch_alter_table("pbl_sessions") as batch:
        if "session_kind" not in session_columns:
            batch.add_column(sa.Column("session_kind", sa.String(30), nullable=False, server_default="classroom"))
        if "created_by_student_id" not in session_columns:
            batch.add_column(sa.Column("created_by_student_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_pbl_session_created_student", "users", ["created_by_student_id"], ["id"]
            )
        if "client_session_id" not in session_columns:
            batch.add_column(sa.Column("client_session_id", sa.String(100), nullable=True))
        batch.create_check_constraint(
            "ck_pbl_session_kind", "session_kind IN ('classroom', 'student_initiated')"
        )
        batch.create_check_constraint(
            "ck_pbl_session_student_origin",
            "(session_kind = 'classroom' AND created_by_student_id IS NULL AND client_session_id IS NULL) OR "
            "(session_kind = 'student_initiated' AND created_by_student_id IS NOT NULL "
            "AND client_session_id IS NOT NULL)",
        )
        batch.create_unique_constraint(
            "uq_pbl_session_student_client", ["created_by_student_id", "client_session_id"]
        )
    session_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("pbl_sessions")}
    if "ix_pbl_sessions_created_by_student_id" not in session_indexes:
        op.create_index("ix_pbl_sessions_created_by_student_id", "pbl_sessions", ["created_by_student_id"])

    participation_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("pbl_participations")
    }
    with op.batch_alter_table("pbl_participations") as batch:
        if "interaction_style" not in participation_columns:
            batch.add_column(sa.Column("interaction_style", sa.String(20), nullable=False, server_default="guided"))
        if "style_selected_at" not in participation_columns:
            batch.add_column(
                sa.Column("style_selected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
            )
        batch.create_check_constraint(
            "ck_pbl_participation_interaction_style", "interaction_style IN ('guided', 'direct')"
        )


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM pbl_sessions WHERE session_kind = 'student_initiated'")):
        raise RuntimeError("Restore the pre-T17 backup before removing student-initiated dialogues")
    if bind.scalar(sa.text("SELECT count(*) FROM pbl_participations WHERE interaction_style <> 'guided'")):
        raise RuntimeError("Restore the pre-T17 backup before removing dialogue interaction styles")

    with op.batch_alter_table("pbl_participations") as batch:
        batch.drop_constraint("ck_pbl_participation_interaction_style", type_="check")
        batch.drop_column("style_selected_at")
        batch.drop_column("interaction_style")

    session_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("pbl_sessions")}
    if "ix_pbl_sessions_created_by_student_id" in session_indexes:
        op.drop_index("ix_pbl_sessions_created_by_student_id", table_name="pbl_sessions")
    with op.batch_alter_table("pbl_sessions") as batch:
        batch.drop_constraint("uq_pbl_session_student_client", type_="unique")
        batch.drop_constraint("ck_pbl_session_student_origin", type_="check")
        batch.drop_constraint("ck_pbl_session_kind", type_="check")
        batch.drop_constraint("fk_pbl_session_created_student", type_="foreignkey")
        batch.drop_column("client_session_id")
        batch.drop_column("created_by_student_id")
        batch.drop_column("session_kind")
