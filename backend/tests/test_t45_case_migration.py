"""Exercise the real 0035 upgrade and protect persisted reflection history."""

import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_t44_data_migrations import _alembic, _upgrade


def test_case_reflection_upgrade_preserves_messages_and_guards_downgrade():
    with TemporaryDirectory(prefix="medical-qa-t45-case-") as directory:
        database = Path(directory) / "case.sqlite3"
        url = f"sqlite:///{database.as_posix()}"
        _upgrade(url, "20260926_0034")
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "INSERT INTO route_case_sessions (id, public_id, step_id, student_id) VALUES (1, 'case', 1, 1)"
            )
            connection.execute(
                "INSERT INTO route_case_messages (id, case_session_id, sequence, role, content, request_revision) "
                "VALUES (1, 1, 1, 'student', 'retained teaching answer', 1)"
            )
            connection.commit()
            before = connection.execute("SELECT * FROM route_case_messages").fetchall()
        _upgrade(url, "head")
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("SELECT * FROM route_case_messages").fetchall() == before
            connection.execute("UPDATE route_case_sessions SET phase='summary_reflection' WHERE id=1")
            connection.commit()
        blocked = _alembic(url, "downgrade", "20260926_0034")
        assert blocked.returncode != 0
        assert "preserve case reflection" in blocked.stdout + blocked.stderr
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("SELECT phase FROM route_case_sessions").fetchone() == ("summary_reflection",)
            assert connection.execute("SELECT * FROM route_case_messages").fetchall() == before
            connection.execute("UPDATE route_case_sessions SET phase='evidence_judgment' WHERE id=1")
            connection.commit()
        restored = _alembic(url, "downgrade", "20260926_0034")
        assert restored.returncode == 0, restored.stdout + restored.stderr
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("SELECT * FROM route_case_messages").fetchall() == before
            try:
                connection.execute("UPDATE route_case_sessions SET phase='summary_reflection' WHERE id=1")
            except sqlite3.IntegrityError:
                pass
            else:
                raise AssertionError("old schema must reject reflection phase")
