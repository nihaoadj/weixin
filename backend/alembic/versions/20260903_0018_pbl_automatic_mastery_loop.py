"""Participation phases and deterministic two-cycle PBL mastery decisions."""

import json

import sqlalchemy as sa

from alembic import op

revision = "20260903_0018"
down_revision = "20260903_0017"
branch_labels = None
depends_on = None


def _columns():
    return {
        "pbl_participations": [
            sa.Column("current_phase", sa.String(40), nullable=False, server_default="problem_framing"),
            sa.Column("phase_started_revision", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("phase_status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("phase_completed_at", sa.DateTime(timezone=True), nullable=True),
        ],
        "pbl_diagnostic_snapshots": [
            sa.Column("phase", sa.String(40), nullable=True),
            sa.Column("phase_decision", sa.String(20), nullable=True),
            sa.Column("phase_evidence_message_ids", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("phase_evidence_summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("phase_missing_elements", sa.JSON(), nullable=False, server_default="[]"),
        ],
        "learning_plans": [
            sa.Column("current_cycle", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("max_cycles", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("automation_exhausted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("decision_policy_version", sa.String(80), nullable=False, server_default="pbl-mastery-v1"),
            sa.Column("decision_basis", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        ],
        "learning_tasks": [
            sa.Column("cycle_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("target_type", sa.String(40), nullable=False, server_default="discussion"),
            sa.Column("target_code", sa.String(160), nullable=False, server_default="discussion"),
            sa.Column("variant_code", sa.String(200), nullable=False, server_default="v1"),
        ],
    }


def upgrade():
    bind = op.get_bind()
    for table, columns in _columns().items():
        existing = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        missing = [column for column in columns if column.name not in existing]
        if missing:
            with op.batch_alter_table(table) as batch:
                for column in missing:
                    batch.add_column(column)

    # Ready v2 conversations are historical completed discussions; all other
    # conversations restart their evidence window at the current revision.
    bind.execute(
        sa.text(
            """
            UPDATE pbl_participations
            SET current_phase = 'synthesis', phase_status = 'completed',
                phase_completed_at = COALESCE(phase_completed_at, updated_at),
                phase_started_revision = revision
            WHERE EXISTS (
                SELECT 1 FROM pbl_diagnostic_snapshots s
                WHERE s.participation_id = pbl_participations.id
                  AND s.status = 'ready' AND s.schema_version = 2
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE pbl_participations
            SET current_phase = 'problem_framing', phase_status = 'active',
                phase_started_revision = revision
            WHERE phase_status <> 'completed'
            """
        )
    )
    legacy = json.dumps({"decision_source": "legacy_teacher"}, ensure_ascii=False)
    bind.execute(
        sa.text(
            """
            UPDATE learning_plans SET decision_basis = :basis
            WHERE verification_status IN ('improved', 'needs_reinforcement')
              AND (decision_basis IS NULL OR decision_basis = '{}')
            """
        ),
        {"basis": legacy},
    )


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM pbl_diagnostic_snapshots WHERE schema_version >= 3")):
        raise RuntimeError("Restore the pre-T14 backup before downgrading schema v3 PBL evidence")
    if bind.scalar(sa.text("SELECT count(*) FROM learning_tasks WHERE cycle_number > 1")):
        raise RuntimeError("Restore the pre-T14 backup before downgrading two-cycle PBL tasks")
    for table, columns in reversed(list(_columns().items())):
        existing = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        with op.batch_alter_table(table) as batch:
            for column in reversed(columns):
                if column.name in existing:
                    batch.drop_column(column.name)
