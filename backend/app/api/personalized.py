from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.dependencies import require_student
from app.models import CaseAssessment, CaseAttempt, LearningTaskAttempt, User
from app.schemas.personalized import (
    LearningPlanRead,
    LearningProfileRead,
    LearningTaskAttemptRead,
    LearningTaskStartRead,
    LearningTaskSubmit,
)
from app.services.personalized import (
    _public_task,
    complete_plan,
    current_plan,
    ensure_learning_plan,
    get_plan,
    mark_all_notifications_read,
    mark_notification_read,
    notification_count,
    profile,
    serialize_plan,
    start_task,
    submit_micro_task,
)

router = APIRouter(tags=["personalized-learning"])


@router.get("/learning/profile", response_model=LearningProfileRead)
def learning_profile(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    return profile(db, student)


@router.post("/attempts/{attempt_id}/learning-plan", response_model=LearningPlanRead)
def create_learning_plan(
    attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict:
    assessment = db.scalar(
        select(CaseAssessment)
        .join(CaseAttempt)
        .where(CaseAssessment.attempt_id == attempt_id, CaseAttempt.student_id == student.id)
        .options(selectinload(CaseAssessment.attempt).selectinload(CaseAttempt.problem))
    )
    if assessment is None or assessment.attempt.status != "assessed":
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return serialize_plan(ensure_learning_plan(db, assessment))


@router.get("/learning-plans/current", response_model=LearningPlanRead)
def read_current_plan(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    plan = current_plan(db, student)
    if plan is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return serialize_plan(plan)


@router.get("/learning-plans/{plan_id}", response_model=LearningPlanRead)
def read_plan(plan_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    return serialize_plan(get_plan(db, plan_id, student))


@router.post("/learning-tasks/{task_id}/start", response_model=LearningTaskStartRead)
def begin_task(task_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    task, attempt = start_task(db, task_id, student)
    return {
        "mode": "micro_drill" if task.task_type == "micro_drill" else "case_attempt",
        "task": _public_task(task),
        "attempt": attempt,
    }


@router.get("/learning-task-attempts/{attempt_id}", response_model=LearningTaskAttemptRead)
def read_task_attempt(attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    attempt = db.scalar(
        select(LearningTaskAttempt)
        .where(LearningTaskAttempt.id == attempt_id, LearningTaskAttempt.student_id == student.id)
        .options(selectinload(LearningTaskAttempt.task))
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return {
        "id": attempt.id,
        "task_id": attempt.task_id,
        "status": attempt.status,
        "answer": attempt.answer or {},
        "public_definition": attempt.task.public_definition if attempt.task else {},
        "score": attempt.score,
        "evidence": attempt.evidence or [],
        "feedback": attempt.feedback,
        "next_step": attempt.next_step,
        "created_at": attempt.created_at,
        "assessed_at": attempt.assessed_at,
    }


@router.post("/learning-task-attempts/{attempt_id}/submit", response_model=LearningTaskAttemptRead)
def submit_task_attempt(
    attempt_id: int,
    payload: LearningTaskSubmit,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    existing = db.scalar(
        select(LearningTaskAttempt).where(
            LearningTaskAttempt.id == attempt_id, LearningTaskAttempt.student_id == student.id
        )
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    result = submit_micro_task(db, existing.task_id, student, payload.answer)
    return {
        "id": result.id,
        "task_id": result.task_id,
        "status": result.status,
        "answer": result.answer or {},
        "public_definition": result.task.public_definition if result.task else {},
        "score": result.score,
        "evidence": result.evidence or [],
        "feedback": result.feedback,
        "next_step": result.next_step,
        "created_at": result.created_at,
        "assessed_at": result.assessed_at,
    }


@router.post("/learning-plans/{plan_id}/complete", response_model=LearningPlanRead)
def finish_plan(plan_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    plan = get_plan(db, plan_id, student)
    return serialize_plan(complete_plan(db, plan, student))


@router.get("/notifications")
def notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    from app.services.personalized import list_notifications

    items = list_notifications(db, student, unread_only, limit)
    return {
        "items": [
            {
                "id": item.id,
                "type": item.type,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "title": item.title,
                "body": item.body,
                "read_at": item.read_at,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "unread_count": notification_count(db, student.id),
    }


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_notification(
    notification_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> None:
    mark_notification_read(db, notification_id, student)


@router.post("/notifications/read-all")
def read_all_notifications(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    return {"marked": mark_all_notifications_read(db, student)}
