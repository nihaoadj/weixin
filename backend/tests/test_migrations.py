import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine, inspect, text


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
            run_alembic(cwd, database_url, "upgrade", "head")
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
            run_alembic(cwd, database_url, "upgrade", "head")
            run_alembic(cwd, database_url, "downgrade", "20260823_0004")
            with engine.connect() as connection:
                assert connection.execute(text("SELECT COUNT(*) FROM class_members")).scalar_one() == 1
        finally:
            engine.dispose()


def test_actual_head_0020_upgrades_empty_and_0008_databases() -> None:
    """Exercise the current worktree head, including the T14 through T17 additions."""
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-migration-head-") as directory:
        db_path = Path(directory) / "head.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic(cwd, database_url, "upgrade", "head")
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
            run_alembic(cwd, database_url, "upgrade", "head")
            run_alembic(cwd, database_url, "downgrade", "20260830_0008")
            assert "auth_provider" not in {column["name"] for column in inspect(engine).get_columns("users")}
            run_alembic(cwd, database_url, "upgrade", "head")
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
        run_alembic(cwd, database_url, "upgrade", "head")
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
            run_alembic(cwd, database_url, "upgrade", "head")
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
        run_alembic(cwd, database_url, "upgrade", "head")
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
        run_alembic(cwd, database_url, "upgrade", "head")
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
            run_alembic(cwd, database_url, "upgrade", "head")
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
        run_alembic(cwd, database_url, "upgrade", "head")
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
            run_alembic(cwd, database_url, "upgrade", "head")
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
