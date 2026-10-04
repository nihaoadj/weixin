"""Student-only classroom package execution; no teacher rubric fields escape."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_student, require_teacher
from app.modules.identity.infrastructure.models import User
from app.shared.errors import AppError

router = APIRouter(tags=["retired-classroom-task-packages"])


class RetiredPage(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


@router.get("/student/classroom-task-packages", response_model=RetiredPage)
def student_classroom_task_packages(
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/student/classroom-task-packages/{package_id}")
def classroom_task_package(package_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return _missing()


@router.post("/student/classroom-tasks/{task_id}/submit")
def submit_classroom_task(
    task_id: int,
    payload: dict | None = None,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    return _retired()


@router.post("/student/classroom-tasks/{task_id}/start")
def start_classroom_case_task(
    task_id: int,
    payload: dict | None = None,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    return _retired()


@router.get(
    "/student/classroom-case-attempts/{attempt_id}/context",
)
def student_classroom_case_attempt_context(
    attempt_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    return _missing()


@router.get("/student/classroom-final-reports/{report_id}")
def student_classroom_final_report(
    report_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return _missing()


@router.get("/teacher/classroom-final-reports", response_model=RetiredPage)
def teacher_classroom_final_reports(
    class_id: int = Query(gt=0),
    session_id: int | None = Query(default=None, gt=0),
    student_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/teacher/classroom-final-reports/{report_id}")
def teacher_classroom_final_report(
    report_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return _missing()


def _retired():
    from app.modules.learning.domain.learning_routes import conflict

    conflict("RETIRED_FLOW")


def _missing():
    raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
