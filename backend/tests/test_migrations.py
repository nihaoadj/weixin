import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

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


def test_actual_head_0017_upgrades_empty_and_0008_databases() -> None:
    """Exercise the current worktree head, including the T11 PBL additions."""
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
