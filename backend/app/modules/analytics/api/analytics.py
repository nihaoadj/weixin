from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_teacher
from app.modules.analytics.api.teacher_insights import router as teacher_insights_router
from app.modules.analytics.public import analytics_view
from app.modules.analytics.wiring import classroom_report_analytics
from app.modules.identity.infrastructure.models import User
from app.shared.actor import Actor

router = APIRouter(prefix="/analytics", tags=["analytics"])
router.include_router(teacher_insights_router)
classroom_progress_router = APIRouter(prefix="/teacher/classes", tags=["classroom-task-progress"])


class ReportAnalyticsScope(BaseModel):
    class_id: int | None
    class_name: str | None
    date_from: str
    date_to: str


class KnowledgeAccuracy(BaseModel):
    point_code: str
    correct_count: int
    question_count: int
    accuracy_rate: float


class ReportAnalyticsOverview(BaseModel):
    schema_version: int = 3
    data_basis: Literal["learning_routes"]
    scope: ReportAnalyticsScope
    student_count: int
    published_routes: int
    completed_tests: int
    completion_rate: float | None
    knowledge: list[KnowledgeAccuracy]


class ReportAnalyticsStudentRow(BaseModel):
    student_id: int
    nickname: str
    published_routes: int
    completed_tests: int
    completion_rate: float | None
    last_completed_at: datetime | None


class ReportAnalyticsStudents(BaseModel):
    schema_version: int = 3
    data_basis: Literal["learning_routes"]
    items: list[ReportAnalyticsStudentRow]
    total: int
    limit: int
    offset: int


class ReportAnalyticsResultSummary(BaseModel):
    result_id: UUID
    route_id: UUID
    session_id: int
    score: float
    correct_count: int
    question_count: int
    completed_at: datetime


class ReportAnalyticsResultPage(BaseModel):
    items: list[ReportAnalyticsResultSummary]
    total: int
    limit: int
    offset: int


class ReportAnalyticsStudent(BaseModel):
    schema_version: int = 3
    data_basis: Literal["learning_routes"]
    student: dict
    class_id: int
    period: dict
    published_routes: int
    completed_tests: int
    completion_rate: float | None
    knowledge: list[KnowledgeAccuracy]
    result_page: ReportAnalyticsResultPage


class ClassroomProgress(BaseModel):
    schema_version: int = 3
    data_basis: Literal["published_classroom_routes"]
    class_id: int
    session_id: int | None
    period: dict
    published_routes: int
    completed_tests: int
    in_progress: int
    completion_rate: float | None


class ClassroomProgressItem(BaseModel):
    student_id: int
    nickname: str
    route_id: UUID | None
    result_id: UUID | None
    execution_status: Literal["unpublished", "in_progress", "completed"]
    score: float | None
    correct_count: int | None
    question_count: int | None
    completed_at: datetime | None


class ClassroomProgressItemPage(BaseModel):
    items: list[ClassroomProgressItem]
    total: int
    limit: int
    offset: int


class ReportAnalyticsKnowledge(BaseModel):
    schema_version: int = 3
    data_basis: Literal["learning_routes"]
    class_id: int
    class_name: str
    participant_count: int
    published_routes: int
    completed_tests: int
    knowledge: list[KnowledgeAccuracy]


@router.get("/overview", response_model=ReportAnalyticsOverview)
def analytics_overview(
    class_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(
        classroom_report_analytics(db).overview(Actor.from_user(teacher), class_id, date_from, date_to)
    )


@router.get("/cases/{problem_id}")
def analytics_case(
    problem_id: int,
    class_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return classroom_report_analytics(db).retired_case_detail(Actor.from_user(teacher), problem_id, class_id)


@router.get("/students", response_model=ReportAnalyticsStudents)
def analytics_students(
    class_id: int = Query(gt=0),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(
        classroom_report_analytics(db).students(Actor.from_user(teacher), class_id, date_from, date_to, limit, offset)
    )


@router.get("/students/{student_id}", response_model=ReportAnalyticsStudent)
def analytics_student(
    student_id: int,
    class_id: int = Query(gt=0),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    result_limit: int = Query(default=20, ge=1, le=100),
    result_offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(
        classroom_report_analytics(db).student_detail(
            Actor.from_user(teacher), class_id, student_id, date_from, date_to, result_limit, result_offset
        )
    )


@router.get("/classroom-progress", response_model=ClassroomProgress)
def analytics_classroom_progress(
    class_id: int = Query(gt=0),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    session_id: int | None = Query(default=None, gt=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(
        classroom_report_analytics(db).progress(Actor.from_user(teacher), class_id, date_from, date_to, session_id)
    )


@classroom_progress_router.get("/{class_id}/classroom-task-progress-items", response_model=ClassroomProgressItemPage)
def classroom_task_progress_items(
    class_id: int,
    session_id: int = Query(gt=0),
    status: Literal["unpublished", "in_progress", "completed"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(
        classroom_report_analytics(db).progress_items(
            Actor.from_user(teacher), class_id, session_id, status, limit, offset
        )
    )


@router.get("/classes/{class_id}/knowledge", response_model=ReportAnalyticsKnowledge)
def analytics_knowledge(
    class_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_view(classroom_report_analytics(db).knowledge(Actor.from_user(teacher), class_id))
