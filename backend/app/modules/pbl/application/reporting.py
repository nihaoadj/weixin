from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from app.modules.content.public import knowledge_point_view
from app.modules.pbl.application.records import (
    PblReportParticipationRecord,
    PblSessionRecord,
    PblSnapshotRecord,
    PblTeacherFeedbackRecord,
)
from app.modules.pbl.domain.catalog import PATHOLOGY_POINTS

PHASES = ("problem_framing", "hypothesis", "evidence", "synthesis")
PHASE_LABELS = {
    "problem_framing": "明确问题",
    "hypothesis": "提出假设",
    "evidence": "讨论证据",
    "synthesis": "总结解释",
}
DIMENSION_LABELS = {
    "information_gathering": "信息采集",
    "problem_representation": "问题表征",
    "differential_diagnosis": "鉴别诊断",
    "evidence_reasoning": "证据推理",
    "test_selection": "检查合理性",
    "management_safety": "处置与安全意识",
}
REPORT_STATUSES = (
    "discussing",
    "awaiting_learning",
    "learning_cycle_1",
    "learning_cycle_2",
    "improved",
    "support_needed",
)


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value).timestamp()


def _point_label(code: str) -> str:
    point = knowledge_point_view(code)
    return str(point.get("title")) if point else code


def _target_label(target_type: str, code: str) -> str:
    if target_type == "knowledge_gap":
        return _point_label(code)
    if target_type in {"reasoning_issue", "case_dimension"}:
        return DIMENSION_LABELS.get(code, code)
    if target_type == "case_retry":
        return "完整病例重练"
    return "正式讨论" if target_type == "discussion" else code


def _report_status(participation, plans: list[dict]) -> str:
    active = [plan for plan in plans if plan.get("status") == "active"]
    if active:
        return (
            "learning_cycle_2" if any(int(plan.get("current_cycle", 1)) >= 2 for plan in active) else "learning_cycle_1"
        )
    if plans and any(plan.get("verification_status") == "needs_reinforcement" for plan in plans):
        return "support_needed"
    if plans and all(plan.get("verification_status") == "improved" for plan in plans):
        return "improved"
    if participation and participation.phase_status == "completed":
        return "awaiting_learning"
    return "discussing"


def _next_action(status: str) -> dict[str, str]:
    if status == "discussing":
        return {"kind": "discussion", "label": "继续四阶段讨论"}
    if status in {"learning_cycle_1", "learning_cycle_2"}:
        return {"kind": "tasks", "label": "继续课后学习任务"}
    if status == "awaiting_learning":
        return {"kind": "none", "label": "学习任务待教师审阅发布"}
    if status == "support_needed":
        return {"kind": "none", "label": "回看未达标目标并结合线下支持"}
    return {"kind": "none", "label": "本次必需目标已达标"}


def _summary_text(status: str, phase: str | None, failed_labels: list[str]) -> str:
    if status == "discussing":
        return f"你正在完成“{PHASE_LABELS.get(phase or '', '明确问题')}”，补齐当前阶段证据后会自动进入下一阶段。"
    if status == "awaiting_learning":
        return "四阶段讨论已完成，个人学习线索已经形成，后续任务待教师审阅发布。"
    if status == "learning_cycle_1":
        return "第一轮针对性学习正在进行，完成所有已激活任务后系统会逐项目标判定。"
    if status == "learning_cycle_2":
        suffix = f" 当前继续巩固：{'、'.join(failed_labels)}。" if failed_labels else ""
        return f"第一轮仍有目标未达标，系统已只激活对应的第二轮等价变式。{suffix}".strip()
    if status == "support_needed":
        suffix = f" 仍需巩固：{'、'.join(failed_labels)}。" if failed_labels else ""
        return f"两轮自动巩固已结束，仍有目标需要结合线下支持继续学习。{suffix}".strip()
    return "本次所有必需知识与推理目标均已达到系统规则要求，可以回看证据巩固迁移。"


def _phase_progress(source: PblReportParticipationRecord | None) -> list[dict]:
    if source is None:
        return []
    part = source.participation
    current_index = len(PHASES) if part.phase_status == "completed" else PHASES.index(part.current_phase)
    result = []
    for index, phase in enumerate(PHASES):
        snapshots = [item for item in source.snapshots if item.phase == phase]
        evidence = next(
            (item for item in reversed(snapshots) if item.phase_decision in {"advance", "complete"}),
            snapshots[-1] if snapshots else None,
        )
        state = "completed" if index < current_index else "current" if index == current_index else "pending"
        result.append(
            {
                "phase": phase,
                "label": PHASE_LABELS[phase],
                "state": state,
                "evidence_summary": evidence.phase_evidence_summary if evidence else "",
                "missing_elements": list(evidence.phase_missing_elements) if state == "current" and evidence else [],
                "evidenced_at": evidence.created_at if evidence else None,
            }
        )
    return result


def _ready_snapshot(source: PblReportParticipationRecord | None) -> PblSnapshotRecord | None:
    if source is None or source.participation.phase_status != "completed":
        return None
    return next(
        (
            item
            for item in reversed(source.snapshots)
            if item.status == "ready"
            and item.schema_version in {3, 4}
            and item.phase == "synthesis"
            and item.phase_decision == "complete"
        ),
        None,
    )


def _diagnosis(snapshot: PblSnapshotRecord | None) -> dict:
    if snapshot is None:
        return {"created_at": None, "knowledge_gaps": [], "reasoning_issues": []}
    return {
        "created_at": snapshot.created_at,
        "knowledge_gaps": [
            {
                "id": str(item.get("id", "")),
                "point_code": str(item.get("point_code", "")),
                "label": _point_label(str(item.get("point_code", ""))),
                "summary": str(item.get("summary", "")),
                "confidence": str(item.get("confidence", "medium")),
                "evidence_summary": str(item.get("evidence_summary", "")),
            }
            for item in snapshot.knowledge_gaps
        ],
        "reasoning_issues": [
            {
                "id": str(item.get("id", "")),
                "dimension_id": str(item.get("dimension_id", "")),
                "label": DIMENSION_LABELS.get(str(item.get("dimension_id", "")), str(item.get("dimension_id", ""))),
                "summary": str(item.get("summary", "")),
                "issue_type": str(item.get("issue_type", "")),
                "improvement": str(item.get("improvement", "")),
                "evidence_summary": str(item.get("evidence_summary", "")),
            }
            for item in snapshot.reasoning_issues
        ],
    }


def _sanitize_check(check: dict) -> dict:
    target_type = str(check.get("target_type", ""))
    target_code = str(check.get("target_code", ""))
    return {
        "target_type": target_type,
        "target_code": target_code,
        "label": _target_label(target_type, target_code),
        "threshold": check.get("threshold"),
        "score": check.get("score"),
        "evidence_present": bool(check.get("evidence_present")),
        "passed": bool(check.get("passed")),
    }


def _plan_view(plan: dict, personal_snapshot_ids: set[int]) -> dict:
    context = plan.get("source_context") or {}
    evaluations = [
        {
            "cycle_number": int(item["cycle_number"]),
            "policy_version": str(item["policy_version"]),
            "result": str(item["result"]),
            "checks": [_sanitize_check(check) for check in item.get("checks", [])],
            "failed_targets": [
                {
                    "target_type": str(target.get("target_type", "")),
                    "target_code": str(target.get("target_code", "")),
                    "label": _target_label(str(target.get("target_type", "")), str(target.get("target_code", ""))),
                }
                for target in item.get("failed_targets", [])
            ],
            "automation_exhausted": bool(item.get("automation_exhausted")),
            "record_source": str(item.get("record_source", "runtime")),
            "evaluated_at": item.get("evaluated_at"),
        }
        for item in plan.get("evaluations", [])
    ]
    tasks = []
    for task in plan.get("tasks", []):
        result = task.get("result")
        public_definition = task.get("public_definition") or {}
        tasks.append(
            {
                "id": int(task["id"]),
                "task_type": str(task["task_type"]),
                "status": str(task["status"]),
                "cycle_number": int(task.get("cycle_number", 1)),
                "target_type": str(task.get("target_type", "")),
                "target_code": str(task.get("target_code", "")),
                "target_label": _target_label(str(task.get("target_type", "")), str(task.get("target_code", ""))),
                "prompt": str(public_definition.get("prompt", "")),
                "reference": str(public_definition.get("reference", "")).strip() or None,
                "score": result.get("score") if result else None,
                "feedback": str(result.get("feedback", "")) if result else "",
                "evidence_present": bool(result and result.get("evidence")),
                "submitted_at": result.get("submitted_at") if result else None,
            }
        )
    snapshot_id = int(context.get("snapshot_id") or 0)
    return {
        "id": int(plan["id"]),
        "assignment_basis": "personal" if snapshot_id in personal_snapshot_ids else "classroom",
        "status": str(plan.get("status", "active")),
        "verification_status": str(plan.get("verification_status", "not_ready")),
        "current_cycle": int(plan.get("current_cycle", 1)),
        "max_cycles": int(plan.get("max_cycles", 2)),
        "automation_exhausted": bool(plan.get("automation_exhausted")),
        "decision_policy_version": str(plan.get("decision_policy_version", "")),
        "due_at": plan.get("due_at"),
        "created_at": plan.get("created_at"),
        "tasks": tasks,
        "evaluations": evaluations,
    }


def build_report(
    session: PblSessionRecord,
    source: PblReportParticipationRecord | None,
    plans: list[dict],
    submission: dict | None = None,
    teacher_feedbacks: tuple[PblTeacherFeedbackRecord, ...] = (),
) -> dict:
    participation = source.participation if source else None
    personal_snapshot_ids = {item.id for item in source.snapshots} if source else set()
    safe_plans = [_plan_view(plan, personal_snapshot_ids) for plan in plans]
    status = _report_status(participation, plans)
    snapshot = _ready_snapshot(source)
    diagnosis = _diagnosis(snapshot)
    failed_labels = []
    for plan in safe_plans:
        for evaluation in plan["evaluations"]:
            if evaluation["cycle_number"] == plan["current_cycle"] or evaluation["result"] == "needs_reinforcement":
                failed_labels.extend(target["label"] for target in evaluation["failed_targets"])
    failed_labels = list(dict.fromkeys(failed_labels))
    target_progress = []
    for plan in safe_plans:
        grouped: dict[tuple[str, str], dict] = {}
        for evaluation in plan["evaluations"]:
            for check in evaluation["checks"]:
                if check["target_type"] == "discussion":
                    continue
                key = (check["target_type"], check["target_code"])
                item = grouped.setdefault(
                    key,
                    {
                        "plan_id": plan["id"],
                        "target_type": key[0],
                        "target_code": key[1],
                        "label": check["label"],
                        "cycles": [],
                    },
                )
                item["cycles"].append({"cycle_number": evaluation["cycle_number"], **check})
        target_progress.extend(grouped.values())
    events = [{"type": "discussion_started", "label": "开始 PBL 讨论", "occurred_at": session.created_at}]
    if participation and participation.phase_completed_at:
        events.append(
            {"type": "discussion_completed", "label": "完成四阶段讨论", "occurred_at": participation.phase_completed_at}
        )
    if submission and submission.get("submitted_at"):
        events.append(
            {"type": "submitted_to_teacher", "label": "已提交教师审阅", "occurred_at": submission["submitted_at"]}
        )
    feedback_labels = {
        "feedback_only": ("teacher_feedback", "收到教师反馈"),
        "task_published": ("task_published", "教师已发布正式任务"),
        "closed": ("teacher_feedback", "教师已结束本轮研讨"),
        "follow_up": ("follow_up_feedback", "收到教师补充支持"),
    }
    for feedback in teacher_feedbacks:
        event_type, label = feedback_labels.get(feedback.action_type, ("teacher_feedback", "收到教师反馈"))
        events.append({"type": event_type, "label": label, "occurred_at": feedback.created_at})
    for plan in safe_plans:
        if plan["created_at"]:
            events.append({"type": "tasks_published", "label": "课后学习任务已发布", "occurred_at": plan["created_at"]})
        for evaluation in plan["evaluations"]:
            label = (
                "本轮目标全部达标"
                if evaluation["result"] == "improved"
                else "第二轮差异化巩固已开启"
                if evaluation["result"] == "next_cycle_activated"
                else "自动轮次结束，仍需线下支持"
            )
            events.append(
                {
                    "type": "cycle_evaluated",
                    "label": label,
                    "cycle_number": evaluation["cycle_number"],
                    "occurred_at": evaluation["evaluated_at"],
                }
            )
    events.sort(key=lambda item: _timestamp(item["occurred_at"]))
    timestamps = [item["occurred_at"] for item in events if item["occurred_at"]]
    completed_tasks = sum(task["status"] == "completed" for plan in safe_plans for task in plan["tasks"])
    relevant_tasks = sum(task["status"] not in {"inactive", "skipped"} for plan in safe_plans for task in plan["tasks"])
    context = session.case_context or {}
    return {
        "session": {
            "id": session.id,
            "topic_code": session.topic_code,
            "topic_label": PATHOLOGY_POINTS.get(session.topic_code, session.topic_code),
            "case_title": str(context.get("title") or "PBL 课堂病例"),
            "status": session.status,
            "created_at": session.created_at,
            "closed_at": session.closed_at,
        },
        "status": status,
        "current_phase": participation.current_phase if participation else None,
        "phase_status": participation.phase_status if participation else None,
        "phase_progress": _phase_progress(source),
        "diagnosis": diagnosis,
        "plans": safe_plans,
        "target_progress": target_progress,
        "task_progress": {"completed": completed_tasks, "total": relevant_tasks},
        "summary_text": _summary_text(status, participation.current_phase if participation else None, failed_labels),
        "next_action": _next_action(status),
        "timeline": events,
        "updated_at": max(timestamps, key=_timestamp) if timestamps else session.created_at,
    }


def build_report_page(reports: list[dict], limit: int, offset: int) -> dict:
    reports.sort(key=lambda item: _timestamp(item["updated_at"]), reverse=True)
    status_counts = {status: 0 for status in REPORT_STATUSES}
    target_counts: Counter[tuple[str, str, str]] = Counter()
    completed_personal_discussions = 0
    for report in reports:
        status_counts[report["status"]] += 1
        if report["diagnosis"]["created_at"] is None:
            continue
        completed_personal_discussions += 1
        report_targets: set[tuple[str, str, str]] = set()
        for item in report["diagnosis"]["knowledge_gaps"]:
            report_targets.add(("knowledge_gap", item["point_code"], item["label"]))
        for item in report["diagnosis"]["reasoning_issues"]:
            report_targets.add(("reasoning_issue", item["dimension_id"], item["label"]))
        target_counts.update(report_targets)
    recurring = [
        {"target_type": kind, "target_code": code, "label": label, "occurrences": count}
        for (kind, code, label), count in sorted(
            target_counts.items(), key=lambda item: (-item[1], item[0][2], item[0][1])
        )[:6]
    ]
    priority = {"learning_cycle_2": 0, "learning_cycle_1": 1, "discussing": 2, "awaiting_learning": 3}
    actionable = sorted(
        (item for item in reports if item["status"] in priority),
        key=lambda item: (priority[item["status"]], -_timestamp(item["updated_at"])),
    )
    next_item = actionable[0] if actionable else reports[0] if reports else None
    return {
        "summary": {
            "total_reports": len(reports),
            "completed_personal_discussions": completed_personal_discussions,
            "status_counts": status_counts,
            "recurring_targets": recurring,
            "next_action": (
                {
                    **next_item["next_action"],
                    "session_id": next_item["session"]["id"],
                    "case_title": next_item["session"]["case_title"],
                }
                if next_item
                else None
            ),
        },
        "items": [
            {
                "session": item["session"],
                "status": item["status"],
                "current_phase": item["current_phase"],
                "phase_status": item["phase_status"],
                "knowledge_gap_count": len(item["diagnosis"]["knowledge_gaps"]),
                "reasoning_issue_count": len(item["diagnosis"]["reasoning_issues"]),
                "task_progress": item["task_progress"],
                "summary_text": item["summary_text"],
                "next_action": item["next_action"],
                "updated_at": item["updated_at"],
            }
            for item in reports[offset : offset + limit]
        ],
        "total": len(reports),
        "limit": limit,
        "offset": offset,
    }
