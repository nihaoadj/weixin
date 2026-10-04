"""T64 adds an internal nullable snapshot without altering historical rows."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.modules.content.infrastructure.models import Problem
from app.modules.identity.infrastructure.models import User
from app.modules.training.infrastructure.models import CaseAttempt
from app.testing_resources import cleanup_managed_database, create_managed_database


def test_snapshot_migration_roundtrip_preserves_schema_and_is_nullable():
    resource = create_managed_database("t64-migration")
    environment = {
        **os.environ,
        "DATABASE_URL": resource.url,
        "TEST_RESOURCE_DIR": str(resource.root),
        "TEST_RESOURCE_TOKEN": resource.token,
    }
    engine = create_engine(resource.url)

    def migrate(*command):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *command],
            cwd=Path(__file__).parents[1],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    try:
        migrate("upgrade", "20260928_0036")
        # The historical initial migration uses current metadata on an empty DB.
        # Remove the new column to exercise the upgrade of an actual pre-T64 schema.
        if "problem_snapshot" in {column["name"] for column in inspect(engine).get_columns("case_attempts")}:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE case_attempts DROP COLUMN problem_snapshot"))
        before = {column["name"] for column in inspect(engine).get_columns("case_attempts")}
        migrate("upgrade", "head")
        columns = {column["name"]: column for column in inspect(engine).get_columns("case_attempts")}
        assert set(columns) == before | {"problem_snapshot"}
        assert columns["problem_snapshot"]["nullable"] is True
        migrate("downgrade", "20260928_0036")
        assert {column["name"] for column in inspect(engine).get_columns("case_attempts")} == before
        migrate("upgrade", "head")
    finally:
        engine.dispose()
        cleanup_managed_database(resource)


def test_snapshot_downgrade_refuses_populated_history_and_accepts_sql_and_json_null():
    resource = create_managed_database("t64-migration-history")
    environment = {
        **os.environ,
        "DATABASE_URL": resource.url,
        "TEST_RESOURCE_DIR": str(resource.root),
        "TEST_RESOURCE_TOKEN": resource.token,
    }
    engine = create_engine(resource.url)

    def migrate(*command):
        return subprocess.run(
            [sys.executable, "-m", "alembic", *command],
            cwd=Path(__file__).parents[1],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    try:
        upgraded = migrate("upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stdout + upgraded.stderr
        snapshot = {"case_definition": {"opening": {"chief_complaint": "synthetic fixture"}}, "rubric": {}}
        with Session(engine) as session:
            student = User(external_id="t64-migration-student", role="student", nickname="fixture")
            case = Problem(type="guided_case", title="fixture", content_type="guided_case")
            session.add_all([student, case])
            session.flush()
            populated = CaseAttempt(
                problem_id=case.id,
                student_id=student.id,
                problem_version=1,
                problem_snapshot=snapshot,
            )
            empty = CaseAttempt(problem_id=case.id, student_id=student.id, problem_version=1)
            session.add_all([populated, empty])
            session.commit()
            populated_id, empty_id = populated.id, empty.id
        refused = migrate("downgrade", "20260928_0036")
        assert refused.returncode != 0
        assert "preserve historical case attempt snapshots" in refused.stderr
        assert "problem_snapshot" in {column["name"] for column in inspect(engine).get_columns("case_attempts")}
        with Session(engine) as session:
            assert session.get(CaseAttempt, populated_id).problem_snapshot == snapshot
            assert session.get(CaseAttempt, empty_id).problem_snapshot is None
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261003_0037"
            # Exercise both storage forms of no snapshot instead of assuming ORM None is SQL NULL.
            connection.execute(
                text("UPDATE case_attempts SET problem_snapshot = 'null' WHERE id = :id"),
                {"id": populated_id},
            )
            connection.execute(
                text("UPDATE case_attempts SET problem_snapshot = NULL WHERE id = :id"),
                {"id": empty_id},
            )
        allowed = migrate("downgrade", "20260928_0036")
        assert allowed.returncode == 0, allowed.stdout + allowed.stderr
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM case_attempts")) == 2
        assert "problem_snapshot" not in {column["name"] for column in inspect(engine).get_columns("case_attempts")}
    finally:
        engine.dispose()
        cleanup_managed_database(resource)
