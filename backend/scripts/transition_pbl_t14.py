"""Convert historical PBL states to T14. Default is a read-only dry run."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = BACKEND / "data/dev.db"
sys.path.insert(0, str(BACKEND))

from app.bootstrap import model_registry  # noqa: E402,F401
from app.modules.content.infrastructure.pbl_publication import SqlAlchemyQuestionPublication  # noqa: E402
from app.modules.learning.infrastructure.models import LearningPlan, LearningTask  # noqa: E402
from app.modules.learning.infrastructure.pbl_mastery import evaluate_pbl_plan  # noqa: E402
from app.modules.pbl.infrastructure.models import (  # noqa: E402
    PblDiagnosticSnapshot,
    PblParticipation,
    PblSession,
)


def _safe_database(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.suffix.lower() not in {".db", ".sqlite", ".sqlite3"} or not resolved.is_file():
        raise ValueError("Database must be an existing local SQLite file")
    if resolved.parent == resolved or resolved.is_symlink():
        raise ValueError("Database path is unsafe")
    return resolved


def _backup(source: Path, target: Path) -> None:
    if target.exists():
        raise ValueError("Backup target already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(source)) as source_db, closing(sqlite3.connect(target)) as target_db:
            source_db.backup(target_db)
            integrity = target_db.execute("PRAGMA integrity_check").fetchone()
            if integrity != ("ok",):
                raise ValueError("Backup integrity check failed")
    except Exception:
        target.unlink(missing_ok=True)
        raise


def _legacy_basis(plan: LearningPlan) -> bool:
    if plan.verification_status not in {"improved", "needs_reinforcement"}:
        return False
    if (plan.decision_basis or {}).get("decision_source") == "legacy_teacher":
        return False
    plan.decision_basis = {
        "decision_source": "legacy_teacher",
        "legacy_verification_status": plan.verification_status,
    }
    return True


def _second_cycle_resources(session: Session, plan: LearningPlan) -> list[dict[str, object]]:
    context = plan.source_context or {}
    pbl_session = session.get(PblSession, context.get("session_id"))
    if pbl_session is None:
        raise ValueError("PBL session missing")
    resources = [
        {
            "task_type": "discussion",
            "problem_id": next((task.problem_id for task in plan.tasks if task.task_type == "discussion"), None),
            "prompt": "第二轮反思：结合首轮反馈，重新说明证据链与仍不确定之处。",
            "cycle_number": 2,
            "target_type": "discussion",
            "target_code": "discussion",
            "variant_code": f"plan:{plan.id}:discussion:v2",
        }
    ]
    resources.extend(
        item
        for item in SqlAlchemyQuestionPublication(session).task_resources(
            pbl_session.case_id,
            tuple(context.get("point_codes", [])),
            tuple(context.get("dimension_ids", [])),
        )
        if int(item.get("cycle_number", 1)) == 2
    )
    retry = next((task for task in plan.tasks if task.task_type == "focused_retry"), None)
    if retry is not None:
        resources.append(
            {
                **retry.public_definition,
                "task_type": "focused_retry",
                "dimension_id": retry.dimension_id,
                "stage_id": retry.stage_id,
                "problem_id": retry.problem_id,
                "cycle_number": 2,
                "target_type": "case_retry",
                "target_code": retry.target_code or f"case:{retry.problem_id}",
                "variant_code": f"case:{retry.problem_id}:retry:v2",
            }
        )
    return resources


def _reconcile_pending(session: Session, plan: LearningPlan) -> None:
    for task in plan.tasks:
        task.cycle_number = 1
        task.target_type = (
            "knowledge_gap"
            if task.task_type in {"knowledge_review", "retest"}
            else "reasoning_issue"
            if task.task_type == "micro_drill"
            else "case_retry"
            if task.task_type == "focused_retry"
            else "discussion"
        )
        task.target_code = str(
            task.public_definition.get("point_code")
            or task.dimension_id
            or (f"case:{task.problem_id}" if task.task_type == "focused_retry" else "discussion")
        )
        task.variant_code = str(task.public_definition.get("card_code") or f"task:{task.id}:v1")
    position = max((task.position for task in plan.tasks), default=0)
    for resource in _second_cycle_resources(session, plan):
        position += 1
        public = {key: value for key, value in resource.items() if key != "private_rubric"}
        public["source"] = {
            key: plan.source_context[key]
            for key in ("session_id", "snapshot_id", "suggestion_id")
            if key in plan.source_context
        }
        plan.tasks.append(
            LearningTask(
                position=position,
                cycle_number=2,
                target_type=str(resource["target_type"]),
                target_code=str(resource["target_code"]),
                variant_code=str(resource["variant_code"]),
                task_type=str(resource["task_type"]),
                dimension_id=str(resource.get("dimension_id", "discussion")),
                stage_id=resource.get("stage_id"),
                problem_id=resource.get("problem_id"),
                public_definition=public,
                private_rubric=resource.get("private_rubric", {}),
                status="inactive",
            )
        )
    plan.status = "active"
    plan.completed_at = None
    plan.current_cycle = 1
    plan.max_cycles = 2
    plan.verification_status = "not_ready"
    session.flush()
    if not evaluate_pbl_plan(session, plan):
        raise ValueError("Pending plan lacks complete first-cycle evidence")


def transition(session: Session) -> dict[str, object]:
    result: dict[str, object] = {
        "participations_completed": 0,
        "participations_restarted": 0,
        "legacy_results_marked": 0,
        "pending_reconciled": 0,
        "failed_plan_ids": [],
    }
    participations = session.scalars(select(PblParticipation)).all()
    for participation in participations:
        ready_v2 = session.scalar(
            select(PblDiagnosticSnapshot.id).where(
                PblDiagnosticSnapshot.participation_id == participation.id,
                PblDiagnosticSnapshot.status == "ready",
                PblDiagnosticSnapshot.schema_version == 2,
            )
        )
        if ready_v2:
            participation.current_phase = "synthesis"
            participation.phase_status = "completed"
            participation.phase_completed_at = participation.updated_at or datetime.now(UTC)
            participation.phase_started_revision = participation.revision
            result["participations_completed"] += 1
        else:
            participation.current_phase = "problem_framing"
            participation.phase_status = "active"
            participation.phase_completed_at = None
            participation.phase_started_revision = participation.revision
            result["participations_restarted"] += 1

    plans = session.scalars(
        select(LearningPlan)
        .where(LearningPlan.source_type == "pbl_suggestion")
        .options(selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt))
    ).all()
    for plan in plans:
        if _legacy_basis(plan):
            result["legacy_results_marked"] += 1
        elif plan.verification_status == "pending_teacher":
            try:
                with session.begin_nested():
                    _reconcile_pending(session, plan)
                result["pending_reconciled"] += 1
            except ValueError:
                result["failed_plan_ids"].append(plan.id)
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
            result = transition(session)
            if result["failed_plan_ids"]:
                session.rollback()
                print(json.dumps({**result, "mode": "blocked"}, ensure_ascii=False, sort_keys=True))
                return 2
            if args.apply:
                session.commit()
            else:
                session.rollback()
            output = {**result, "mode": "apply" if args.apply else "dry-run"}
            print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
