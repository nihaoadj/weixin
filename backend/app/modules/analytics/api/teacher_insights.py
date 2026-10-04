"""Teacher-only read projections; full answers remain in authorized result details."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_teacher
from app.modules.analytics.wiring import teacher_insights_application
from app.shared.actor import Actor

router = APIRouter(prefix="/teacher-insights", tags=["teacher-insights"])


class MetricBasis(BaseModel):
    progress: Literal["published_route_cohort"]
    results: Literal["completed_test_window"]
    diagnoses: Literal["completed_diagnosis_window"]


class InsightScope(BaseModel):
    class_id: int | None
    class_name: str | None
    class_ids: list[int]
    session_id: int | None
    date_from: str
    date_to: str
    timezone: Literal["Asia/Shanghai"]
    as_of: datetime
    metric_basis: MetricBasis


class CohortProgress(BaseModel):
    published_routes: int
    completed_tests: int
    completion_rate: float | None
    grading_tests: int


class PeriodResults(BaseModel):
    completed_tests: int
    average_score: float | None
    format_counts: dict[str, int]


class InsightOverview(BaseModel):
    scope: InsightScope
    cohort: CohortProgress
    period_results: PeriodResults
    diagnosis_count: int
    student_count: int


class DiscussionProgress(BaseModel):
    participated: int
    active: int
    completed: int


class InsightDiscussion(BaseModel):
    participation_id: int
    session_id: int
    class_id: int
    student_id: int
    phase: str
    status: str
    started_at: datetime
    completed_at: datetime | None


class InsightStudent(BaseModel):
    student_id: int
    student_name: str
    class_ids: list[int]
    cohort: CohortProgress
    period_results: PeriodResults
    diagnosis_count: int
    last_completed_at: datetime | None
    discussion_progress: DiscussionProgress


class InsightStudentPage(BaseModel):
    scope: InsightScope
    items: list[InsightStudent]
    total: int
    limit: int
    offset: int


class InsightKnowledge(BaseModel):
    point_code: str
    correct_count: int
    objective_count: int
    invalid_objective_count: int
    accuracy_rate: float | None
    short_answer_count: int
    invalid_short_answer_count: int
    points_awarded: float
    points_possible: float
    short_answer_score_rate: float | None


class InsightKnowledgePage(BaseModel):
    scope: InsightScope
    items: list[InsightKnowledge]
    result_count: int


class InsightFinding(BaseModel):
    code: str
    summary: str


class InsightDiagnosis(BaseModel):
    participation_id: int
    session_id: int
    class_id: int
    class_name: str
    student_id: int
    student_name: str
    completed_at: datetime
    knowledge_gap_codes: list[str]
    reasoning_issue_codes: list[str]
    knowledge_gaps: list[InsightFinding]
    reasoning_issues: list[InsightFinding]


class InsightFindingGroup(BaseModel):
    code: str
    student_count: int
    diagnosis_count: int
    last_completed_at: datetime


class InsightDiagnosisPage(BaseModel):
    scope: InsightScope
    items: list[InsightDiagnosis]
    total: int
    limit: int
    offset: int
    knowledge_gaps: list[InsightFindingGroup]
    reasoning_issues: list[InsightFindingGroup]


class InsightResultSummary(BaseModel):
    result_id: str
    route_id: str
    class_id: int
    session_id: int
    student_id: int
    score: float
    completed_at: datetime
    format_version: Literal["single_choice_v1", "mixed_v2"]


class InsightRouteProgress(BaseModel):
    route_id: str
    student_id: int
    class_id: int
    session_id: int
    published_at: datetime
    result_id: str | None
    test_generation_state: str | None
    test_review_state: str | None
    attempt_status: str | None
    completed_steps: int | None
    total_steps: int | None
    reading_seconds: int | None


class InsightStudentDetail(BaseModel):
    scope: InsightScope
    summary: InsightStudent
    discussions: list[InsightDiscussion]
    routes: list[InsightRouteProgress]
    results: list[InsightResultSummary]
    diagnoses: list[InsightDiagnosis]
    knowledge: list[InsightKnowledge]


def insight_filters(
    class_id: int | None = Query(default=None, gt=0),
    session_id: int | None = Query(default=None, gt=0),
    date_from: str | None = None,
    date_to: str | None = None,
):
    return {"class_id": class_id, "session_id": session_id, "date_from": date_from, "date_to": date_to}


@router.get("/overview", response_model=InsightOverview)
def overview(filters: dict = Depends(insight_filters), teacher=Depends(require_teacher), db: Session = Depends(get_db)):
    return teacher_insights_application(db).overview(Actor.from_user(teacher), **filters)


@router.get("/students", response_model=InsightStudentPage)
def students(
    filters: dict = Depends(insight_filters),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    teacher=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return teacher_insights_application(db).students(Actor.from_user(teacher), **filters, limit=limit, offset=offset)


@router.get("/students/{student_id}", response_model=InsightStudentDetail)
def student(
    student_id: int,
    class_id: int = Query(gt=0),
    session_id: int | None = Query(default=None, gt=0),
    date_from: str | None = None,
    date_to: str | None = None,
    teacher=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return teacher_insights_application(db).student(
        Actor.from_user(teacher), student_id, class_id, session_id, date_from, date_to
    )


@router.get("/knowledge", response_model=InsightKnowledgePage)
def knowledge(
    filters: dict = Depends(insight_filters), teacher=Depends(require_teacher), db: Session = Depends(get_db)
):
    return teacher_insights_application(db).knowledge(Actor.from_user(teacher), **filters)


@router.get("/diagnostics", response_model=InsightDiagnosisPage)
def diagnostics(
    filters: dict = Depends(insight_filters),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    teacher=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return teacher_insights_application(db).diagnostics(Actor.from_user(teacher), **filters, limit=limit, offset=offset)
