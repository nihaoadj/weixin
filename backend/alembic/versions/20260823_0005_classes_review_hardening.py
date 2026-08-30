"""Harden class compatibility, ownership constraints and analytics indexes."""

import json
import logging

import sqlalchemy as sa

from alembic import op

revision = "20260823_0005"
down_revision = "20260823_0004"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")


def _indexes(bind: sa.Connection, table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(bind).get_indexes(table)}


def _backfill_legacy_members(bind: sa.Connection) -> int:
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if not {"users", "classes", "class_members"}.issubset(tables):
        return 0

    users = sa.table("users", sa.column("id", sa.Integer), sa.column("class_ids", sa.JSON))
    classes = sa.table(
        "classes",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("status", sa.String),
    )
    members = sa.table(
        "class_members",
        sa.column("id", sa.Integer),
        sa.column("class_id", sa.Integer),
        sa.column("student_id", sa.Integer),
    )
    class_ids = {
        str(row.code): row.id
        for row in bind.execute(sa.select(classes.c.id, classes.c.code).where(classes.c.status == "active"))
    }
    inserted = 0
    for row in bind.execute(sa.select(users.c.id, users.c.class_ids)):
        raw_codes = row.class_ids
        if isinstance(raw_codes, str):
            try:
                raw_codes = json.loads(raw_codes)
            except json.JSONDecodeError:
                raw_codes = []
        if not isinstance(raw_codes, list):
            raw_codes = []
        for code in {str(item).strip() for item in raw_codes if str(item).strip()}:
            class_id = class_ids.get(code)
            if class_id is None:
                continue
            exists = bind.execute(
                sa.select(members.c.id).where(members.c.class_id == class_id, members.c.student_id == row.id)
            ).first()
            if exists is None:
                bind.execute(members.insert().values(class_id=class_id, student_id=row.id))
                inserted += 1
    return inserted


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "problems" in tables:
        foreign_keys = inspector.get_foreign_keys("problems")
        if not any(item.get("constrained_columns") == ["author_id"] for item in foreign_keys):
            with op.batch_alter_table("problems") as batch:
                batch.create_foreign_key("fk_problems_author_id", "users", ["author_id"], ["id"])

    if "classes" in tables and "ix_classes_teacher_status" not in _indexes(bind, "classes"):
        op.create_index("ix_classes_teacher_status", "classes", ["teacher_id", "status"])
    if "problems" in tables and "ix_problems_content_status" not in _indexes(bind, "problems"):
        op.create_index("ix_problems_content_status", "problems", ["content_type", "status"])
    if (
        "medical_reviews" in tables
        and "ix_medical_reviews_problem_decision_created" not in _indexes(bind, "medical_reviews")
    ):
        op.create_index(
            "ix_medical_reviews_problem_decision_created",
            "medical_reviews",
            ["problem_id", "decision", "created_at"],
        )

    inserted = _backfill_legacy_members(bind)
    logger.info("legacy class_ids compatibility backfill inserted %s class memberships", inserted)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "medical_reviews" in inspector.get_table_names() and "ix_medical_reviews_problem_decision_created" in _indexes(
        bind, "medical_reviews"
    ):
        op.drop_index("ix_medical_reviews_problem_decision_created", table_name="medical_reviews")
    if "problems" in inspector.get_table_names() and "ix_problems_content_status" in _indexes(bind, "problems"):
        op.drop_index("ix_problems_content_status", table_name="problems")
    if "classes" in inspector.get_table_names() and "ix_classes_teacher_status" in _indexes(bind, "classes"):
        op.drop_index("ix_classes_teacher_status", table_name="classes")
    if "problems" in inspector.get_table_names():
        if any(item.get("name") == "fk_problems_author_id" for item in inspector.get_foreign_keys("problems")):
            with op.batch_alter_table("problems") as batch:
                batch.drop_constraint("fk_problems_author_id", type_="foreignkey")
