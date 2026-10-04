from __future__ import annotations

from app.modules.reports.application.ports import (
    ReportClassroomScope,
    ReportDraftCommand,
    ReportRepository,
    ReportReviewCommand,
    ReportSubmitCommand,
)
from app.modules.reports.application.records import ReportRecord, ReportSummaryPage
from app.modules.reports.domain.policy import ReportPolicy
from app.shared.actor import Actor
from app.shared.errors import AppError, ResourceAmbiguous
from app.shared.uow import UnitOfWork

_NOT_FOUND = ("RESOURCE_NOT_FOUND", "报告不存在", 404)


class ReportsApplication:
    def __init__(
        self,
        repository: ReportRepository,
        uow: UnitOfWork,
        policy: ReportPolicy | None = None,
        classroom_scope: ReportClassroomScope | None = None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._policy = policy or ReportPolicy()
        self._classroom_scope = classroom_scope

    def list_summaries(self, actor: Actor, limit: int, offset: int, class_id: int | None = None) -> ReportSummaryPage:
        self._require_student_history(actor)
        return self._repository.list_summaries(actor, limit, offset)

    def list_full(self, actor: Actor, class_id: int | None = None) -> tuple[ReportRecord, ...]:
        self._require_student_history(actor)
        return self._repository.list_full(actor)

    def get(self, actor: Actor, report_id: int) -> ReportRecord:
        self._require_student_history(actor)
        record = self._repository.find_visible(actor, report_id)
        if record is None:
            raise AppError(*_NOT_FOUND)
        return record

    def get_by_client_id(self, actor: Actor, client_id: str) -> ReportRecord:
        self._require_student_history(actor)
        try:
            record = self._repository.find_by_client_id(actor, client_id)
        except ResourceAmbiguous as error:
            raise AppError("STATE_CONFLICT", "报告标识不唯一，请使用报告 ID", 409) from error
        if record is None:
            raise AppError(*_NOT_FOUND)
        return record

    def save_draft(self, actor: Actor, command: ReportDraftCommand) -> ReportRecord:
        actor.require_role("student")
        raise AppError("STATE_CONFLICT", "普通问答不再生成学习总结", 409)

    def submit(self, actor: Actor, report_id: int, command: ReportSubmitCommand) -> ReportRecord:
        actor.require_role("student")
        raise AppError("STATE_CONFLICT", "普通问答学习总结不再提交教师", 409)

    def review(self, actor: Actor, report_id: int, command: ReportReviewCommand) -> ReportRecord:
        actor.require_role("teacher")
        raise AppError("STATE_CONFLICT", "普通问答学习总结已退役，历史数据仅供学生查看", 409)

    @staticmethod
    def _require_student_history(actor: Actor) -> None:
        if actor.role != "student":
            raise AppError(*_NOT_FOUND)
