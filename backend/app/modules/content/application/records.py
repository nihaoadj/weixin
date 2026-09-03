from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProblemRecord:
    id: int
    type: str
    title: str
    description: str
    target: str
    target_label: str
    target_ids: tuple[str, ...]
    status: str
    created_at: datetime
    published_at: datetime | None
    content_type: str
    slug: str | None
    specialty: str
    difficulty: str
    estimated_minutes: int
    version: int
    parent_problem_id: int | None
    author_id: int | None
    medical_review_status: str
    capability_tags: tuple[str, ...]
    case_definition: dict[str, object] | None
    rubric: dict[str, object] | None
    answer_count: int = 0
    knowledge_point_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    id: int
    problem_id: int
    reviewer_id: int
    decision: str
    comment: str
    problem_version: int
    case_digest: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProblemCommand:
    type: str
    title: str
    description: str
    target: str
    target_label: str
    target_ids: tuple[str, ...]
    content_type: str
    slug: str | None
    specialty: str
    difficulty: str
    estimated_minutes: int
    version: int
    parent_problem_id: int | None
    case_definition: dict[str, object] | None
    rubric: dict[str, object] | None
    capability_tags: tuple[str, ...]
    status: str | None = None
    knowledge_point_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseDraftResult:
    payload: dict[str, object]
    generation_mode: str
    safety_notice: str
    model_name: str = "deterministic-fallback"
    prompt_version: str = "case-v2"
    fallback_used: bool = True
    failure_reason: str | None = None
    latency_ms: int = 0


@dataclass(frozen=True, slots=True)
class KnowledgeCardContributionRecord:
    id: int
    point_code: str
    owner_id: int
    class_code: str | None
    version: int
    card_type: str
    prompt: str
    options: tuple[str, ...]
    correct_option: int | None
    explanation: str
    reference: str
    status: str
    reviewer_id: int | None
    review_comment: str
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeCardContributionCommand:
    point_code: str
    class_code: str | None
    card_type: str
    prompt: str
    options: tuple[str, ...]
    correct_option: int | None
    explanation: str
    reference: str
