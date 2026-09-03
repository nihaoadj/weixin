from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.training.domain.state import AssessmentCandidate


@dataclass(frozen=True, slots=True)
class TrainingProblemRecord:
    id: int
    slug: str | None
    difficulty: str
    version: int
    status: str
    content_type: str
    author_id: int | None
    target: str
    target_ids: tuple[str, ...]
    case_definition: dict[str, object]
    rubric: dict[str, object]


@dataclass(frozen=True, slots=True)
class MessageRecord:
    id: int
    role: str
    content: str
    created_at: datetime
    revealed_fact_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StageSubmissionRecord:
    id: int
    stage_id: str
    answer: dict[str, object]
    feedback: str
    inherited_from_id: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AssessmentRecord:
    id: int
    attempt_id: int
    total_score: float
    dimensions: tuple[dict[str, object], ...]
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    next_steps: tuple[str, ...]
    summary: str
    focus_stage: str
    model_name: str
    prompt_version: str
    fallback_used: bool
    failure_reason: str | None
    latency_ms: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AssessmentDraft:
    total_score: float
    dimensions: tuple[dict[str, object], ...]
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    next_steps: tuple[str, ...]
    summary: str
    focus_stage: str
    model_name: str
    prompt_version: str
    fallback_used: bool
    failure_reason: str | None
    latency_ms: int


@dataclass(frozen=True, slots=True)
class AssessmentGenerationResult:
    candidates: tuple[AssessmentCandidate, ...]
    fallback_used: bool
    failure_reason: str | None
    model_name: str
    prompt_version: str
    latency_ms: int


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    id: int
    problem_id: int
    problem_version: int
    status: str
    current_stage: str
    retry_of_id: int | None
    focus_stage: str | None
    learning_task_id: int | None
    started_at: datetime
    completed_at: datetime | None
    assessed_at: datetime | None
    problem: TrainingProblemRecord
    messages: tuple[MessageRecord, ...]
    submissions: tuple[StageSubmissionRecord, ...]
    assessment: AssessmentRecord | None


@dataclass(frozen=True, slots=True)
class AttemptSummaryRecord:
    id: int
    problem_id: int
    status: str
    current_stage: str
    focus_stage: str | None
    total_score: float | None
    started_at: datetime


@dataclass(frozen=True, slots=True)
class PatientReplyResult:
    reply: str
    revealed_fact_ids: tuple[str, ...]
    response_mode: str
    fallback_used: bool
    failure_reason: str | None
    model_name: str
    prompt_version: str
    latency_ms: int


@dataclass(frozen=True, slots=True)
class PatientMessageResult:
    message: MessageRecord
    response_mode: str
