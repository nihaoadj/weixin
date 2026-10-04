"""Add one classroom package per student/session and frozen reporting facts."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260923_0031"
down_revision = "20260919_0030"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    # 0001 creates current metadata on a new database. Existing databases reach
    # this revision without the T43 tables; both paths must produce one schema.
    if "classroom_task_packages" not in _tables():
        op.create_table(
            "classroom_task_packages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "session_id", sa.Integer(), sa.ForeignKey("pbl_sessions.id", ondelete="RESTRICT"), nullable=False
            ),
            sa.Column(
                "completion_snapshot_id",
                sa.Integer(),
                sa.ForeignKey("pbl_diagnostic_snapshots.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("learning_plans.id", ondelete="RESTRICT")),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("draft_digest", sa.String(64)),
            sa.Column("reviewed_version", sa.Integer()),
            sa.Column("published_version", sa.Integer()),
            sa.Column("diagnosis_outcome", sa.String(30), nullable=False),
            sa.Column("feedback_draft", sa.Text(), nullable=False, server_default=""),
            sa.Column("record_source", sa.String(20), nullable=False, server_default="runtime"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("published_at", sa.DateTime(timezone=True)),
            sa.Column("due_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("student_id", "session_id", name="uq_classroom_package_student_session"),
            sa.UniqueConstraint("completion_snapshot_id", name="uq_classroom_package_snapshot"),
            sa.UniqueConstraint("plan_id"),
            sa.CheckConstraint("status IN ('draft', 'build_failed', 'published')", name="ck_classroom_package_status"),
            sa.CheckConstraint(
                "record_source IN ('runtime', 'legacy_verified')", name="ck_classroom_package_record_source"
            ),
            sa.CheckConstraint("version >= 1", name="ck_classroom_package_version"),
            sa.CheckConstraint(
                "(status = 'published' AND plan_id IS NOT NULL AND published_at IS NOT NULL "
                "AND published_version IS NOT NULL AND due_at IS NOT NULL) OR "
                "(status != 'published' AND plan_id IS NULL AND published_at IS NULL "
                "AND published_version IS NULL AND due_at IS NULL)",
                name="ck_classroom_package_published_fields",
            ),
        )
        op.create_index("ix_classroom_package_class_session", "classroom_task_packages", ["class_id", "session_id"])
    feedback_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("pbl_teacher_feedbacks")}
    session_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("pbl_sessions")}
    if "ai_schema_version" not in session_columns:
        op.add_column("pbl_sessions", sa.Column("ai_schema_version", sa.Integer(), nullable=False, server_default="6"))
        with op.batch_alter_table("pbl_sessions") as batch:
            batch.create_check_constraint("ck_pbl_session_ai_schema_version", "ai_schema_version IN (6, 7)")
    if "package_id" not in feedback_columns:
        op.add_column("pbl_teacher_feedbacks", sa.Column("package_id", sa.Integer(), nullable=True))
    feedback_fks = {foreign["name"] for foreign in sa.inspect(op.get_bind()).get_foreign_keys("pbl_teacher_feedbacks")}
    if "fk_pbl_teacher_feedback_package" not in feedback_fks:
        with op.batch_alter_table("pbl_teacher_feedbacks") as batch:
            batch.create_foreign_key(
                "fk_pbl_teacher_feedback_package",
                "classroom_task_packages",
                ["package_id"],
                ["id"],
                ondelete="RESTRICT",
            )
    snapshot_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("pbl_diagnostic_snapshots")}
    if "diagnosis_outcome" not in snapshot_columns:
        op.add_column("pbl_diagnostic_snapshots", sa.Column("diagnosis_outcome", sa.String(30), nullable=True))
    if "candidate_tasks" not in snapshot_columns:
        op.add_column(
            "pbl_diagnostic_snapshots", sa.Column("candidate_tasks", sa.JSON(), nullable=False, server_default="[]")
        )
    if "classroom_package_items" not in _tables():
        op.create_table(
            "classroom_package_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "package_id",
                sa.Integer(),
                sa.ForeignKey("classroom_task_packages.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("stable_key", sa.String(100), nullable=False),
            sa.Column("candidate_key", sa.String(100)),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("cycle_number", sa.Integer(), nullable=False),
            sa.Column("task_type", sa.String(30), nullable=False),
            sa.Column("primary_point_code", sa.String(120), nullable=False),
            sa.Column("point_codes", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("dimension_ids", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("target_type", sa.String(40), nullable=False),
            sa.Column("target_code", sa.String(160), nullable=False),
            sa.Column("public_definition", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("private_rubric", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("source_ref", sa.JSON()),
            sa.Column("source_version", sa.Integer()),
            sa.Column("source_digest", sa.String(64)),
            sa.Column("content_resource_id", sa.Integer()),
            sa.Column("medical_status", sa.String(30)),
            sa.UniqueConstraint("package_id", "stable_key", "cycle_number", name="uq_classroom_package_item_variant"),
            sa.UniqueConstraint("package_id", "position", name="uq_classroom_package_item_position"),
            sa.CheckConstraint("cycle_number IN (1, 2)", name="ck_classroom_package_item_cycle"),
        )
        op.create_index("ix_classroom_package_items_package_id", "classroom_package_items", ["package_id"])
    if "classroom_question_reviews" not in _tables():
        op.create_table(
            "classroom_question_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "package_item_id",
                sa.Integer(),
                sa.ForeignKey("classroom_package_items.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("content_digest", sa.String(64), nullable=False),
            sa.Column("content_snapshot", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("submitted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
            sa.Column("review_comment", sa.Text(), nullable=False, server_default=""),
            sa.Column("reviewed_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("package_item_id", "content_digest", name="uq_classroom_question_review_revision"),
            sa.CheckConstraint(
                "status IN ('pending', 'approved', 'rejected')", name="ck_classroom_question_review_status"
            ),
        )
        op.create_index(
            "ix_classroom_question_reviews_package_item_id", "classroom_question_reviews", ["package_item_id"]
        )
    if "classroom_final_reports" not in _tables():
        op.create_table(
            "classroom_final_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "package_id",
                sa.Integer(),
                sa.ForeignKey("classroom_task_packages.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "session_id", sa.Integer(), sa.ForeignKey("pbl_sessions.id", ondelete="RESTRICT"), nullable=False
            ),
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("policy_version", sa.String(80), nullable=False),
            sa.Column("source_digest", sa.String(64), nullable=False),
            sa.Column("result", sa.String(30), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("record_source", sa.String(20), nullable=False, server_default="runtime"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("package_id"),
            sa.CheckConstraint("result IN ('improved', 'needs_reinforcement')", name="ck_classroom_report_result"),
            sa.CheckConstraint(
                "record_source IN ('runtime', 'legacy_verified')", name="ck_classroom_report_record_source"
            ),
        )
        op.create_index("ix_classroom_report_class_completed", "classroom_final_reports", ["class_id", "completed_at"])
        op.create_index(
            "ix_classroom_report_student_completed", "classroom_final_reports", ["student_id", "completed_at"]
        )
    if "teaching_command_receipts" not in _tables():
        op.create_table(
            "teaching_command_receipts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("operation", sa.String(50), nullable=False),
            sa.Column("client_request_id", sa.String(100), nullable=False),
            sa.Column("request_digest", sa.String(64), nullable=False),
            sa.Column("resource_id", sa.Integer(), nullable=False),
            sa.Column("result_version", sa.Integer(), nullable=False),
            sa.Column("response_payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("teacher_id", "operation", "client_request_id", name="uq_teaching_command_request"),
        )
    if "t43_legacy_plan_mappings" not in _tables():
        op.create_table(
            "t43_legacy_plan_mappings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "legacy_plan_id", sa.Integer(), sa.ForeignKey("learning_plans.id", ondelete="RESTRICT"), nullable=False
            ),
            sa.Column(
                "package_id",
                sa.Integer(),
                sa.ForeignKey("classroom_task_packages.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("converted_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("legacy_plan_id"),
            sa.UniqueConstraint("package_id"),
        )
    if "teacher_question_bank_items" not in _tables():
        op.create_table(
            "teacher_question_bank_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_teacher_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("current_revision_id", sa.Integer()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("status IN ('active', 'archived')", name="ck_teacher_question_bank_status"),
            sa.CheckConstraint("version >= 1", name="ck_teacher_question_bank_version"),
        )
        op.create_index(
            "ix_teacher_question_bank_items_owner_teacher_id", "teacher_question_bank_items", ["owner_teacher_id"]
        )
    if "teacher_question_bank_revisions" not in _tables():
        op.create_table(
            "teacher_question_bank_revisions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "bank_item_id",
                sa.Integer(),
                sa.ForeignKey("teacher_question_bank_items.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("task_type", sa.String(30), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("options", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("answer", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
            sa.Column("point_codes", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("dimension_ids", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column(
                "source_package_item_id",
                sa.Integer(),
                sa.ForeignKey("classroom_package_items.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("source_digest", sa.String(64), nullable=False),
            sa.Column("medical_status", sa.String(30)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("bank_item_id", "version", name="uq_teacher_bank_revision_version"),
        )
        op.create_index(
            "ix_teacher_question_bank_revisions_bank_item_id", "teacher_question_bank_revisions", ["bank_item_id"]
        )
    if "bank_import_receipts" not in _tables():
        op.create_table(
            "bank_import_receipts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "source_package_item_id",
                sa.Integer(),
                sa.ForeignKey("classroom_package_items.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("source_digest", sa.String(64), nullable=False),
            sa.Column("client_request_id", sa.String(100), nullable=False),
            sa.Column("payload_digest", sa.String(64), nullable=False),
            sa.Column(
                "bank_item_id",
                sa.Integer(),
                sa.ForeignKey("teacher_question_bank_items.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("teacher_id", "source_package_item_id", "source_digest", name="uq_bank_import_source"),
            sa.UniqueConstraint("teacher_id", "client_request_id", name="uq_bank_import_request"),
        )
    if "bank_archive_receipts" not in _tables():
        op.create_table(
            "bank_archive_receipts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "bank_item_id",
                sa.Integer(),
                sa.ForeignKey("teacher_question_bank_items.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("client_request_id", sa.String(100), nullable=False),
            sa.Column("expected_version", sa.Integer(), nullable=False),
            sa.Column("result_version", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("teacher_id", "client_request_id", name="uq_bank_archive_request"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables()
    if bind.scalar(sa.text("SELECT COUNT(*) FROM pbl_teacher_feedbacks WHERE package_id IS NOT NULL")):
        raise RuntimeError("T43 package feedback exists; use a forward fix or verified backup")
    snapshots = sa.Table("pbl_diagnostic_snapshots", sa.MetaData(), autoload_with=bind)
    if bind.scalar(
        sa.select(sa.func.count()).select_from(snapshots).where(snapshots.c.diagnosis_outcome.is_not(None))
    ) or any(value for value in bind.execute(sa.select(snapshots.c.candidate_tasks)).scalars()):
        raise RuntimeError("T43 v7 diagnostic data exists; use a forward fix or verified backup")
    for table in (
        "bank_archive_receipts",
        "classroom_question_reviews",
        "bank_import_receipts",
        "teacher_question_bank_revisions",
        "teacher_question_bank_items",
        "t43_legacy_plan_mappings",
        "teaching_command_receipts",
        "classroom_final_reports",
        "classroom_package_items",
        "classroom_task_packages",
    ):
        if table in tables and bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table}")):
            raise RuntimeError(f"T43 data exists in {table}; use a forward fix or verified backup")
    feedback_fks = {foreign["name"] for foreign in sa.inspect(bind).get_foreign_keys("pbl_teacher_feedbacks")}
    session_columns = {column["name"] for column in sa.inspect(bind).get_columns("pbl_sessions")}
    if "ai_schema_version" in session_columns:
        with op.batch_alter_table("pbl_sessions") as batch:
            if "ck_pbl_session_ai_schema_version" in {
                item["name"] for item in sa.inspect(bind).get_check_constraints("pbl_sessions")
            }:
                batch.drop_constraint("ck_pbl_session_ai_schema_version", type_="check")
            batch.drop_column("ai_schema_version")
    feedback_columns = {column["name"] for column in sa.inspect(bind).get_columns("pbl_teacher_feedbacks")}
    if "package_id" in feedback_columns:
        with op.batch_alter_table("pbl_teacher_feedbacks") as batch:
            if "fk_pbl_teacher_feedback_package" in feedback_fks:
                batch.drop_constraint("fk_pbl_teacher_feedback_package", type_="foreignkey")
            batch.drop_column("package_id")
    snapshot_columns = {column["name"] for column in sa.inspect(bind).get_columns("pbl_diagnostic_snapshots")}
    if "diagnosis_outcome" in snapshot_columns or "candidate_tasks" in snapshot_columns:
        with op.batch_alter_table("pbl_diagnostic_snapshots") as batch:
            if "candidate_tasks" in snapshot_columns:
                batch.drop_column("candidate_tasks")
            if "diagnosis_outcome" in snapshot_columns:
                batch.drop_column("diagnosis_outcome")
    for table in (
        "bank_archive_receipts",
        "classroom_question_reviews",
        "bank_import_receipts",
        "teacher_question_bank_revisions",
        "teacher_question_bank_items",
        "t43_legacy_plan_mappings",
        "teaching_command_receipts",
        "classroom_final_reports",
        "classroom_package_items",
        "classroom_task_packages",
    ):
        if table in tables:
            op.drop_table(table)
