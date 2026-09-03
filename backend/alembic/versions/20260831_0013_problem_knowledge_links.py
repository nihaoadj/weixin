"""Bind authored questions and cases to fixed T08 knowledge points."""

import sqlalchemy as sa

from alembic import op

revision = "20260831_0013"
down_revision = "20260831_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "problem_knowledge_links" in set(inspector.get_table_names()):
        return
    op.create_table(
        "problem_knowledge_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("problem_id", sa.Integer(), sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("point_code", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("problem_id", "point_code", name="uq_problem_knowledge_link"),
    )
    op.create_index("ix_problem_knowledge_links_problem_id", "problem_knowledge_links", ["problem_id"])
    op.create_index("ix_problem_knowledge_links_point_code", "problem_knowledge_links", ["point_code"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "problem_knowledge_links" not in set(inspector.get_table_names()):
        return
    indexes = {item["name"] for item in inspector.get_indexes("problem_knowledge_links")}
    for name in ("ix_problem_knowledge_links_point_code", "ix_problem_knowledge_links_problem_id"):
        if name in indexes:
            op.drop_index(name, table_name="problem_knowledge_links")
    op.drop_table("problem_knowledge_links")
