"""PBL context, response identity and independent intervention plans. No business cleanup."""

import sqlalchemy as sa

from alembic import op

revision = "20260903_0017"
down_revision = "20260903_0016"
branch_labels = None
depends_on = None


def _columns():
    return {
        "knowledge_card_contributions": [sa.Column("catalog_card_code", sa.String(160), nullable=True)],
        "pbl_sessions": [
            sa.Column("case_id", sa.Integer(), nullable=True),
            sa.Column("case_version", sa.Integer(), nullable=True),
            sa.Column("case_digest", sa.String(64), nullable=True),
            sa.Column("case_context", sa.JSON(), nullable=True),
            sa.Column("goal_point_codes", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("phase", sa.String(40), nullable=False, server_default="problem_framing"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        ],
        "pbl_messages": [
            sa.Column("request_revision", sa.Integer(), nullable=True),
            sa.Column("processing_status", sa.String(20), nullable=False, server_default="legacy"),
            sa.Column("result_snapshot_id", sa.Integer(), nullable=True),
        ],
        "pbl_diagnostic_snapshots": [
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("safety_notice", sa.Text(), nullable=False, server_default=""),
            sa.Column("safety_status", sa.String(30), nullable=False, server_default="educational"),
        ],
        "learning_plans": [
            sa.Column("source_type", sa.String(30), nullable=False, server_default="case_assessment"),
            sa.Column("source_id", sa.Integer(), nullable=True),
            sa.Column("source_context", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("verification_status", sa.String(30), nullable=False, server_default="not_ready"),
            sa.Column("verification_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("verified_by", sa.Integer(), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        ],
        "learning_task_attempts": [sa.Column("client_submission_id", sa.String(100), nullable=True)],
    }


def upgrade():
    for table, columns in _columns().items():
        inspector = sa.inspect(op.get_bind())
        existing = {column["name"] for column in inspector.get_columns(table)}
        missing = [column for column in columns if column.name not in existing]
        if not missing:
            continue
        with op.batch_alter_table(table) as batch:
            for column in missing:
                batch.add_column(column)
            if table == "knowledge_card_contributions":
                batch.create_unique_constraint("uq_catalog_card_code", ["catalog_card_code"])
            if table == "pbl_sessions":
                batch.create_foreign_key("fk_pbl_session_case", "problems", ["case_id"], ["id"])
            if table == "learning_plans":
                batch.alter_column("source_assessment_id", existing_type=sa.Integer(), nullable=True)
                batch.drop_constraint("uq_learning_plan_source", type_="unique")
                batch.create_unique_constraint("uq_learning_plan_source_v2", ["student_id", "source_type", "source_id"])
                batch.create_foreign_key("fk_learning_verifier", "users", ["verified_by"], ["id"])
    op.execute("UPDATE learning_plans SET source_id = source_assessment_id WHERE source_type = 'case_assessment'")


def downgrade():
    # Do not silently destroy intervention records to satisfy the old non-null schema.
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM learning_plans WHERE source_assessment_id IS NULL")):
        raise RuntimeError("Restore the pre-T11 backup before downgrading PBL intervention data")
    for table, columns in reversed(list(_columns().items())):
        with op.batch_alter_table(table) as batch:
            if table == "learning_plans":
                batch.drop_constraint("fk_learning_verifier", type_="foreignkey")
                batch.drop_constraint("uq_learning_plan_source_v2", type_="unique")
                batch.create_unique_constraint("uq_learning_plan_source", ["student_id", "source_assessment_id"])
                batch.alter_column("source_assessment_id", existing_type=sa.Integer(), nullable=False)
            if table == "pbl_sessions":
                batch.drop_constraint("fk_pbl_session_case", type_="foreignkey")
            for column in reversed(columns):
                batch.drop_column(column.name)
