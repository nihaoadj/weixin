from __future__ import annotations

from typing import Protocol

from app.modules.learning.application.records import (
    LearningPlanRecord,
    LearningProfileRecord,
    LearningTaskAttemptRecord,
    LearningTaskRecord,
    NotificationRecord,
)
from app.modules.learning.application.review_records import (
    KnowledgeMapPoint,
    ReviewCardPrompt,
    ReviewDashboard,
    ReviewItemRecord,
    ReviewResult,
)
from app.modules.training.public import CaseAttemptContract, case_attempt_view


class PblLearningPort(Protocol):
    def create(
        self, student_ids: tuple[int, ...], source_id: int, context: dict, resources: tuple[dict, ...]
    ) -> tuple[int, ...]: ...
    def list(
        self, *, student_id: int | None = None, teacher_id: int | None = None, session_id: int | None = None
    ) -> tuple[dict, ...]: ...
    def submit(self, student_id: int, task_id: int, submission_id: str, answer: dict) -> dict: ...
    def notify(self, student_id: int, entity_id: int, title: str, body: str, dedupe_key: str) -> None: ...


def task_view(task: LearningTaskRecord) -> dict[str, object]:
    return {
        "id": task.id,
        "position": task.position,
        "task_type": task.task_type,
        "dimension_id": task.dimension_id,
        "stage_id": task.stage_id,
        "problem_id": task.problem_id,
        "status": task.status,
        "public_definition": task.public_definition,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }


def plan_view(plan: LearningPlanRecord) -> dict[str, object]:
    return {
        "id": plan.id,
        "status": plan.status,
        "source_assessment_id": plan.source_assessment_id,
        "source_type": plan.source_type,
        "source_id": plan.source_id,
        "target_dimension_ids": list(plan.target_dimension_ids),
        "due_at": plan.due_at,
        "generation_mode": plan.generation_mode,
        "model_name": plan.model_name,
        "prompt_version": plan.prompt_version,
        "fallback_used": plan.fallback_used,
        "failure_reason": plan.failure_reason,
        "created_at": plan.created_at,
        "completed_at": plan.completed_at,
        "superseded_at": plan.superseded_at,
        "tasks": [task_view(task) for task in sorted(plan.tasks, key=lambda item: item.position)],
    }


def task_attempt_view(attempt: LearningTaskAttemptRecord) -> dict[str, object]:
    return {
        "id": attempt.id,
        "task_id": attempt.task_id,
        "status": attempt.status,
        "answer": attempt.answer,
        "public_definition": attempt.public_definition,
        "score": attempt.score,
        "evidence": list(attempt.evidence),
        "feedback": attempt.feedback,
        "next_step": attempt.next_step,
        "created_at": attempt.created_at,
        "assessed_at": attempt.assessed_at,
    }


def start_view(task: LearningTaskRecord, attempt: CaseAttemptContract | LearningTaskAttemptRecord) -> dict[str, object]:
    return {
        "mode": "micro_drill" if task.task_type == "micro_drill" else "case_attempt",
        "task": task_view(task),
        "attempt": (
            case_attempt_view(attempt) if isinstance(attempt, CaseAttemptContract) else task_attempt_view(attempt)
        ),
    }


def notification_view(item: NotificationRecord) -> dict[str, object]:
    return {
        "id": item.id,
        "type": item.type,
        "entity_type": item.entity_type,
        "entity_id": item.entity_id,
        "title": item.title,
        "body": item.body,
        "read_at": item.read_at,
        "created_at": item.created_at,
    }


def profile_view(profile: LearningProfileRecord) -> dict[str, object]:
    return {
        "formal_dimensions": list(profile.formal_dimensions),
        "recent_assessments": [
            {"attempt_id": item.attempt_id, "total_score": item.total_score, "created_at": item.created_at}
            for item in profile.recent_assessments
        ],
        "practice_mastery": {
            item.dimension_id: {"average_score": round(item.average_score, 1), "attempt_count": item.attempt_count}
            for item in profile.practice_mastery
        },
        "active_plan": plan_view(profile.active_plan) if profile.active_plan else None,
        "unread_count": profile.unread_count,
    }


def review_card_view(card: ReviewCardPrompt) -> dict[str, object]:
    return {
        "card_code": card.card_code,
        "point_code": card.point_code,
        "prompt": card.prompt,
        "options": list(card.options),
        "due_at": card.due_at,
    }


def review_item_view(item: ReviewItemRecord) -> dict[str, object]:
    return {
        "id": item.id,
        "point_code": item.point_code,
        "card_code": item.card_code,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "note": item.note,
        "active": item.active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def review_dashboard_view(dashboard: ReviewDashboard) -> dict[str, object]:
    return {
        "due_count": dashboard.due_count,
        "weak_point_codes": list(dashboard.weak_point_codes),
        "items": [review_item_view(item) for item in dashboard.items],
    }


def knowledge_map_view(items: tuple[KnowledgeMapPoint, ...]) -> dict[str, object]:
    return {"items": [{"code": item.code, "status": item.status} for item in items]}


def review_result_view(result: ReviewResult) -> dict[str, object]:
    return {
        "card_code": result.card_code,
        "correct": result.correct,
        "rating": result.rating,
        "explanation": result.explanation,
        "due_at": result.next_due_at,
    }
