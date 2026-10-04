import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, inspect, text

T43_TABLES = (
    "bank_archive_receipts",
    "classroom_question_reviews",
    "bank_import_receipts",
    "teacher_question_bank_revisions",
    "teacher_question_bank_items",
    "t43_legacy_plan_mappings",
    "teaching_command_receipts",
    "classroom_final_reports",
    "classroom_package_items",
    "classroom_task_packages",
)


def alembic(cwd: Path, database_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_0032_upgrades_existing_schema_and_refuses_data_loss() -> None:
    cwd = Path(__file__).parents[1]
    with TemporaryDirectory(prefix="medical-qa-t43-migration-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'packages.db').as_posix()}"
        assert alembic(cwd, database_url, "upgrade", "20260919_0030").returncode == 0
        engine = create_engine(database_url)
        try:
            # Emulate an existing 0030 database created by the previous code.
            existing_tables = set(inspect(engine).get_table_names())
            with engine.begin() as connection:
                for table in T43_TABLES:
                    if table in existing_tables:
                        connection.execute(text(f"DROP TABLE {table}"))
                columns = {column["name"] for column in inspect(connection).get_columns("pbl_diagnostic_snapshots")}
                for column in ("candidate_tasks", "diagnosis_outcome"):
                    if column in columns:
                        connection.execute(text(f"ALTER TABLE pbl_diagnostic_snapshots DROP COLUMN {column}"))
            upgraded = alembic(cwd, database_url, "upgrade", "20260924_0032")
            assert upgraded.returncode == 0, upgraded.stdout + upgraded.stderr
            assert set(T43_TABLES).issubset(inspect(engine).get_table_names())
            assert "included_in_package" in {
                column["name"] for column in inspect(engine).get_columns("classroom_package_items")
            }
            assert {"candidate_tasks", "diagnosis_outcome"}.issubset(
                {column["name"] for column in inspect(engine).get_columns("pbl_diagnostic_snapshots")}
            )
            assert "ai_schema_version" in {column["name"] for column in inspect(engine).get_columns("pbl_sessions")}

            downgraded = alembic(cwd, database_url, "downgrade", "20260919_0030")
            assert downgraded.returncode == 0, downgraded.stdout + downgraded.stderr
            assert not set(T43_TABLES).intersection(inspect(engine).get_table_names())
            assert "candidate_tasks" not in {
                column["name"] for column in inspect(engine).get_columns("pbl_diagnostic_snapshots")
            }

            assert alembic(cwd, database_url, "upgrade", "20260923_0031").returncode == 0
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO classroom_task_packages "
                        "(student_id, class_id, session_id, completion_snapshot_id, teacher_id, diagnosis_outcome) "
                        "VALUES (7101, 7201, 7301, 7401, 7501, 'no_clear_gaps')"
                    )
                )
                package_id = connection.scalar(text("SELECT id FROM classroom_task_packages LIMIT 1"))
                connection.execute(
                    text(
                        "INSERT INTO classroom_package_items "
                        "(package_id, stable_key, position, cycle_number, task_type, primary_point_code, "
                        "point_codes, dimension_ids, target_type, target_code) "
                        "VALUES (:package_id, 'excluded-source', 1, 1, 'retest', 'point', '[]', '[]', "
                        "'knowledge_goal', 'point')"
                    ),
                    {"package_id": package_id},
                )
            assert alembic(cwd, database_url, "upgrade", "20260924_0032").returncode == 0
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT included_in_package FROM classroom_package_items")) == 1
            with engine.begin() as connection:
                connection.execute(text("UPDATE classroom_package_items SET included_in_package = 0"))
            excluded_downgrade = alembic(cwd, database_url, "downgrade", "20260923_0031")
            assert excluded_downgrade.returncode != 0
            assert "items are excluded" in excluded_downgrade.stdout + excluded_downgrade.stderr
            with engine.begin() as connection:
                connection.execute(text("UPDATE classroom_package_items SET included_in_package = 1"))
            refused = alembic(cwd, database_url, "downgrade", "20260919_0030")
            assert refused.returncode != 0
            assert "T43 data exists" in refused.stdout + refused.stderr
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260923_0031"
        finally:
            engine.dispose()
