from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.modules.training.application.records import (
    AssessmentRecord,
    AttemptRecord,
    AttemptSummaryRecord,
    PatientMessageResult,
    StageSubmissionRecord,
)
from app.shared.actor import Actor

CASE_DIMENSION_ORDER = {
    "information_gathering": 0,
    "problem_representation": 1,
    "differential_diagnosis": 2,
    "evidence_reasoning": 3,
    "test_selection": 4,
    "management_safety": 5,
}
CASE_DIMENSION_STAGES = {
    "information_gathering": "history",
    "problem_representation": "problem_representation",
    "differential_diagnosis": "differential",
    "evidence_reasoning": "differential",
    "test_selection": "tests",
    "management_safety": "management",
}


def _numeric_score(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


@dataclass(frozen=True, slots=True)
class CaseProblemContract:
    """Minimum public problem contract consumed by another bounded context."""

    id: int
    slug: str | None
    difficulty: str
    version: int
    case_definition: dict[str, object]
    rubric: dict[str, object]


@dataclass(frozen=True, slots=True)
class AssessmentSourceContract:
    """Assessment data exposed to learning-plan selection."""

    id: int
    dimensions: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class CaseSourceContract:
    """Small training source contract used by the learning application."""

    id: int
    learning_task_id: int | None
    problem: CaseProblemContract


@dataclass(frozen=True, slots=True)
class CaseMessageContract:
    id: int
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CaseSubmissionContract:
    id: int
    stage_id: str
    answer: dict[str, object]
    feedback: str
    inherited_from_id: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CaseAttemptContract:
    """Public case-attempt result used by learning without importing internals."""

    id: int
    problem_id: int
    problem_version: int
    status: str
    current_stage: str
    focus_stage: str | None
    retry_of_id: int | None
    opening: dict[str, object]
    messages: tuple[CaseMessageContract, ...]
    submissions: tuple[CaseSubmissionContract, ...]
    assessment_ready: bool
    started_at: datetime


class TrainingCasePort(Protocol):
    """Cross-module training contract; concrete assembly belongs to bootstrap."""

    def start(
        self, actor: Actor, problem_id: int, retry_of_id: int | None, learning_task_id: int
    ) -> CaseAttemptContract: ...

    def get(self, actor: Actor, attempt_id: int) -> CaseAttemptContract: ...


def source_contract(attempt: AttemptRecord) -> CaseSourceContract:
    return CaseSourceContract(
        id=attempt.id,
        learning_task_id=attempt.learning_task_id,
        problem=CaseProblemContract(
            id=attempt.problem.id,
            slug=attempt.problem.slug,
            difficulty=attempt.problem.difficulty,
            version=attempt.problem.version,
            case_definition=attempt.problem.case_definition,
            rubric=attempt.problem.rubric,
        ),
    )


def assessment_source_contract(assessment: AssessmentRecord) -> AssessmentSourceContract:
    return AssessmentSourceContract(id=assessment.id, dimensions=assessment.dimensions)


def attempt_contract(attempt: AttemptRecord) -> CaseAttemptContract:
    opening = (attempt.problem.case_definition or {}).get("opening", {})
    return CaseAttemptContract(
        id=attempt.id,
        problem_id=attempt.problem_id,
        problem_version=attempt.problem_version,
        status=attempt.status,
        current_stage=attempt.current_stage,
        focus_stage=attempt.focus_stage,
        retry_of_id=attempt.retry_of_id,
        opening=opening if isinstance(opening, dict) else {},
        messages=tuple(
            CaseMessageContract(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in attempt.messages
        ),
        submissions=tuple(
            CaseSubmissionContract(
                id=submission.id,
                stage_id=submission.stage_id,
                answer=submission.answer,
                feedback=submission.feedback,
                inherited_from_id=submission.inherited_from_id,
                created_at=submission.created_at,
            )
            for submission in attempt.submissions
        ),
        assessment_ready=attempt.assessment is not None,
        started_at=attempt.started_at,
    )


def case_attempt_view(attempt: CaseAttemptContract) -> dict[str, object]:
    return {
        "id": attempt.id,
        "problem_id": attempt.problem_id,
        "problem_version": attempt.problem_version,
        "status": attempt.status,
        "current_stage": attempt.current_stage,
        "focus_stage": attempt.focus_stage,
        "retry_of_id": attempt.retry_of_id,
        "opening": attempt.opening,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in attempt.messages
        ],
        "submissions": [
            {
                "id": submission.id,
                "stage_id": submission.stage_id,
                "answer": submission.answer,
                "feedback": submission.feedback,
                "inherited_from_id": submission.inherited_from_id,
                "created_at": submission.created_at,
            }
            for submission in attempt.submissions
        ],
        "assessment_ready": attempt.assessment_ready,
        "started_at": attempt.started_at,
    }


def attempt_view(attempt: AttemptRecord) -> dict[str, object]:
    return case_attempt_view(attempt_contract(attempt))


def attempt_summary_view(attempt: AttemptSummaryRecord) -> dict[str, object]:
    return {
        "id": attempt.id,
        "problem_id": attempt.problem_id,
        "status": attempt.status,
        "current_stage": attempt.current_stage,
        "focus_stage": attempt.focus_stage,
        "total_score": attempt.total_score,
        "started_at": attempt.started_at,
    }


def patient_message_view(result: PatientMessageResult) -> dict[str, object]:
    return {
        "id": result.message.id,
        "role": "assistant",
        "content": result.message.content,
        "created_at": result.message.created_at,
        "response_mode": result.response_mode,
    }


def submission_view(submission: StageSubmissionRecord) -> dict[str, object]:
    return {
        "id": submission.id,
        "stage_id": submission.stage_id,
        "answer": submission.answer,
        "feedback": submission.feedback,
        "inherited_from_id": submission.inherited_from_id,
        "created_at": submission.created_at,
    }


def assessment_view(assessment: AssessmentRecord, previous: AssessmentRecord | None = None) -> dict[str, object]:
    comparison = None
    if previous is not None:
        old = {item.get("dimension_id"): item for item in previous.dimensions}
        comparison = {
            "total_delta": round(assessment.total_score - previous.total_score, 1),
            "dimensions": [
                {
                    "dimension_id": item.get("dimension_id"),
                    "previous_score": old.get(item.get("dimension_id"), {"score": 0}).get("score", 0),
                    "current_score": item.get("score", 0),
                    "delta": round(
                        _numeric_score(item.get("score", 0))
                        - _numeric_score(old.get(item.get("dimension_id"), {"score": 0}).get("score", 0)),
                        1,
                    ),
                }
                for item in assessment.dimensions
            ],
        }
    return {
        "attempt_id": assessment.attempt_id,
        "total_score": assessment.total_score,
        "dimensions": list(assessment.dimensions),
        "strengths": list(assessment.strengths),
        "weaknesses": list(assessment.weaknesses),
        "next_steps": list(assessment.next_steps),
        "summary": assessment.summary,
        "focus_stage": assessment.focus_stage,
        "model_name": assessment.model_name,
        "prompt_version": assessment.prompt_version,
        "fallback_used": assessment.fallback_used,
        "comparison": comparison,
    }


class CaseSnapshotPort(Protocol):
    """Freeze existing attempts before an author changes their reusable case."""

    def freeze(self, problem_id: int) -> None: ...
