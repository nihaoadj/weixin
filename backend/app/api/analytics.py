from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_teacher
from app.models import User
from app.schemas.classroom import AnalyticsCaseRead, AnalyticsOverview, AnalyticsStudentRead
from app.services.analytics import case_detail, overview, student_detail

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview(
    class_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    return overview(teacher, class_id, date_from, date_to, db)


@router.get("/cases/{problem_id}", response_model=AnalyticsCaseRead)
def analytics_case(
    problem_id: int,
    class_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    return case_detail(teacher, problem_id, class_id, date_from, date_to, db)


@router.get("/students/{student_id}", response_model=AnalyticsStudentRead)
def analytics_student(
    student_id: int,
    class_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    return student_detail(teacher, student_id, class_id, date_from, date_to, db)
