from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.learning.application.records import (
    LearningPlanDraft,
    LearningPlanRecord,
    LearningProfileRecord,
    LearningSourceRecord,
    LearningTaskAttemptRecord,
    LearningTaskRecord,
    NotificationRecord,
    PracticeGenerationResult,
    TransferCaseRecord,
)
from app.modules.training.public import CaseAttemptContract
from app.shared.actor import Actor


class LearningRepository(Protocol):
    def find_source(self, student_id: int, attempt_id: int) -> LearningSourceRecord | None: ...

    def find_plan_by_assessment(self, student_id: int, assessment_id: int) -> LearningPlanRecord | None: ...

    def find_active_plan(self, student_id: int) -> LearningPlanRecord | None: ...

    def find_plan(self, student_id: int, plan_id: int) -> LearningPlanRecord | None: ...

    def find_task(self, student_id: int, task_id: int) -> LearningTaskRecord | None: ...

    def find_task_attempt(self, student_id: int, attempt_id: int) -> LearningTaskAttemptRecord | None: ...

    def find_case_attempt_for_task(self, student_id: int, task_id: int) -> int | None: ...

    def find_transfer_case(
        self, source_problem_id: int, source_difficulty: str, dimension_id: str, student: Actor
    ) -> TransferCaseRecord | None: ...

    def create_plan(self, draft: LearningPlanDraft) -> LearningPlanRecord: ...

    def mark_task_started(self, student_id: int, task_id: int, started_at: datetime) -> LearningTaskRecord: ...

    def create_micro_attempt(self, student_id: int, task_id: int) -> LearningTaskAttemptRecord: ...

    def assess_micro_task(
        self,
        student_id: int,
        task_id: int,
        attempt_id: int,
        answer: dict[str, object],
        score: float,
        evidence: list[str],
        feedback: str,
        next_step: str,
    ) -> LearningTaskAttemptRecord: ...

    def mark_task_completed(self, student_id: int, task_id: int, completed_at: datetime) -> None: ...

    def complete_plan(self, student_id: int, plan_id: int, completed_at: datetime) -> LearningPlanRecord: ...

    def add_notification(
        self, student_id: int, plan_id: int, kind: str, title: str, body: str
    ) -> NotificationRecord | None: ...

    def list_notifications(self, student_id: int, unread_only: bool, limit: int) -> tuple[NotificationRecord, ...]: ...

    def unread_count(self, student_id: int) -> int: ...

    def mark_notification_read(self, student_id: int, notification_id: int, read_at: datetime) -> None: ...

    def mark_all_notifications_read(self, student_id: int, read_at: datetime) -> int: ...

    def profile(self, student_id: int) -> LearningProfileRecord: ...

    def record_ai_call(
        self,
        *,
        student_id: int,
        task: str,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
        learning_task_id: int | None,
        blueprint_id: str | None,
        blueprint_digest: str | None,
    ) -> None: ...


class PracticeGenerator(Protocol):
    def generate(self, blueprint: dict[str, object], weakness_summary: str) -> PracticeGenerationResult: ...


class CaseAttemptPort(Protocol):
    def start(
        self, actor: Actor, problem_id: int, retry_of_id: int | None, learning_task_id: int
    ) -> CaseAttemptContract: ...

    def get(self, actor: Actor, attempt_id: int) -> CaseAttemptContract: ...


__all__ = ["CaseAttemptPort", "LearningRepository", "PracticeGenerator"]
