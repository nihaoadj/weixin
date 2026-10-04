"""Add classes, medical review records and analytics ownership fields."""

import sqlalchemy as sa

from alembic import op

revision = "20260823_0004"
down_revision = "20260823_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "users" in tables and "permissions" not in {item["name"] for item in inspector.get_columns("users")}:
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("permissions", sa.JSON(), nullable=False, server_default="[]"))
    if "problems" in tables:
        columns = {item["name"] for item in inspector.get_columns("problems")}
        with op.batch_alter_table("problems") as batch:
            if "author_id" not in columns:
                batch.add_column(sa.Column("author_id", sa.Integer(), nullable=True))
                batch.create_index("ix_problems_author_id", ["author_id"])
            if "medical_review_status" not in columns:
                batch.add_column(
                    sa.Column("medical_review_status", sa.String(30), nullable=False, server_default="not_submitted")
                )
                batch.create_index("ix_problems_medical_review_status", ["medical_review_status"])
    metadata = sa.MetaData()
    # These two referenced pilot tables live in a different SQLAlchemy
    # metadata registry.  Local stubs let this revision retain its original
    # explicit CREATE TABLE behavior after revision 0001 stops creating every
    # current runtime table up front.
    sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table("problems", metadata, sa.Column("id", sa.Integer, primary_key=True))
    classes = sa.Table(
        "classes",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("teacher_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    members = sa.Table(
        "class_members",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("class_id", sa.Integer, sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("class_id", "student_id", name="uq_class_member"),
    )
    reviews = sa.Table(
        "medical_reviews",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("problem_id", sa.Integer, sa.ForeignKey("problems.id"), nullable=False),
        sa.Column("reviewer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("comment", sa.String(2000), nullable=False, server_default=""),
        sa.Column("problem_version", sa.Integer, nullable=False),
        sa.Column("case_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for table in (classes, members, reviews):
        table.create(bind, checkfirst=True)
    inspector = sa.inspect(bind)
    if "class_members" in inspector.get_table_names():
        indexes = {item["name"] for item in inspector.get_indexes("class_members")}
        if "ix_class_members_class_student" not in indexes:
            op.create_index("ix_class_members_class_student", "class_members", ["class_id", "student_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "class_members" in inspector.get_table_names():
        if "ix_class_members_class_student" in {item["name"] for item in inspector.get_indexes("class_members")}:
            op.drop_index("ix_class_members_class_student", table_name="class_members")
        op.drop_table("class_members")
    for table in ("medical_reviews", "classes"):
        if table in inspector.get_table_names():
            op.drop_table(table)
    if "problems" in inspector.get_table_names():
        columns = {item["name"] for item in sa.inspect(bind).get_columns("problems")}
        with op.batch_alter_table("problems") as batch:
            if "medical_review_status" in columns:
                batch.drop_index("ix_problems_medical_review_status")
                batch.drop_column("medical_review_status")
            if "author_id" in columns:
                batch.drop_index("ix_problems_author_id")
                batch.drop_column("author_id")
    if "users" in sa.inspect(bind).get_table_names() and "permissions" in {
        item["name"] for item in sa.inspect(bind).get_columns("users")
    }:
        with op.batch_alter_table("users") as batch:
            batch.drop_column("permissions")
