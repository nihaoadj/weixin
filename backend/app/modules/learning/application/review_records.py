from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReviewStateRecord:
    id: int
    student_id: int
    card_code: str
    point_code: str
    due_at: datetime
    interval_days: int
    ease: float
    repetitions: int
    lapses: int
    last_rating: str | None
    last_reviewed_at: datetime | None


@dataclass(frozen=True, slots=True)
class ReviewItemRecord:
    id: int
    point_code: str
    card_code: str | None
    source_type: str
    source_id: str
    note: str
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewCardPrompt:
    card_code: str
    point_code: str
    prompt: str
    options: tuple[str, ...]
    due_at: datetime | None


@dataclass(frozen=True, slots=True)
class SupplementalChoiceCard:
    card_code: str
    point_code: str
    prompt: str
    options: tuple[str, ...]
    correct_option: int
    explanation: str


@dataclass(frozen=True, slots=True)
class ReviewResult:
    card_code: str
    correct: bool
    rating: str
    explanation: str
    next_due_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewDashboard:
    due_count: int
    weak_point_codes: tuple[str, ...]
    items: tuple[ReviewItemRecord, ...]


@dataclass(frozen=True, slots=True)
class KnowledgeMapPoint:
    code: str
    status: str
