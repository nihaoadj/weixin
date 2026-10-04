"""Freeze, audit and remove the retired PBL learning closure from a managed SQLite database.

Dry-run is the default. The manifest contains only typed row identifiers, counts,
digests and cutoff metadata; it never contains learner content or credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.testing_resources import (  # noqa: E402
    ManagedDatabase,
    ResourceOwnershipError,
    assert_owned_resource,
)

DROP_TABLES = {
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
}
CORE_TARGETS = {"pbl_sessions", "pbl_participations", "pbl_diagnostic_snapshots"}
PRESERVE_TABLES = {
    "users",
    "classes",
    "class_members",
    "knowledge_catalogs",
    "knowledge_modules",
    "knowledge_points",
    "knowledge_dependencies",
    "knowledge_dependency_sources",
    "knowledge_point_sources",
    "knowledge_sources",
    "knowledge_study_materials",
    "problems",
    "problem_knowledge_links",
    "teacher_question_bank_items",
    "teacher_question_bank_revisions",
    "bank_import_receipts",
    "bank_archive_receipts",
    "case_attempts",
    "case_attempt_messages",
    "stage_submissions",
    "case_assessments",
    "ai_call_logs",
    "conversations",
    "conversation_learning_contexts",
    "messages",
    "question_threads",
    "question_thread_messages",
}


class CleanupRefused(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: {"$bytes": item.hex()} if isinstance(item, bytes) else str(item),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        if row[0] != "sqlite_sequence"
    }


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _ids(connection: sqlite3.Connection, table: str, sql: str, params: tuple[object, ...] = ()) -> list[int]:
    if table not in _tables(connection) or "id" not in _columns(connection, table):
        return []
    return [int(row[0]) for row in connection.execute(sql, params).fetchall()]


def _in(values: list[int]) -> tuple[str, tuple[int, ...]]:
    if not values:
        return "(NULL)", ()
    return f"({','.join('?' for _ in values)})", tuple(values)


def _select_ids(connection: sqlite3.Connection, table: str, column: str, values: list[int]) -> list[int]:
    if not values or table not in _tables(connection) or not {"id", column}.issubset(_columns(connection, table)):
        return []
    clause, params = _in(values)
    return [int(row[0]) for row in connection.execute(f'SELECT id FROM "{table}" WHERE "{column}" IN {clause}', params)]


def _json_field(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


def _schema_head(connection: sqlite3.Connection) -> str:
    tables = _tables(connection)
    if "alembic_version" not in tables:
        raise CleanupRefused("Database has no Alembic version")
    versions = [row[0] for row in connection.execute("SELECT version_num FROM alembic_version")]
    if len(versions) != 1:
        raise CleanupRefused("Database must have exactly one Alembic head")
    return str(versions[0])


def _safe_sqlite_error_category(error: sqlite3.Error) -> str:
    if isinstance(error, sqlite3.IntegrityError):
        return "integrity constraint failure"
    return "database operation failure"


def _assert_integrity(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
        raise CleanupRefused("SQLite integrity check failed")
    fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if fk_errors:
        raise CleanupRefused("SQLite foreign key check found inconsistent rows")


def _safe_database(path: Path, applying: bool) -> Path:
    if not path.is_absolute():
        raise CleanupRefused("--database must be an absolute path")
    cursor = path
    while cursor != cursor.parent:
        if cursor.is_symlink() or getattr(cursor, "is_junction", lambda: False)():
            raise CleanupRefused("Linked database paths are not supported")
        cursor = cursor.parent
    resolved = path.resolve(strict=True)
    if resolved.suffix.lower() not in {".db", ".sqlite", ".sqlite3"} or not resolved.is_file():
        raise CleanupRefused("Database must be an existing SQLite file")
    if applying:
        if os.environ.get("APP_ENV", "").strip().lower() == "production":
            raise CleanupRefused("Production databases are not supported")
        try:
            is_production = get_settings().is_production
        except Exception:
            raise CleanupRefused("Unable to verify application environment") from None
        if is_production:
            raise CleanupRefused("Production databases are not supported")
        resource_dir = os.environ.get("TEST_RESOURCE_DIR")
        token = os.environ.get("TEST_RESOURCE_TOKEN")
        if not resource_dir or not token:
            raise CleanupRefused("Apply requires a verified managed-resource ownership marker")
        root = Path(resource_dir).absolute()
        resource = ManagedDatabase(root=root, database_path=root / "app.sqlite3", token=token)
        try:
            assert_owned_resource(resource)
        except (ResourceOwnershipError, OSError) as error:
            raise CleanupRefused("Managed-resource ownership could not be verified") from error
        if resolved != resource.database_path.resolve(strict=True):
            raise CleanupRefused("Database path does not match the verified managed resource")
    return resolved


def _backup(source: Path, target: Path, expected_head: str) -> dict[str, object]:
    target = target.absolute()
    if not target.is_absolute() or target.exists() or target.is_symlink():
        raise CleanupRefused("Backup path must be a new absolute SQLite path")
    if not target.parent.is_dir() or target.resolve(strict=False) == source:
        raise CleanupRefused("Backup parent must exist and differ from the database")
    try:
        with closing(sqlite3.connect(source)) as original, closing(sqlite3.connect(target)) as saved:
            original.backup(saved)
            if saved.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise CleanupRefused("Backup integrity check failed")
            if _schema_head(saved) != expected_head:
                raise CleanupRefused(f"Backup must contain Alembic head {expected_head}")
            with closing(sqlite3.connect(":memory:")) as restored:
                saved.backup(restored)
                if _schema_head(restored) != expected_head:
                    raise CleanupRefused("Restored backup has a different Alembic head")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    with closing(sqlite3.connect(target)) as saved:
        _assert_integrity(saved)
        head = _schema_head(saved)
    return {"path": str(target), "sha256": _file_digest(target), "head": head}


def _empty_sets() -> dict[str, list[int]]:
    return {}


def _build_plan(connection: sqlite3.Connection) -> dict[str, Any]:
    tables = _tables(connection)
    required = {
        "alembic_version",
        "pbl_sessions",
        "pbl_participations",
        "pbl_messages",
        "pbl_diagnostic_snapshots",
        "learning_plans",
        "learning_tasks",
        "learning_task_attempts",
        "case_attempts",
        "case_assessments",
        "learning_evidence_events",
        "learning_evidence_metrics",
    }
    if not required.issubset(tables):
        raise CleanupRefused("0033 schema is incomplete")
    head = _schema_head(connection)
    if head != "20260926_0033":
        raise CleanupRefused("Cleanup requires the pinned 0033 maintenance head")

    ids = _empty_sets()
    blockers: list[str] = []
    ids["pbl_sessions"] = _ids(
        connection,
        "pbl_sessions",
        "SELECT id FROM pbl_sessions WHERE session_kind IN ('classroom', 'student_initiated') ORDER BY id",
    )
    ids["pbl_participations"] = _select_ids(connection, "pbl_participations", "session_id", ids["pbl_sessions"])
    ids["pbl_diagnostic_snapshots"] = _select_ids(
        connection, "pbl_diagnostic_snapshots", "participation_id", ids["pbl_participations"]
    )
    # The participation pointer can reveal a snapshot with a mismatched parent;
    # record it for closure validation rather than silently orphaning it.
    if ids["pbl_participations"] and "completion_snapshot_id" in _columns(connection, "pbl_participations"):
        clause, params = _in(ids["pbl_participations"])
        completion_ids = [
            int(row[0])
            for row in connection.execute(
                f"SELECT completion_snapshot_id FROM pbl_participations WHERE id IN {clause} "
                "AND completion_snapshot_id IS NOT NULL",
                params,
            )
        ]
        actual = set(_select_ids(connection, "pbl_diagnostic_snapshots", "id", completion_ids))
        if actual != set(completion_ids):
            blockers.append("missing_completion_snapshot")
        ids["pbl_diagnostic_snapshots"] = sorted(set(ids["pbl_diagnostic_snapshots"]) | actual)

    ids["pbl_messages"] = _select_ids(connection, "pbl_messages", "participation_id", ids["pbl_participations"])
    ids["pbl_private_follow_up_results"] = _select_ids(
        connection, "pbl_private_follow_up_results", "participation_id", ids["pbl_participations"]
    )
    ids["pbl_question_suggestions"] = _select_ids(
        connection, "pbl_question_suggestions", "snapshot_id", ids["pbl_diagnostic_snapshots"]
    )
    ids["pbl_submissions"] = _select_ids(connection, "pbl_submissions", "session_id", ids["pbl_sessions"])
    ids["pbl_teacher_feedbacks"] = _select_ids(
        connection, "pbl_teacher_feedbacks", "snapshot_id", ids["pbl_diagnostic_snapshots"]
    )
    if "pbl_teacher_feedbacks" in tables and "package_id" in _columns(connection, "pbl_teacher_feedbacks"):
        ids["pbl_teacher_feedbacks"] = sorted(
            set(ids["pbl_teacher_feedbacks"])
            | set(
                _select_ids(
                    connection,
                    "pbl_teacher_feedbacks",
                    "package_id",
                    _select_ids(connection, "classroom_task_packages", "session_id", ids["pbl_sessions"]),
                )
            )
        )

    ids["study_paths"] = _select_ids(connection, "study_paths", "session_id", ids["pbl_sessions"])
    ids["study_practice_groups"] = _select_ids(connection, "study_practice_groups", "path_id", ids["study_paths"])
    ids["study_practice_attempts"] = _select_ids(
        connection, "study_practice_attempts", "group_id", ids["study_practice_groups"]
    )
    ids["classroom_task_packages"] = sorted(
        set(_select_ids(connection, "classroom_task_packages", "session_id", ids["pbl_sessions"]))
        | set(
            _select_ids(
                connection, "classroom_task_packages", "completion_snapshot_id", ids["pbl_diagnostic_snapshots"]
            )
        )
    )
    ids["classroom_package_items"] = _select_ids(
        connection, "classroom_package_items", "package_id", ids["classroom_task_packages"]
    )
    ids["classroom_question_reviews"] = _select_ids(
        connection, "classroom_question_reviews", "package_item_id", ids["classroom_package_items"]
    )
    ids["classroom_final_reports"] = _select_ids(
        connection, "classroom_final_reports", "package_id", ids["classroom_task_packages"]
    )
    ids["t43_legacy_plan_mappings"] = _select_ids(
        connection, "t43_legacy_plan_mappings", "package_id", ids["classroom_task_packages"]
    )
    ids["teaching_command_receipts"] = []
    if "teaching_command_receipts" in tables:
        package_ids = set(ids["classroom_task_packages"])
        ids["teaching_command_receipts"] = [
            int(row[0])
            for row in connection.execute(
                "SELECT id FROM teaching_command_receipts WHERE operation = 'publish_classroom_package' "
                "AND resource_id IN " + (_in(sorted(package_ids))[0]),
                _in(sorted(package_ids))[1],
            )
        ]

    suggestion_ids = set(ids["pbl_question_suggestions"])
    package_ids = set(ids["classroom_task_packages"])
    for row in connection.execute(
        "SELECT id, source_type, source_id, source_context, source_assessment_id FROM learning_plans"
    ):
        plan_id, source_type, source_id, source_context, source_assessment_id = row
        if source_type not in {"pbl_suggestion", "classroom_package"}:
            continue
        context = _json_field(source_context)
        provable = (
            source_type == "pbl_suggestion"
            and (
                str(source_id) in {str(value) for value in suggestion_ids}
                or context.get("session_id") in ids["pbl_sessions"]
                or context.get("snapshot_id") in ids["pbl_diagnostic_snapshots"]
            )
        ) or (source_type == "classroom_package" and str(source_id) in {str(value) for value in package_ids})
        if provable:
            ids.setdefault("learning_plans", []).append(int(plan_id))
        else:
            blockers.append("unmapped_legacy_learning_plan")

    # Expand only typed relationships. The loop handles task-derived cases and
    # their assessment-derived plans without deleting shared case history.
    changed = True
    while changed:
        before = sum(len(values) for values in ids.values())
        ids["learning_tasks"] = _select_ids(connection, "learning_tasks", "plan_id", ids.get("learning_plans", []))
        ids["learning_task_attempts"] = _select_ids(
            connection, "learning_task_attempts", "task_id", ids["learning_tasks"]
        )
        case_ids = _select_ids(connection, "case_attempts", "learning_task_id", ids["learning_tasks"])
        if ids.get("case_attempts"):
            case_ids = sorted(
                set(case_ids) | set(_select_ids(connection, "case_attempts", "retry_of_id", ids["case_attempts"]))
            )
        if "learning_tasks" in tables and "source_attempt_id" in _columns(connection, "learning_tasks"):
            case_ids = sorted(
                set(case_ids) | set(_select_ids(connection, "learning_tasks", "source_attempt_id", case_ids))
            )
        ids["case_attempts"] = sorted(set(ids.get("case_attempts", [])) | set(case_ids))
        ids["case_assessments"] = _select_ids(connection, "case_assessments", "attempt_id", ids["case_attempts"])
        ids["case_attempt_messages"] = _select_ids(
            connection, "case_attempt_messages", "attempt_id", ids["case_attempts"]
        )
        ids["stage_submissions"] = _select_ids(connection, "stage_submissions", "attempt_id", ids["case_attempts"])
        ids["ai_call_logs"] = sorted(
            set(_select_ids(connection, "ai_call_logs", "attempt_id", ids["case_attempts"]))
            | set(_select_ids(connection, "ai_call_logs", "learning_task_id", ids["learning_tasks"]))
        )
        source_assessment_plans = _select_ids(
            connection, "learning_plans", "source_assessment_id", ids["case_assessments"]
        )
        known_plans = set(ids.get("learning_plans", []))
        ids.setdefault("learning_plans", []).extend(
            plan_id for plan_id in source_assessment_plans if plan_id not in known_plans
        )
        changed = sum(len(values) for values in ids.values()) != before
        if changed:
            ids["learning_plans"] = sorted(set(ids.get("learning_plans", [])))

    ids["learning_plan_evaluations"] = _select_ids(
        connection, "learning_plan_evaluations", "plan_id", ids.get("learning_plans", [])
    )

    # Exact polymorphic source matches only; unknown source references block.
    event_sources = {
        "self_pbl_completion": set(ids["pbl_sessions"]),
        "pbl_task_attempt": set(ids["learning_task_attempts"]),
        "pbl_cycle_evaluation": set(ids.get("learning_plans", [])),
        "case_assessment": set(ids["case_assessments"]),
    }
    event_ids: list[int] = []
    for event_id, source_type, source_id in connection.execute(
        "SELECT id, source_type, source_id FROM learning_evidence_events"
    ):
        target_values = event_sources.get(str(source_type))
        if target_values is not None and str(source_id) in {str(value) for value in target_values}:
            event_ids.append(int(event_id))
        elif source_type in {"self_pbl_completion", "pbl_task_attempt", "pbl_cycle_evaluation"}:
            blockers.append("unmapped_learning_evidence_source")
    ids["learning_evidence_events"] = sorted(event_ids)
    ids["learning_evidence_metrics"] = _select_ids(
        connection, "learning_evidence_metrics", "event_id", ids["learning_evidence_events"]
    )

    # Review rows tied to old PBL evidence are removed precisely. Shared states
    # are not guessed from a knowledge point or card code.
    review_source_ids = set(ids["learning_task_attempts"]) | set(ids.get("learning_plans", []))
    ids["review_items"] = []
    if "review_items" in tables:
        for review_id, source_type, source_id in connection.execute(
            "SELECT id, source_type, source_id FROM review_items"
        ):
            if source_type in {"pbl_task_attempt", "pbl_cycle_evaluation"} and str(source_id) in {
                str(value) for value in review_source_ids
            }:
                ids["review_items"].append(int(review_id))
    ids["review_states"] = []
    ids["review_attempts"] = []
    if ids["review_items"] and {"student_id", "card_code"}.issubset(_columns(connection, "review_items")):
        clause, params = _in(ids["review_items"])
        target_cards = {
            (int(student_id), str(card_code))
            for student_id, card_code in connection.execute(
                f"SELECT student_id, card_code FROM review_items WHERE id IN {clause} AND card_code IS NOT NULL",
                params,
            )
        }
        for student_id, card_code in target_cards:
            shared = connection.execute(
                "SELECT COUNT(*) FROM review_items WHERE student_id = ? AND card_code = ? "
                "AND source_type NOT IN ('pbl_task_attempt', 'pbl_cycle_evaluation')",
                (student_id, card_code),
            ).fetchone()[0]
            if shared:
                blockers.append("shared_review_state_card")
            else:
                ids["review_states"].extend(
                    _ids(
                        connection,
                        "review_states",
                        "SELECT id FROM review_states WHERE student_id = ? AND card_code = ?",
                        (student_id, card_code),
                    )
                )
        ids["review_states"] = sorted(set(ids["review_states"]))
        ids["review_attempts"] = _select_ids(connection, "review_attempts", "state_id", ids["review_states"])

    ids["student_notifications"] = []
    if "student_notifications" in tables:
        notify_targets = {
            "pbl_session": set(ids["pbl_sessions"]),
            "learning_plan": set(ids.get("learning_plans", [])),
            "learning_task": set(ids["learning_tasks"]),
            "case_attempt": set(ids["case_attempts"]),
            "case_assessment": set(ids["case_assessments"]),
            "classroom_task_package": set(ids["classroom_task_packages"]),
        }
        for notification_id, entity_type, entity_id in connection.execute(
            "SELECT id, entity_type, entity_id FROM student_notifications"
        ):
            if str(entity_type) in notify_targets:
                if entity_id is not None and int(entity_id) in notify_targets[str(entity_type)]:
                    ids["student_notifications"].append(int(notification_id))
                elif str(entity_type) in {"pbl_session", "classroom_task_package"}:
                    blockers.append("unmapped_pbl_notification")

    ids["knowledge_card_contributions"] = []
    if "knowledge_card_contributions" in tables and ids["pbl_diagnostic_snapshots"]:
        clause, params = _in(ids["pbl_diagnostic_snapshots"])
        for card_id, source_type in connection.execute(
            f"SELECT id, source_type FROM knowledge_card_contributions WHERE source_snapshot_id IN {clause}", params
        ):
            if source_type not in {"pbl_ai", "pbl_suggestion"}:
                blockers.append("unclassified_knowledge_card_source")
            else:
                ids["knowledge_card_contributions"].append(int(card_id))

    # Package source references in the bank have already been assigned random
    # UUID identities at 0033. They are cleared here before package deletion.
    for table in ("teacher_question_bank_revisions", "bank_import_receipts"):
        if table in tables and "source_package_item_id" in _columns(connection, table):
            clause, params = _in(ids["classroom_package_items"])
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE source_package_item_id IN {clause}", params
            ).fetchone()[0]
            if count:
                ids.setdefault("detached_bank_source_rows", []).append(int(count))

    for table in (
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
    ):
        if table in tables and int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]):
            blockers.append("new_route_data_exists")

    # Refuse any actual FK edge into this closure whose source row is not also
    # in its typed deletion set. In particular, preserved cases/plans/tasks may
    # not be silently disconnected from targeted rows.
    target_table_ids = {key: set(values) for key, values in ids.items() if values}
    for child_table in tables:
        if child_table in {"alembic_version", "t44_cutover_manifests", "t44_legacy_id_high_water"}:
            continue
        child_columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{child_table}")')}
        if "id" not in child_columns:
            continue
        planned = set(ids.get(child_table, []))
        for foreign in connection.execute(f'PRAGMA foreign_key_list("{child_table}")'):
            target_table, source_column = str(foreign[2]), str(foreign[3])
            selected = target_table_ids.get(target_table)
            if not selected or source_column not in child_columns:
                continue
            clause, params = _in(sorted(selected))
            refs = {
                int(row[0])
                for row in connection.execute(
                    f'SELECT id FROM "{child_table}" WHERE "{source_column}" IN {clause}', params
                )
            }
            if refs - planned:
                blockers.append(f"retained_fk:{child_table}.{source_column}->{target_table}")

    # Every extra legacy PBL object must be explained by the target session set.
    for table in sorted(DROP_TABLES):
        if table not in tables:
            continue
        count = int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        selected_count = len(set(ids.get(table, [])))
        if count != selected_count:
            blockers.append(f"unmapped_legacy_rows:{table}")
        ids.setdefault(table, [])

    counts = {key: len(value) for key, value in sorted(ids.items()) if not key.endswith("_rows")}
    high_water = {}
    for table in sorted(CORE_TARGETS):
        if table in tables:
            high_water[table] = int(connection.execute(f'SELECT COALESCE(MAX(id),0) FROM "{table}"').fetchone()[0])
    target_core = {
        "sessions": ids.get("pbl_sessions", []),
        "participations": ids.get("pbl_participations", []),
        "snapshots": ids.get("pbl_diagnostic_snapshots", []),
    }
    return {
        "head": head,
        "target_ids": target_core,
        "closure_ids": {key: sorted(set(value)) for key, value in sorted(ids.items()) if not key.endswith("_rows")},
        "counts": counts,
        "high_water": high_water,
        "blockers": sorted(set(blockers)),
    }


def _protected_digest(connection: sqlite3.Connection, plan: dict[str, Any]) -> str:
    tables = _tables(connection)
    excluded = plan["closure_ids"]
    payload: list[object] = []
    bookkeeping = {"alembic_version", "t44_cutover_manifests", "t44_legacy_id_high_water"}
    for table in sorted(tables - bookkeeping):
        names = [item[1] for item in connection.execute(f'PRAGMA table_info("{table}")')]
        if not names:
            continue
        rows = []
        target_ids = set(excluded.get(table, []))
        for raw in connection.execute(f'SELECT * FROM "{table}"'):
            record = dict(zip(names, raw, strict=False))
            if "id" in record and int(record["id"]) in target_ids:
                continue
            if table in {"teacher_question_bank_revisions", "bank_import_receipts"}:
                record.pop("source_package_item_id", None)
            if table == "problem_origins" and record.get("source_type") == "pbl_suggestion":
                record["source_type"] = "legacy_detached"
                record["source_id"] = "<detached>"
            rows.append(record)
        rows.sort(key=lambda row: _canonical(row))
        payload.append((table, rows))
    return _digest(payload)


def _database_fingerprint(connection: sqlite3.Connection, plan: dict[str, Any]) -> str:
    schema = [
        (row[0], row[1], row[2])
        for row in connection.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE type IN ('table','index','trigger','view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY type,name"
        )
    ]
    return _digest(
        {"head": plan["head"], "schema": schema, "closure": plan["closure_ids"], "high_water": plan["high_water"]}
    )


def _verify_fk_closure(connection: sqlite3.Connection, plan: dict[str, Any]) -> None:
    if plan["blockers"]:
        raise CleanupRefused("Cutoff has unresolved blockers: " + ", ".join(plan["blockers"]))
    if connection.execute("PRAGMA foreign_keys").fetchone() != (1,):
        raise CleanupRefused("SQLite foreign key enforcement must be enabled")


def _manifest_payload(
    database: Path,
    baseline: dict[str, object],
    plan: dict[str, Any],
    protected_digest: str,
    fingerprint: str,
) -> dict[str, object]:
    return {
        "format_version": 1,
        "cutover_token": str(uuid4()),
        "database_identity": _digest(str(database)),
        "baseline_backup": baseline,
        "original_head": baseline["head"],
        "target_resource_digest": fingerprint,
        "planned_delete_counts": plan["counts"],
        "retained_digest": {"protected_rows": protected_digest},
        "id_high_water": plan["high_water"],
        "target_ids": plan["target_ids"],
        "closure_ids": plan["closure_ids"],
        "blockers": plan["blockers"],
        "manifest_digest": "",
    }


def _seal_manifest(value: dict[str, object]) -> dict[str, object]:
    value["manifest_digest"] = _digest({key: item for key, item in value.items() if key != "manifest_digest"})
    return value


def _save_manifest(path: Path, manifest: dict[str, object]) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise CleanupRefused("--manifest must be a new absolute file path")
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.write_bytes(_canonical(manifest) + b"\n")
        temp.replace(path)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def _load_manifest(path: Path, expected_digest: str, database: Path) -> dict[str, Any]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise CleanupRefused("--manifest must be an existing absolute file")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise CleanupRefused("Manifest is unreadable") from None
    recorded = manifest.get("manifest_digest")
    actual = _digest({key: value for key, value in manifest.items() if key != "manifest_digest"})
    if recorded != actual or recorded != expected_digest:
        raise CleanupRefused("Manifest digest does not match; run dry-run again")
    if manifest.get("database_identity") != _digest(str(database)):
        raise CleanupRefused("Manifest belongs to a different database resource")
    return manifest


def _delete_ids(connection: sqlite3.Connection, table: str, values: list[int]) -> None:
    if not values or table not in _tables(connection):
        return
    clause, params = _in(values)
    connection.execute(f'DELETE FROM "{table}" WHERE id IN {clause}', params)


def _apply_deletion(connection: sqlite3.Connection, manifest: dict[str, Any]) -> None:
    ids: dict[str, list[int]] = manifest["closure_ids"]

    def values(table: str) -> list[int]:
        return [int(value) for value in ids.get(table, [])]

    # Keep exact source UUIDs and content copies while cutting integer links to
    # the package items that are about to be retired.
    for table in ("teacher_question_bank_revisions", "bank_import_receipts"):
        if table in _tables(connection) and "source_package_item_id" in _columns(connection, table):
            connection.execute(
                f"UPDATE {table} SET source_package_item_id = NULL WHERE source_package_item_id IN "
                + _in(values("classroom_package_items"))[0],
                _in(values("classroom_package_items"))[1],
            )

    # Detach an already-published teaching problem from the old suggestion key.
    if "problem_origins" in _tables(connection):
        origins = connection.execute(
            "SELECT id FROM problem_origins WHERE source_type = 'pbl_suggestion' AND source_id IN "
            + _in(values("pbl_question_suggestions"))[0],
            _in(values("pbl_question_suggestions"))[1],
        ).fetchall()
        used = {
            int(row[0])
            for row in connection.execute("SELECT source_id FROM problem_origins WHERE source_type = 'legacy_detached'")
        }
        for (origin_id,) in origins:
            locator = secrets.randbelow(2**62 - 1) + 1
            while locator in used:
                locator = secrets.randbelow(2**62 - 1) + 1
            used.add(locator)
            connection.execute(
                "UPDATE problem_origins SET source_type = 'legacy_detached', source_id = ? WHERE id = ?",
                (locator, origin_id),
            )

    # Remove only source-typed evidence, preserving unrelated evidence rows.
    _delete_ids(connection, "learning_evidence_metrics", values("learning_evidence_metrics"))
    _delete_ids(connection, "learning_evidence_events", values("learning_evidence_events"))
    _delete_ids(connection, "review_attempts", values("review_attempts"))
    _delete_ids(connection, "review_states", values("review_states"))
    _delete_ids(connection, "review_items", values("review_items"))
    _delete_ids(connection, "student_notifications", values("student_notifications"))
    _delete_ids(connection, "knowledge_card_contributions", values("knowledge_card_contributions"))

    # Break only closure-internal nullable cycles; retained-side references are
    # checked by _build_plan and are never cleared here.
    for table, column in (
        ("pbl_participations", "completion_snapshot_id"),
        ("learning_tasks", "source_attempt_id"),
        ("case_attempts", "learning_task_id"),
        ("case_attempts", "retry_of_id"),
        ("learning_plans", "source_assessment_id"),
    ):
        if table in _tables(connection) and column in _columns(connection, table) and values(table):
            clause, params = _in(values(table))
            connection.execute(f'UPDATE "{table}" SET "{column}" = NULL WHERE id IN {clause}', params)

    for table in (
        "case_attempt_messages",
        "stage_submissions",
        "ai_call_logs",
        "case_assessments",
        "case_attempts",
        "learning_task_attempts",
        "pbl_teacher_feedbacks",
        "classroom_question_reviews",
        "classroom_final_reports",
        "t43_legacy_plan_mappings",
        "teaching_command_receipts",
        "classroom_package_items",
        "classroom_task_packages",
        "study_practice_attempts",
        "study_practice_groups",
        "study_paths",
        "pbl_submissions",
        "pbl_question_suggestions",
        "pbl_private_follow_up_results",
        "pbl_messages",
    ):
        _delete_ids(connection, table, values(table))

    for table in (
        "learning_plan_evaluations",
        "learning_tasks",
        "learning_plans",
    ):
        _delete_ids(connection, table, values(table))

    # Null the source snapshot cycle, then delete only the frozen session set.
    if values("pbl_participations"):
        clause, params = _in(values("pbl_participations"))
        connection.execute(f"UPDATE pbl_participations SET completion_snapshot_id = NULL WHERE id IN {clause}", params)
    _delete_ids(connection, "pbl_diagnostic_snapshots", values("pbl_diagnostic_snapshots"))
    _delete_ids(connection, "pbl_participations", values("pbl_participations"))
    _delete_ids(connection, "pbl_sessions", values("pbl_sessions"))

    # Save high-water marks independently of rows which have now been removed.
    for table, max_id in manifest["id_high_water"].items():
        current = connection.execute(
            "SELECT max_id FROM t44_legacy_id_high_water WHERE table_name = ?", (table,)
        ).fetchone()
        if current is None:
            connection.execute(
                "INSERT INTO t44_legacy_id_high_water (table_name, max_id) VALUES (?, ?)", (table, max_id)
            )
        elif int(current[0]) < int(max_id):
            connection.execute("UPDATE t44_legacy_id_high_water SET max_id = ? WHERE table_name = ?", (max_id, table))


def _verify_deleted(connection: sqlite3.Connection, manifest: dict[str, Any]) -> None:
    ids: dict[str, list[int]] = manifest["closure_ids"]
    for table, values in ids.items():
        if table.endswith("_rows") or table not in _tables(connection) or not values:
            continue
        if "id" not in _columns(connection, table):
            continue
        clause, params = _in([int(value) for value in values])
        if connection.execute(f'SELECT COUNT(*) FROM "{table}" WHERE id IN {clause}', params).fetchone()[0]:
            raise CleanupRefused(f"Target rows remain in {table}")
    _assert_integrity(connection)


def _store_cutover(connection: sqlite3.Connection, manifest: dict[str, Any], plan: dict[str, Any]) -> None:
    connection.execute(
        "INSERT INTO t44_cutover_manifests "
        "(cutover_token, target_resource_digest, original_head, planned_delete_counts, retained_digest, "
        "id_high_water, target_ids, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (
            manifest["cutover_token"],
            manifest["target_resource_digest"],
            manifest["original_head"],
            _canonical(manifest["planned_delete_counts"]).decode(),
            _canonical(manifest["retained_digest"]).decode(),
            _canonical(manifest["id_high_water"]).decode(),
            _canonical(manifest["target_ids"]).decode(),
        ),
    )


def _prior_token(connection: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    if "t44_cutover_manifests" not in _tables(connection):
        return None
    row = connection.execute(
        "SELECT target_resource_digest, planned_delete_counts, retained_digest, completed_at "
        "FROM t44_cutover_manifests WHERE cutover_token = ?",
        (token,),
    ).fetchone()
    if row is None or row[3] is None:
        return None
    return {
        "target_resource_digest": row[0],
        "planned_delete_counts": json.loads(row[1]),
        "retained_digest": json.loads(row[2]),
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path, help="absolute, managed development SQLite file")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="read only and write a new manifest (default)")
    mode.add_argument("--apply", action="store_true", help="apply the exact frozen manifest")
    parser.add_argument("--manifest", required=True, type=Path, help="new output file for dry-run, input for apply")
    parser.add_argument("--confirm-development", action="store_true")
    parser.add_argument("--backup", type=Path, help="new 0033-state SQLite backup required by apply")
    parser.add_argument("--baseline-backup", type=Path, help="required, verified 0032 B0 backup for dry-run")
    parser.add_argument("--expected-manifest-digest")
    args = parser.parse_args(argv)
    applying = bool(args.apply)
    try:
        database = _safe_database(args.database, applying)
        if applying:
            if not args.confirm_development or args.backup is None or not args.expected_manifest_digest:
                raise CleanupRefused("--apply requires --confirm-development, --backup and --expected-manifest-digest")
            manifest = _load_manifest(args.manifest, args.expected_manifest_digest, database)
            if args.baseline_backup is not None:
                raise CleanupRefused("--baseline-backup is used by dry-run only")
            baseline_path = Path(manifest["baseline_backup"]["path"])
            if not baseline_path.is_file() or _file_digest(baseline_path) != manifest["baseline_backup"]["sha256"]:
                raise CleanupRefused("Baseline B0 is missing or has changed")
            with closing(sqlite3.connect(baseline_path)) as baseline:
                _assert_integrity(baseline)
                if _schema_head(baseline) != "20260924_0032":
                    raise CleanupRefused("Baseline B0 must be the original 0032 database")
            prior = None
            with closing(sqlite3.connect(database)) as connection:
                prior = _prior_token(connection, str(manifest["cutover_token"]))
            if prior is not None:
                print(
                    json.dumps(
                        {"mode": "already_applied", "cutover_token": manifest["cutover_token"], **prior}, sort_keys=True
                    )
                )
                return 0
            backup_info = _backup(database, args.backup, "20260926_0033")
            if backup_info["path"] == str(database) or args.backup.resolve(strict=False) == baseline_path.resolve(
                strict=True
            ):
                raise CleanupRefused("B1 backup, B0 backup and source database must be distinct")
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                _assert_integrity(connection)
                plan = _build_plan(connection)
                if plan["target_ids"] != manifest["target_ids"] or plan["closure_ids"] != manifest["closure_ids"]:
                    raise CleanupRefused("Target closure changed after dry-run; generate a new manifest")
                if plan["high_water"] != manifest["id_high_water"]:
                    raise CleanupRefused("PBL id high-water changed after dry-run; generate a new manifest")
                if _protected_digest(connection, plan) != manifest["retained_digest"]["protected_rows"]:
                    raise CleanupRefused("Retained data changed after dry-run; generate a new manifest")
                if _database_fingerprint(connection, plan) != manifest["target_resource_digest"]:
                    raise CleanupRefused("Database schema or cutoff changed after dry-run")
                _verify_fk_closure(connection, plan)
                connection.execute("BEGIN IMMEDIATE")
                try:
                    _apply_deletion(connection, manifest)
                    _verify_deleted(connection, manifest)
                    if _protected_digest(connection, plan) != manifest["retained_digest"]["protected_rows"]:
                        raise CleanupRefused("Retained data changed during cleanup")
                    _store_cutover(connection, manifest, plan)
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
            print(
                json.dumps(
                    {
                        "mode": "applied",
                        "cutover_token": manifest["cutover_token"],
                        "counts": manifest["planned_delete_counts"],
                        "backup": backup_info,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0

        if args.baseline_backup is None:
            raise CleanupRefused("Dry-run requires --baseline-backup pointing to a verified pre-0033 B0")
        baseline_path = args.baseline_backup
        if not baseline_path.is_absolute() or not baseline_path.is_file() or baseline_path.is_symlink():
            raise CleanupRefused("B0 baseline must be an existing absolute SQLite file")
        if baseline_path.resolve(strict=True) == database:
            raise CleanupRefused("B0 baseline must differ from the 0033 database")
        with closing(sqlite3.connect(baseline_path)) as baseline:
            _assert_integrity(baseline)
            if _schema_head(baseline) != "20260924_0032":
                raise CleanupRefused("B0 baseline must contain the pre-0033 0032 head")
        with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            _assert_integrity(connection)
            plan = _build_plan(connection)
            if connection.execute("PRAGMA foreign_keys").fetchone() != (1,):
                raise CleanupRefused("SQLite foreign key enforcement must be enabled")
            protected = _protected_digest(connection, plan)
            fingerprint = _database_fingerprint(connection, plan)
        baseline_info = {
            "path": str(baseline_path.resolve(strict=True)),
            "sha256": _file_digest(baseline_path),
            "head": "20260924_0032",
        }
        manifest = _seal_manifest(_manifest_payload(database, baseline_info, plan, protected, fingerprint))
        _save_manifest(args.manifest, manifest)
        print(
            json.dumps(
                {
                    "mode": "dry_run",
                    "manifest_digest": manifest["manifest_digest"],
                    "counts": manifest["planned_delete_counts"],
                    "blockers": manifest["blockers"],
                    "protected_digest": protected,
                    "writes_to_database": 0,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except CleanupRefused as error:
        print(json.dumps({"error": str(error), "database_changed": False}, ensure_ascii=False), file=sys.stderr)
        return 2
    except sqlite3.Error as error:
        print(
            json.dumps(
                {
                    "error": type(error).__name__,
                    "reason": _safe_sqlite_error_category(error),
                    "database_changed": False,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    except OSError as error:
        print(
            json.dumps({"error": type(error).__name__, "database_changed": False}, ensure_ascii=False), file=sys.stderr
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
