from __future__ import annotations

from app.modules.content.public import knowledge_point_view
from app.modules.qa.application.ports import (
    ConversationCommand,
    ConversationRepository,
    QuestionRepository,
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
    def __init__(self, repository: ConversationRepository, uow: UnitOfWork) -> None:
        self._repository = repository
        self._uow = uow

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

    @staticmethod
    def _validate_topic(knowledge_point_code: str | None) -> None:
        if knowledge_point_code is not None and knowledge_point_view(knowledge_point_code) is None:
            raise AppError("VALIDATION_ERROR", "学习主题不存在", 422)

    @staticmethod
    def _validate_topics(topic_codes: tuple[str, ...]) -> None:
        if len(topic_codes) > 3 or any(knowledge_point_view(code) is None for code in topic_codes):
            raise AppError("VALIDATION_ERROR", "学习主题不存在或数量超限", 422)


class QuestionsApplication:
    def __init__(self, repository: QuestionRepository, uow: UnitOfWork) -> None:
        self._repository = repository
        self._uow = uow

    def list(self, actor: Actor) -> tuple[StudentQuestionRecord, ...]:
        actor.require_role("student")
        class_codes = set(actor.class_ids) | self._repository.class_codes(actor.id)
        return self._repository.list_student_questions(actor, class_codes)

    def get(self, actor: Actor, problem_id: int) -> StudentQuestionRecord:
        actor.require_role("student")
        class_codes = set(actor.class_ids) | self._repository.class_codes(actor.id)
        result = self._repository.find_student_question(actor, problem_id, class_codes)
        if result is None:
            raise AppError("RESOURCE_NOT_FOUND", "题目不存在", 404)
        return result

    def thread(self, actor: Actor, problem_id: int) -> QuestionThreadRecord:
        actor.require_role("student")
        result = self._repository.find_thread(problem_id, actor.id)
        if result is None:
            raise AppError("RESOURCE_NOT_FOUND", "题目作答线程不存在", 404)
        return result

    def upsert_thread(self, actor: Actor, problem_id: int, command: QuestionThreadCommand) -> QuestionThreadRecord:
        actor.require_role("student")
        class_codes = set(actor.class_ids) | self._repository.class_codes(actor.id)
        if self._repository.find_student_question(actor, problem_id, class_codes) is None:
            raise AppError("RESOURCE_NOT_FOUND", "题目不存在", 404)
        result = self._repository.upsert_thread(problem_id, actor.id, command)
        self._uow.commit()
        return result
