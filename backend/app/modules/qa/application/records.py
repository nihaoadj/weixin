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
class ConversationRecord:
    id: int
    client_id: str
    student_id: int
    created_at: datetime
    updated_at: datetime
    messages: tuple[MessageRecord, ...]
    topic_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversationSummaryRecord:
    id: int
    client_id: str
    message_preview: str
    message_count: int
    report_id: int | None
    report_status: str | None
    created_at: datetime
    updated_at: datetime
    topic_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversationSummaryPage:
    items: tuple[ConversationSummaryRecord, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class MessageInput:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class StudentQuestionRecord:
    id: int
    type: str
    title: str
    description: str
    published_at: datetime
    answered: bool
    topic_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QuestionThreadRecord:
    question_id: int
    messages: tuple[MessageRecord, ...]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ChatHistoryMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class MedicalChatRequestRecord:
    prompt: str
    mode: str | None
    messages: tuple[ChatHistoryMessage, ...]
    topic_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MedicalChatResult:
    content: str
    fallback_used: bool
    failure_reason: str | None
    model_name: str
    prompt_version: str
    latency_ms: int
