from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.bootstrap.composition import learning_application, training_application
from app.db import get_db
from app.dependencies import require_student
from app.modules.identity.infrastructure.models import User
from app.modules.training.api.schemas import (
    CaseAssessmentRead,
    CaseAttemptCreate,
    CaseAttemptRead,
    CaseAttemptSummaryRead,
    PatientMessageCreate,
    PatientMessageRead,
    StageSubmissionCreate,
    StageSubmissionRead,
)
from app.modules.training.public import (
    assessment_view,
    attempt_summary_view,
    attempt_view,
    patient_message_view,
    submission_view,
)
from app.shared.actor import Actor

router = APIRouter(tags=["case-attempts"])


@router.get("/attempts", response_model=list[CaseAttemptSummaryRead])
def list_attempts(
    problem_id: int | None = None, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    return [
        attempt_summary_view(item)
        for item in training_application(db).list_attempts(Actor.from_user(student), problem_id)
    ]


@router.post("/problems/{problem_id}/attempts", response_model=CaseAttemptRead)
def start_attempt(
    problem_id: int, payload: CaseAttemptCreate, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    attempt = training_application(db).start(Actor.from_user(student), problem_id, payload.retry_of_id)
    return attempt_view(attempt)


@router.get("/attempts/{attempt_id}", response_model=CaseAttemptRead)
def read_attempt(
    attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    return attempt_view(training_application(db).get(Actor.from_user(student), attempt_id))


@router.post("/attempts/{attempt_id}/messages", response_model=PatientMessageRead)
def send_patient_message(
    attempt_id: int,
    payload: PatientMessageCreate,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = training_application(db).send_patient_message(Actor.from_user(student), attempt_id, payload.content)
    return patient_message_view(result)


@router.post("/attempts/{attempt_id}/stages/{stage_id}/submit", response_model=StageSubmissionRead)
def submit_attempt_stage(
    attempt_id: int,
    stage_id: str,
    payload: StageSubmissionCreate,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    submission = training_application(db).submit_stage(
        Actor.from_user(student), attempt_id, stage_id, payload.answer.model_dump(mode="json")
    )
    return submission_view(submission)


@router.post("/attempts/{attempt_id}/complete", response_model=CaseAssessmentRead)
def complete_attempt(
    attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    application = training_application(db)
    actor = Actor.from_user(student)
    application.complete(actor, attempt_id)
    learning_application(db).ensure_for_case_completion(actor, attempt_id)
    assessment, previous = application.assessment_comparison(actor, attempt_id)
    return assessment_view(assessment, previous)


@router.get("/attempts/{attempt_id}/assessment", response_model=CaseAssessmentRead)
def read_assessment(
    attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    application = training_application(db)
    actor = Actor.from_user(student)
    assessment, previous = application.assessment_comparison(actor, attempt_id)
    return assessment_view(assessment, previous)
