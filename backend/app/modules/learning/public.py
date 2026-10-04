from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from app.modules.learning.application.records import (
    LearningPlanRecord,
    LearningProfileRecord,
    LearningTaskAttemptRecord,
    LearningTaskRecord,
    NotificationRecord,
)
from app.modules.learning.application.review_records import (
    KnowledgeMapPoint,
)
from app.modules.training.public import CaseAttemptContract, case_attempt_view

AuthorityLevel = Literal["personal_unverified", "reviewed_practice", "formal_instruction", "pbl_formal"]
VisibilityScope = Literal["student_only", "class_aggregate", "class_detail"]
EvidenceEventKind = Literal["engagement", "assessment", "outcome"]
EvidenceMetricKind = Literal["knowledge", "dimension", "participation", "goal"]
EvidenceMetricResult = Literal["observed", "correct", "incorrect", "partial", "passed", "failed"]
EvidenceSourceType = Literal[
    "qa_topic_activity",
    "self_pbl_completion",
    "ai_personal_practice",
    "reviewed_question_attempt",
    "case_assessment",
    "pbl_task_attempt",
    "pbl_cycle_evaluation",
    "classroom_final_test",
    "private_final_test",
]


class CompletionLearningRoutePort(Protocol):
    def ensure_shell(self, context: dict) -> dict: ...
    def review_locator(self, teacher_id: int, participation_id: int) -> dict | None: ...
    def classroom_progress(self, teacher_id: int, class_id: int, session_id: int) -> list[dict]: ...


class LearningRouteGenerationDispatchPort(Protocol):
    def generate(self, route_id: str, component: str = "route", token: str | None = None) -> None: ...


class LearningRouteResultReadPort(Protocol):
    def teacher_results(self, teacher_id: int, filters: dict) -> dict: ...

    def completed_for_teacher(
        self, teacher_id: int, class_ids: tuple[int, ...], start: datetime, end: datetime
    ) -> tuple[dict, ...]: ...

    def published_for_teacher(
        self, teacher_id: int, class_ids: tuple[int, ...], start: datetime, end: datetime, session_id: int | None = None
    ) -> tuple[dict, ...]: ...

    def classroom_progress_for_teacher(self, teacher_id: int, class_id: int, session_id: int) -> tuple[dict, ...]: ...


@dataclass(frozen=True, slots=True)
class StudentInsightQuestionScore:
    target_code: str
    earned_points: float
    possible_points: float


@dataclass(frozen=True, slots=True)
class StudentInsightTestResult:
    result_id: str
    score: float
    correct_count: int
    question_count: int
    completed_at: datetime
    question_scores: tuple[StudentInsightQuestionScore, ...]


@dataclass(frozen=True, slots=True)
class StudentInsightRouteRecord:
    route_id: str
    session_id: int
    source_kind: str
    goal_point_codes: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    route_generation_state: str
    status: str
    completed_steps: int
    total_steps: int
    reading_seconds: int
    current_step_kind: str | None
    current_case_phase: str | None
    result: StudentInsightTestResult | None
    title: str = "学习路线"


class StudentInsightRouteReadPort(Protocol):
    def student_insight_routes(self, student_id: int) -> tuple[StudentInsightRouteRecord, ...]: ...


class RouteTestQuestionSourcePort(Protocol):
    def bank_source(self, teacher_id: int, question_id: str) -> dict: ...


def retired_learning_flow():
    from app.shared.errors import AppError

    error = AppError("STATE_CONFLICT", "该旧学习流程已退役，请打开学习计划", 409)
    error.reason = "RETIRED_FLOW"
    raise error


@dataclass(frozen=True, slots=True)
class LearningEvidenceMetricCommand:
    metric_kind: EvidenceMetricKind
    metric_code: str
    normalized_score: float | None = None
    result: EvidenceMetricResult = "observed"
    evidence_present: bool = True


@dataclass(frozen=True, slots=True)
class LearningEvidenceCommand:
    student_id: int
    class_id: int | None
    source_type: EvidenceSourceType
    source_id: str
    source_version: int
    authority_level: AuthorityLevel
    visibility_scope: VisibilityScope
    event_kind: EvidenceEventKind
    occurred_at: datetime
    dedupe_key: str
    contract_version: int = 1
    metrics: tuple[LearningEvidenceMetricCommand, ...] = ()


@dataclass(frozen=True, slots=True)
class LearningEvidenceMetricRecord:
    id: int
    metric_kind: str
    metric_code: str
    normalized_score: float | None
    result: str
    evidence_present: bool


@dataclass(frozen=True, slots=True)
class LearningEvidenceEventRecord:
    id: int
    student_id: int
    class_id: int | None
    source_type: str
    source_id: str
    source_version: int
    authority_level: str
    visibility_scope: str
    event_kind: str
    occurred_at: datetime
    dedupe_key: str
    contract_version: int
    created_at: datetime
    metrics: tuple[LearningEvidenceMetricRecord, ...]


class LearningEvidencePort(Protocol):
    def append(self, command: LearningEvidenceCommand) -> LearningEvidenceEventRecord: ...

    def append_and_commit(self, command: LearningEvidenceCommand) -> LearningEvidenceEventRecord: ...


class LearningEvidenceReadPort(Protocol):
    def list_events(
        self,
        student_ids: tuple[int, ...],
        start: datetime,
        end: datetime,
        *,
        include_student_only: bool = True,
    ) -> tuple[LearningEvidenceEventRecord, ...]: ...


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


def knowledge_map_view(items: tuple[KnowledgeMapPoint, ...]) -> dict[str, object]:
    return {"items": [{"code": item.code, "status": item.status} for item in items]}
