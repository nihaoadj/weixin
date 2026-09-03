from __future__ import annotations

from typing import Protocol

from app.modules.training.application.records import (
    AssessmentDraft,
    AssessmentGenerationResult,
    AssessmentRecord,
    AttemptRecord,
    AttemptSummaryRecord,
    MessageRecord,
    PatientReplyResult,
    StageSubmissionRecord,
    TrainingProblemRecord,
)
from app.shared.actor import Actor


class TrainingRepository(Protocol):
    def class_codes(self, student_id: int) -> set[str]: ...

    def list_attempts(self, student_id: int, problem_id: int | None) -> tuple[AttemptSummaryRecord, ...]: ...

    def find_visible_problem(
        self, student: Actor, class_codes: set[str], problem_id: int
    ) -> TrainingProblemRecord | None: ...

    def find_attempt(self, student_id: int, attempt_id: int) -> AttemptRecord | None: ...

    def find_assessment(self, student_id: int, attempt_id: int) -> AssessmentRecord | None: ...

    def create_attempt(
        self,
        problem: TrainingProblemRecord,
        student_id: int,
        retry_of_id: int | None,
        focus_stage: str | None,
        learning_task_id: int | None,
        inherited_submissions: tuple[StageSubmissionRecord, ...],
    ) -> AttemptRecord: ...

    def append_exchange(
        self,
        student_id: int,
        attempt_id: int,
        question: str,
        reply: PatientReplyResult,
    ) -> MessageRecord: ...

    def save_submission(
        self,
        student_id: int,
        attempt_id: int,
        stage_id: str,
        answer: dict[str, object],
        feedback: str,
        next_stage: str | None,
    ) -> StageSubmissionRecord: ...

    def save_assessment(self, student_id: int, attempt_id: int, assessment: AssessmentDraft) -> AssessmentRecord: ...

    def record_ai_call(
        self,
        *,
        student_id: int,
        attempt_id: int | None,
        task: str,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
    ) -> None: ...


class PatientReplyGateway(Protocol):
    def reply(self, attempt: AttemptRecord, content: str) -> PatientReplyResult: ...


class AssessmentGateway(Protocol):
    def assess(self, attempt: AttemptRecord) -> AssessmentGenerationResult: ...
