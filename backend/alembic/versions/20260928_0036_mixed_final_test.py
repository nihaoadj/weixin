"""Add versioned mixed final tests, pending grading, and result tutoring."""

import sqlalchemy as sa

from alembic import op

revision = "20260928_0036"
down_revision = "20260927_0035"
branch_labels = None
depends_on = None


def _attempt_constraints(mixed: bool) -> None:
    with op.batch_alter_table("route_test_attempts") as batch:
        batch.drop_constraint("ck_route_test_attempt_status", type_="check")
        batch.drop_constraint("ck_route_test_attempt_submission_fields", type_="check")
        batch.create_check_constraint(
            "ck_route_test_attempt_status",
            "status IN ('in_progress', 'grading', 'submitted')" if mixed else "status IN ('in_progress', 'submitted')",
        )
        submitted = (
            "status = 'submitted' AND submission_id IS NOT NULL AND submission_digest IS NOT NULL "
            "AND correct_count IS NOT NULL AND question_count IS NOT NULL AND score IS NOT NULL "
            "AND submitted_at IS NOT NULL"
        )
        grading = (
            " OR (status = 'grading' AND submission_id IS NOT NULL AND submission_digest IS NOT NULL "
            "AND correct_count IS NOT NULL AND question_count IS NOT NULL AND score IS NULL "
            "AND submitted_at IS NOT NULL)"
            if mixed
            else ""
        )
        batch.create_check_constraint(
            "ck_route_test_attempt_submission_fields", f"({submitted}){grading} OR status = 'in_progress'"
        )


def upgrade() -> None:
    with op.batch_alter_table("route_final_tests") as batch:
        batch.add_column(
            sa.Column("format_version", sa.String(24), nullable=False, server_default="single_choice_v1")
        )
        batch.create_check_constraint(
            "ck_route_final_test_format_version", "format_version IN ('single_choice_v1', 'mixed_v2')"
        )
    with op.batch_alter_table("route_test_questions") as batch:
        batch.add_column(sa.Column("question_type", sa.String(20), nullable=False, server_default="single_choice"))
        batch.alter_column("correct_option", existing_type=sa.Integer(), nullable=True)
        batch.drop_constraint("ck_route_test_question_correct_option", type_="check")
        batch.create_check_constraint(
            "ck_route_test_question_correct_option",
            "(question_type = 'single_choice' AND correct_option BETWEEN 0 AND 3) OR "
            "(question_type IN ('multiple_choice', 'short_answer') AND correct_option IS NULL)",
        )
    with op.batch_alter_table("route_test_attempts") as batch:
        batch.add_column(sa.Column("grading_claim_token", sa.String(100), nullable=True))
        batch.add_column(sa.Column("grading_claim_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("grading_error_code", sa.String(80), nullable=True))
    _attempt_constraints(True)

    op.create_table(
        "route_test_tutor_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column(
            "result_id", sa.Integer(), sa.ForeignKey("route_learning_results.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claim_token", sa.String(100), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("public_id", name="uq_route_test_tutor_session_public_id"),
        sa.UniqueConstraint("result_id", name="uq_route_test_tutor_session_result"),
        sa.CheckConstraint("revision >= 0", name="ck_route_test_tutor_session_revision"),
    )
    op.create_table(
        "route_test_tutor_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("route_test_tutor_sessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "question_id", sa.Integer(), sa.ForeignKey("route_test_questions.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("turn_id", sa.String(100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(12), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("public_id", name="uq_route_test_tutor_message_public_id"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_route_test_tutor_message_sequence"),
        sa.UniqueConstraint("session_id", "turn_id", "role", name="uq_route_test_tutor_message_turn_role"),
        sa.CheckConstraint("role IN ('student', 'assistant')", name="ck_route_test_tutor_message_role"),
        sa.CheckConstraint("sequence >= 1", name="ck_route_test_tutor_message_sequence"),
    )


def downgrade() -> None:
    db = op.get_bind()
    if any(
        db.scalar(sa.text(query))
        for query in (
            "SELECT COUNT(*) FROM route_final_tests WHERE format_version != 'single_choice_v1'",
            "SELECT COUNT(*) FROM route_test_attempts WHERE status = 'grading'",
            "SELECT COUNT(*) FROM route_test_tutor_sessions",
            "SELECT COUNT(*) FROM route_test_tutor_messages",
        )
    ):
        raise RuntimeError("Cannot downgrade: preserve mixed tests, grading attempts, and tutor dialogue")
    op.drop_table("route_test_tutor_messages")
    op.drop_table("route_test_tutor_sessions")
    _attempt_constraints(False)
    with op.batch_alter_table("route_test_attempts") as batch:
        batch.drop_column("grading_error_code")
        batch.drop_column("grading_claim_expires_at")
        batch.drop_column("grading_claim_token")
    with op.batch_alter_table("route_test_questions") as batch:
        batch.drop_constraint("ck_route_test_question_correct_option", type_="check")
        batch.alter_column("correct_option", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("question_type")
        batch.create_check_constraint("ck_route_test_question_correct_option", "correct_option BETWEEN 0 AND 3")
    with op.batch_alter_table("route_final_tests") as batch:
        batch.drop_constraint("ck_route_final_test_format_version", type_="check")
        batch.drop_column("format_version")
