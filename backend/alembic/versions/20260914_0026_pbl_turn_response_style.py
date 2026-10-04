"""Preserve the response style of every PBL turn."""

import sqlalchemy as sa

from alembic import op

revision = "20260914_0026"
down_revision = "20260913_0025"
branch_labels = None
depends_on = None

TABLES = {
    "pbl_messages": "ck_pbl_message_interaction_style",
    "pbl_diagnostic_snapshots": "ck_pbl_snapshot_interaction_style",
}


def upgrade():
    bind = op.get_bind()
    for table, constraint in TABLES.items():
        columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        if "interaction_style" in columns:
            # Initial migration creates current metadata for fresh databases.
            continue
        op.add_column(table, sa.Column("interaction_style", sa.String(20), nullable=True))
        bind.execute(
            sa.text(
                f"UPDATE {table} SET interaction_style = "
                f"(SELECT interaction_style FROM pbl_participations WHERE id = {table}.participation_id)"
            )
        )
        if bind.scalar(
            sa.text(
                f"SELECT COUNT(*) FROM {table} WHERE interaction_style IS NULL "
                "OR interaction_style NOT IN ('guided', 'direct')"
            )
        ):
            raise RuntimeError("T31 cannot establish historical response styles")
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "interaction_style", existing_type=sa.String(20), nullable=False, server_default="guided"
            )
            batch.create_check_constraint(constraint, "interaction_style IN ('guided', 'direct')")


def downgrade():
    bind = op.get_bind()
    present = [
        table
        for table in TABLES
        if "interaction_style" in {column["name"] for column in sa.inspect(bind).get_columns(table)}
    ]
    # Check all tables before dropping either column. Any difference from the
    # participation value is history the old single-value model cannot express.
    for table in present:
        if bind.scalar(
            sa.text(
                f"SELECT COUNT(*) FROM {table} AS turn LEFT JOIN pbl_participations AS part "
                "ON part.id = turn.participation_id WHERE part.id IS NULL "
                "OR turn.interaction_style IS NULL OR turn.interaction_style <> part.interaction_style"
            )
        ):
            raise RuntimeError("T31 mixed or inconsistent response styles exist; use a forward fix or verified backup")
    for table in present:
        checks = {check["name"] for check in sa.inspect(bind).get_check_constraints(table)}
        with op.batch_alter_table(table) as batch:
            if TABLES[table] in checks:
                batch.drop_constraint(TABLES[table], type_="check")
            batch.drop_column("interaction_style")
