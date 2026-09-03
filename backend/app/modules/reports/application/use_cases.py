from __future__ import annotations

from app.modules.content.public import knowledge_point_view
from app.modules.reports.application.ports import ReportDraftCommand, ReportRepository, ReportReviewCommand
from app.modules.reports.application.records import ReportRecord, ReportSummaryPage
from app.modules.reports.domain.policy import ReportPolicy
from app.shared.actor import Actor
from app.shared.errors import AppError, ResourceAmbiguous
from app.shared.uow import UnitOfWork


class ReportsApplication:
    def __init__(self, repository: ReportRepository, uow: UnitOfWork, policy: ReportPolicy | None = None) -> None:
        self._repository = repository
        self._uow = uow
        self._policy = policy or ReportPolicy()

    def list_summaries(self, actor: Actor, limit: int, offset: int) -> ReportSummaryPage:
        return self._repository.list_summaries(actor, limit, offset)

    def list_full(self, actor: Actor) -> tuple[ReportRecord, ...]:
        return self._repository.list_full(actor)

    def get(self, actor: Actor, report_id: int) -> ReportRecord:
        record = self._repository.find_visible(actor, report_id)
        if record is None:
            raise AppError("RESOURCE_NOT_FOUND", "报告不存在", 404)
        return record

    def get_by_client_id(self, actor: Actor, client_id: str) -> ReportRecord:
        try:
            record = self._repository.find_by_client_id(actor, client_id)
        except ResourceAmbiguous as error:
            raise AppError("STATE_CONFLICT", "报告标识不唯一，请使用报告 ID", 409) from error
        if record is None:
            raise AppError("RESOURCE_NOT_FOUND", "报告不存在", 404)
        return record

    def save_draft(self, actor: Actor, command: ReportDraftCommand) -> ReportRecord:
        actor.require_role("student")
        owner_id = self._repository.conversation_owner(command.conversation_id)
        if owner_id != actor.id:
            raise AppError("RESOURCE_NOT_FOUND", "对话不存在", 404)
        existing = self._repository.find_for_student_by_conversation(command.conversation_id, actor.id)
        if existing is not None and existing.status != "draft":
            return existing
        report_id = self._repository.save_draft(existing.id if existing is not None else None, actor.id, command)
        self._uow.commit()
        result = self._repository.find_for_student(report_id, actor.id)
        if result is None:
            raise AppError("SERVICE_ERROR", "报告保存失败", 500)
        return result

    def submit(self, actor: Actor, report_id: int) -> ReportRecord:
        actor.require_role("student")
        report = self._repository.find_for_student(report_id, actor.id)
        if report is None:
            raise AppError("RESOURCE_NOT_FOUND", "报告不存在", 404)
        self._policy.require_transition(report.status, "pending_review")
        self._repository.submit(report_id, actor.id)
        self._uow.commit()
        result = self._repository.find_for_student(report_id, actor.id)
        if result is None:
            raise AppError("SERVICE_ERROR", "报告提交失败", 500)
        return result

    def review(self, actor: Actor, report_id: int, command: ReportReviewCommand) -> ReportRecord:
        actor.require_role("teacher")
        topic_codes = tuple(dict.fromkeys(command.review_topic_codes))
        if len(topic_codes) > 3:
            raise AppError("VALIDATION_ERROR", "建议复习知识点最多选择 3 个", 422)
        for code in topic_codes:
            if knowledge_point_view(code) is None:
                raise AppError("VALIDATION_ERROR", "知识点不存在", 422)
        report = self._repository.find_visible(actor, report_id)
        if report is None:
            # Drafts are intentionally not returned by the teacher visibility adapter,
            # but the application maps the attempted review to the stable conflict.
            draft = self._repository.find_by_id_for_review(report_id)
            if draft is None:
                raise AppError("RESOURCE_NOT_FOUND", "报告不存在", 404)
            report = draft
        self._policy.require_transition(report.status, "reviewed")
        self._repository.review(
            report_id,
            actor.id,
            ReportReviewCommand(
                teacher_score=command.teacher_score,
                teacher_feedback=command.teacher_feedback,
                review_topic_codes=topic_codes,
            ),
        )
        self._uow.commit()
        result = self._repository.find_by_id_for_review(report_id)
        if result is None:
            raise AppError("SERVICE_ERROR", "报告批阅失败", 500)
        return result
