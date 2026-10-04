from __future__ import annotations

from typing import Protocol

from app.modules.content.application.records import (
    CaseDraftResult,
    KnowledgeCardContributionRecord,
    ProblemCommand,
    ProblemRecord,
    ReviewRecord,
)
from app.shared.actor import Actor


class ProblemRepository(Protocol):
    def teacher_action_counts(self, teacher_id: int, *, medical_reviewer: bool) -> dict[str, int | None]: ...

    def class_codes(self, student_id: int) -> set[str]: ...

    def list_all(self) -> tuple[ProblemRecord, ...]: ...

    def list_visible_for_student(self, student: Actor, class_codes: set[str]) -> tuple[ProblemRecord, ...]: ...

    def get(self, problem_id: int) -> ProblemRecord | None: ...

    def create(self, teacher_id: int, command: ProblemCommand) -> ProblemRecord: ...

    def update(self, problem_id: int, teacher_id: int, command: ProblemCommand) -> ProblemRecord: ...

    def delete(self, problem_id: int) -> None: ...

    def answer_counts(self, problem_ids: list[int]) -> dict[int, int]: ...

    def review_view(self, problem_id: int) -> tuple[ProblemRecord, str | None, tuple[ReviewRecord, ...]]: ...

    def review_history(self, problem_id: int) -> tuple[ReviewRecord, ...]: ...

    def get_knowledge_card(self, card_id: int) -> KnowledgeCardContributionRecord | None: ...


class CaseDraftGenerator(Protocol):
    def generate(self, topic: str, learner_level: str, objectives: list[str], teacher_id: int) -> CaseDraftResult: ...


class CaseDraftAudit(Protocol):
    def record_ai_call(
        self,
        *,
        user_id: int,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
    ) -> None: ...
