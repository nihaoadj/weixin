"""Backfill provable report class attribution for T29. Default is dry-run.

Only two provenance rules are accepted, and they never overwrite:

1. A reviewed report with ``reviewer_id`` is assigned the student member class
   owned by that reviewer, when exactly one such class exists.
2. Every other non-draft report is assigned the student's current member class,
   when exactly one exists.

Zero or ambiguous candidates stay unassigned; drafts are never assigned.
Output carries IDs and category counts only, never student content.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = BACKEND / "data/dev.db"
sys.path.insert(0, str(BACKEND))

from app.bootstrap import model_registry  # noqa: E402,F401
from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom  # noqa: E402
from app.modules.reports.infrastructure.models import Report  # noqa: E402
from scripts.transition_pathology import backup_verified as _backup  # noqa: E402


def _safe_database(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_file() or resolved.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("Database must be an existing local SQLite file")
    return resolved


def _member_rows(session: Session, student_id: int) -> list[tuple[int, int, str]]:
    rows = session.execute(
        select(ClassRoom.id, ClassRoom.teacher_id, ClassRoom.name)
        .join(ClassMember, ClassMember.class_id == ClassRoom.id)
        .where(ClassMember.student_id == student_id)
        .order_by(ClassRoom.id)
    ).all()
    return [(int(row[0]), int(row[1]), str(row[2])) for row in rows]


def backfill(session: Session) -> dict[str, int]:
    result = {
        "pending_total": 0,
        "unique_reviewer_candidate": 0,
        "unique_student_class": 0,
        "zero_candidate": 0,
        "ambiguous_candidate": 0,
        "already_assigned_skipped": 0,
        "draft_skipped": 0,
        "written": 0,
    }
    reports = session.scalars(select(Report).order_by(Report.id)).all()
    for report in reports:
        if report.status == "draft":
            result["draft_skipped"] += 1
            continue
        if report.class_id is not None:
            result["already_assigned_skipped"] += 1
            continue
        result["pending_total"] += 1
        members = _member_rows(session, report.student_id)
        reviewer_matched = report.status == "reviewed" and report.reviewer_id is not None
        candidates = [row for row in members if row[1] == report.reviewer_id] if reviewer_matched else members
        if len(candidates) == 1:
            class_id, _teacher_id, class_name = candidates[0]
            report.class_id = class_id
            report.class_name_snapshot = class_name
            result["written"] += 1
            result["unique_reviewer_candidate" if reviewer_matched else "unique_student_class"] += 1
        elif not candidates:
            result["zero_candidate"] += 1
        else:
            result["ambiguous_candidate"] += 1
    session.flush()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-development", action="store_true")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    database = _safe_database(args.database)
    if args.apply and (not args.confirm_development or args.backup is None):
        parser.error("--apply requires --confirm-development and --backup")
    if args.apply:
        _backup(database, args.backup.resolve())
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    try:
        with Session(engine) as session:
            columns = {column["name"] for column in inspect(engine).get_columns("reports")}
            if not {"class_id", "class_name_snapshot"} <= columns:
                print(json.dumps({"error": "reports class columns missing; apply revision 20260913_0024 first"}))
                return 1
            result = backfill(session)
            if args.apply:
                session.commit()
            else:
                session.rollback()
            print(json.dumps({**result, "mode": "apply" if args.apply else "dry-run"}, sort_keys=True))
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
