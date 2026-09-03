from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.bootstrap.composition import learning_application
from app.db import get_db
from app.dependencies import require_student
from app.modules.identity.infrastructure.models import User
from app.modules.learning.api.schemas import (
    LearningPlanRead,
    LearningProfileRead,
    LearningTaskAttemptRead,
    LearningTaskStartRead,
    LearningTaskSubmit,
    NotificationListRead,
    NotificationMarkRead,
)
from app.modules.learning.public import (
    notification_view,
    plan_view,
    profile_view,
    start_view,
    task_attempt_view,
)
from app.shared.actor import Actor

router = APIRouter(tags=["personalized-learning"])


@router.get("/learning/profile", response_model=LearningProfileRead)
def learning_profile(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, object]:
    return profile_view(learning_application(db).profile(Actor.from_user(student)))


@router.post("/attempts/{attempt_id}/learning-plan", response_model=LearningPlanRead)
def create_learning_plan(
    attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    result = learning_application(db).ensure_for_assessment(Actor.from_user(student), attempt_id)
    return plan_view(result)


@router.get("/learning-plans/current", response_model=LearningPlanRead)
def read_current_plan(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, object]:
    return plan_view(learning_application(db).current_plan(Actor.from_user(student)))


@router.get("/learning-plans/{plan_id}", response_model=LearningPlanRead)
def read_plan(
    plan_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    return plan_view(learning_application(db).get_plan(Actor.from_user(student), plan_id))


@router.post("/learning-tasks/{task_id}/start", response_model=LearningTaskStartRead)
def begin_task(
    task_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    task, attempt = learning_application(db).start_task(Actor.from_user(student), task_id)
    return start_view(task, attempt)


@router.get("/learning-task-attempts/{attempt_id}", response_model=LearningTaskAttemptRead)
def read_task_attempt(
    attempt_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    return task_attempt_view(learning_application(db).get_task_attempt(Actor.from_user(student), attempt_id))


@router.post("/learning-task-attempts/{attempt_id}/submit", response_model=LearningTaskAttemptRead)
def submit_task_attempt(
    attempt_id: int,
    payload: LearningTaskSubmit,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = learning_application(db).submit_micro_task(Actor.from_user(student), attempt_id, payload.answer)
    return task_attempt_view(result)


@router.post("/learning-plans/{plan_id}/complete", response_model=LearningPlanRead)
def finish_plan(
    plan_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    return plan_view(learning_application(db).complete_plan(Actor.from_user(student), plan_id))


@router.get("/notifications", response_model=NotificationListRead)
def notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    application = learning_application(db)
    actor = Actor.from_user(student)
    return {
        "items": [notification_view(item) for item in application.notifications(actor, unread_only, limit)],
        "unread_count": application.unread_count(actor),
    }


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_notification(
    notification_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> None:
    learning_application(db).mark_notification_read(Actor.from_user(student), notification_id)


@router.post("/notifications/read-all", response_model=NotificationMarkRead)
def read_all_notifications(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, int]:
    return {"marked": learning_application(db).mark_all_notifications_read(Actor.from_user(student))}
