import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def run_alembic(cwd: Path, database_url: str, *command: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *command],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_0028_persists_a_reproducible_evidence_linked_knowledge_graph() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t38-knowledge-graph-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'knowledge-graph.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260914_0027")
        engine = create_engine(database_url)
        try:
            run_alembic(cwd, database_url, "upgrade", "20260924_0032")

            def fingerprint() -> tuple[tuple[object, ...], ...]:
                with engine.connect() as connection:
                    return tuple(
                        connection.execute(
                            text(
                                "SELECT source.code, target.code, dependency.relation_kind, dependency.confidence "
                                "FROM knowledge_dependencies dependency "
                                "JOIN knowledge_points source ON source.id = dependency.prerequisite_point_id "
                                "JOIN knowledge_points target ON target.id = dependency.dependent_point_id "
                                "ORDER BY dependency.position"
                            )
                        ).all()
                    )

            first_fingerprint = fingerprint()
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260924_0032"
                objectives = connection.execute(
                    text("SELECT learning_objectives FROM knowledge_study_materials ORDER BY id")
                ).scalars()
                assert all(len(json.loads(value)) >= 2 for value in objectives)
                assert connection.execute(
                    text("SELECT version, status, evidence_status, medical_review_status FROM knowledge_catalogs")
                ).one() == (
                    "pathology-general-v4",
                    "active",
                    "source_supported",
                    "pending_expert_review",
                )
                assert {
                    table: connection.scalar(text(f"SELECT COUNT(*) FROM {table}"))
                    for table in (
                        "knowledge_modules",
                        "knowledge_points",
                        "knowledge_study_materials",
                        "knowledge_dependencies",
                        "knowledge_sources",
                    )
                } == {
                    "knowledge_modules": 5,
                    "knowledge_points": 30,
                    "knowledge_study_materials": 30,
                    "knowledge_dependencies": 34,
                    "knowledge_sources": 14,
                }
                point_id = connection.scalar(
                    text("SELECT id FROM knowledge_points WHERE code = 'pathology.cell-injury.necrosis'")
                )
                catalog_id = connection.scalar(text("SELECT id FROM knowledge_catalogs"))
                with pytest.raises(IntegrityError):
                    connection.execute(
                        text(
                            "INSERT INTO knowledge_dependencies "
                            "(catalog_id, prerequisite_point_id, dependent_point_id, relation_kind, rationale, "
                            "limitation, confidence, evidence_status, medical_review_status, position) VALUES "
                            "(:catalog, :point, :point, 'mechanistic_basis', 'invalid', 'invalid', 'high', "
                            "'source_supported', 'pending_expert_review', 999)"
                        ),
                        {"catalog": catalog_id, "point": point_id},
                    )

            assert len(first_fingerprint) == 34
            assert (
                "pathology.inflammation.chronic",
                "pathology.repair.fibrosis",
                "mechanistic_basis",
                "high",
            ) in first_fingerprint
            run_alembic(cwd, database_url, "downgrade", "20260914_0027")
            assert "knowledge_catalogs" not in set(inspect(engine).get_table_names())
            run_alembic(cwd, database_url, "upgrade", "20260924_0032")
            assert fingerprint() == first_fingerprint
        finally:
            engine.dispose()


def test_0029_refuses_downgrade_after_learning_objectives_are_edited() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t39-learning-objectives-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'learning-objectives.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260917_0029")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE knowledge_study_materials SET learning_objectives = :objectives "
                        "WHERE id = (SELECT id FROM knowledge_study_materials ORDER BY id LIMIT 1)"
                    ),
                    {"objectives": json.dumps(["课程负责人修订目标一", "课程负责人修订目标二"], ensure_ascii=False)},
                )
            environment = os.environ.copy()
            environment["DATABASE_URL"] = database_url
            attempted = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "20260916_0028"],
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert attempted.returncode != 0
            assert "learning objectives contain edited data" in attempted.stdout + attempted.stderr
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260917_0029"
        finally:
            engine.dispose()


def test_0030_refuses_downgrade_after_ai_knowledge_card_is_persisted() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t40-ai-card-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'ai-card.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260919_0030")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (9001, 't40-migration-teacher', 'teacher', 'teacher', '', '[]', '[]'), "
                        "(9002, 't40-migration-student', 'student', 'student', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO knowledge_card_contributions "
                        "(point_code, owner_id, class_code, version, card_type, prompt, options, explanation, "
                        "reference, status, review_comment, source_type, source_snapshot_id, source_position, "
                        "source_finding_ids, "
                        "origin_student_id, origin_student_name, target_student_ids) VALUES "
                        "('pathology.inflammation.vascular', 9001, 't40', 1, 'recall', 'prompt', '[]', "
                        "'explanation', '', 'draft', '', 'pbl_ai', 1, 0, '[\"gap\"]', 9002, 'student', '[9002]')"
                    )
                )
            environment = os.environ.copy()
            environment["DATABASE_URL"] = database_url
            attempted = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "20260917_0029"],
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert attempted.returncode != 0
            assert "AI knowledge card data exists" in attempted.stdout + attempted.stderr
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260919_0030"
        finally:
            engine.dispose()


def test_0028_refuses_downgrade_after_expert_review_state_changes() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t38-reviewed-knowledge-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'reviewed-knowledge.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260916_0028")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE knowledge_dependencies SET medical_review_status = 'expert_reviewed' "
                        "WHERE id = (SELECT id FROM knowledge_dependencies ORDER BY position LIMIT 1)"
                    )
                )
            environment = os.environ.copy()
            environment["DATABASE_URL"] = database_url
            attempted = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "20260914_0027"],
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert attempted.returncode != 0
            assert "reviewed knowledge dependencies exist" in attempted.stdout + attempted.stderr
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260916_0028"
                assert connection.scalar(text("SELECT COUNT(*) FROM knowledge_dependencies")) == 34
        finally:
            engine.dispose()


def test_0028_scopes_stable_point_codes_to_a_catalog_version() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t38-versioned-points-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'versioned-points.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260914_0027")
        run_alembic(cwd, database_url, "upgrade", "20260916_0028")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO knowledge_catalogs "
                        "(version, label, status, reference_note, evidence_status, medical_review_status) "
                        "VALUES ('archive-test', '历史目录', 'archived', '测试', "
                        "'source_supported', 'pending_expert_review')"
                    )
                )
                archived_id = connection.scalar(
                    text("SELECT id FROM knowledge_catalogs WHERE version = 'archive-test'")
                )
                connection.execute(
                    text(
                        "INSERT INTO knowledge_modules (catalog_id, code, label, description, position) "
                        "VALUES (:catalog, 'pathology.cell-injury', '历史模块', '测试', 1)"
                    ),
                    {"catalog": archived_id},
                )
                archived_module = connection.scalar(
                    text("SELECT id FROM knowledge_modules WHERE catalog_id = :catalog"), {"catalog": archived_id}
                )
                connection.execute(
                    text(
                        "INSERT INTO knowledge_points "
                        "(catalog_id, module_id, code, title, objective, description, case_slug, position, "
                        "evidence_status, medical_review_status) "
                        "VALUES (:catalog, :module, 'pathology.cell-injury.adaptation', '历史标题', "
                        "'测试', '测试', 'archived-case', 1, 'source_supported', 'pending_expert_review')"
                    ),
                    {"catalog": archived_id, "module": archived_module},
                )
            with engine.connect() as connection:
                assert (
                    connection.scalar(
                        text("SELECT COUNT(*) FROM knowledge_points WHERE code = 'pathology.cell-injury.adaptation'")
                    )
                    == 2
                )
                assert (
                    connection.scalar(
                        text(
                            "SELECT p.title FROM knowledge_points p JOIN knowledge_catalogs c ON c.id = p.catalog_id "
                            "WHERE p.code = 'pathology.cell-injury.adaptation' AND c.status = 'active'"
                        )
                    )
                    == "细胞适应"
                )
                with pytest.raises(IntegrityError):
                    connection.execute(
                        text(
                            "INSERT INTO knowledge_points "
                            "(catalog_id, module_id, code, title, objective, description, case_slug, position, "
                            "evidence_status, medical_review_status) "
                            "VALUES (:catalog, :module, 'pathology.cell-injury.adaptation', '重复标题', "
                            "'测试', '测试', 'duplicate', 2, 'source_supported', 'pending_expert_review')"
                        ),
                        {"catalog": archived_id, "module": archived_module},
                    )
        finally:
            engine.dispose()


def seed_0026_completed_pbl(connection, *, include_messages: bool = True) -> None:
    connection.execute(
        text(
            "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
            "VALUES (1, 't32-student', 'student', 'fixture', '', '[]', '[]')"
        )
    )
    connection.execute(
        text(
            "INSERT INTO pbl_sessions (id, topic_code, provider, status, goal_point_codes, phase, version, "
            "session_kind, created_by_student_id, client_session_id) "
            "VALUES (1, 'pathology.inflammation', 'disabled', 'active', '[]', 'synthesis', 1, "
            "'student_initiated', 1, 't32-migration')"
        )
    )
    connection.execute(
        text(
            "INSERT INTO pbl_participations "
            "(id, session_id, student_id, revision, current_phase, phase_started_revision, phase_status, "
            "phase_completed_at, interaction_style) "
            "VALUES (1, 1, 1, 4, 'completed', 4, 'completed', CURRENT_TIMESTAMP, 'guided')"
        )
    )
    connection.execute(
        text(
            "INSERT INTO pbl_diagnostic_snapshots "
            "(id, participation_id, revision, status, interaction_style, schema_version, phase, phase_decision, "
            "phase_evidence_message_ids, phase_evidence_summary, phase_missing_elements, safety_notice, "
            "safety_status, assistant_reply, knowledge_gaps, reasoning_issues, provider_metadata) "
            "VALUES (1, 1, 4, 'ready', 'guided', 5, 'synthesis', 'complete', '[\"1\"]', "
            "'fixture evidence', '[]', 'teaching only', 'educational', 'fixture completion reply', "
            "'[]', '[]', '{}')"
        )
    )
    if include_messages:
        connection.execute(
            text(
                "INSERT INTO pbl_messages "
                "(id, participation_id, sequence, role, content, interaction_style, request_revision, "
                "processing_status, result_snapshot_id, client_message_id) VALUES "
                "(1, 1, 1, 'student', 'fixture synthesis', 'guided', 4, 'completed', 1, 't32-final'), "
                "(2, 1, 2, 'assistant', 'fixture completion reply', 'guided', NULL, 'completed', NULL, NULL)"
            )
        )


def test_0027_backfills_completion_boundary_and_protects_private_downgrade() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t32-migration-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'private-follow-up.db').as_posix()}"
        # Migration 0001 intentionally uses current metadata for a brand-new SQLite
        # database. Round-trip through 0027 so this fixture has the exact 0026 schema.
        run_alembic(cwd, database_url, "upgrade", "20260914_0027")
        run_alembic(cwd, database_url, "downgrade", "20260914_0026")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                seed_0026_completed_pbl(connection)
            run_alembic(cwd, database_url, "upgrade", "20260914_0027")
            with engine.connect() as connection:
                assert connection.execute(
                    text(
                        "SELECT completion_snapshot_id, evidence_completed_revision "
                        "FROM pbl_participations WHERE id = 1"
                    )
                ).one() == (1, 4)
                assert connection.execute(
                    text("SELECT turn_scope, reply_to_message_id FROM pbl_messages ORDER BY id")
                ).all() == [("evidence", None), ("evidence", 1)]
            run_alembic(cwd, database_url, "downgrade", "20260914_0026")
            assert "turn_scope" not in {column["name"] for column in inspect(engine).get_columns("pbl_messages")}

            run_alembic(cwd, database_url, "upgrade", "20260914_0027")
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO pbl_messages "
                        "(id, participation_id, sequence, role, content, interaction_style, turn_scope, "
                        "request_revision, processing_status, client_message_id) VALUES "
                        "(3, 1, 3, 'student', 'private question', 'direct', 'private_follow_up', 4, "
                        "'completed', 'private-1'), (4, 1, 4, 'assistant', 'private reply', 'direct', "
                        "'private_follow_up', NULL, 'completed', NULL)"
                    )
                )
                connection.execute(text("UPDATE pbl_messages SET reply_to_message_id = 3 WHERE id = 4"))
                connection.execute(
                    text(
                        "INSERT INTO pbl_private_follow_up_results "
                        "(participation_id, student_message_id, assistant_message_id, interaction_style, "
                        "processing_status, safety_status, provider_name, fallback_used) "
                        "VALUES (1, 3, 4, 'direct', 'completed', 'normal', 'disabled', 0)"
                    )
                )
            with pytest.raises(AssertionError, match="private follow-up data exists"):
                run_alembic(cwd, database_url, "downgrade", "20260914_0026")
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260914_0027"
                assert connection.scalar(text("SELECT COUNT(*) FROM pbl_private_follow_up_results")) == 1
        finally:
            engine.dispose()


def test_0027_rejects_unlocatable_completion_without_partial_schema() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t32-invalid-migration-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'invalid-completion.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260914_0027")
        run_alembic(cwd, database_url, "downgrade", "20260914_0026")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                seed_0026_completed_pbl(connection, include_messages=False)
            with pytest.raises(AssertionError, match="cannot uniquely locate the message"):
                run_alembic(cwd, database_url, "upgrade", "20260914_0027")
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260914_0026"
            assert "completion_snapshot_id" not in {
                column["name"] for column in inspect(engine).get_columns("pbl_participations")
            }
            assert "turn_scope" not in {column["name"] for column in inspect(engine).get_columns("pbl_messages")}
        finally:
            engine.dispose()


@pytest.mark.parametrize("style", ["guided", "direct"])
def test_0026_backfill_and_lossless_downgrade(style):
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t31-migration-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'turns.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260914_0026")
        run_alembic(cwd, database_url, "downgrade", "20260913_0025")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't31-student', 'student', 'fixture', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_sessions (id, topic_code, provider, status, goal_point_codes, phase, version, "
                        "session_kind, created_by_student_id, client_session_id) "
                        "VALUES (1, 'pathology.inflammation', 'disabled', "
                        "'active', '[]', 'problem_framing', 1, 'student_initiated', 1, 't31-migration')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_participations (id, session_id, student_id, revision, interaction_style) "
                        "VALUES (1, 1, 1, 1, :style)"
                    ),
                    {"style": style},
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_messages (participation_id, sequence, role, content, request_revision) "
                        "VALUES (1, 1, 'student', 'synthetic preserved content', 1)"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_diagnostic_snapshots (participation_id, revision, status, assistant_reply, "
                        "knowledge_gaps, reasoning_issues, provider_metadata) "
                        "VALUES (1, 1, 'unavailable', 'synthetic preserved reply', '[]', '[]', '{}')"
                    )
                )
            run_alembic(cwd, database_url, "upgrade", "20260914_0026")
            for table in ("pbl_messages", "pbl_diagnostic_snapshots"):
                with engine.connect() as connection:
                    assert connection.scalar(text(f"SELECT interaction_style FROM {table}")) == style
            run_alembic(cwd, database_url, "downgrade", "20260913_0025")
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT content FROM pbl_messages")) == "synthetic preserved content"
            run_alembic(cwd, database_url, "upgrade", "20260914_0026")
            other = "direct" if style == "guided" else "guided"
            with engine.begin() as connection:
                connection.execute(text("UPDATE pbl_messages SET interaction_style = :style"), {"style": other})
            with pytest.raises(AssertionError, match="T31 mixed or inconsistent"):
                run_alembic(cwd, database_url, "downgrade", "20260913_0025")
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260914_0026"
                assert connection.scalar(text("SELECT interaction_style FROM pbl_messages")) == other
        finally:
            engine.dispose()


def test_0005_upgrades_legacy_members_and_downgrade_preserves_data() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-migration-") as directory:
        db_path = Path(directory) / "legacy.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260823_0004")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 'migration-teacher', 'teacher', '教师', '', '[]', '[]'), "
                        "(2, 'migration-student', 'student', '学生', '', '[\"legacy-code\"]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO classes (id, name, code, teacher_id, status) "
                        "VALUES (1, '兼容班', 'legacy-code', 1, 'active')"
                    )
                )
            run_alembic(cwd, database_url, "upgrade", "20260830_0008")
            with engine.connect() as connection:
                assert connection.execute(text("SELECT COUNT(*) FROM class_members")).scalar_one() == 1
            for table in ("conversations", "reports"):
                names = {index["name"] for index in inspect(engine).get_indexes(table)}
                assert f"ix_{table}_updated_id" in names
                assert f"ix_{table}_student_updated_id" in names
            run_alembic(cwd, database_url, "downgrade", "20260828_0007")
            for table in ("conversations", "reports"):
                names = {index["name"] for index in inspect(engine).get_indexes(table)}
                assert f"ix_{table}_updated_id" not in names
                assert f"ix_{table}_student_updated_id" not in names
            run_alembic(cwd, database_url, "upgrade", "20260830_0008")
            run_alembic(cwd, database_url, "downgrade", "20260823_0004")
            with engine.connect() as connection:
                assert connection.execute(text("SELECT COUNT(*) FROM class_members")).scalar_one() == 1
        finally:
            engine.dispose()


def test_0023_upgrades_empty_and_0008_databases() -> None:
    """Exercise the historical 0023 target and its 0008 downgrade round-trip."""
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-migration-head-") as directory:
        db_path = Path(directory) / "head.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260909_0023")
        engine = create_engine(database_url)
        try:
            inspector = inspect(engine)
            assert "reviewer_id" in {column["name"] for column in inspector.get_columns("reports")}
            assert "auth_provider" in {column["name"] for column in inspector.get_columns("users")}
            assert "ix_reports_reviewer_id" in {index["name"] for index in inspector.get_indexes("reports")}
            assert "ix_users_auth_provider" in {index["name"] for index in inspector.get_indexes("users")}
            assert {"case_id", "goal_point_codes", "phase", "version"} <= {
                column["name"] for column in inspector.get_columns("pbl_sessions")
            }
            assert {"source_type", "source_id", "verification_status", "version"} <= {
                column["name"] for column in inspector.get_columns("learning_plans")
            }
            assert {"current_phase", "phase_started_revision", "phase_status", "phase_completed_at"} <= {
                column["name"] for column in inspector.get_columns("pbl_participations")
            }
            assert {"session_kind", "created_by_student_id", "client_session_id"} <= {
                column["name"] for column in inspector.get_columns("pbl_sessions")
            }
            assert {"interaction_style", "style_selected_at"} <= {
                column["name"] for column in inspector.get_columns("pbl_participations")
            }
            assert {"snapshot_id", "student_id", "class_id", "teacher_id", "preview_payload"} <= {
                column["name"] for column in inspector.get_columns("pbl_submissions")
            }
            assert {"study_paths", "study_practice_groups", "study_practice_attempts"} <= set(
                inspector.get_table_names()
            )
            assert "pbl_teacher_feedbacks" in set(inspector.get_table_names())
            feedback_columns = {column["name"] for column in inspector.get_columns("pbl_teacher_feedbacks")}
            assert {
                "snapshot_id",
                "plan_id",
                "student_id",
                "class_id",
                "teacher_id",
                "action_type",
                "body",
            } <= feedback_columns
            assert "uq_pbl_session_student_client" in {
                constraint["name"] for constraint in inspector.get_unique_constraints("pbl_sessions")
            }
            assert {
                "current_cycle",
                "max_cycles",
                "automation_exhausted",
                "decision_policy_version",
                "decision_basis",
                "evaluated_at",
            } <= {column["name"] for column in inspector.get_columns("learning_plans")}
            assert {"cycle_number", "target_type", "target_code", "variant_code"} <= {
                column["name"] for column in inspector.get_columns("learning_tasks")
            }
            assert {
                "plan_id",
                "cycle_number",
                "policy_version",
                "result",
                "checks",
                "failed_targets",
                "automation_exhausted",
                "record_source",
                "evaluated_at",
            } <= {column["name"] for column in inspector.get_columns("learning_plan_evaluations")}
            assert "ix_learning_plan_evaluations_plan_id" in {
                index["name"] for index in inspector.get_indexes("learning_plan_evaluations")
            }
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (external_id, role, nickname, avatar_url, class_ids, permissions, "
                        "auth_provider) "
                        "VALUES ('head-user', 'teacher', '迁移教师', '', '[]', '[]', 'wechat')"
                    )
                )
            run_alembic(cwd, database_url, "upgrade", "20260909_0023")
            run_alembic(cwd, database_url, "downgrade", "20260830_0008")
            assert "auth_provider" not in {column["name"] for column in inspect(engine).get_columns("users")}
            run_alembic(cwd, database_url, "upgrade", "20260909_0023")
            with engine.connect() as connection:
                assert (
                    connection.execute(text("SELECT COUNT(*) FROM users WHERE external_id = 'head-user'")).scalar_one()
                    == 1
                )
        finally:
            engine.dispose()


def test_0023_rejects_downgrade_when_teacher_feedback_exists() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t21-migration-") as directory:
        db_path = Path(directory) / "teacher-feedback.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260909_0023")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO pbl_teacher_feedbacks "
                        "(snapshot_id, student_id, class_id, teacher_id, action_type, body, client_feedback_id) "
                        "VALUES (1, 1, 1, 1, 'feedback_only', '保留反馈历史', 't21-downgrade')"
                    )
                )
            with pytest.raises(AssertionError, match="teacher feedback exists"):
                run_alembic(cwd, database_url, "downgrade", "20260908_0022")
            assert "pbl_teacher_feedbacks" in set(inspect(engine).get_table_names())
        finally:
            engine.dispose()


def test_0020_backfills_history_and_enforces_student_creation_idempotency() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t17-from-0019-") as directory:
        db_path = Path(directory) / "from-0019.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260904_0019")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't17-teacher', 'teacher', 'teacher', '', '[]', '[]'), "
                        "(2, 't17-student', 'student', 'student', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO classes (id, name, code, teacher_id, status) VALUES (1, 'T17', 't17', 1, 'active')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_sessions (id, class_id, teacher_id, topic_code, provider, status) "
                        "VALUES (1, 1, 1, 'pathology.inflammation', 'coze', 'active')"
                    )
                )
                connection.execute(
                    text("INSERT INTO pbl_participations (id, session_id, student_id, revision) VALUES (1, 1, 2, 0)")
                )
            run_alembic(cwd, database_url, "upgrade", "20260907_0020")
            with engine.begin() as connection:
                assert (
                    connection.execute(text("SELECT session_kind FROM pbl_sessions WHERE id = 1")).scalar_one()
                    == "classroom"
                )
                assert (
                    connection.execute(
                        text("SELECT interaction_style FROM pbl_participations WHERE id = 1")
                    ).scalar_one()
                    == "guided"
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_sessions "
                        "(id, class_id, teacher_id, session_kind, created_by_student_id, client_session_id, "
                        "topic_code, provider, status) VALUES "
                        "(2, 1, 1, 'student_initiated', 2, 'same-client-id', "
                        "'pathology.inflammation', 'coze', 'active')"
                    )
                )
            with engine.begin() as connection:
                try:
                    connection.execute(
                        text(
                            "INSERT INTO pbl_sessions "
                            "(id, class_id, teacher_id, session_kind, created_by_student_id, client_session_id, "
                            "topic_code, provider, status) VALUES "
                            "(3, 1, 1, 'student_initiated', 2, 'same-client-id', "
                            "'pathology.inflammation', 'coze', 'active')"
                        )
                    )
                    raise AssertionError("student client session id must be unique per student")
                except Exception as error:
                    assert "UNIQUE constraint failed" in str(error)
        finally:
            engine.dispose()


def test_0020_downgrade_refuses_unified_dialogue_business_data() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t17-downgrade-") as directory:
        db_path = Path(directory) / "t17.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260907_0020")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't17-owner', 'teacher', 'owner', '', '[]', '[]'), "
                        "(2, 't17-creator', 'student', 'creator', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO classes (id, name, code, teacher_id, status) VALUES (1, 'T17', 't17', 1, 'active')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_sessions "
                        "(id, class_id, teacher_id, session_kind, created_by_student_id, client_session_id, "
                        "topic_code, provider, status) VALUES "
                        "(1, 1, 1, 'student_initiated', 2, 'client-1', "
                        "'pathology.inflammation', 'coze', 'active')"
                    )
                )
            environment = os.environ.copy()
            environment["DATABASE_URL"] = database_url
            attempted = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "20260904_0019"],
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert attempted.returncode != 0
            assert "pre-T17 backup" in attempted.stdout + attempted.stderr
            with engine.connect() as connection:
                assert (
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20260907_0020"
                )
        finally:
            engine.dispose()


def test_0019_downgrade_refuses_append_only_evaluation_history() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t15-downgrade-") as directory:
        db_path = Path(directory) / "t15.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260904_0019")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't15-student', 'student', 'student', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO learning_plans "
                        "(id, student_id, source_type, source_id, due_at, status, target_dimension_ids, "
                        "generation_mode, model_name, prompt_version, fallback_used) "
                        "VALUES (1, 1, 'pbl_diagnostic', 91, '2026-09-11 08:00:00', 'completed', '[]', "
                        "'deterministic', 'migration', 'migration-v1', 1)"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO learning_plan_evaluations "
                        "(plan_id, cycle_number, policy_version, result, checks, failed_targets, evaluated_at) "
                        "VALUES (1, 1, 'pbl-mastery-v1', 'improved', '[]', '[]', '2026-09-04 08:00:00')"
                    )
                )
            environment = os.environ.copy()
            environment["DATABASE_URL"] = database_url
            attempted = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "20260903_0018"],
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert attempted.returncode != 0
            assert "pre-T15 backup" in attempted.stdout + attempted.stderr
            with engine.connect() as connection:
                version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                assert version == "20260904_0019"
                assert connection.execute(text("SELECT COUNT(*) FROM learning_plan_evaluations")).scalar_one() == 1
        finally:
            engine.dispose()


def test_0018_downgrade_refuses_schema_v3_business_data() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t14-downgrade-") as directory:
        db_path = Path(directory) / "t14.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260903_0018")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't14-teacher', 'teacher', 'teacher', '', '[]', '[]'), "
                        "(2, 't14-student', 'student', 'student', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO classes (id, name, code, teacher_id, status) VALUES (1, 'T14', 't14', 1, 'active')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_sessions (id, class_id, teacher_id, topic_code, provider, status) "
                        "VALUES (1, 1, 1, 'pathology.inflammation', 'coze', 'active')"
                    )
                )
                connection.execute(
                    text("INSERT INTO pbl_participations (id, session_id, student_id, revision) VALUES (1, 1, 2, 1)")
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_diagnostic_snapshots "
                        "(participation_id, revision, status, schema_version, assistant_reply, knowledge_gaps, "
                        "reasoning_issues, provider_metadata) "
                        "VALUES (1, 1, 'probing', 3, 'continue', '[]', '[]', '{}')"
                    )
                )
            environment = os.environ.copy()
            environment["DATABASE_URL"] = database_url
            attempted = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "20260903_0017"],
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert attempted.returncode != 0
            assert "pre-T14 backup" in attempted.stdout + attempted.stderr
            with engine.connect() as connection:
                version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                assert version == "20260903_0018"
        finally:
            engine.dispose()


def test_0018_upgrades_0017_history_into_participation_level_phases() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t14-from-0017-") as directory:
        db_path = Path(directory) / "from-0017.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260903_0017")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't14-history-teacher', 'teacher', 'teacher', '', '[]', '[]'), "
                        "(2, 't14-ready-student', 'student', 'ready', '', '[]', '[]'), "
                        "(3, 't14-active-student', 'student', 'active', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO classes (id, name, code, teacher_id, status) "
                        "VALUES (1, 'T14 history', 't14-history', 1, 'active')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_sessions (id, class_id, teacher_id, topic_code, provider, status) "
                        "VALUES (1, 1, 1, 'pathology.inflammation', 'coze', 'active')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_participations (id, session_id, student_id, revision) "
                        "VALUES (1, 1, 2, 4), (2, 1, 3, 3)"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_diagnostic_snapshots "
                        "(participation_id, revision, status, schema_version, assistant_reply, knowledge_gaps, "
                        "reasoning_issues, provider_metadata) "
                        "VALUES (1, 4, 'ready', 2, 'legacy ready', '[]', '[]', '{}'), "
                        "(2, 3, 'probing', 2, 'legacy probing', '[]', '[]', '{}')"
                    )
                )
            # This fixture intentionally predates the message/snapshot linkage required by
            # T32. Keep this historical T14 assertion at the 0018 boundary; 0027 has a
            # separate negative test proving that such unlocatable completion data blocks.
            run_alembic(cwd, database_url, "upgrade", "20260903_0018")
            with engine.connect() as connection:
                rows = connection.execute(
                    text(
                        "SELECT id, current_phase, phase_status, phase_started_revision "
                        "FROM pbl_participations ORDER BY id"
                    )
                ).all()
                assert rows == [(1, "synthesis", "completed", 4), (2, "problem_framing", "active", 3)]
        finally:
            engine.dispose()


def test_0016_backfills_legacy_pbl_messages_and_downgrade_restores_history() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-pbl-migration-") as directory:
        db_path = Path(directory) / "pbl-history.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260903_0016")
        run_alembic(cwd, database_url, "downgrade", "20260903_0015")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 'pbl-teacher', 'teacher', 'teacher', '', '[]', '[]'), "
                        "(2, 'pbl-student', 'student', 'student', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO classes (id, name, code, teacher_id, status) "
                        "VALUES (1, 'PBL', 'pbl-a', 1, 'active')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_sessions (id, class_id, teacher_id, topic_code, provider, status) "
                        "VALUES (1, 1, 1, 'pathology.inflammation', 'coze', 'active')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO pbl_participations (id, session_id, student_id, messages, revision) "
                        "VALUES (1, 1, 2, :messages, 1)"
                    ),
                    {
                        "messages": (
                            '[{"role":"student","content":"first","client_message_id":"first"},'
                            '{"role":"assistant","content":"second"}]'
                        )
                    },
                )
            run_alembic(cwd, database_url, "upgrade", "20260903_0016")
            with engine.connect() as connection:
                history = (
                    connection.execute(
                        text("SELECT role, content, client_message_id FROM pbl_messages ORDER BY sequence")
                    )
                    .mappings()
                    .all()
                )
                assert [(item["role"], item["content"], item["client_message_id"]) for item in history] == [
                    ("student", "first", "first"),
                    ("assistant", "second", None),
                ]
                assert "messages" not in {item["name"] for item in inspect(engine).get_columns("pbl_participations")}
            run_alembic(cwd, database_url, "downgrade", "20260903_0015")
            with engine.connect() as connection:
                restored = connection.execute(text("SELECT messages FROM pbl_participations WHERE id = 1")).scalar_one()
                assert "first" in str(restored) and "second" in str(restored)
        finally:
            engine.dispose()


def test_0024_upgrades_report_class_scope_and_allows_empty_downgrade() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t29-migration-") as directory:
        db_path = Path(directory) / "report-class.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260909_0023")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't29-teacher', 'teacher', 'teacher', '', '[]', '[]'), "
                        "(2, 't29-student', 'student', 'student', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO classes (id, name, code, teacher_id, status) "
                        "VALUES (1, 'T29 班', 't29-a', 1, 'active')"
                    )
                )
                connection.execute(
                    text("INSERT INTO conversations (id, client_id, student_id) VALUES (11, 't29-conv', 2)")
                )
                connection.execute(
                    text(
                        "INSERT INTO reports (id, conversation_id, student_id, status, ai_score, ai_summary) "
                        "VALUES (21, 11, 2, 'pending_review', 80, 'T29 迁移保留的历史报告')"
                    )
                )
            run_alembic(cwd, database_url, "upgrade", "20260913_0024")
            columns = {column["name"] for column in inspect(engine).get_columns("reports")}
            assert {"class_id", "class_name_snapshot"} <= columns
            assert "ix_reports_class_status_updated_id" in {
                index["name"] for index in inspect(engine).get_indexes("reports")
            }
            with engine.connect() as connection:
                row = connection.execute(
                    text("SELECT status, ai_summary, class_id, class_name_snapshot FROM reports WHERE id = 21")
                ).one()
                assert row[0] == "pending_review"
                assert "T29 迁移保留" in row[1]
                assert row[2] is None and row[3] is None
            run_alembic(cwd, database_url, "downgrade", "20260909_0023")
            columns = {column["name"] for column in inspect(engine).get_columns("reports")}
            assert "class_id" not in columns and "class_name_snapshot" not in columns
            with engine.connect() as connection:
                assert connection.execute(text("SELECT COUNT(*) FROM reports")).scalar_one() == 1
            run_alembic(cwd, database_url, "upgrade", "20260913_0024")
        finally:
            engine.dispose()


def test_0024_downgrade_refuses_when_class_scope_assigned() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t29-downgrade-") as directory:
        db_path = Path(directory) / "report-class-assigned.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260913_0024")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't29-teacher-b', 'teacher', 'teacher', '', '[]', '[]'), "
                        "(2, 't29-student-b', 'student', 'student', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO classes (id, name, code, teacher_id, status) "
                        "VALUES (1, 'T29 班 B', 't29-b', 1, 'active')"
                    )
                )
                connection.execute(
                    text("INSERT INTO conversations (id, client_id, student_id) VALUES (12, 't29-conv-b', 2)")
                )
                connection.execute(
                    text(
                        "INSERT INTO reports (id, conversation_id, student_id, status, ai_score, ai_summary, "
                        "class_id, class_name_snapshot) "
                        "VALUES (22, 12, 2, 'reviewed', 90, '已归属报告', 1, 'T29 班 B')"
                    )
                )
            with pytest.raises(AssertionError, match="class scope"):
                run_alembic(cwd, database_url, "downgrade", "20260909_0023")
            assert "class_id" in {column["name"] for column in inspect(engine).get_columns("reports")}
            with engine.connect() as connection:
                assert connection.execute(text("SELECT class_id FROM reports WHERE id = 22")).scalar_one() == 1
        finally:
            engine.dispose()


def test_0025_creates_learning_evidence_schema_and_empty_downgrade_is_reversible() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t30-evidence-schema-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'evidence-empty.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260913_0025")
        engine = create_engine(database_url)
        try:
            inspector = inspect(engine)
            assert {"learning_evidence_events", "learning_evidence_metrics"} <= set(inspector.get_table_names())
            assert {
                "student_id",
                "class_id",
                "source_type",
                "source_id",
                "source_version",
                "authority_level",
                "visibility_scope",
                "event_kind",
                "occurred_at",
                "dedupe_key",
                "contract_version",
            } <= {column["name"] for column in inspector.get_columns("learning_evidence_events")}
            assert {"event_id", "metric_kind", "metric_code", "normalized_score", "result"} <= {
                column["name"] for column in inspector.get_columns("learning_evidence_metrics")
            }
            assert "uq_learning_evidence_event_dedupe" in {
                constraint["name"] for constraint in inspector.get_unique_constraints("learning_evidence_events")
            }
            assert "uq_learning_evidence_metric_code" in {
                constraint["name"] for constraint in inspector.get_unique_constraints("learning_evidence_metrics")
            }
            run_alembic(cwd, database_url, "downgrade", "20260913_0024")
            assert not (
                {"learning_evidence_events", "learning_evidence_metrics"} & set(inspect(engine).get_table_names())
            )
            run_alembic(cwd, database_url, "upgrade", "20260913_0025")
        finally:
            engine.dispose()


def test_0025_downgrade_refuses_nonempty_learning_evidence() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t30-evidence-downgrade-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'evidence-nonempty.db').as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "20260913_0025")
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, external_id, role, nickname, avatar_url, class_ids, permissions) "
                        "VALUES (1, 't30-student', 'student', '学生', '', '[]', '[]')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO learning_evidence_events "
                        "(id, student_id, source_type, source_id, source_version, authority_level, "
                        "visibility_scope, event_kind, occurred_at, dedupe_key, contract_version) "
                        "VALUES (1, 1, 'ai_personal_practice', 'attempt-1', 1, 'personal_unverified', "
                        "'student_only', 'assessment', '2026-09-13 08:00:00', 't30-dedupe-1', 1)"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO learning_evidence_metrics "
                        "(event_id, metric_kind, metric_code, normalized_score, result, evidence_present) "
                        "VALUES (1, 'knowledge', 'knowledge_point_view', 0, 'incorrect', 1)"
                    )
                )
            environment = os.environ.copy()
            environment["DATABASE_URL"] = database_url
            attempted = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", "20260913_0024"],
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert attempted.returncode != 0
            assert "T30 learning evidence" in attempted.stdout + attempted.stderr
            with engine.connect() as connection:
                assert (
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20260913_0025"
                )
                assert connection.execute(text("SELECT COUNT(*) FROM learning_evidence_events")).scalar_one() == 1
        finally:
            engine.dispose()
