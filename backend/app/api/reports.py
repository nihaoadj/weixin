from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.dependencies import get_current_user, require_student, require_teacher
from app.models import Conversation, Report, User
from app.schemas import ReportCreate, ReportRead, ReportReview
from app.services.access_control import ensure_report_transition

router = APIRouter(prefix="/reports", tags=["reports"])


def serialize_report(report: Report) -> dict:
    return {
        "id": report.id,
        "conversation_id": report.conversation_id,
        "conversation_client_id": report.conversation.client_id if report.conversation else None,
        "student_id": report.student_id,
        "student_name": report.student.nickname if report.student else None,
        "status": report.status,
        "ai_score": report.ai_score,
        "ai_summary": report.ai_summary,
        "analysis": report.ai_analysis,
        "messages": report.conversation.messages if report.conversation else [],
        "teacher_score": report.teacher_score,
        "teacher_feedback": report.teacher_feedback,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


@router.get("", response_model=list[ReportRead])
def list_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    statement = (
        select(Report)
        .options(selectinload(Report.conversation).selectinload(Conversation.messages), selectinload(Report.student))
        .order_by(Report.updated_at.desc())
    )
    if user.role == "student":
        statement = statement.where(Report.student_id == user.id)
    else:
        statement = statement.where(Report.status.in_(["pending_review", "reviewed"]))
    return [serialize_report(report) for report in db.scalars(statement).all()]


@router.post("", response_model=ReportRead)
def create_draft_report(
    payload: ReportCreate,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can create reports")
    conversation = db.get(Conversation, payload.conversation_id)
    if conversation is None or conversation.student_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    report = db.scalar(select(Report).where(Report.conversation_id == payload.conversation_id))
    if report and report.status != "draft":
        report = db.scalar(
            select(Report)
            .where(Report.id == report.id)
            .options(
                selectinload(Report.conversation).selectinload(Conversation.messages),
                selectinload(Report.student),
            )
        )
        return serialize_report(report)
    if report is None:
        report = Report(conversation_id=payload.conversation_id, student_id=user.id)
        db.add(report)
    report.ai_score = payload.ai_score
    report.ai_summary = payload.ai_summary
    report.ai_analysis = payload.analysis.model_dump(mode="json") if payload.analysis else None
    report.status = "draft"
    db.commit()
    db.refresh(report)
    report = db.scalar(
        select(Report)
        .where(Report.id == report.id)
        .options(selectinload(Report.conversation).selectinload(Conversation.messages), selectinload(Report.student))
    )
    return serialize_report(report)


@router.post("/{report_id}/submit", response_model=ReportRead)
def submit_report(
    report_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    report = db.get(Report, report_id)
    if report is None or report.student_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report is not a draft")
    ensure_report_transition(report.status, "pending_review")
    report.status = "pending_review"
    db.commit()
    db.refresh(report)
    report = db.scalar(
        select(Report)
        .where(Report.id == report.id)
        .options(selectinload(Report.conversation).selectinload(Conversation.messages), selectinload(Report.student))
    )
    return serialize_report(report)


@router.post("/{report_id}/review", response_model=ReportRead)
def review_report(
    report_id: int,
    payload: ReportReview,
    _teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    try:
        ensure_report_transition(report.status, "reviewed")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report is not ready for review") from None
    report.status = "reviewed"
    report.teacher_score = payload.teacher_score
    report.teacher_feedback = payload.teacher_feedback
    db.commit()
    db.refresh(report)
    report = db.scalar(
        select(Report)
        .where(Report.id == report.id)
        .options(selectinload(Report.conversation).selectinload(Conversation.messages), selectinload(Report.student))
    )
    return serialize_report(report)
