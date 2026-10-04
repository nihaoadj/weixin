"""Allow draft package items to be excluded without deleting their provenance."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260924_0032"
down_revision = "20260923_0031"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("classroom_package_items")}


def upgrade() -> None:
    if "included_in_package" not in _columns():
        op.add_column(
            "classroom_package_items",
            sa.Column("included_in_package", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    if "included_in_package" not in _columns():
        return
    excluded_count = op.get_bind().scalar(
        sa.text("SELECT COUNT(*) FROM classroom_package_items WHERE included_in_package = 0")
    )
    if excluded_count:
        raise RuntimeError("Cannot downgrade 0032 while classroom package items are excluded")
    with op.batch_alter_table("classroom_package_items") as batch:
        batch.drop_column("included_in_package")
