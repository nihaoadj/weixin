"""Harden structured-case constraints for databases created before 0002."""

import sqlalchemy as sa

from alembic import op

revision = "20260823_0003"
down_revision = "20260823_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "problems" in tables:
        indexes = {item["name"] for item in inspector.get_indexes("problems")}
        with op.batch_alter_table("problems") as batch:
            if "ix_problems_guided_case_slug_version" not in indexes:
                batch.create_index(
                    "ix_problems_guided_case_slug_version",
                    ["slug", "version"],
                    unique=True,
                )
            foreign_keys = inspector.get_foreign_keys("problems")
            if not any(item.get("constrained_columns") == ["parent_problem_id"] for item in foreign_keys):
                batch.create_foreign_key(
                    "fk_problems_parent_problem_id",
                    "problems",
                    ["parent_problem_id"],
                    ["id"],
                )
    if "case_attempts" in tables:
        indexes = {item["name"] for item in inspector.get_indexes("case_attempts")}
        if "ix_case_attempts_analytics" not in indexes:
            op.create_index(
                "ix_case_attempts_analytics",
                "case_attempts",
                ["student_id", "problem_id", "status", "assessed_at"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "case_attempts" in inspector.get_table_names():
        if "ix_case_attempts_analytics" in {item["name"] for item in inspector.get_indexes("case_attempts")}:
            op.drop_index("ix_case_attempts_analytics", table_name="case_attempts")
    if "problems" in inspector.get_table_names():
        indexes = {item["name"] for item in inspector.get_indexes("problems")}
        with op.batch_alter_table("problems") as batch:
            if "ix_problems_guided_case_slug_version" in indexes:
                batch.drop_index("ix_problems_guided_case_slug_version")
            if any(
                item.get("name") == "fk_problems_parent_problem_id" for item in inspector.get_foreign_keys("problems")
            ):
                batch.drop_constraint("fk_problems_parent_problem_id", type_="foreignkey")
