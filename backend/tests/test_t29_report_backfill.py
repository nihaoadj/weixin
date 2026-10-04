"""T29 report class-scope backfill: provenance rules, idempotency, CLI safety."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.identity.infrastructure.models import User
from app.modules.qa.infrastructure.models import Conversation
from app.modules.reports.infrastructure.models import Report
from scripts.backfill_report_class_scope import _safe_database, backfill


def _backup_sqlite_database(source: Path, target: Path) -> None:
    if target.exists():
        raise ValueError("Backup target already exists")
    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(target)
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()


def _setup(db, *, second_class: bool = False):
    teacher = User(external_id="t29-backfill-teacher", role="teacher", nickname="教师", class_ids=[])
    other_teacher = User(external_id="t29-backfill-other", role="teacher", nickname="其他教师", class_ids=[])
    student = User(external_id="t29-backfill-student", role="student", nickname="学生", class_ids=[])
    db.add_all([teacher, other_teacher, student])
    db.flush()
    classroom = ClassRoom(name="T29 回填班", code="t29-backfill-a", teacher_id=teacher.id, status="active")
    db.add(classroom)
    db.flush()
    db.add(ClassMember(class_id=classroom.id, student_id=student.id))
    if second_class:
        extra = ClassRoom(name="T29 第二班", code="t29-backfill-b", teacher_id=teacher.id, status="active")
        db.add(extra)
        db.flush()
        db.add(ClassMember(class_id=extra.id, student_id=student.id))
    db.flush()
    return teacher, other_teacher, student, classroom


_conversation_counter = 0


def _report(db, student_id: int, *, status: str, reviewer_id: int | None = None) -> Report:
    global _conversation_counter
    _conversation_counter += 1
    conversation = Conversation(
        client_id=f"t29-backfill-{_conversation_counter}-{status}-{reviewer_id or 0}", student_id=student_id
    )
    db.add(conversation)
    db.flush()
    report = Report(
        conversation_id=conversation.id,
        student_id=student_id,
        status=status,
        ai_score=80,
        ai_summary="回填测试报告",
        reviewer_id=reviewer_id,
    )
    db.add(report)
    db.flush()
    return report


def test_backfill_assigns_only_unique_provable_candidates(db) -> None:
    teacher, _other, student, classroom = _setup(db)
    # Rule 1: reviewed + reviewer_id resolves through the reviewer-owned class.
    reviewed = _report(db, student.id, status="reviewed", reviewer_id=teacher.id)
    # Rule 2: pending report resolves through the single student class.
    pending = _report(db, student.id, status="pending_review")
    # A reviewed report whose reviewer owns none of the student classes is not
    # guessed through rule 2.
    mismatched = _report(db, student.id, status="reviewed", reviewer_id=99999)
    # Drafts and already assigned reports are skipped.
    draft = _report(db, student.id, status="draft")
    assigned = _report(db, student.id, status="reviewed", reviewer_id=teacher.id)
    assigned.class_id = classroom.id
    assigned.class_name_snapshot = "T29 回填班"
    db.flush()

    result = backfill(db)
    db.flush()
    assert result["pending_total"] == 3
    assert result["unique_reviewer_candidate"] == 1
    assert result["unique_student_class"] == 1
    assert result["zero_candidate"] == 1
    assert result["ambiguous_candidate"] == 0
    assert result["draft_skipped"] == 1
    assert result["already_assigned_skipped"] == 1
    assert result["written"] == 2

    assert reviewed.class_id == classroom.id and reviewed.class_name_snapshot == "T29 回填班"
    assert pending.class_id == classroom.id
    assert mismatched.class_id is None
    assert draft.class_id is None
    # Existing values are never overwritten.
    assert assigned.class_name_snapshot == "T29 回填班"


def test_backfill_is_idempotent_and_reports_ambiguity(db) -> None:
    teacher, _other, student, classroom = _setup(db, second_class=True)
    pending = _report(db, student.id, status="pending_review")

    first = backfill(db)
    assert first["ambiguous_candidate"] == 1 and first["written"] == 0
    assert pending.class_id is None

    pending.class_id = classroom.id
    pending.class_name_snapshot = "T29 回填班"
    db.flush()
    second = backfill(db)
    assert second["written"] == 0 and second["already_assigned_skipped"] == 1
    assert pending.class_name_snapshot == "T29 回填班"
    assert teacher.id > 0


def test_backfill_cli_is_dry_run_by_default_and_requires_new_backup_and_confirm(db) -> None:
    source = Path(str(db.get_bind().url.database)).resolve()
    working = source.with_name("t29-backfill-working.db")
    backup = source.with_name("t29-backfill-before-apply.db")
    script = Path(__file__).resolve().parents[1] / "scripts" / "backfill_report_class_scope.py"
    _backup_sqlite_database(source, working)

    dry_run = subprocess.run(
        [sys.executable, str(script), "--database", str(working)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert dry_run.returncode == 0, dry_run.stderr
    payload = json.loads(dry_run.stdout)
    assert payload["mode"] == "dry-run" and payload["written"] == 0

    denied = subprocess.run(
        [sys.executable, str(script), "--database", str(working), "--apply", "--backup", str(backup)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert denied.returncode == 2
    assert not backup.exists()

    applied = subprocess.run(
        [
            sys.executable,
            str(script),
            "--database",
            str(working),
            "--apply",
            "--confirm-development",
            "--backup",
            str(backup),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert applied.returncode == 0, applied.stderr
    assert json.loads(applied.stdout)["mode"] == "apply"
    assert backup.is_file()

    conflict = subprocess.run(
        [
            sys.executable,
            str(script),
            "--database",
            str(working),
            "--apply",
            "--confirm-development",
            "--backup",
            str(backup),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert conflict.returncode != 0
    assert "already exists" in conflict.stderr + conflict.stdout


def test_backfill_cli_rejects_unsafe_database_paths() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "backfill_report_class_scope.py"
    missing = subprocess.run(
        [sys.executable, str(script), "--database", "definitely/missing/t29.db"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert missing.returncode != 0
    assert "existing local SQLite file" in missing.stderr

    try:
        _safe_database(Path("definitely/missing/t29.db"))
    except ValueError as error:
        assert "existing local SQLite file" in str(error)
    else:
        raise AssertionError("unsafe database path was accepted")
