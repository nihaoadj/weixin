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
