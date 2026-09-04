"""Persistence orchestration for the pure, fail-closed PBL mastery rules."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.modules.learning.infrastructure.models import LearningPlan, LearningPlanEvaluation, StudentNotification

POLICY_VERSION = "pbl-mastery-v1"
MASTERY_THRESHOLD = 70.0


def _dimension_scores(task) -> dict[str, float]:
    if not task.attempt or not isinstance(task.attempt.answer, dict):
        return {}
    value = task.attempt.answer.get("dimension_scores")
    if not isinstance(value, dict):
        return {}
    return {str(key): float(score) for key, score in value.items() if isinstance(score, int | float)}


def _checks(plan: LearningPlan, cycle_number: int | None = None) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    cycle = cycle_number or plan.current_cycle
    for task in plan.tasks:
        if task.cycle_number != cycle or task.status in {"inactive", "skipped"}:
            continue
        attempt = task.attempt
        evidence_present = bool(attempt and attempt.evidence)
        if task.task_type == "discussion":
            passed = task.status == "completed" and attempt is not None
            checks.append(
                {
                    "target_type": "discussion",
                    "target_code": task.target_code,
                    "task_id": task.id,
                    "threshold": None,
                    "score": None,
                    "evidence_present": evidence_present,
                    "passed": passed and evidence_present,
                }
            )
        elif task.task_type == "retest":
            score = attempt.score if attempt else None
            checks.append(
                {
                    "target_type": task.target_type,
                    "target_code": task.target_code,
                    "task_id": task.id,
                    "threshold": 100,
                    "score": score,
                    "evidence_present": evidence_present,
                    "passed": score == 100 and evidence_present,
                }
            )
        elif task.task_type == "micro_drill":
            score = attempt.score if attempt else None
            checks.append(
                {
                    "target_type": task.target_type,
                    "target_code": task.target_code,
                    "task_id": task.id,
                    "threshold": MASTERY_THRESHOLD,
                    "score": score,
                    "evidence_present": evidence_present,
                    "passed": score is not None and score >= MASTERY_THRESHOLD and evidence_present,
                }
            )
        elif task.task_type == "focused_retry":
            scores = _dimension_scores(task)
            targets = task.public_definition.get("target_dimension_ids", plan.target_dimension_ids)
            for dimension in targets:
                score = scores.get(str(dimension))
                checks.append(
                    {
                        "target_type": "case_dimension",
                        "target_code": str(dimension),
                        "activation_target_type": "case_retry",
                        "activation_target_code": task.target_code,
                        "task_id": task.id,
                        "threshold": MASTERY_THRESHOLD,
                        "score": score,
                        "evidence_present": evidence_present,
                        "passed": score is not None and score >= MASTERY_THRESHOLD and evidence_present,
                    }
                )
    return checks


def _notify(session, plan: LearningPlan, kind: str, title: str, body: str) -> None:
    key = f"pbl:{plan.id}:{kind}:cycle:{plan.current_cycle}"
    if session.scalar(select(StudentNotification.id).where(StudentNotification.dedupe_key == key)) is None:
        session.add(
            StudentNotification(
                student_id=plan.student_id,
                type=kind,
                entity_id=plan.id,
                title=title,
                body=body,
                dedupe_key=key,
            )
        )


def _record_evaluation(
    session, plan: LearningPlan, basis: dict[str, object], result: str, evaluated_at: datetime
) -> None:
    existing = session.scalar(
        select(LearningPlanEvaluation.id).where(
            LearningPlanEvaluation.plan_id == plan.id,
            LearningPlanEvaluation.cycle_number == int(basis["cycle"]),
        )
    )
    if existing is not None:
        return
    session.add(
        LearningPlanEvaluation(
            plan_id=plan.id,
            cycle_number=int(basis["cycle"]),
            policy_version=str(basis["policy_version"]),
            result=result,
            checks=list(basis["checks"]),
            failed_targets=list(basis["failed_targets"]),
            automation_exhausted=plan.automation_exhausted,
            record_source="runtime",
            evaluated_at=evaluated_at,
        )
    )


def evaluate_pbl_plan(session, plan: LearningPlan, now: datetime | None = None) -> bool:
    """Evaluate only a fully submitted active cycle; return whether state changed."""

    if plan.source_type != "pbl_suggestion" or plan.status != "active":
        return False
    active = [
        task
        for task in plan.tasks
        if task.cycle_number == plan.current_cycle and task.status not in {"inactive", "skipped"}
    ]
    if not active or any(task.status != "completed" for task in active):
        return False

    evaluated_at = now or datetime.now(UTC)
    checks = _checks(plan)
    failed = [item for item in checks if not item["passed"]]
    basis = {
        "decision_source": "automatic",
        "policy_version": POLICY_VERSION,
        "cycle": plan.current_cycle,
        "checks": checks,
        "failed_targets": [
            {
                "target_type": item.get("activation_target_type", item["target_type"]),
                "target_code": item.get("activation_target_code", item["target_code"]),
            }
            for item in failed
            if item["target_type"] != "discussion"
        ],
    }
    plan.decision_policy_version = POLICY_VERSION
    plan.evaluated_at = evaluated_at
    plan.version += 1

    if not failed:
        plan.status = "completed"
        plan.completed_at = evaluated_at
        plan.verification_status = "improved"
        plan.automation_exhausted = False
        plan.decision_basis = {**basis, "result": "improved"}
        _record_evaluation(session, plan, basis, "improved", evaluated_at)
        _notify(session, plan, "pbl_mastery_improved", "PBL 巩固已达标", "系统已根据逐项目标确认本轮学习达标。")
        return True

    if plan.current_cycle < plan.max_cycles:
        failed_keys = {
            (str(item["target_type"]), str(item["target_code"])) for item in basis["failed_targets"]
        }
        plan.current_cycle += 1
        plan.verification_status = "not_ready"
        plan.decision_basis = {**basis, "result": "next_cycle_activated"}
        _record_evaluation(session, plan, basis, "next_cycle_activated", evaluated_at)
        for task in plan.tasks:
            if task.cycle_number != plan.current_cycle or task.status != "inactive":
                continue
            key = (task.target_type, task.target_code)
            task.status = "pending" if task.target_type == "discussion" or key in failed_keys else "skipped"
        _notify(
            session,
            plan,
            "pbl_reinforcement_activated",
            "第二轮差异化巩固已开启",
            "系统仅激活首轮未达标目标的等价变式任务。",
        )
        return True

    plan.status = "completed"
    plan.completed_at = evaluated_at
    plan.verification_status = "needs_reinforcement"
    plan.automation_exhausted = True
    plan.decision_basis = {**basis, "result": "needs_reinforcement", "offline_support_required": True}
    _record_evaluation(session, plan, basis, "needs_reinforcement", evaluated_at)
    _notify(
        session,
        plan,
        "pbl_automation_exhausted",
        "自动巩固轮次已结束",
        "仍有目标未达标，请结合线下支持继续学习。",
    )
    return True


__all__ = ["MASTERY_THRESHOLD", "POLICY_VERSION", "evaluate_pbl_plan"]
