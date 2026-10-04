"""Preserve independent case attempts when teacher resources are edited or deleted."""

import sqlalchemy as sa

from alembic import op

revision = "20261003_0037"
down_revision = "20260928_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("case_attempts")}
    if "problem_snapshot" not in columns:
        op.add_column("case_attempts", sa.Column("problem_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    attempts = sa.table("case_attempts", sa.column("problem_snapshot", sa.JSON()))
    with bind.execute(sa.select(attempts.c.problem_snapshot)) as snapshots:
        # JSON deserialization treats both SQL NULL and the JSON literal null as None.
        # Preserve every populated snapshot; dropping it would silently rewrite history.
        if any(snapshot is not None for snapshot in snapshots.scalars()):
            raise RuntimeError("Cannot downgrade 0037: preserve historical case attempt snapshots")
    with op.batch_alter_table("case_attempts") as batch:
        batch.drop_column("problem_snapshot")
