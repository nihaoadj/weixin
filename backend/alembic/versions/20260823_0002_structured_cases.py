"""Add versioned guided cases and structured training records.

The initial migration creates metadata dynamically, so this migration deliberately
checks each object before changing a developer database or an empty database.
"""

import sqlalchemy as sa

from alembic import op
from app import models  # noqa: F401
from app.db import Base

revision = "20260823_0002"
down_revision = "20260820_0001"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "problems" not in inspector.get_table_names():
        Base.metadata.tables["problems"].create(bind, checkfirst=True)
    columns = _columns(bind, "problems")
    additions = [
        sa.Column("slug", sa.String(120), nullable=True),
        sa.Column("content_type", sa.String(30), nullable=False, server_default="question"),
        sa.Column("specialty", sa.String(80), nullable=False, server_default=""),
        sa.Column("difficulty", sa.String(30), nullable=False, server_default="basic"),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_problem_id", sa.Integer(), nullable=True),
        sa.Column("case_definition", sa.JSON(), nullable=True),
        sa.Column("rubric", sa.JSON(), nullable=True),
    ]
    with op.batch_alter_table("problems") as batch:
        for column in additions:
            if column.name not in columns:
                batch.add_column(column)
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("problems")}
    with op.batch_alter_table("problems") as batch:
        if "ix_problems_slug" not in indexes:
            batch.create_index("ix_problems_slug", ["slug"])
        if "ix_problems_content_type" not in indexes:
            batch.create_index("ix_problems_content_type", ["content_type"])
    for table_name in (
        "case_attempts",
        "case_attempt_messages",
        "stage_submissions",
        "case_assessments",
        "ai_call_logs",
    ):
        Base.metadata.tables[table_name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in (
        "ai_call_logs",
        "case_assessments",
        "stage_submissions",
        "case_attempt_messages",
        "case_attempts",
    ):
        if table_name in inspector.get_table_names():
            Base.metadata.tables[table_name].drop(bind, checkfirst=True)
    if "problems" in sa.inspect(bind).get_table_names():
        columns = _columns(bind, "problems")
        removable = [
            "rubric",
            "case_definition",
            "parent_problem_id",
            "version",
            "estimated_minutes",
            "difficulty",
            "specialty",
            "content_type",
            "slug",
        ]
        with op.batch_alter_table("problems") as batch:
            for name in removable:
                if name in columns:
                    batch.drop_column(name)
