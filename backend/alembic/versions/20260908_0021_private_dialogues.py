"""Private student dialogue and explicit, immutable teacher submission."""

import sqlalchemy as sa

from alembic import op

revision = "20260908_0021"
down_revision = "20260907_0020"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    checks = {c["name"] for c in sa.inspect(bind).get_check_constraints("pbl_sessions")}
    with op.batch_alter_table("pbl_sessions") as batch:
        batch.alter_column("class_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("teacher_id", existing_type=sa.Integer(), nullable=True)
        if "ck_pbl_classroom_scope" not in checks:
            batch.create_check_constraint(
                "ck_pbl_classroom_scope",
                "session_kind != 'classroom' OR (class_id IS NOT NULL AND teacher_id IS NOT NULL)",
            )
    if "pbl_submissions" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "pbl_submissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("pbl_sessions.id"), nullable=False, unique=True),
            sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("pbl_diagnostic_snapshots.id"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
            sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("client_submission_id", sa.String(100), nullable=False),
            sa.Column("source", sa.String(30), nullable=False),
            sa.Column("preview_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_pbl_submissions_student_id", "pbl_submissions", ["student_id"])
        op.create_index("ix_pbl_submissions_teacher_id", "pbl_submissions", ["teacher_id"])
    # Only an existing published relationship justifies retaining historical sharing.
    bind.execute(sa.text("""
        INSERT INTO pbl_submissions
        (session_id, snapshot_id, student_id, class_id, teacher_id, client_submission_id, source, submitted_at)
        SELECT s.id, max(d.id), p.student_id, s.class_id, s.teacher_id,
               'legacy-' || s.id, 'legacy_shared', NULL
        FROM pbl_sessions s JOIN pbl_participations p ON p.session_id = s.id
        JOIN pbl_diagnostic_snapshots d ON d.participation_id = p.id
        JOIN pbl_question_suggestions q ON q.snapshot_id = d.id
        WHERE s.session_kind = 'student_initiated' AND q.problem_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM pbl_submissions x WHERE x.session_id = s.id)
        GROUP BY s.id, p.student_id, s.class_id, s.teacher_id
    """))


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM pbl_sessions WHERE session_kind = 'student_initiated'")):
        raise RuntimeError("Private dialogue data exists; restore a verified pre-T20 backup, never old authorization")
    if bind.scalar(sa.text("SELECT count(*) FROM pbl_submissions")):
        raise RuntimeError("T20 submissions exist; restore a verified backup")
    op.drop_table("pbl_submissions")
    with op.batch_alter_table("pbl_sessions") as batch:
        batch.drop_constraint("ck_pbl_classroom_scope", type_="check")
        batch.alter_column("class_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("teacher_id", existing_type=sa.Integer(), nullable=False)
