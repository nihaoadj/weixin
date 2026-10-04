from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session

from app.modules.content.infrastructure.models import KnowledgeCardContribution, Problem
from app.modules.learning.infrastructure.models import LearningPlan, LearningPlanEvaluation, LearningTask
from app.modules.learning.infrastructure.package_models import ClassroomPackageItem, ClassroomTaskPackage
from app.modules.training.infrastructure.models import CaseAssessment, CaseAttempt
from app.testing_resources import cleanup_managed_database, create_managed_database

BACKEND = Path(__file__).resolve().parents[1]
RETIRED_TABLES = {
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
}


def _alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["APP_ENV"] = "test"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _upgrade(database_url: str, target: str) -> None:
    result = _alembic(database_url, "upgrade", target)
    assert result.returncode == 0, result.stdout + result.stderr


def _sqlite_backup(source: Path, target: Path) -> None:
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
        assert dst.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def _knowledge_graph_rows(connection: sqlite3.Connection) -> tuple[tuple[str, tuple[tuple[object, ...], ...]], ...]:
    tables = (
        "knowledge_catalogs",
        "knowledge_modules",
        "knowledge_points",
        "knowledge_dependencies",
        "knowledge_sources",
        "knowledge_point_sources",
        "knowledge_dependency_sources",
        "knowledge_study_materials",
    )
    return tuple(
        (table, tuple(tuple(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')))
        for table in tables
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cleanup_command(
    env: dict[str, str],
    database: Path,
    manifest: Path,
    *,
    apply: bool = False,
    backup: Path | None = None,
    expected_digest: str | None = None,
    baseline: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(BACKEND / "scripts" / "cleanup_t44_learning.py"),
        "--database",
        str(database),
        "--manifest",
        str(manifest),
    ]
    if apply:
        assert backup is not None and expected_digest is not None
        command.extend(
            [
                "--apply",
                "--confirm-development",
                "--backup",
                str(backup),
                "--expected-manifest-digest",
                expected_digest,
            ]
        )
    else:
        assert baseline is not None
        command.extend(["--dry-run", "--baseline-backup", str(baseline)])
    return subprocess.run(command, cwd=BACKEND, env=env, capture_output=True, text=True, check=False)


def _seed_target_session(path: Path) -> None:
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute(
            "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions, auth_provider) "
            "VALUES (1, 't44-teacher', 'teacher', '教师', '', '[]', '[]', 'demo')"
        )
        db.execute(
            "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions, auth_provider) "
            "VALUES (2, 't44-student', 'student', '学生', '', '[]', '[]', 'demo')"
        )
        db.execute(
            "INSERT INTO classes (id, name, code, teacher_id, status) VALUES (10, '保留班', 't44-class', 1, 'active')"
        )
        db.execute("INSERT INTO class_members (class_id, student_id) VALUES (10, 2)")
        db.execute(
            "INSERT INTO pbl_sessions "
            "(id, class_id, teacher_id, session_kind, ai_schema_version, topic_code, phase, version, provider, status) "
            "VALUES (50, 10, 1, 'classroom', 6, 'pathology.cell-injury', 'evidence_collection', 1, 'test', 'completed')"
        )
        db.execute(
            "INSERT INTO pbl_participations "
            "(id, session_id, student_id, interaction_style, revision, current_phase, "
            "phase_started_revision, phase_status) "
            "VALUES (60, 50, 2, 'guided', 1, 'completed', 1, 'completed')"
        )
        db.execute(
            "INSERT INTO pbl_diagnostic_snapshots "
            "(id, participation_id, revision, status, interaction_style, schema_version, phase_evidence_message_ids, "
            "phase_evidence_summary, phase_missing_elements, safety_notice, safety_status, assistant_reply, "
            "knowledge_gaps, reasoning_issues, candidate_tasks, provider_metadata) "
            "VALUES (70, 60, 1, 'ready', 'guided', 3, '[]', '', '[]', '', 'educational', "
            "'诊断摘要', '[]', '[]', '[]', '{}')"
        )
        db.execute(
            "UPDATE pbl_participations SET completion_snapshot_id = 70, evidence_completed_revision = 1 WHERE id = 60"
        )
        db.execute(
            "INSERT INTO pbl_messages "
            "(id, participation_id, sequence, role, content, interaction_style, turn_scope, request_revision, "
            "processing_status, client_message_id) "
            "VALUES (80, 60, 1, 'student', '保密回答只作删除验证', 'guided', 'evidence', 1, 'completed', 't44-msg')"
        )
        db.execute(
            "INSERT INTO pbl_messages "
            "(id, participation_id, sequence, role, content, interaction_style, turn_scope, request_revision, "
            "processing_status, client_message_id) "
            "VALUES (81, 60, 2, 'assistant', '续问答只作删除验证', 'guided', 'private_follow_up', "
            "1, 'completed', 't44-reply')"
        )
        db.execute(
            "INSERT INTO pbl_private_follow_up_results "
            "(id, participation_id, student_message_id, assistant_message_id, interaction_style, "
            "processing_status, safety_status, provider_name) "
            "VALUES (90, 60, 80, 81, 'guided', 'completed', 'educational', 'test')"
        )
        db.commit()


def _seed_case_dependency_graph(engine, *, retained_task_points_into_target: bool = False) -> None:
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    now = datetime.now(UTC)
    due_at = now + timedelta(days=7)
    with Session(engine) as session:
        session.add(
            Problem(
                id=140,
                type="case",
                title="保留的独立病例资源",
                description="只用于迁移保留验证",
                target="all",
                target_label="全体学生",
                target_ids="",
                status="published",
                content_type="case",
                specialty="pathology",
                difficulty="basic",
                estimated_minutes=10,
                version=1,
                author_id=1,
            )
        )
        session.add(
            KnowledgeCardContribution(
                id=450,
                point_code="pathology.inflammation.vascular",
                owner_id=1,
                version=1,
                card_type="single_choice",
                prompt="独立教师知识卡",
                options=["形态与机制相符", "忽略证据"],
                correct_option=0,
                explanation="只用于迁移保留验证。",
                reference="教学资料",
                status="approved",
                source_type="teacher",
                source_snapshot_id=None,
                source_position=None,
            )
        )
        session.flush()

        target_case = CaseAttempt(
            id=300,
            problem_id=140,
            student_id=2,
            problem_version=1,
            status="completed",
            current_stage="assessment",
        )
        retained_case = CaseAttempt(
            id=310,
            problem_id=140,
            student_id=2,
            problem_version=1,
            status="completed",
            current_stage="assessment",
        )
        session.add_all([target_case, retained_case])
        session.flush()

        target_assessment = CaseAssessment(
            id=301,
            attempt_id=300,
            total_score=2,
            dimensions=[{"dimension": "reasoning", "score": 2}],
            strengths=[],
            weaknesses=[],
            next_steps=["target follow-up"],
            summary="由PBL任务派生",
            focus_stage="assessment",
        )
        retained_assessment = CaseAssessment(
            id=311,
            attempt_id=310,
            total_score=3,
            dimensions=[{"dimension": "reasoning", "score": 3}],
            strengths=["independent"],
            weaknesses=[],
            next_steps=["retain"],
            summary="独立病例评估",
            focus_stage="assessment",
        )
        session.add_all([target_assessment, retained_assessment])
        session.flush()

        package = ClassroomTaskPackage(
            id=160,
            student_id=2,
            class_id=10,
            session_id=50,
            completion_snapshot_id=70,
            teacher_id=1,
            status="draft",
            version=1,
            diagnosis_outcome="no_clear_gaps",
        )
        session.add(package)
        session.flush()
        session.add(
            ClassroomPackageItem(
                id=161,
                package_id=160,
                stable_key="target-task",
                position=1,
                cycle_number=1,
                task_type="micro_drill",
                primary_point_code="pathology.cell-injury",
                point_codes=["pathology.cell-injury"],
                dimension_ids=["reasoning"],
                target_type="reasoning_issue",
                target_code="pathology.cell-injury",
                public_definition={"prompt": "target"},
                private_rubric={"criteria": ["target"]},
                included_in_package=True,
            )
        )

        package_plan = LearningPlan(
            id=200,
            student_id=2,
            source_type="classroom_package",
            source_id=160,
            source_context={"session_id": 50},
            due_at=due_at,
        )
        independent_plan = LearningPlan(
            id=210,
            student_id=2,
            source_type="case_assessment",
            source_id=311,
            source_assessment_id=311,
            source_context={"case_attempt_id": 310},
            due_at=due_at,
        )
        session.add_all([package_plan, independent_plan])
        session.flush()
        package.status = "published"
        package.plan_id = package_plan.id
        package.published_version = 1
        package.published_at = now
        package.due_at = due_at

        target_task = LearningTask(
            id=201,
            plan_id=200,
            position=1,
            cycle_number=1,
            target_type="reasoning_issue",
            target_code="pathology.cell-injury",
            variant_code="v1",
            task_type="micro_drill",
            dimension_id="reasoning",
            source_attempt_id=300,
            status="completed",
            public_definition={"prompt": "target"},
            private_rubric={"criteria": ["target"]},
        )
        independent_task = LearningTask(
            id=211,
            plan_id=210,
            position=1,
            cycle_number=1,
            target_type="case_assessment",
            target_code="independent-case",
            variant_code="v1",
            task_type="case_reflection",
            dimension_id="reasoning",
            source_attempt_id=310,
            status="completed",
            public_definition={"prompt": "independent"},
            private_rubric={"criteria": ["independent"]},
        )
        session.add_all([target_task, independent_task])
        session.flush()
        target_case.learning_task_id = target_task.id
        retained_case.learning_task_id = independent_task.id

        target_derived_plan = LearningPlan(
            id=202,
            student_id=2,
            source_type="case_assessment",
            source_id=301,
            source_assessment_id=301,
            source_context={"case_attempt_id": 300},
            due_at=due_at,
        )
        session.add(target_derived_plan)
        session.flush()
        session.add_all(
            [
                LearningPlanEvaluation(
                    id=203,
                    plan_id=202,
                    cycle_number=1,
                    policy_version="case-v1",
                    result="needs_reinforcement",
                    evaluated_at=now,
                ),
                LearningPlanEvaluation(
                    id=212,
                    plan_id=210,
                    cycle_number=1,
                    policy_version="case-v1",
                    result="completed",
                    evaluated_at=now,
                ),
            ]
        )
        if retained_task_points_into_target:
            session.add(
                LearningTask(
                    id=220,
                    plan_id=210,
                    position=2,
                    cycle_number=1,
                    target_type="case_assessment",
                    target_code="cross-closure-reference",
                    variant_code="v1",
                    task_type="case_reflection",
                    dimension_id="reasoning",
                    source_attempt_id=300,
                    status="completed",
                    public_definition={"prompt": "retained"},
                    private_rubric={"criteria": ["retained"]},
                )
            )
        session.commit()


def test_0032_fixture_is_historical_and_0033_preserves_schema_6_and_7() -> None:
    with TemporaryDirectory(prefix="medical-qa-t44-old-schema-") as directory:
        database = Path(directory) / "old-schema.sqlite3"
        database_url = f"sqlite:///{database.as_posix()}"
        _upgrade(database_url, "20260924_0032")
        with closing(sqlite3.connect(database)) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert "learning_routes" not in tables
            session_ddl = db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='pbl_sessions'"
            ).fetchone()[0]
            assert "ai_schema_version IN (6, 7)" in session_ddl
            assert "ai_schema_version IN (6, 7, 8)" not in session_ddl
            for session_id, version in ((501, 6), (502, 7)):
                db.execute(
                    "INSERT INTO pbl_sessions "
                    "(id, class_id, teacher_id, session_kind, ai_schema_version, topic_code, phase, "
                    "version, provider, status) "
                    "VALUES (?, 10, 1, 'classroom', ?, 'pathology.cell-injury', 'evidence_collection', "
                    "1, 'test', 'completed')",
                    (session_id, version),
                )
            db.commit()

        _upgrade(database_url, "20260926_0033")
        with closing(sqlite3.connect(database)) as db:
            session_ddl = db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='pbl_sessions'"
            ).fetchone()[0]
            assert "ai_schema_version IN (6, 7, 8)" in session_ddl
            assert db.execute("SELECT id, ai_schema_version FROM pbl_sessions ORDER BY id").fetchall() == [
                (501, 6),
                (502, 7),
            ]
            default = next(
                row[4] for row in db.execute("PRAGMA table_info(pbl_sessions)") if row[1] == "ai_schema_version"
            )
            assert str(default).strip("'\"()") == "8"


def test_empty_database_upgrades_to_head_with_route_schema_and_no_retired_tables() -> None:
    with TemporaryDirectory(prefix="medical-qa-t44-empty-head-") as directory:
        database = Path(directory) / "empty.sqlite3"
        database_url = f"sqlite:///{database.as_posix()}"
        _upgrade(database_url, "head")
        engine = create_engine(database_url)
        try:
            tables = set(inspect(engine).get_table_names())
            assert inspect(engine).get_table_names().count("alembic_version") == 1
            assert "learning_routes" in tables
            assert "route_command_receipts" in tables
            assert not RETIRED_TABLES.intersection(tables)
            with engine.connect() as connection:
                assert (
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20260928_0036"
                )
                assert (
                    connection.execute(
                        text("SELECT COUNT(*) FROM t44_cutover_manifests WHERE completed_at IS NOT NULL")
                    ).scalar_one()
                    == 1
                )
        finally:
            engine.dispose()


def test_0036_refuses_downgrade_with_mixed_test_data() -> None:
    with TemporaryDirectory(prefix="medical-qa-t48-no-downgrade-") as directory:
        database = Path(directory) / "mixed-gate.sqlite3"
        database_url = f"sqlite:///{database.as_posix()}"
        _upgrade(database_url, "head")
        with closing(sqlite3.connect(database)) as db:
            db.execute(
                "INSERT INTO route_final_tests (id, public_id, route_id, format_version) "
                "VALUES (1, '00000000-0000-4000-8000-000000000001', 1, 'mixed_v2')"
            )
            db.commit()
        result = _alembic(database_url, "downgrade", "20260927_0035")
        assert result.returncode != 0
        assert "Cannot downgrade: preserve mixed tests" in result.stdout + result.stderr
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("20260928_0036",)
            assert db.execute("SELECT format_version FROM route_final_tests WHERE id = 1").fetchone() == ("mixed_v2",)


def test_0034_rejects_new_route_data_without_persisting_an_empty_cutover_marker() -> None:
    with TemporaryDirectory(prefix="medical-qa-t44-new-route-gate-") as directory:
        database = Path(directory) / "route-gate.sqlite3"
        database_url = f"sqlite:///{database.as_posix()}"
        _upgrade(database_url, "20260926_0033")
        with closing(sqlite3.connect(database)) as db:
            db.execute(
                "INSERT INTO learning_routes "
                "(id, public_id, student_id, source_participation_id, session_id, completion_snapshot_id, "
                "source_kind, class_id, teacher_id, title, goal_point_codes, diagnosis_summary, generation_context, "
                "generation_state) VALUES (1, '00000000-0000-4000-8000-000000000001', 1, 1, 1, 1, "
                "'classroom', 1, 1, '冻结路由', '[]', '{}', '{}', 'pending')"
            )
            db.commit()
        result = _alembic(database_url, "upgrade", "20260926_0034")
        assert result.returncode != 0
        assert "new T44 data exists in learning_routes" in result.stdout + result.stderr
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260926_0033"
            assert db.execute("SELECT COUNT(*) FROM learning_routes").fetchone()[0] == 1
            assert db.execute("SELECT COUNT(*) FROM t44_cutover_manifests").fetchone()[0] == 0


def test_0034_downgrade_refuses_new_route_data_without_removing_it() -> None:
    with TemporaryDirectory(prefix="medical-qa-t44-no-downgrade-") as directory:
        database = Path(directory) / "route-data.sqlite3"
        database_url = f"sqlite:///{database.as_posix()}"
        _upgrade(database_url, "head")
        route_id = "00000000-0000-4000-8000-000000000002"
        with closing(sqlite3.connect(database)) as db:
            db.execute(
                "INSERT INTO learning_routes "
                "(id, public_id, student_id, source_participation_id, session_id, completion_snapshot_id, "
                "source_kind, class_id, teacher_id, title, goal_point_codes, diagnosis_summary, generation_context, "
                "generation_state) VALUES (1, ?, 1, 1, 1, 1, 'classroom', 1, 1, '保留路线', "
                "'[]', '{}', '{}', 'pending')",
                (route_id,),
            )
            db.commit()
        result = _alembic(database_url, "downgrade", "20260926_0033")
        assert result.returncode != 0
        assert "Cannot downgrade 0034 while new single-round learning data exists" in result.stdout + result.stderr
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260926_0034"
            assert db.execute("SELECT public_id FROM learning_routes WHERE id=1").fetchone()[0] == route_id
            assert (
                db.execute("SELECT COUNT(*) FROM t44_cutover_manifests WHERE completed_at IS NOT NULL").fetchone()[0]
                == 1
            )


def test_runtime_metadata_create_all_does_not_recreate_retired_tables() -> None:
    from app.bootstrap import model_registry  # noqa: F401
    from app.db import Base

    dangling_fks = [
        (table.name, foreign_key.target_fullname)
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
        if foreign_key.target_fullname.split(".")[0] in RETIRED_TABLES
    ]
    assert dangling_fks == []

    with TemporaryDirectory(prefix="medical-qa-t44-runtime-metadata-") as directory:
        engine = create_engine(f"sqlite:///{(Path(directory) / 'runtime.sqlite3').as_posix()}")
        try:
            Base.metadata.create_all(engine)
            tables = set(inspect(engine).get_table_names())
            assert RETIRED_TABLES.isdisjoint(tables)
            assert "learning_routes" in tables
            assert "pbl_sessions" in tables
        finally:
            engine.dispose()


def test_0033_detaches_legacy_question_bank_source_to_a_random_shared_uuid() -> None:
    with TemporaryDirectory(prefix="medical-qa-t44-bank-migration-") as directory:
        database = Path(directory) / "bank.sqlite3"
        database_url = f"sqlite:///{database.as_posix()}"
        _upgrade(database_url, "20260924_0032")
        with closing(sqlite3.connect(database)) as db:
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute("DROP TABLE bank_import_receipts")
            db.execute("DROP TABLE teacher_question_bank_revisions")
            db.execute(
                "CREATE TABLE teacher_question_bank_revisions ("
                "id INTEGER PRIMARY KEY, bank_item_id INTEGER NOT NULL, version INTEGER NOT NULL, "
                "source_package_item_id INTEGER NOT NULL REFERENCES classroom_package_items(id) ON DELETE RESTRICT, "
                "source_digest VARCHAR(64) NOT NULL, "
                "CONSTRAINT uq_teacher_bank_revision_version UNIQUE(bank_item_id, version))"
            )
            db.execute(
                "CREATE TABLE bank_import_receipts ("
                "id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, "
                "source_package_item_id INTEGER NOT NULL REFERENCES classroom_package_items(id) ON DELETE RESTRICT, "
                "source_digest VARCHAR(64) NOT NULL, client_request_id VARCHAR(100) NOT NULL, "
                "payload_digest VARCHAR(64) NOT NULL, bank_item_id INTEGER NOT NULL, "
                "CONSTRAINT uq_bank_import_source UNIQUE(teacher_id, source_package_item_id, source_digest), "
                "CONSTRAINT uq_bank_import_request UNIQUE(teacher_id, client_request_id))"
            )
            db.execute(
                "INSERT INTO teacher_question_bank_revisions "
                "(id, bank_item_id, version, source_package_item_id, source_digest) "
                "VALUES (1, 4, 1, 901, 'a' || printf('%063d', 0))"
            )
            db.execute(
                "INSERT INTO bank_import_receipts "
                "(id, teacher_id, source_package_item_id, source_digest, client_request_id, "
                "payload_digest, bank_item_id) "
                "VALUES (2, 1, 901, 'a' || printf('%063d', 0), 'request', 'b' || printf('%063d', 0), 4)"
            )
            db.commit()
        _upgrade(database_url, "20260926_0033")
        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                revisions = inspect(engine).get_columns("teacher_question_bank_revisions")
                receipts = inspect(engine).get_columns("bank_import_receipts")
                revision = connection.execute(
                    text(
                        "SELECT source_kind, source_public_id, source_package_item_id, source_digest "
                        "FROM teacher_question_bank_revisions"
                    )
                ).one()
                receipt = connection.execute(
                    text(
                        "SELECT source_kind, source_public_id, source_package_item_id, source_digest "
                        "FROM bank_import_receipts"
                    )
                ).one()
                assert revision.source_kind == receipt.source_kind == "legacy_detached"
                assert revision.source_public_id == receipt.source_public_id
                assert str(UUID(revision.source_public_id)) == revision.source_public_id
                assert revision.source_public_id != "901"
                assert revision.source_package_item_id == receipt.source_package_item_id == 901
                assert revision.source_digest == receipt.source_digest
                assert next(column for column in revisions if column["name"] == "source_package_item_id")["nullable"]
                assert next(column for column in receipts if column["name"] == "source_package_item_id")["nullable"]
                for table in ("teacher_question_bank_revisions", "bank_import_receipts"):
                    assert not any(
                        foreign["referred_table"] == "classroom_package_items"
                        for foreign in inspect(engine).get_foreign_keys(table)
                    )
        finally:
            engine.dispose()


def test_0034_refuses_uncleaned_rows_without_advancing_revision() -> None:
    with TemporaryDirectory(prefix="medical-qa-t44-gate-") as directory:
        database = Path(directory) / "gate.sqlite3"
        database_url = f"sqlite:///{database.as_posix()}"
        _upgrade(database_url, "20260926_0033")
        with closing(sqlite3.connect(database)) as db:
            db.execute(
                "INSERT INTO classroom_task_packages "
                "(student_id, class_id, session_id, completion_snapshot_id, teacher_id, status, version, "
                "diagnosis_outcome) "
                "VALUES (1, 2, 3, 4, 1, 'draft', 1, 'no_clear_gaps')"
            )
            db.commit()
        result = _alembic(database_url, "upgrade", "20260926_0034")
        assert result.returncode != 0
        assert "completed T44 cleanup manifest" in result.stdout + result.stderr
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260926_0033"
            assert db.execute("SELECT COUNT(*) FROM classroom_task_packages").fetchone()[0] == 1


def test_cleanup_rejects_an_unowned_apply_resource_without_modifying_it() -> None:
    with TemporaryDirectory(prefix="medical-qa-t44-unowned-") as directory:
        root = Path(directory)
        database = root / "unowned.sqlite3"
        with closing(sqlite3.connect(database)):
            pass
        before = _file_sha256(database)
        result = subprocess.run(
            [
                sys.executable,
                str(BACKEND / "scripts" / "cleanup_t44_learning.py"),
                "--database",
                str(database),
                "--apply",
                "--manifest",
                str(root / "manifest.json"),
                "--confirm-development",
                "--backup",
                str(root / "backup.sqlite3"),
                "--expected-manifest-digest",
                "0" * 64,
            ],
            cwd=BACKEND,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2
        assert "does not match the verified managed resource" in result.stderr
        assert _file_sha256(database) == before
        assert not (root / "backup.sqlite3").exists()


def test_cleanup_rejects_a_managed_resource_when_application_environment_is_production() -> None:
    resource = create_managed_database("t44-production-mode")
    try:
        _upgrade(resource.url, "20260924_0032")
        _upgrade(resource.url, "20260926_0033")
        before = _file_sha256(resource.database_path)
        env = os.environ.copy()
        env.update(
            {
                "APP_ENV": "production",
                "TEST_RESOURCE_DIR": str(resource.root),
                "TEST_RESOURCE_TOKEN": resource.token,
            }
        )
        result = _cleanup_command(
            env,
            resource.database_path,
            resource.root / "manifest.json",
            apply=True,
            backup=resource.root / "backup.sqlite3",
            expected_digest="0" * 64,
        )
        assert result.returncode == 2
        assert "Production databases are not supported" in result.stderr
        assert _file_sha256(resource.database_path) == before
        assert not (resource.root / "backup.sqlite3").exists()
    finally:
        cleanup_managed_database(resource)


def test_cleanup_requires_a_readable_0032_baseline_backup() -> None:
    resource = create_managed_database("t44-missing-baseline")
    try:
        database = resource.database_path
        _upgrade(resource.url, "20260924_0032")
        _upgrade(resource.url, "20260926_0033")
        manifest = resource.root / "cutover-manifest.json"
        missing_baseline = resource.root / "missing-baseline-0032.sqlite3"
        env = os.environ.copy()
        env.update(
            {
                "APP_ENV": "test",
                "TEST_RESOURCE_DIR": str(resource.root),
                "TEST_RESOURCE_TOKEN": resource.token,
            }
        )
        before = _file_sha256(database)
        result = _cleanup_command(env, database, manifest, baseline=missing_baseline)
        assert result.returncode == 2
        assert "B0 baseline must be an existing absolute SQLite file" in result.stderr
        assert _file_sha256(database) == before
        assert not manifest.exists()
    finally:
        cleanup_managed_database(resource)


def test_cleanup_refuses_a_retained_foreign_key_into_the_frozen_target_closure() -> None:
    resource = create_managed_database("t44-retained-cross-reference")
    try:
        database = resource.database_path
        _upgrade(resource.url, "20260924_0032")
        _seed_target_session(database)
        baseline = resource.root / "baseline-0032.sqlite3"
        _sqlite_backup(database, baseline)
        _upgrade(resource.url, "20260926_0033")
        engine = create_engine(resource.url)
        try:
            _seed_case_dependency_graph(engine, retained_task_points_into_target=True)
        finally:
            engine.dispose()

        env = os.environ.copy()
        env.update(
            {
                "APP_ENV": "test",
                "TEST_RESOURCE_DIR": str(resource.root),
                "TEST_RESOURCE_TOKEN": resource.token,
            }
        )
        manifest = resource.root / "blocked-cutover-manifest.json"
        dry_run = _cleanup_command(env, database, manifest, baseline=baseline)
        assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
        plan = json.loads(dry_run.stdout)
        assert "retained_fk:learning_tasks.source_attempt_id->case_attempts" in plan["blockers"]
        before = _file_sha256(database)
        apply = _cleanup_command(
            env,
            database,
            manifest,
            apply=True,
            backup=resource.root / "blocked-maintenance.sqlite3",
            expected_digest=plan["manifest_digest"],
        )
        assert apply.returncode == 2
        assert "Cutoff has unresolved blockers" in apply.stderr
        assert _file_sha256(database) == before
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("SELECT COUNT(*) FROM pbl_sessions WHERE id=50").fetchone()[0] == 1
            assert db.execute("SELECT COUNT(*) FROM case_attempts WHERE id=300").fetchone()[0] == 1
            assert db.execute("SELECT COUNT(*) FROM learning_tasks WHERE id=220").fetchone()[0] == 1
            assert (
                db.execute("SELECT COUNT(*) FROM t44_cutover_manifests WHERE completed_at IS NOT NULL").fetchone()[0]
                == 0
            )
    finally:
        cleanup_managed_database(resource)


def test_cleanup_cutoff_apply_preserves_identity_and_restorable_backups() -> None:
    resource = create_managed_database("t44-cleanup")
    try:
        database = resource.database_path
        database_url = resource.url
        _upgrade(database_url, "20260924_0032")
        _seed_target_session(database)
        baseline = resource.root / "baseline-0032.sqlite3"
        _sqlite_backup(database, baseline)
        _upgrade(database_url, "20260926_0033")
        case_engine = create_engine(database_url)
        try:
            _seed_case_dependency_graph(case_engine)
        finally:
            case_engine.dispose()
        bank_source_id = "00000000-0000-4000-8000-000000000050"
        with closing(sqlite3.connect(database)) as db:
            db.execute(
                "INSERT INTO student_notifications "
                "(id, student_id, type, entity_type, entity_id, entity_public_id, title, body, dedupe_key) "
                "VALUES (100, 2, 'pbl_completed', 'pbl_session', 50, "
                "'00000000-0000-4000-8000-000000000050', '清理目标通知', '仅用于删除测试', 'target-pbl-notice')"
            )
            db.execute(
                "INSERT INTO student_notifications "
                "(id, student_id, type, entity_type, entity_id, entity_public_id, title, body, dedupe_key) "
                "VALUES (101, 2, 'learning_ready', 'learning_plan', 50, "
                "'00000000-0000-4000-8000-000000000050', '保留通知', '不关联PBL session', 'retained-plan-notice')"
            )
            for event_id, source_type in ((110, "self_pbl_completion"), (111, "case_assessment")):
                db.execute(
                    "INSERT INTO learning_evidence_events "
                    "(id, student_id, source_type, source_id, source_version, authority_level, visibility_scope, "
                    "event_kind, occurred_at, dedupe_key, contract_version) "
                    "VALUES (?, 2, ?, '50', 1, 'verified', 'student_only', 'completed', "
                    "'2026-09-27T00:00:00+00:00', ?, 1)",
                    (event_id, source_type, f"typed-source-{event_id}"),
                )
            db.execute(
                "INSERT INTO learning_evidence_metrics "
                "(id, event_id, metric_kind, metric_code, normalized_score, result, evidence_present) "
                "VALUES (120, 110, 'completion', 'pbl.complete', 100, 'completed', 1)"
            )
            db.execute(
                "INSERT INTO teacher_question_bank_items "
                "(id, owner_teacher_id, status, version, current_revision_id) VALUES (130, 1, 'active', 1, 131)"
            )
            db.execute(
                "INSERT INTO teacher_question_bank_revisions "
                "(id, bank_item_id, version, task_type, title, prompt, options, answer, explanation, point_codes, "
                "dimension_ids, source_kind, source_public_id, source_package_item_id, source_digest, medical_status) "
                "VALUES (131, 130, 1, 'retest', '保留副本', '独立题库题干', '[\"选项一\",\"选项二\"]', "
                "'{\"correct_option\":0}', '解析', '[\"pathology.cell-injury\"]', '[]', "
                "'route_test_question', ?, NULL, ?, 'released')",
                (bank_source_id, "a" * 64),
            )
            db.execute(
                "INSERT INTO bank_import_receipts "
                "(id, teacher_id, source_kind, source_public_id, source_package_item_id, source_digest, "
                "client_request_id, payload_digest, bank_item_id) "
                "VALUES (132, 1, 'route_test_question', ?, NULL, ?, 'retained-import', ?, 130)",
                (bank_source_id, "a" * 64, "b" * 64),
            )
            db.commit()
        with closing(sqlite3.connect(database)) as db:
            knowledge_before = _knowledge_graph_rows(db)
            assert dict(knowledge_before)["knowledge_catalogs"]
            assert dict(knowledge_before)["knowledge_study_materials"]
            assert dict(knowledge_before)["knowledge_point_sources"]
            manual_card_before = db.execute(
                "SELECT id, point_code, version, prompt, options, correct_option, status, source_type, "
                "source_snapshot_id FROM knowledge_card_contributions WHERE id=450"
            ).fetchone()
            assert manual_card_before is not None
        manifest_path = resource.root / "cutover-manifest.json"
        backup_path = resource.root / "maintenance-0033.sqlite3"
        env = os.environ.copy()
        env.update(
            {
                "APP_ENV": "test",
                "TEST_RESOURCE_DIR": str(resource.root),
                "TEST_RESOURCE_TOKEN": resource.token,
            }
        )
        database_before_dry_run = _file_sha256(database)
        dry_run = _cleanup_command(env, database, manifest_path, baseline=baseline)
        assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
        dry = json.loads(dry_run.stdout)
        assert dry["counts"]["pbl_sessions"] == 1
        assert dry["counts"]["pbl_participations"] == 1
        assert dry["counts"]["pbl_diagnostic_snapshots"] == 1
        assert "保密回答只作删除验证" not in manifest_path.read_text(encoding="utf-8")
        assert dry["writes_to_database"] == 0
        assert _file_sha256(database) == database_before_dry_run
        database_before_rejected_apply = _file_sha256(database)
        original_manifest = manifest_path.read_bytes()
        manifest_path.write_bytes(original_manifest.replace(dry["manifest_digest"].encode("ascii"), b"0" * 64, 1))
        tampered = _cleanup_command(
            env,
            database,
            manifest_path,
            apply=True,
            backup=resource.root / "tampered-backup.sqlite3",
            expected_digest=dry["manifest_digest"],
        )
        assert tampered.returncode == 2
        assert "Manifest digest does not match" in tampered.stderr
        assert _file_sha256(database) == database_before_rejected_apply
        assert not (resource.root / "tampered-backup.sqlite3").exists()
        manifest_path.write_bytes(original_manifest)

        # Force a failure after closure pointers have been cleared. All row
        # changes and the completion marker must roll back together.
        with closing(sqlite3.connect(database)) as db:
            db.execute(
                "CREATE TRIGGER t44_test_fail_mid_cleanup BEFORE DELETE ON pbl_messages "
                "BEGIN SELECT RAISE(ABORT, 'injected cleanup failure'); END"
            )
            db.commit()
        failed_manifest = resource.root / "failed-cutover-manifest.json"
        failed_dry_run = _cleanup_command(env, database, failed_manifest, baseline=baseline)
        assert failed_dry_run.returncode == 0, failed_dry_run.stdout + failed_dry_run.stderr
        failed_plan = json.loads(failed_dry_run.stdout)
        failed_apply = _cleanup_command(
            env,
            database,
            failed_manifest,
            apply=True,
            backup=resource.root / "failed-maintenance.sqlite3",
            expected_digest=failed_plan["manifest_digest"],
        )
        assert failed_apply.returncode == 2
        assert '"reason": "integrity constraint failure"' in failed_apply.stderr
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("SELECT COUNT(*) FROM pbl_sessions WHERE id=50").fetchone()[0] == 1
            assert db.execute("SELECT completion_snapshot_id FROM pbl_participations WHERE id=60").fetchone()[0] == 70
            assert db.execute("SELECT COUNT(*) FROM pbl_messages WHERE id=80").fetchone()[0] == 1
            assert (
                db.execute("SELECT COUNT(*) FROM t44_cutover_manifests WHERE completed_at IS NOT NULL").fetchone()[0]
                == 0
            )
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            db.execute("DROP TRIGGER t44_test_fail_mid_cleanup")
            db.commit()

        # Dropping the test trigger changes the schema fingerprint, so freeze
        # a new manifest for the valid apply.
        manifest_path.unlink()
        dry_run = _cleanup_command(env, database, manifest_path, baseline=baseline)
        assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
        dry = json.loads(dry_run.stdout)
        apply = _cleanup_command(
            env,
            database,
            manifest_path,
            apply=True,
            backup=backup_path,
            expected_digest=dry["manifest_digest"],
        )
        assert apply.returncode == 0, apply.stdout + apply.stderr
        with closing(sqlite3.connect(backup_path)) as before_cleanup:
            assert before_cleanup.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert before_cleanup.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260926_0033"
            assert before_cleanup.execute("SELECT COUNT(*) FROM pbl_sessions").fetchone()[0] == 1
        restored = resource.root / "restored-b1.sqlite3"
        _sqlite_backup(backup_path, restored)
        with closing(sqlite3.connect(restored)) as restored_db:
            assert restored_db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260926_0033"
        with closing(sqlite3.connect(database)) as db:
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            assert _knowledge_graph_rows(db) == knowledge_before
            assert (
                db.execute(
                    "SELECT id, point_code, version, prompt, options, correct_option, status, source_type, "
                    "source_snapshot_id FROM knowledge_card_contributions WHERE id=450"
                ).fetchone()
                == manual_card_before
            )
            assert db.execute("SELECT COUNT(*) FROM pbl_sessions").fetchone()[0] == 0
            assert db.execute("SELECT COUNT(*) FROM pbl_participations").fetchone()[0] == 0
            assert db.execute("SELECT COUNT(*) FROM pbl_diagnostic_snapshots").fetchone()[0] == 0
            assert db.execute("SELECT COUNT(*) FROM pbl_messages").fetchone()[0] == 0
            assert db.execute("SELECT COUNT(*) FROM pbl_private_follow_up_results").fetchone()[0] == 0
            assert db.execute("SELECT COUNT(*) FROM student_notifications WHERE id=100").fetchone()[0] == 0
            assert (
                db.execute(
                    "SELECT COUNT(*) FROM student_notifications "
                    "WHERE id=101 AND entity_type='learning_plan' AND entity_id=50"
                ).fetchone()[0]
                == 1
            )
            assert db.execute("SELECT COUNT(*) FROM learning_evidence_events WHERE id=110").fetchone()[0] == 0
            assert db.execute(
                "SELECT source_type, source_id FROM learning_evidence_events WHERE id=111"
            ).fetchone() == ("case_assessment", "50")
            assert db.execute("SELECT COUNT(*) FROM learning_evidence_metrics WHERE id=120").fetchone()[0] == 0
            assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
            assert db.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 1
            assert db.execute("SELECT COUNT(*) FROM class_members").fetchone()[0] == 1
            assert (
                db.execute("SELECT max_id FROM t44_legacy_id_high_water WHERE table_name = 'pbl_sessions'").fetchone()[
                    0
                ]
                == 50
            )
            marker = db.execute(
                "SELECT completed_at, target_ids FROM t44_cutover_manifests WHERE completed_at IS NOT NULL"
            ).fetchone()
            assert marker[0]
            assert json.loads(marker[1])["sessions"] == [50]
            assert db.execute("SELECT id FROM problems ORDER BY id").fetchall() == [(140,)]
            assert db.execute("SELECT id, learning_task_id FROM case_attempts ORDER BY id").fetchall() == [(310, 211)]
            assert db.execute("SELECT id, attempt_id FROM case_assessments ORDER BY id").fetchall() == [(311, 310)]
            assert db.execute("SELECT id, source_assessment_id FROM learning_plans ORDER BY id").fetchall() == [
                (210, 311)
            ]
            assert db.execute("SELECT id, source_attempt_id FROM learning_tasks ORDER BY id").fetchall() == [(211, 310)]
            assert db.execute("SELECT id, plan_id FROM learning_plan_evaluations ORDER BY id").fetchall() == [
                (212, 210)
            ]
            for table, target_id in (
                ("case_attempts", 300),
                ("case_assessments", 301),
                ("learning_plans", 200),
                ("learning_plans", 202),
                ("learning_tasks", 201),
                ("learning_plan_evaluations", 203),
            ):
                assert db.execute(f"SELECT COUNT(*) FROM {table} WHERE id=?", (target_id,)).fetchone()[0] == 0

        # The same frozen token is a no-op replay and cannot reselect rows.
        replay = subprocess.run(
            [
                sys.executable,
                str(BACKEND / "scripts" / "cleanup_t44_learning.py"),
                "--database",
                str(database),
                "--apply",
                "--manifest",
                str(manifest_path),
                "--confirm-development",
                "--backup",
                str(resource.root / "must-not-be-created.sqlite3"),
                "--expected-manifest-digest",
                dry["manifest_digest"],
            ],
            cwd=BACKEND,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert replay.returncode == 0, replay.stdout + replay.stderr
        assert json.loads(replay.stdout)["mode"] == "already_applied"
        assert not (resource.root / "must-not-be-created.sqlite3").exists()

        _upgrade(database_url, "20260926_0034")
        engine = create_engine(database_url)
        try:
            tables = set(inspect(engine).get_table_names())
            assert "study_paths" not in tables
            assert "classroom_task_packages" not in tables
            assert "pbl_question_suggestions" not in tables
            assert "pbl_private_follow_up_results" in tables
            assert "pbl_sessions" in tables
            assert "source_package_item_id" not in {
                column["name"] for column in inspect(engine).get_columns("teacher_question_bank_revisions")
            }
            checks = {item["name"]: item["sqltext"] for item in inspect(engine).get_check_constraints("pbl_sessions")}
            assert checks["ck_pbl_session_ai_schema_version"].endswith("ai_schema_version = 8")
            with engine.connect() as connection:
                assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 2
                assert connection.execute(text("SELECT COUNT(*) FROM classes")).scalar_one() == 1
                assert connection.execute(text("SELECT COUNT(*) FROM problems WHERE id=140")).scalar_one() == 1
                assert (
                    connection.execute(text("SELECT learning_task_id FROM case_attempts WHERE id=310")).scalar_one()
                    == 211
                )
                assert (
                    connection.execute(
                        text("SELECT source_assessment_id FROM learning_plans WHERE id=210")
                    ).scalar_one()
                    == 311
                )
                assert (
                    connection.execute(text("SELECT source_attempt_id FROM learning_tasks WHERE id=211")).scalar_one()
                    == 310
                )
                assert (
                    connection.execute(text("SELECT plan_id FROM learning_plan_evaluations WHERE id=212")).scalar_one()
                    == 210
                )
                assert connection.execute(text("SELECT COUNT(*) FROM case_attempts WHERE id=300")).scalar_one() == 0
                assert connection.execute(text("SELECT COUNT(*) FROM case_assessments WHERE id=301")).scalar_one() == 0
                assert (
                    connection.execute(text("SELECT COUNT(*) FROM learning_plans WHERE id IN (200, 202)")).scalar_one()
                    == 0
                )
                assert connection.execute(text("SELECT COUNT(*) FROM learning_tasks WHERE id=201")).scalar_one() == 0
                assert (
                    connection.execute(text("SELECT COUNT(*) FROM learning_plan_evaluations WHERE id=203")).scalar_one()
                    == 0
                )
                retained_question = connection.execute(
                    text(
                        "SELECT r.prompt, r.version, r.source_kind, r.source_public_id, i.status "
                        "FROM teacher_question_bank_revisions r JOIN teacher_question_bank_items i "
                        "ON i.id = r.bank_item_id WHERE r.id = 131"
                    )
                ).one()
                assert retained_question == (
                    "独立题库题干",
                    1,
                    "route_test_question",
                    bank_source_id,
                    "active",
                )
                assert (
                    connection.execute(
                        text("SELECT source_public_id FROM bank_import_receipts WHERE id = 132")
                    ).scalar_one()
                    == bank_source_id
                )
        finally:
            engine.dispose()
    finally:
        cleanup_managed_database(resource)
