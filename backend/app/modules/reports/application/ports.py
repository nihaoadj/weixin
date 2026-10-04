from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.classroom.public import ClassroomScope
from app.modules.reports.application.records import ReportRecord, ReportSummaryPage
from app.shared.actor import Actor


@dataclass(frozen=True, slots=True)
class ReportDraftCommand:
    conversation_id: int
    ai_score: float
    ai_summary: str
    analysis: dict[str, object] | None


@dataclass(frozen=True, slots=True)
class ReportSubmitCommand:
    class_id: int


@dataclass(frozen=True, slots=True)
class ReportReviewCommand:
    teacher_score: float
    teacher_feedback: str
    review_topic_codes: tuple[str, ...] = ()


class ReportClassroomScope(Protocol):
    """Narrow classroom port consumed by reports; resolved in reports wiring."""

    def owned_class_ids(self, teacher_id: int) -> tuple[int, ...]: ...

    def owned(self, teacher_id: int, class_id: int) -> ClassroomScope | None: ...

    def active_classes_for_student(self, student_id: int) -> tuple[ClassroomScope, ...]: ...


class ReportRepository(Protocol):
    def conversation_owner(self, conversation_id: int) -> int | None: ...

    def find_for_student(self, report_id: int, student_id: int) -> ReportRecord | None: ...

    def find_for_student_by_conversation(self, conversation_id: int, student_id: int) -> ReportRecord | None: ...

    def find_visible(
        self, actor: Actor, report_id: int, owned_class_ids: tuple[int, ...] | None = None
    ) -> ReportRecord | None: ...

    def find_by_client_id(
        self, actor: Actor, client_id: str, owned_class_ids: tuple[int, ...] | None = None
    ) -> ReportRecord | None: ...

    def list_full(self, actor: Actor, owned_class_ids: tuple[int, ...] | None = None) -> tuple[ReportRecord, ...]: ...

    def list_summaries(
        self, actor: Actor, limit: int, offset: int, owned_class_ids: tuple[int, ...] | None = None
    ) -> ReportSummaryPage: ...

    def save_draft(self, report_id: int | None, student_id: int, command: ReportDraftCommand) -> int: ...

    def submit(self, report_id: int, student_id: int, class_id: int, class_name_snapshot: str) -> None: ...

    def review(self, report_id: int, reviewer_id: int, command: ReportReviewCommand) -> None: ...
