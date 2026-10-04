from __future__ import annotations

from sqlalchemy import case, false, func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.identity.infrastructure.models import User
from app.modules.qa.infrastructure.models import Conversation, Message
from app.modules.reports.application.ports import ReportDraftCommand, ReportRepository, ReportReviewCommand
from app.modules.reports.application.records import MessageRecord, ReportRecord, ReportSummaryPage, ReportSummaryRecord
from app.modules.reports.infrastructure.models import Report, ReportKnowledgeLink
from app.shared.actor import Actor
from app.shared.errors import ResourceAmbiguous


class SqlAlchemyReportRepository(ReportRepository):
    """SQL adapter for reports plus the explicitly declared conversation read port.

    Teacher visibility is expressed purely through the application-resolved
    ``owned_class_ids`` (classroom scope port); no classroom tables are joined
    or imported here.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def _visible_statement(self, actor: Actor, owned_class_ids: tuple[int, ...] | None = None):
        statement = select(Report)
        if actor.role == "student":
            return statement.where(Report.student_id == actor.id)
        return statement.where(false())

    def _to_record(self, report: Report) -> ReportRecord:
        messages = tuple(
            MessageRecord(id=item.id, role=item.role, content=item.content, created_at=item.created_at)
            for item in (report.conversation.messages if report.conversation else [])
        )
        return ReportRecord(
            id=report.id,
            conversation_id=report.conversation_id,
            conversation_client_id=report.conversation.client_id if report.conversation else None,
            student_id=report.student_id,
            student_name=report.student.nickname if report.student else None,
            status=report.status,
            ai_score=report.ai_score,
            ai_summary=report.ai_summary,
            analysis=report.ai_analysis,
            messages=messages,
            teacher_score=report.teacher_score,
            teacher_feedback=report.teacher_feedback,
            reviewer_id=report.reviewer_id,
            review_topic_codes=tuple(link.point_code for link in report.knowledge_links),
            class_id=report.class_id,
            class_name=report.class_name_snapshot,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    def _load_options(self, statement):
        return statement.options(
            selectinload(Report.conversation).selectinload(Conversation.messages),
            selectinload(Report.student),
            selectinload(Report.knowledge_links),
        )

    def _load(self, statement) -> ReportRecord | None:
        report = self._session.scalar(self._load_options(statement))
        return self._to_record(report) if report is not None else None

    def conversation_owner(self, conversation_id: int) -> int | None:
        return self._session.scalar(select(Conversation.student_id).where(Conversation.id == conversation_id))

    def find_for_student(self, report_id: int, student_id: int) -> ReportRecord | None:
        return self._load(select(Report).where(Report.id == report_id, Report.student_id == student_id))

    def find_for_student_by_conversation(self, conversation_id: int, student_id: int) -> ReportRecord | None:
        return self._load(
            select(Report).where(Report.conversation_id == conversation_id, Report.student_id == student_id)
        )

    def find_visible(self, actor: Actor, report_id: int, owned_class_ids=None) -> ReportRecord | None:
        return self._load(self._visible_statement(actor, owned_class_ids).where(Report.id == report_id))

    def find_by_client_id(self, actor: Actor, client_id: str, owned_class_ids=None) -> ReportRecord | None:
        statement = (
            self._visible_statement(actor, owned_class_ids)
            .join(Conversation, Conversation.id == Report.conversation_id)
            .where(Conversation.client_id == client_id)
            .limit(2)
        )
        reports = self._session.scalars(self._load_options(statement)).all()
        if len(reports) > 1:
            raise ResourceAmbiguous
        return self._to_record(reports[0]) if reports else None

    def list_full(self, actor: Actor, owned_class_ids=None) -> tuple[ReportRecord, ...]:
        reports = self._session.scalars(
            self._load_options(
                self._visible_statement(actor, owned_class_ids).order_by(Report.updated_at.desc(), Report.id.desc())
            )
        ).all()
        return tuple(self._to_record(report) for report in reports)

    def list_summaries(self, actor: Actor, limit: int, offset: int, owned_class_ids=None) -> ReportSummaryPage:
        visible = self._visible_statement(actor, owned_class_ids)
        base = visible.subquery()
        total, pending_count, reviewed_count = self._session.execute(
            select(
                func.count(),
                func.sum(case((base.c.status == "pending_review", 1), else_=0)),
                func.sum(case((base.c.status == "reviewed", 1), else_=0)),
            ).select_from(base)
        ).one()
        message_count = (
            select(func.count(Message.id))
            .where(Message.conversation_id == Report.conversation_id)
            .correlate(Report)
            .scalar_subquery()
        )
        message_preview = (
            select(func.substr(Message.content, 1, 160))
            .where(Message.conversation_id == Report.conversation_id)
            .order_by(Message.id.asc())
            .limit(1)
            .correlate(Report)
            .scalar_subquery()
        )
        rows = (
            self._session.execute(
                visible.join(Conversation, Conversation.id == Report.conversation_id)
                .join(User, User.id == Report.student_id)
                .with_only_columns(
                    Report.id,
                    Report.conversation_id,
                    Report.student_id,
                    Report.status,
                    Report.ai_score,
                    Report.teacher_score,
                    Report.class_id,
                    Report.class_name_snapshot,
                    Report.created_at,
                    Report.updated_at,
                    Conversation.client_id.label("conversation_client_id"),
                    User.nickname.label("student_name"),
                    func.coalesce(message_preview, "").label("message_preview"),
                    message_count.label("message_count"),
                )
                .order_by(Report.updated_at.desc(), Report.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .mappings()
            .all()
        )
        items = tuple(
            ReportSummaryRecord(
                id=row["id"],
                conversation_id=row["conversation_id"],
                conversation_client_id=row["conversation_client_id"],
                student_id=row["student_id"],
                student_name=row["student_name"],
                status=row["status"],
                ai_score=row["ai_score"],
                teacher_score=row["teacher_score"],
                message_preview=row["message_preview"],
                message_count=row["message_count"] or 0,
                class_id=row["class_id"],
                class_name=row["class_name_snapshot"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        )
        return ReportSummaryPage(
            items=items,
            total=total or 0,
            pending_count=pending_count or 0,
            reviewed_count=reviewed_count or 0,
            limit=limit,
            offset=offset,
        )

    def save_draft(self, report_id: int | None, student_id: int, command: ReportDraftCommand) -> int:
        report = self._session.get(Report, report_id) if report_id is not None else None
        if report is None:
            report = Report(conversation_id=command.conversation_id, student_id=student_id)
            self._session.add(report)
        report.ai_score = command.ai_score
        report.ai_summary = command.ai_summary
        report.ai_analysis = command.analysis
        report.status = "draft"
        self._session.flush()
        return report.id

    def submit(self, report_id: int, student_id: int, class_id: int, class_name_snapshot: str) -> None:
        report = self._session.get(Report, report_id)
        if report is None or report.student_id != student_id:
            return
        report.status = "pending_review"
        report.class_id = class_id
        report.class_name_snapshot = class_name_snapshot

    def review(self, report_id: int, reviewer_id: int, command: ReportReviewCommand) -> None:
        report = self._session.get(Report, report_id)
        if report is None:
            return
        report.status = "reviewed"
        report.teacher_score = command.teacher_score
        report.teacher_feedback = command.teacher_feedback
        report.reviewer_id = reviewer_id
        report.knowledge_links.clear()
        report.knowledge_links.extend(ReportKnowledgeLink(point_code=code) for code in command.review_topic_codes)
