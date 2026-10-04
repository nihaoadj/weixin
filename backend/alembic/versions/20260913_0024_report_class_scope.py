"""T29 report class scope: teacher-visible reports are scoped to owned classes."""

import sqlalchemy as sa

from alembic import op

revision = "20260913_0024"
down_revision = "20260909_0023"
branch_labels = None
depends_on = None


def _report_columns(bind) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns("reports")}


def upgrade():
    bind = op.get_bind()
    columns = _report_columns(bind)
    if "class_id" in columns and "class_name_snapshot" in columns:
        # Fresh databases are created from latest metadata, including the index.
        return
    # SQLite rejects ALTER of foreign-key constraints, so the columns are added
    # through the batch copy-and-move strategy with an explicitly named key.
    with op.batch_alter_table("reports") as batch_op:
        if "class_id" not in columns:
            batch_op.add_column(sa.Column("class_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_reports_class_id_classes", "classes", ["class_id"], ["id"])
        if "class_name_snapshot" not in columns:
            batch_op.add_column(sa.Column("class_name_snapshot", sa.String(120), nullable=True))
    if not bind.scalar(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='index' AND name='ix_reports_class_status_updated_id'")
    ):
        op.create_index(
            "ix_reports_class_status_updated_id",
            "reports",
            ["class_id", "status", "updated_at", "id"],
        )


def downgrade():
    bind = op.get_bind()
    if "reports" not in sa.inspect(bind).get_table_names():
        return
    columns = _report_columns(bind)
    if "class_id" not in columns and "class_name_snapshot" not in columns:
        return
    # Class attribution is irreversible teaching-record scope: a downgrade with
    # any assigned report would silently reopen the global teacher queue.
    if "class_id" in columns and bind.scalar(sa.text("SELECT count(*) FROM reports WHERE class_id IS NOT NULL")):
        raise RuntimeError(
            "T29 report class assignments exist; apply a forward fix or restore a verified T29-backup"
            " instead of dropping class scope"
        )
    if bind.scalar(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='index' AND name='ix_reports_class_status_updated_id'")
    ):
        op.drop_index("ix_reports_class_status_updated_id", table_name="reports")
    # SQLite cannot drop a column referenced by a foreign key definition; the
    # batch rebuild recreates the remaining columns, keys and indexes verbatim.
    to_drop = [name for name in ("class_name_snapshot", "class_id") if name in columns]
    with op.batch_alter_table("reports") as batch_op:
        for name in to_drop:
            batch_op.drop_column(name)
