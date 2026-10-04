"""Persist at least two learning objectives for every knowledge material."""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260917_0029"
down_revision = "20260916_0028"
branch_labels = None
depends_on = None


def _second_objective(title: str) -> str:
    return f"结合典型形态或病理情境，区分{title}与相邻概念并说明判断依据。"


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"]: column for column in sa.inspect(bind).get_columns("knowledge_study_materials")}
    existing_column = columns.get("learning_objectives")
    if existing_column is None:
        op.add_column("knowledge_study_materials", sa.Column("learning_objectives", sa.JSON(), nullable=True))
    materials = sa.table(
        "knowledge_study_materials",
        sa.column("id", sa.Integer()),
        sa.column("point_id", sa.Integer()),
        sa.column("learning_objectives", sa.JSON()),
    )
    points = sa.table(
        "knowledge_points",
        sa.column("id", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("objective", sa.Text()),
    )
    rows = bind.execute(
        sa.select(materials.c.id, points.c.title, points.c.objective).select_from(
            materials.join(points, points.c.id == materials.c.point_id)
        )
    ).mappings()
    for row in rows:
        objectives = [str(row["objective"]).strip(), _second_objective(str(row["title"]).strip())]
        if any(not item for item in objectives) or len(set(objectives)) != 2:
            raise RuntimeError("T39 cannot backfill two distinct learning objectives")
        bind.execute(
            materials.update().where(materials.c.id == row["id"]).values(learning_objectives=objectives)
        )
    missing = bind.scalar(
        sa.select(sa.func.count()).select_from(materials).where(materials.c.learning_objectives.is_(None))
    )
    if missing:
        raise RuntimeError("T39 learning objective backfill is incomplete")
    if existing_column is None or existing_column.get("nullable", True):
        with op.batch_alter_table("knowledge_study_materials") as batch:
            batch.alter_column("learning_objectives", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    materials = sa.table(
        "knowledge_study_materials",
        sa.column("point_id", sa.Integer()),
        sa.column("learning_objectives", sa.JSON()),
    )
    points = sa.table(
        "knowledge_points",
        sa.column("id", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("objective", sa.Text()),
    )
    rows = bind.execute(
        sa.select(points.c.title, points.c.objective, materials.c.learning_objectives).select_from(
            materials.join(points, points.c.id == materials.c.point_id)
        )
    ).mappings()
    for row in rows:
        expected = [str(row["objective"]).strip(), _second_objective(str(row["title"]).strip())]
        if _as_list(row["learning_objectives"]) != expected:
            raise RuntimeError("T39 refuses downgrade because learning objectives contain edited data")
    with op.batch_alter_table("knowledge_study_materials") as batch:
        batch.drop_column("learning_objectives")
