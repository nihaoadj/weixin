"""T30 append-only learning evidence event and metric ledger."""

import sqlalchemy as sa

from alembic import op

revision = "20260913_0025"
down_revision = "20260913_0024"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "learning_evidence_events" in tables or "learning_evidence_metrics" in tables:
        if {"learning_evidence_events", "learning_evidence_metrics"} <= tables:
            return
        raise RuntimeError("T30 learning evidence schema is partially present; repair forward before retrying")
    op.create_table(
        "learning_evidence_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("authority_level", sa.String(length=30), nullable=False),
        sa.Column("visibility_scope", sa.String(length=30), nullable=False),
        sa.Column("event_kind", sa.String(length=30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedupe_key", sa.String(length=180), nullable=False),
        sa.Column("contract_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(visibility_scope = 'student_only' AND class_id IS NULL) OR "
            "(visibility_scope IN ('class_aggregate', 'class_detail') AND class_id IS NOT NULL)",
            name="ck_learning_evidence_visibility_class",
        ),
        sa.CheckConstraint(
            "authority_level != 'personal_unverified' OR visibility_scope = 'student_only'",
            name="ck_learning_evidence_personal_visibility",
        ),
        sa.UniqueConstraint("dedupe_key", name="uq_learning_evidence_event_dedupe"),
    )
    op.create_index(
        "ix_learning_evidence_event_student_time", "learning_evidence_events", ["student_id", "occurred_at", "id"]
    )
    op.create_index(
        "ix_learning_evidence_event_class_time", "learning_evidence_events", ["class_id", "occurred_at", "id"]
    )
    op.create_index("ix_learning_evidence_event_source", "learning_evidence_events", ["source_type", "source_id"])
    op.create_index(
        "ix_learning_evidence_event_authority_visibility_time",
        "learning_evidence_events",
        ["authority_level", "visibility_scope", "occurred_at"],
    )
    op.create_index("ix_learning_evidence_events_student_id", "learning_evidence_events", ["student_id"])
    op.create_index("ix_learning_evidence_events_class_id", "learning_evidence_events", ["class_id"])
    op.create_index("ix_learning_evidence_events_occurred_at", "learning_evidence_events", ["occurred_at"])
    op.create_table(
        "learning_evidence_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id", sa.Integer(), sa.ForeignKey("learning_evidence_events.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("metric_kind", sa.String(length=30), nullable=False),
        sa.Column("metric_code", sa.String(length=120), nullable=False),
        sa.Column("normalized_score", sa.Float(), nullable=True),
        sa.Column("result", sa.String(length=24), nullable=False),
        sa.Column("evidence_present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "normalized_score IS NULL OR (normalized_score >= 0 AND normalized_score <= 100)",
            name="ck_learning_evidence_metric_score",
        ),
        sa.UniqueConstraint("event_id", "metric_kind", "metric_code", name="uq_learning_evidence_metric_code"),
    )
    op.create_index("ix_learning_evidence_metrics_event_id", "learning_evidence_metrics", ["event_id"])
    op.create_index(
        "ix_learning_evidence_metric_kind_code_event",
        "learning_evidence_metrics",
        ["metric_kind", "metric_code", "event_id"],
    )


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "learning_evidence_events" not in tables and "learning_evidence_metrics" not in tables:
        return
    if "learning_evidence_events" in tables and bind.scalar(sa.text("SELECT count(*) FROM learning_evidence_events")):
        raise RuntimeError(
            "T30 learning evidence exists; export a verified evidence backup and apply a forward fix before downgrade"
        )
    if "learning_evidence_metrics" in tables and bind.scalar(sa.text("SELECT count(*) FROM learning_evidence_metrics")):
        raise RuntimeError(
            "T30 learning evidence metrics exist; export a verified evidence backup and apply a "
            "forward fix before downgrade"
        )
    if "learning_evidence_metrics" in tables:
        op.drop_table("learning_evidence_metrics")
    if "learning_evidence_events" in tables:
        op.drop_table("learning_evidence_events")
