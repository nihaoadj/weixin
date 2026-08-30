"""Add personalized practice plans, tasks, notifications and AI audit links."""

import sqlalchemy as sa

from alembic import op

revision = "20260823_0006"
down_revision = "20260823_0005"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return
    existing_columns = {item["name"] for item in inspector.get_columns(table)}
    if column.name not in existing_columns:
        with op.batch_alter_table(table) as batch:
            batch.add_column(column)


def upgrade() -> None:
    _add_column_if_missing(
        "problems", sa.Column("capability_tags", sa.JSON(), nullable=False, server_default="[]")
    )
    _add_column_if_missing(
        "case_attempts", sa.Column("learning_task_id", sa.Integer(), nullable=True)
    )
    if "case_attempts" in sa.inspect(op.get_bind()).get_table_names():
        indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("case_attempts")}
        if "uq_case_attempt_learning_task" not in indexes:
            op.create_index("uq_case_attempt_learning_task", "case_attempts", ["learning_task_id"], unique=True)
    _add_column_if_missing(
        "ai_call_logs", sa.Column("learning_task_id", sa.Integer(), nullable=True)
    )
    _add_column_if_missing(
        "ai_call_logs", sa.Column("blueprint_id", sa.String(100), nullable=True)
    )
    _add_column_if_missing(
        "ai_call_logs", sa.Column("blueprint_digest", sa.String(64), nullable=True)
    )

    metadata = sa.MetaData()
    # Declare existing targets in this metadata so SQLite can compile foreign keys
    # while creating the new tables; these tables are never created by this revision.
    for name in ("users", "case_assessments", "case_attempts", "problems"):
        sa.Table(name, metadata, sa.Column("id", sa.Integer, primary_key=True))
    plans = sa.Table(
        "learning_plans",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "source_assessment_id", sa.Integer, sa.ForeignKey("case_assessments.id"), nullable=False, unique=True
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("target_dimension_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generation_mode", sa.String(30), nullable=False, server_default="deterministic"),
        sa.Column("model_name", sa.String(120), nullable=False, server_default="deterministic-fallback"),
        sa.Column("prompt_version", sa.String(80), nullable=False, server_default="practice-v1"),
        sa.Column("fallback_used", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("student_id", "source_assessment_id", name="uq_learning_plan_source"),
    )
    tasks = sa.Table(
        "learning_tasks",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("task_type", sa.String(30), nullable=False),
        sa.Column("dimension_id", sa.String(50), nullable=False),
        sa.Column("stage_id", sa.String(40), nullable=True),
        sa.Column("problem_id", sa.Integer, sa.ForeignKey("problems.id"), nullable=True),
        sa.Column("source_attempt_id", sa.Integer, sa.ForeignKey("case_attempts.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("public_definition", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("private_rubric", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("blueprint_id", sa.String(100), nullable=True),
        sa.Column("blueprint_digest", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("plan_id", "position", name="uq_learning_task_position"),
    )
    attempts = sa.Table(
        "learning_task_attempts",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "task_id", sa.Integer, sa.ForeignKey("learning_tasks.id", ondelete="CASCADE"), nullable=False, unique=True
        ),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("answer", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("evidence", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("feedback", sa.Text, nullable=False, server_default=""),
        sa.Column("next_step", sa.Text, nullable=False, server_default=""),
        sa.Column("model_name", sa.String(120), nullable=False, server_default="deterministic-fallback"),
        sa.Column("prompt_version", sa.String(80), nullable=False, server_default="practice-v1"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fallback_used", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    notifications = sa.Table(
        "student_notifications",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False, server_default="learning_plan"),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("dedupe_key", sa.String(160), nullable=False, unique=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for table in (plans, tasks, attempts, notifications):
        table.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "case_attempts" in inspector.get_table_names() and "uq_case_attempt_learning_task" in {
        item["name"] for item in inspector.get_indexes("case_attempts")
    }:
        op.drop_index("uq_case_attempt_learning_task", table_name="case_attempts")
    # The 0002 dynamic metadata creation may have created an implicit index for
    # this column before 0006 started managing it explicitly. Remove every
    # index that references a column about to be dropped so SQLite batch mode
    # does not recreate an index against a missing column.
    for table, columns in (
        ("ai_call_logs", ("blueprint_digest", "blueprint_id", "learning_task_id")),
        ("case_attempts", ("learning_task_id",)),
        ("problems", ("capability_tags",)),
    ):
        if sa.inspect(bind).has_table(table):
            # 0002 built some tables from the current ORM metadata and may
            # therefore have implicit indexes for these columns. Batch mode
            # reflects them and would otherwise recreate an index after its
            # column has been removed.
            for index in list(sa.inspect(bind).get_indexes(table)):
                if set(index.get("column_names") or []).intersection(columns):
                    op.drop_index(index["name"], table_name=table)
            existing = {item["name"] for item in sa.inspect(bind).get_columns(table)}
            with op.batch_alter_table(table) as batch:
                for column in columns:
                    if column in existing:
                        batch.drop_column(column)
    for table in ("student_notifications", "learning_task_attempts", "learning_tasks", "learning_plans"):
        if sa.inspect(bind).has_table(table):
            op.drop_table(table)
