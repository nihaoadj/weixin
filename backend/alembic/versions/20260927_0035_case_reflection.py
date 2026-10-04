"""Allow a fourth reflection stage without rewriting completed cases or messages."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_0035"
down_revision = "20260926_0034"
branch_labels = None
depends_on = None


def _constraints(include_reflection: bool) -> None:
    phases = "'pathology_recognition', 'mechanism_explanation', 'evidence_judgment'"
    if include_reflection:
        phases += ", 'summary_reflection'"
    for table, name, extra in (
        ("route_case_sessions", "ck_route_case_session_phase", ", 'completed'"),
        ("route_case_phase_decisions", "ck_route_case_decision_phase", ""),
    ):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
            batch.create_check_constraint(name, f"phase IN ({phases}{extra})")


def upgrade() -> None:
    _constraints(True)


def downgrade() -> None:
    connection = op.get_bind()
    for table in ("route_case_sessions", "route_case_phase_decisions"):
        if connection.scalar(sa.text(f"SELECT COUNT(*) FROM {table} WHERE phase = 'summary_reflection'")):
            raise RuntimeError("Cannot downgrade: preserve case reflection sessions and decisions")
    _constraints(False)
