from __future__ import annotations

from app.modules.content.public import KnowledgeCatalogPort
from app.modules.qa.application.ports import (
    ConversationCommand,
    ConversationRepository,
    QuestionThreadCommand,
)
from app.modules.qa.application.records import (
    ConversationRecord,
    ConversationSummaryPage,
    QuestionThreadRecord,
    StudentQuestionRecord,
)
from app.shared.actor import Actor
from app.shared.errors import AppError
from app.shared.uow import UnitOfWork


class ConversationsApplication:
    def __init__(
        self, repository: ConversationRepository, uow: UnitOfWork, knowledge_catalog: KnowledgeCatalogPort
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._knowledge_catalog = knowledge_catalog

    def list_summaries(
        self, actor: Actor, limit: int, offset: int, knowledge_point_code: str | None = None
    ) -> ConversationSummaryPage:
        actor.require_role("student")
        self._validate_topic(knowledge_point_code)
        return self._repository.list_summaries(actor.id, limit, offset, knowledge_point_code)

    def get_by_client(self, actor: Actor, client_id: str) -> ConversationRecord:
        actor.require_role("student")
        record = self._repository.find_by_client(client_id, actor.id)
        if record is None:
            raise AppError("RESOURCE_NOT_FOUND", "对话不存在", 404)
        return record

    def get(self, actor: Actor, conversation_id: int) -> ConversationRecord:
        actor.require_role("student")
        record = self._repository.find_by_id(conversation_id, actor.id)
        if record is None:
            raise AppError("RESOURCE_NOT_FOUND", "对话不存在", 404)
        return record

    def list_full(self, actor: Actor, knowledge_point_code: str | None = None) -> tuple[ConversationRecord, ...]:
        actor.require_role("student")
        self._validate_topic(knowledge_point_code)
        return self._repository.list_full(actor.id, knowledge_point_code)

    def upsert(self, actor: Actor, command: ConversationCommand) -> ConversationRecord:
        actor.require_role("student")
        self._validate_topics(command.topic_codes)
        record = self._repository.upsert(actor.id, command)
        self._uow.commit()
        result = self._repository.find_by_id(record.id, actor.id)
        if result is None:
            raise AppError("SERVICE_ERROR", "对话保存失败", 500)
        return result

    def set_topics(self, actor: Actor, conversation_id: int, topic_codes: tuple[str, ...]) -> ConversationRecord:
        actor.require_role("student")
        self._validate_topics(topic_codes)
        result = self._repository.set_topics(actor.id, conversation_id, topic_codes)
        if result is None:
            raise AppError("RESOURCE_NOT_FOUND", "对话不存在", 404)
        self._uow.commit()
        return result

    def _validate_topic(self, knowledge_point_code: str | None) -> None:
        if knowledge_point_code is not None and self._knowledge_catalog.point_view(knowledge_point_code) is None:
            raise AppError("VALIDATION_ERROR", "学习主题不存在", 422)

    def _validate_topics(self, topic_codes: tuple[str, ...]) -> None:
        if len(topic_codes) > 3 or not self._knowledge_catalog.contains_points(topic_codes):
            raise AppError("VALIDATION_ERROR", "学习主题不存在或数量超限", 422)


class QuestionsApplication:
    def list(self, actor: Actor) -> tuple[StudentQuestionRecord, ...]:
        actor.require_role("student")
        return ()

    def get(self, actor: Actor, problem_id: int) -> StudentQuestionRecord:
        actor.require_role("student")
        raise AppError("RESOURCE_NOT_FOUND", "题目不存在", 404)

    def thread(self, actor: Actor, problem_id: int) -> QuestionThreadRecord:
        actor.require_role("student")
        raise AppError("RESOURCE_NOT_FOUND", "题目作答线程不存在", 404)

    def upsert_thread(self, actor: Actor, problem_id: int, command: QuestionThreadCommand) -> QuestionThreadRecord:
        actor.require_role("student")
        raise AppError("RETIRED_FLOW", "开放讨论题已退役，请打开学习计划", 409)
