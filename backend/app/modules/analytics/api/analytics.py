from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_teacher
from app.modules.analytics.public import analytics_view
from app.modules.analytics.wiring import analytics_application
from app.modules.classroom.api.schemas import (
    AnalyticsCaseRead,
    AnalyticsKnowledgeRead,
    AnalyticsOverview,
    AnalyticsStudentRead,
)
from app.modules.identity.infrastructure.models import User
from app.shared.actor import Actor

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview(
    class_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(analytics_application(db).overview(Actor.from_user(teacher), class_id, date_from, date_to))


@router.get("/cases/{problem_id}", response_model=AnalyticsCaseRead)
def analytics_case(
    problem_id: int,
    class_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(
        analytics_application(db).case_detail(Actor.from_user(teacher), problem_id, class_id, date_from, date_to)
    )


@router.get("/students/{student_id}", response_model=AnalyticsStudentRead)
def analytics_student(
    student_id: int,
    class_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(
        analytics_application(db).student_detail(Actor.from_user(teacher), student_id, class_id, date_from, date_to)
    )


@router.get("/classes/{class_id}/knowledge", response_model=AnalyticsKnowledgeRead)
def analytics_knowledge(
    class_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(analytics_application(db).knowledge(Actor.from_user(teacher), class_id))
