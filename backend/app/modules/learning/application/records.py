from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.training.public import AssessmentSourceContract, CaseSourceContract


@dataclass(frozen=True, slots=True)
class LearningSourceRecord:
    attempt: CaseSourceContract
    assessment: AssessmentSourceContract


@dataclass(frozen=True, slots=True)
class TransferCaseRecord:
    problem_id: int
    difficulty: str
    blueprint: dict[str, object]


@dataclass(frozen=True, slots=True)
class LearningTaskDraft:
    position: int
    task_type: str
    dimension_id: str
    stage_id: str | None
    problem_id: int | None
    source_attempt_id: int | None
    public_definition: dict[str, object]
    private_rubric: dict[str, object]
    blueprint_id: str | None = None
    blueprint_digest: str | None = None


@dataclass(frozen=True, slots=True)
class PracticeGenerationResult:
    public_definition: dict[str, object]
    fallback_used: bool
    failure_reason: str | None
    model_name: str
    prompt_version: str
    latency_ms: int


@dataclass(frozen=True, slots=True)
class LearningPlanDraft:
    student_id: int
    source_assessment_id: int
    target_dimension_ids: tuple[str, ...]
    due_at: datetime
    generation_mode: str
    model_name: str
    prompt_version: str
    fallback_used: bool
    failure_reason: str | None
    tasks: tuple[LearningTaskDraft, ...]


@dataclass(frozen=True, slots=True)
class LearningTaskRecord:
    id: int
    plan_id: int
    position: int
    task_type: str
    dimension_id: str
    stage_id: str | None
    problem_id: int | None
    source_attempt_id: int | None
    status: str
    public_definition: dict[str, object]
    private_rubric: dict[str, object]
    blueprint_id: str | None
    blueprint_digest: str | None
    started_at: datetime | None
    completed_at: datetime | None
    previous_status: str | None = None
    attempt: LearningTaskAttemptRecord | None = None
    cycle_number: int = 1
    target_type: str = ""
    target_code: str = ""
    variant_code: str = ""
    plan_source_type: str = ""
    plan_source_id: int | None = None
    plan_source_context: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class LearningTaskAttemptRecord:
    id: int
    task_id: int
    student_id: int
    status: str
    answer: dict[str, object]
    score: float | None
    evidence: tuple[str, ...]
    feedback: str
    next_step: str
    model_name: str
    prompt_version: str
    fallback_used: bool
    failure_reason: str | None
    created_at: datetime
    assessed_at: datetime | None
    public_definition: dict[str, object]


@dataclass(frozen=True, slots=True)
class LearningPlanRecord:
    id: int
    student_id: int
    status: str
    source_assessment_id: int | None
    target_dimension_ids: tuple[str, ...]
    due_at: datetime
    generation_mode: str
    model_name: str
    prompt_version: str
    fallback_used: bool
    failure_reason: str | None
    created_at: datetime
    completed_at: datetime | None
    superseded_at: datetime | None
    tasks: tuple[LearningTaskRecord, ...]
    source_type: str = "case_assessment"
    source_id: int | None = None
    source_context: dict[str, object] | None = None
    current_cycle: int = 1
    verification_status: str = "not_ready"
    automation_exhausted: bool = False
    decision_policy_version: str = ""
    decision_basis: dict[str, object] | None = None
    evaluated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NotificationRecord:
    id: int
    type: str
    entity_type: str
    entity_id: int | str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RecentAssessmentRecord:
    attempt_id: int
    total_score: float
    dimensions: tuple[dict[str, object], ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PracticeMasteryRecord:
    dimension_id: str
    average_score: float
    attempt_count: int


@dataclass(frozen=True, slots=True)
class LearningProfileRecord:
    formal_dimensions: tuple[dict[str, object], ...]
    recent_assessments: tuple[RecentAssessmentRecord, ...]
    practice_mastery: tuple[PracticeMasteryRecord, ...]
    active_plan: LearningPlanRecord | None
    unread_count: int
