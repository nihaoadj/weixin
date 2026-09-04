"""Backfill provable PBL cycle evaluations for T15 reports. Default is dry-run."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = BACKEND / "data/dev.db"
sys.path.insert(0, str(BACKEND))

from app.bootstrap import model_registry  # noqa: E402,F401
from app.modules.learning.infrastructure.models import (  # noqa: E402
    LearningPlan,
    LearningPlanEvaluation,
    LearningTask,
)
from app.modules.learning.infrastructure.pbl_mastery import POLICY_VERSION, _checks  # noqa: E402
from scripts.transition_pbl_t14 import _backup, _safe_database  # noqa: E402


def _failed(checks: list[dict[str, object]]) -> list[dict[str, str]]:
    result = []
    for item in checks:
        if item["passed"] or item["target_type"] == "discussion":
            continue
        result.append(
            {
                "target_type": str(item.get("activation_target_type", item["target_type"])),
                "target_code": str(item.get("activation_target_code", item["target_code"])),
            }
        )
    return list({(item["target_type"], item["target_code"]): item for item in result}.values())


def _evaluated_at(plan: LearningPlan, cycle: int) -> datetime:
    values = [
        task.attempt.assessed_at
        for task in plan.tasks
        if task.cycle_number == cycle and task.attempt and task.attempt.assessed_at
    ]
    return max(values) if values else plan.evaluated_at or plan.completed_at or plan.created_at or datetime.now(UTC)


def backfill(session: Session) -> dict[str, int]:
    result = {"runtime_existing": 0, "automatic_created": 0, "legacy_created": 0}
    plans = session.scalars(
        select(LearningPlan)
        .where(LearningPlan.source_type == "pbl_suggestion")
        .options(
            selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt),
            selectinload(LearningPlan.evaluations),
        )
    ).all()
    for plan in plans:
        existing_cycles = {item.cycle_number for item in plan.evaluations}
        result["runtime_existing"] += len(existing_cycles)
        basis = plan.decision_basis or {}
        if basis.get("decision_source") == "legacy_teacher":
            if (
                plan.current_cycle not in existing_cycles
                and plan.verification_status in {"improved", "needs_reinforcement"}
            ):
                session.add(
                    LearningPlanEvaluation(
                        plan_id=plan.id,
                        cycle_number=plan.current_cycle,
                        policy_version="legacy-teacher",
                        result=plan.verification_status,
                        checks=[],
                        failed_targets=[],
                        automation_exhausted=plan.automation_exhausted,
                        record_source="legacy",
                        evaluated_at=_evaluated_at(plan, plan.current_cycle),
                    )
                )
                result["legacy_created"] += 1
            continue
        evaluated_cycles = list(range(1, plan.current_cycle))
        if plan.status == "completed" or basis.get("cycle") == plan.current_cycle:
            evaluated_cycles.append(plan.current_cycle)
        for cycle in evaluated_cycles:
            if cycle in existing_cycles:
                continue
            checks = _checks(plan, cycle)
            if not checks or any(
                task.status not in {"completed", "skipped"}
                for task in plan.tasks
                if task.cycle_number == cycle and task.status != "inactive"
            ):
                continue
            failed_targets = _failed(checks)
            if cycle < plan.current_cycle:
                outcome = "next_cycle_activated"
            elif plan.verification_status == "needs_reinforcement":
                outcome = "needs_reinforcement"
            elif plan.verification_status == "improved":
                outcome = "improved"
            else:
                continue
            session.add(
                LearningPlanEvaluation(
                    plan_id=plan.id,
                    cycle_number=cycle,
                    policy_version=str(basis.get("policy_version") or plan.decision_policy_version or POLICY_VERSION),
                    result=outcome,
                    checks=checks,
                    failed_targets=failed_targets,
                    automation_exhausted=outcome == "needs_reinforcement" and plan.automation_exhausted,
                    record_source="backfill",
                    evaluated_at=_evaluated_at(plan, cycle),
                )
            )
            result["automatic_created"] += 1
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
