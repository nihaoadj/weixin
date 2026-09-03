from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.qa.application.records import (
    ConversationRecord,
    ConversationSummaryPage,
    MedicalChatRequestRecord,
    MedicalChatResult,
    MessageInput,
    QuestionThreadRecord,
    StudentQuestionRecord,
)
from app.shared.actor import Actor


@dataclass(frozen=True, slots=True)
class ConversationCommand:
    client_id: str
    messages: tuple[MessageInput, ...]
    topic_codes: tuple[str, ...] = ()


class ConversationRepository(Protocol):
    def list_summaries(
        self, student_id: int, limit: int, offset: int, knowledge_point_code: str | None = None
    ) -> ConversationSummaryPage: ...

    def find_by_client(self, client_id: str, student_id: int) -> ConversationRecord | None: ...

    def find_by_id(self, conversation_id: int, student_id: int) -> ConversationRecord | None: ...

    def list_full(self, student_id: int, knowledge_point_code: str | None = None) -> tuple[ConversationRecord, ...]: ...

    def set_topics(
        self, student_id: int, conversation_id: int, topic_codes: tuple[str, ...]
    ) -> ConversationRecord | None: ...

    def upsert(self, student_id: int, command: ConversationCommand) -> ConversationRecord: ...


@dataclass(frozen=True, slots=True)
class QuestionThreadCommand:
    messages: tuple[MessageInput, ...]


class QuestionRepository(Protocol):
    def class_codes(self, student_id: int) -> set[str]: ...

    def list_student_questions(self, student: Actor, class_codes: set[str]) -> tuple[StudentQuestionRecord, ...]: ...

    def find_student_question(
        self, student: Actor, problem_id: int, class_codes: set[str]
    ) -> StudentQuestionRecord | None: ...

    def find_thread(self, problem_id: int, student_id: int) -> QuestionThreadRecord | None: ...

    def upsert_thread(
        self, problem_id: int, student_id: int, command: QuestionThreadCommand
    ) -> QuestionThreadRecord: ...


class MedicalChatGateway(Protocol):
    def reply(self, request: MedicalChatRequestRecord) -> MedicalChatResult: ...


class MedicalChatAudit(Protocol):
    def record_ai_call(
        self,
        *,
        user_id: int | None,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
    ) -> None: ...
