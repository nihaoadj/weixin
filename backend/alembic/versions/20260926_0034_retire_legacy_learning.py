"""Retire the old PBL learning loop after an explicit T44 cutover."""

from __future__ import annotations

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "20260926_0034"
down_revision = "20260926_0033"
branch_labels = None
depends_on = None


LEGACY_EMPTY_TABLES = (
    "study_practice_attempts",
    "study_practice_groups",
    "study_paths",
    "classroom_question_reviews",
    "t43_legacy_plan_mappings",
    "classroom_final_reports",
    "classroom_package_items",
    "classroom_task_packages",
    "teaching_command_receipts",
    "pbl_question_suggestions",
    "pbl_submissions",
    "pbl_teacher_feedbacks",
)
LEGACY_SHARED_PLAN_TYPES = ("pbl_suggestion", "classroom_package")
NO_DOWNGRADE_TABLES = (
    "learning_routes",
    "learning_route_steps",
    "route_reading_progress",
    "route_case_sessions",
    "route_case_messages",
    "route_case_phase_decisions",
    "route_final_tests",
    "route_test_questions",
    "route_test_attempts",
    "route_learning_results",
    "route_test_review_events",
    "route_command_receipts",
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    if table not in _tables():
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _count(table: str) -> int:
    return int(op.get_bind().scalar(sa.text(f"SELECT COUNT(*) FROM {table}")) or 0)


def _empty_cutover_marker() -> None:
    bind = op.get_bind()
    if "t44_cutover_manifests" not in _tables():
        raise RuntimeError("0034 requires the 0033 T44 cutover manifest table")
    bind.execute(
        sa.text(
            "INSERT INTO t44_cutover_manifests "
            "(cutover_token, target_resource_digest, original_head, planned_delete_counts, "
            "retained_digest, id_high_water, target_ids, completed_at) "
            "VALUES (:token, :resource, :head, :counts, :retained, :high_water, :target_ids, CURRENT_TIMESTAMP)"
        ),
        {
            "token": f"empty-{uuid4()}",
            "resource": "empty-cutover",
            "head": "20260924_0032",
            "counts": "{}",
            "retained": "{}",
            "high_water": "{}",
            "target_ids": '{"sessions":[],"participations":[],"snapshots":[]}',
        },
    )


def _latest_cutover() -> dict[str, object] | None:
    if "t44_cutover_manifests" not in _tables():
        return None
    row = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT cutover_token, target_ids FROM t44_cutover_manifests "
                "WHERE completed_at IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    import json

    try:
        targets = json.loads(row["target_ids"] or "{}")
    except (TypeError, ValueError):
        raise RuntimeError("0034 found an unreadable completed T44 cutoff") from None
    if not isinstance(targets, dict):
        raise RuntimeError("0034 found an invalid completed T44 cutoff")
    return {"token": str(row["cutover_token"]), "target_ids": targets}


def _assert_no_new_route_data() -> None:
    for table in NO_DOWNGRADE_TABLES:
        if table in _tables() and _count(table):
            raise RuntimeError(f"0034 refuses while new T44 data exists in {table}")


def _assert_cutover() -> None:
    bind = op.get_bind()
    missing = [
        table
        for table in (*LEGACY_EMPTY_TABLES, "pbl_sessions", "pbl_participations", "pbl_diagnostic_snapshots")
        if table not in _tables()
    ]
    if missing:
        raise RuntimeError(f"0034 requires a complete 0032 schema; missing {', '.join(missing)}")
    # Check this before making the convenience marker for a truly empty
    # database.  A refusal must not leave behind a false completed cutoff.
    _assert_no_new_route_data()
    marker = _latest_cutover()
    if marker is None:
        # A truly empty temporary database can skip an explicit data cleanup.
        old_counts = {
            table: _count(table)
            for table in (*LEGACY_EMPTY_TABLES, "pbl_sessions", "pbl_participations", "pbl_diagnostic_snapshots")
        }
        if any(old_counts.values()):
            raise RuntimeError("0034 requires a completed T44 cleanup manifest before removing legacy schema")
        if "learning_plans" in _tables():
            escaped = (
                bind.scalar(
                    sa.text(
                        "SELECT COUNT(*) FROM learning_plans "
                        "WHERE source_type IN ('pbl_suggestion', 'classroom_package')"
                    )
                )
                or 0
            )
            if escaped:
                raise RuntimeError("0034 found legacy PBL plans without a cleanup manifest")
        _empty_cutover_marker()
        marker = _latest_cutover()
    assert marker is not None
    target_ids = marker["target_ids"]
    for key, table in (
        ("sessions", "pbl_sessions"),
        ("participations", "pbl_participations"),
        ("snapshots", "pbl_diagnostic_snapshots"),
    ):
        values = target_ids.get(key, [])
        if not isinstance(values, list) or any(not isinstance(value, int) or value <= 0 for value in values):
            raise RuntimeError(f"0034 found invalid frozen {key} targets in the cutover manifest")
        if values:
            placeholders = ", ".join(f":id{index}" for index in range(len(values)))
            params = {f"id{index}": value for index, value in enumerate(values)}
            count = bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table} WHERE id IN ({placeholders})"), params) or 0
            if count:
                raise RuntimeError(f"0034 refuses while cutoff rows remain in {table}")
    for table in LEGACY_EMPTY_TABLES:
        if _count(table):
            raise RuntimeError(f"0034 refuses while legacy rows remain in {table}")
    if "learning_plans" in _tables():
        escaped = (
            bind.scalar(
                sa.text(
                    "SELECT COUNT(*) FROM learning_plans WHERE source_type IN ('pbl_suggestion', 'classroom_package')"
                )
            )
            or 0
        )
        if escaped:
            raise RuntimeError("0034 refuses while legacy PBL plans remain")
    if "teacher_question_bank_revisions" in _tables() and "source_package_item_id" in _columns(
        "teacher_question_bank_revisions"
    ):
        if bind.scalar(
            sa.text("SELECT COUNT(*) FROM teacher_question_bank_revisions WHERE source_package_item_id IS NOT NULL")
        ):
            raise RuntimeError("0034 refuses while question revisions retain package item references")
    allowed_bank_sources = "('legacy_detached', 'route_test_question')"
    for table in ("teacher_question_bank_revisions", "bank_import_receipts"):
        if table not in _tables():
            continue
        columns = _columns(table)
        if not {"source_kind", "source_public_id", "source_digest"}.issubset(columns):
            raise RuntimeError(f"0034 refuses {table} without detached generic source identity")
        unknown = (
            bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table} WHERE source_kind NOT IN {allowed_bank_sources}")) or 0
        )
        if unknown:
            raise RuntimeError(f"0034 refuses unrecognized legacy question source types in {table}")
    if "bank_import_receipts" in _tables() and "source_package_item_id" in _columns("bank_import_receipts"):
        if bind.scalar(sa.text("SELECT COUNT(*) FROM bank_import_receipts WHERE source_package_item_id IS NOT NULL")):
            raise RuntimeError("0034 refuses while import receipts retain package item references")
    if "pbl_diagnostic_snapshots" in _tables():
        columns = _columns("pbl_diagnostic_snapshots")
        if "candidate_tasks" in columns:
            count = (
                bind.scalar(
                    sa.text(
                        "SELECT COUNT(*) FROM pbl_diagnostic_snapshots "
                        "WHERE candidate_tasks IS NOT NULL AND candidate_tasks NOT IN ('[]', 'null')"
                    )
                )
                or 0
            )
            if count:
                raise RuntimeError("0034 refuses while legacy candidate task data remains")


def _drop_legacy_tables() -> None:
    tables = _tables()
    for table in (
        "pbl_teacher_feedbacks",
        "pbl_submissions",
        "pbl_question_suggestions",
        "classroom_question_reviews",
        "classroom_final_reports",
        "t43_legacy_plan_mappings",
        "classroom_package_items",
        "teaching_command_receipts",
        "classroom_task_packages",
        "study_practice_attempts",
        "study_practice_groups",
        "study_paths",
    ):
        if table in tables:
            op.drop_table(table)


def _drop_column_if_present(table: str, column: str) -> None:
    if table not in _tables() or column not in _columns(table):
        return
    with op.batch_alter_table(table) as batch:
        batch.drop_column(column)


def _detach_question_bank_columns() -> None:
    if "teacher_question_bank_revisions" in _tables() and "source_package_item_id" in _columns(
        "teacher_question_bank_revisions"
    ):
        with op.batch_alter_table("teacher_question_bank_revisions") as batch:
            batch.drop_column("source_package_item_id")


def _tighten_pbl_schema_version() -> None:
    if "pbl_sessions" not in _tables() or "ai_schema_version" not in _columns("pbl_sessions"):
        return
    bind = op.get_bind()
    legacy_versions = bind.scalar(sa.text("SELECT COUNT(*) FROM pbl_sessions WHERE ai_schema_version != 8")) or 0
    if legacy_versions:
        raise RuntimeError("0034 refuses while non-v8 PBL sessions remain after cutoff cleanup")
    checks = {item["name"]: item.get("sqltext", "") for item in sa.inspect(bind).get_check_constraints("pbl_sessions")}
    current = checks.get("ck_pbl_session_ai_schema_version", "")
    if "= 8" in current or "=8" in current:
        return
    with op.batch_alter_table("pbl_sessions") as batch:
        if "ck_pbl_session_ai_schema_version" in checks:
            batch.drop_constraint("ck_pbl_session_ai_schema_version", type_="check")
        batch.alter_column(
            "ai_schema_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="8",
        )
        batch.create_check_constraint("ck_pbl_session_ai_schema_version", "ai_schema_version = 8")
    if "bank_import_receipts" in _tables() and "source_package_item_id" in _columns("bank_import_receipts"):
        with op.batch_alter_table("bank_import_receipts") as batch:
            unique_names = {
                item["name"] for item in sa.inspect(op.get_bind()).get_unique_constraints("bank_import_receipts")
            }
            if "uq_bank_import_source" in unique_names:
                batch.drop_constraint("uq_bank_import_source", type_="unique")
            batch.drop_column("source_package_item_id")


def upgrade() -> None:
    _assert_cutover()
    _detach_question_bank_columns()
    _drop_legacy_tables()
    _drop_column_if_present("pbl_diagnostic_snapshots", "candidate_tasks")
    _drop_column_if_present("pbl_diagnostic_snapshots", "diagnosis_outcome")
    _tighten_pbl_schema_version()


def downgrade() -> None:
    for table in NO_DOWNGRADE_TABLES:
        if table in _tables() and _count(table):
            raise RuntimeError("Cannot downgrade 0034 while new single-round learning data exists")
    raise RuntimeError("0034 removes legacy schema; restore a verified pre-cutover backup")
