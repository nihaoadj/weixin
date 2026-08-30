from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_student
from app.models import CaseAttempt, Problem, User
from app.schemas.case_training import (
    CaseAssessmentRead,
    CaseAttemptCreate,
    CaseAttemptRead,
    CaseAttemptSummaryRead,
    PatientMessageCreate,
    PatientMessageRead,
    StageSubmissionCreate,
    StageSubmissionRead,
)
from app.services.access_control import is_problem_visible_to_student
from app.services.case_training import (
    add_patient_message,
    assess_attempt,
    create_attempt,
    get_attempt,
    serialize_assessment,
    submit_stage,
)

router = APIRouter(tags=["case-attempts"])


def serialize_attempt(attempt: CaseAttempt) -> dict:
    return {
        "id": attempt.id,
        "problem_id": attempt.problem_id,
        "problem_version": attempt.problem_version,
        "status": attempt.status,
        "current_stage": attempt.current_stage,
        "focus_stage": attempt.focus_stage,
        "retry_of_id": attempt.retry_of_id,
        "opening": (attempt.problem.case_definition or {}).get("opening"),
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


@router.get("/attempts", response_model=list[CaseAttemptSummaryRead])
def list_attempts(
    problem_id: int | None = None, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> list[dict]:
    statement = select(CaseAttempt).where(CaseAttempt.student_id == student.id).order_by(CaseAttempt.started_at.desc())
    if problem_id:
        statement = statement.where(CaseAttempt.problem_id == problem_id)
    attempts = db.scalars(statement).all()
    return [
        {
            "id": item.id,
            "problem_id": item.problem_id,
            "status": item.status,
            "current_stage": item.current_stage,
            "focus_stage": item.focus_stage,
            "total_score": item.assessment.total_score if item.assessment else None,
            "started_at": item.started_at,
        }
        for item in attempts
    ]


@router.post("/problems/{problem_id}/attempts", response_model=CaseAttemptRead)
def start_attempt(
    problem_id: int, payload: CaseAttemptCreate, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict:
    problem = db.get(Problem, problem_id)
    if (
        problem is None
        or problem.content_type != "guided_case"
        or not is_problem_visible_to_student(problem, student, db)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return serialize_attempt(create_attempt(db, problem, student, payload.retry_of_id))


@router.get("/attempts/{attempt_id}", response_model=CaseAttemptRead)
def read_attempt(attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    return serialize_attempt(get_attempt(db, attempt_id, student))


@router.post("/attempts/{attempt_id}/messages", response_model=PatientMessageRead)
def send_patient_message(
    attempt_id: int,
    payload: PatientMessageCreate,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    message, response_mode = add_patient_message(db, get_attempt(db, attempt_id, student), payload.content)
    return {
        "id": message.id,
        "role": "assistant",
        "content": message.content,
        "created_at": message.created_at,
        "response_mode": response_mode,
    }


@router.post("/attempts/{attempt_id}/stages/{stage_id}/submit", response_model=StageSubmissionRead)
def submit_attempt_stage(
    attempt_id: int,
    stage_id: str,
    payload: StageSubmissionCreate,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    submission = submit_stage(db, get_attempt(db, attempt_id, student), stage_id, payload.answer)
    return {
        "id": submission.id,
        "stage_id": submission.stage_id,
        "answer": submission.answer,
        "feedback": submission.feedback,
        "inherited_from_id": submission.inherited_from_id,
        "created_at": submission.created_at,
    }


@router.post("/attempts/{attempt_id}/complete", response_model=CaseAssessmentRead)
def complete_attempt(attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    attempt = get_attempt(db, attempt_id, student)
    assessment = assess_attempt(db, attempt)
    return serialize_assessment(db, assessment)


@router.get("/attempts/{attempt_id}/assessment", response_model=CaseAssessmentRead)
def read_assessment(attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    attempt = get_attempt(db, attempt_id, student)
    if attempt.assessment is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment is not available")
    return serialize_assessment(db, attempt.assessment)
