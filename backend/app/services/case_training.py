"""Compatibility facade for seed tooling and established test injection seams.

New HTTP code belongs to ``app.modules.training``.  These functions intentionally
only translate the old ORM-shaped call signature to that module and are not a
second implementation of case-attempt rules.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.content.infrastructure.models import Problem
from app.modules.identity.infrastructure.models import User
from app.modules.training.api.schemas import StageAnswer
from app.modules.training.application.records import AttemptRecord
from app.modules.training.infrastructure.ai_gateway import CaseAiGateway
from app.modules.training.infrastructure.ai_schemas import AIAssessmentDimension, AIAssessmentResponse
from app.modules.training.infrastructure.models import CaseAssessment, CaseAttempt, StageSubmission
from app.modules.training.infrastructure.repositories import SqlAlchemyTrainingRepository
from app.modules.training.public import assessment_view
from app.modules.training.wiring import training_application
from app.shared.actor import Actor


def _load_orm_attempt(db: Session, attempt_id: int, student_id: int) -> CaseAttempt:
    attempt = db.scalar(
        select(CaseAttempt)
        .where(CaseAttempt.id == attempt_id, CaseAttempt.student_id == student_id)
        .options(
            selectinload(CaseAttempt.problem),
            selectinload(CaseAttempt.messages),
            selectinload(CaseAttempt.submissions),
            selectinload(CaseAttempt.assessment),
        )
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case attempt not found")
    return attempt


def get_attempt(db: Session, attempt_id: int, student: User) -> CaseAttempt:
    training_application(db).get(Actor.from_user(student), attempt_id)
    return _load_orm_attempt(db, attempt_id, student.id)


def serialize_attempt(attempt: CaseAttempt) -> dict[str, object]:
    return {
        "id": attempt.id,
        "problem_id": attempt.problem_id,
        "problem_version": attempt.problem_version,
        "status": attempt.status,
        "current_stage": attempt.current_stage,
        "focus_stage": attempt.focus_stage,
        "retry_of_id": attempt.retry_of_id,
        "opening": (attempt.problem.case_definition or {}).get("opening", {}),
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
        "assessment_ready": attempt.assessment is not None,
        "started_at": attempt.started_at,
    }


def create_attempt(
    db: Session,
    problem: Problem,
    student: User,
    retry_of_id: int | None = None,
    learning_task_id: int | None = None,
) -> CaseAttempt:
    result = training_application(db).start(
        Actor.from_user(student), problem.id, retry_of_id, learning_task_id=learning_task_id
    )
    return _load_orm_attempt(db, result.id, student.id)


def submit_stage(db: Session, attempt: CaseAttempt, stage_id: str, answer: StageAnswer) -> StageSubmission:
    student = db.get(User, attempt.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    result = training_application(db).submit_stage(
        Actor.from_user(student), attempt.id, stage_id, answer.model_dump(mode="json")
    )
    submission = db.get(StageSubmission, result.id)
    if submission is None:
        raise HTTPException(status_code=500, detail="Stage submission was not persisted")
    return submission


def assess_attempt(db: Session, attempt: CaseAttempt) -> CaseAssessment:
    student = db.get(User, attempt.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    result = training_application(db).complete(Actor.from_user(student), attempt.id)
    assessment = db.get(CaseAssessment, result.id)
    if assessment is None:
        raise HTTPException(status_code=500, detail="Assessment was not persisted")
    return assessment


def serialize_assessment(db: Session, assessment: CaseAssessment) -> dict[str, object]:
    student = assessment.attempt.student
    application = training_application(db)
    current, previous = application.assessment_comparison(Actor.from_user(student), assessment.attempt_id)
    return assessment_view(current, previous)


def ai_assessment(_db: Session | None, attempt: AttemptRecord) -> AIAssessmentResponse | None:
    """Keep the T05 monkeypatch seam while delegating the real call to the module gateway."""
    result = CaseAiGateway().assess(attempt)
    if result.fallback_used:
        return None
    return AIAssessmentResponse(
        dimensions=[
            AIAssessmentDimension(
                dimension_id=item.dimension_id,
                score=item.score,
                evidence=list(item.evidence),
                feedback=item.feedback,
                next_step=item.next_step,
            )
            for item in result.candidates
        ]
    )


def patient_reply(db: Session, attempt: CaseAttempt, content: str) -> tuple[str, list[str], str]:
    student = db.get(User, attempt.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    record = SqlAlchemyTrainingRepository(db).find_attempt(student.id, attempt.id)
    if record is None:
        raise HTTPException(status_code=404, detail="Case attempt not found")
    result = CaseAiGateway().reply(record, content)
    return result.reply, list(result.revealed_fact_ids), result.response_mode
