from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ScopeClass:
    id: int
    name: str
    code: str


@dataclass(frozen=True, slots=True)
class ScopeStudent:
    id: int
    external_id: str
    nickname: str
    class_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProblemAnalyticsRecord:
    id: int
    title: str
    slug: str | None
    version: int
    status: str
    content_type: str
    author_id: int | None
    target: str
    target_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AssessmentRecord:
    id: int
    attempt_id: int
    total_score: float
    dimensions: tuple[dict[str, object], ...]
    focus_stage: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AttemptAnalyticsRecord:
    id: int
    student_id: int
    problem_id: int
    status: str
    retry_of_id: int | None
    started_at: datetime
    assessed_at: datetime | None
    assessment: AssessmentRecord | None


@dataclass(frozen=True, slots=True)
class LearningPlanRecord:
    id: int
    status: str
    target_dimension_ids: tuple[str, ...]
    due_at: datetime
    tasks: tuple[tuple[int, str, str], ...]


@dataclass(frozen=True, slots=True)
class PracticeMasteryRecord:
    dimension_id: str
    average_score: float
    attempt_count: int


@dataclass(frozen=True, slots=True)
class KnowledgeAnalyticsRecord:
    participant_count: int
    due_backlog: int
    objective_attempt_count: int
    objective_correct_count: int
    weak_points: tuple[tuple[str, int], ...]
