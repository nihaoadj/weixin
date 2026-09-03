"""Add T08 student review items, states and attempts."""

import sqlalchemy as sa

from alembic import op

revision = "20260831_0011"
down_revision = "20260831_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "review_items" not in tables:
        op.create_table(
            "review_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("point_code", sa.String(length=120), nullable=False),
            sa.Column("card_code", sa.String(length=160), nullable=True),
            sa.Column("source_type", sa.String(length=40), nullable=False),
            sa.Column("source_id", sa.String(length=160), nullable=False),
            sa.Column("note", sa.Text(), nullable=False, server_default=""),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("student_id", "source_type", "source_id", "point_code", name="uq_review_item_source"),
        )
        op.create_index("ix_review_items_student_active", "review_items", ["student_id", "active"])
        op.create_index("ix_review_items_point_code", "review_items", ["point_code"])
    if "review_states" not in tables:
        op.create_table(
            "review_states",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("card_code", sa.String(length=160), nullable=False),
            sa.Column("point_code", sa.String(length=120), nullable=False),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ease", sa.Float(), nullable=False, server_default="2.5"),
            sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lapses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_rating", sa.String(length=12), nullable=True),
            sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("student_id", "card_code", name="uq_review_state_student_card"),
        )
        op.create_index("ix_review_states_student_due", "review_states", ["student_id", "due_at"])
    if "review_attempts" not in tables:
        op.create_table(
            "review_attempts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("state_id", sa.Integer(), sa.ForeignKey("review_states.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("selected_option", sa.Integer(), nullable=True),
            sa.Column("correct", sa.Boolean(), nullable=False),
            sa.Column("rating", sa.String(length=12), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_review_attempts_student_id", "review_attempts", ["student_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "review_attempts" in tables:
        indexes = {item["name"] for item in inspector.get_indexes("review_attempts")}
        if "ix_review_attempts_student_id" in indexes:
            op.drop_index("ix_review_attempts_student_id", table_name="review_attempts")
        op.drop_table("review_attempts")
    if "review_states" in tables:
        indexes = {item["name"] for item in inspector.get_indexes("review_states")}
        if "ix_review_states_student_due" in indexes:
            op.drop_index("ix_review_states_student_due", table_name="review_states")
        op.drop_table("review_states")
    if "review_items" in tables:
        indexes = {item["name"] for item in inspector.get_indexes("review_items")}
        if "ix_review_items_point_code" in indexes:
            op.drop_index("ix_review_items_point_code", table_name="review_items")
        if "ix_review_items_student_active" in indexes:
            op.drop_index("ix_review_items_student_active", table_name="review_items")
        op.drop_table("review_items")
