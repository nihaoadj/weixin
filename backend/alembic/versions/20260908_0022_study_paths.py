"""T20 learning paths and private, unreviewed practice history."""

import sqlalchemy as sa

from alembic import op

revision = "20260908_0022"
down_revision = "20260908_0021"
branch_labels = None
depends_on = None


def upgrade():
    # The repository's initial migration intentionally creates current ORM
    # metadata for a fresh database.  Older upgrade paths still need this
    # migration, but fresh databases already have all three owned tables.
    if {"study_paths", "study_practice_groups", "study_practice_attempts"} <= set(
        sa.inspect(op.get_bind()).get_table_names()
    ):
        return
    op.create_table(
        "study_paths",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("point_code", sa.String(120), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("pbl_sessions.id"), nullable=False),
        sa.Column("client_id", sa.String(100), nullable=False),
        sa.Column("material_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "client_id", name="uq_study_path_student_client"),
        sa.UniqueConstraint("session_id", "point_code", name="uq_study_path_session_point"),
    )
    op.create_index("ix_study_paths_student_id", "study_paths", ["student_id"])
    op.create_table(
        "study_practice_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("path_id", sa.Integer(), sa.ForeignKey("study_paths.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("pbl_diagnostic_snapshots.id"), nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("claim", sa.String(100), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("failure", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("path_id", "cycle", name="uq_study_practice_path_cycle"),
        sa.CheckConstraint("cycle IN (1, 2)", name="ck_study_practice_cycle"),
    )
    op.create_index("ix_study_practice_groups_student_id", "study_practice_groups", ["student_id"])
    op.create_index("ix_study_practice_groups_path_id", "study_practice_groups", ["path_id"])
    op.create_table(
        "study_practice_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("study_practice_groups.id"), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(100), nullable=False),
        sa.Column("selected_option", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "client_id", name="uq_study_practice_attempt_student_client"),
    )
    op.create_index("ix_study_practice_attempts_student_id", "study_practice_attempts", ["student_id"])
    op.create_index("ix_study_practice_attempts_group_id", "study_practice_attempts", ["group_id"])


def downgrade():
    bind = op.get_bind()
    has_paths = bind.scalar(sa.text("SELECT count(*) FROM study_paths"))
    has_groups = bind.scalar(sa.text("SELECT count(*) FROM study_practice_groups"))
    if has_paths or has_groups:
        raise RuntimeError("T20 learning records exist; restore a verified backup instead of removing learning history")
    op.drop_table("study_practice_attempts")
    op.drop_table("study_practice_groups")
    op.drop_table("study_paths")
