from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MessageRecord:
    id: int
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReportRecord:
    id: int
    conversation_id: int
    conversation_client_id: str | None
    student_id: int
    student_name: str | None
    status: str
    ai_score: float
    ai_summary: str
    analysis: dict[str, object] | None
    messages: tuple[MessageRecord, ...]
    teacher_score: float | None
    teacher_feedback: str | None
    reviewer_id: int | None
    review_topic_codes: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReportSummaryRecord:
    id: int
    conversation_id: int
    conversation_client_id: str
    student_id: int
    student_name: str
    status: str
    ai_score: float
    teacher_score: float | None
    message_preview: str
    message_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReportSummaryPage:
    items: tuple[ReportSummaryRecord, ...]
    total: int
    pending_count: int
    reviewed_count: int
    limit: int
    offset: int
