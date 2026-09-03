from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.bootstrap.composition import knowledge_review_application
from app.db import get_db
from app.dependencies import get_current_user, require_student, require_teacher
from app.modules.identity.infrastructure.models import User
from app.modules.reports.api.schemas import ReportCreate, ReportRead, ReportReview, ReportSummaryPage
from app.modules.reports.application.ports import ReportDraftCommand, ReportReviewCommand
from app.modules.reports.application.records import ReportRecord
from app.modules.reports.public import report_summary_page_view, report_view
from app.modules.reports.wiring import reports_application
from app.shared.actor import Actor

router = APIRouter(prefix="/reports", tags=["reports"])


def load_visible_report(db: Session, user: User, report_id: int) -> ReportRecord:
    """Narrow compatibility seam retained for the existing error-boundary test."""
    return reports_application(db).get(Actor.from_user(user), report_id)


@router.get("/summaries", response_model=ReportSummaryPage)
def list_report_summaries(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    page = reports_application(db).list_summaries(Actor.from_user(user), limit, offset)
    return report_summary_page_view(page)


@router.get("/by-conversation/{client_id:path}", response_model=ReportRead)
def get_report_by_conversation(
    client_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return report_view(reports_application(db).get_by_client_id(Actor.from_user(user), client_id))


@router.get("/{report_id}", response_model=ReportRead)
def get_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return report_view(load_visible_report(db, user, report_id))


@router.get("", response_model=list[ReportRead])
def list_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [report_view(item) for item in reports_application(db).list_full(Actor.from_user(user))]


@router.post("", response_model=ReportRead)
def create_draft_report(
    payload: ReportCreate,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    command = ReportDraftCommand(
        conversation_id=payload.conversation_id,
        ai_score=payload.ai_score,
        ai_summary=payload.ai_summary,
        analysis=payload.analysis.model_dump(mode="json") if payload.analysis else None,
    )
    return report_view(reports_application(db).save_draft(Actor.from_user(user), command))


@router.post("/{report_id}/submit", response_model=ReportRead)
def submit_report(
    report_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return report_view(reports_application(db).submit(Actor.from_user(user), report_id))


@router.post("/{report_id}/review", response_model=ReportRead)
def review_report(
    report_id: int,
    payload: ReportReview,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    command = ReportReviewCommand(
        teacher_score=payload.teacher_score,
        teacher_feedback=payload.teacher_feedback,
        review_topic_codes=tuple(payload.review_topic_codes),
    )
    report = reports_application(db).review(Actor.from_user(teacher), report_id, command)
    student = Actor(id=report.student_id, external_id="", role="student", nickname="")
    for point_code in report.review_topic_codes:
        knowledge_review_application(db).capture(
            student,
            point_code,
            source_type="teacher_report_review",
            source_id=str(report.id),
            note="教师批阅建议复习",
        )
    return report_view(report)
