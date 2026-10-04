from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.qa.application.ports import ConversationCommand, ConversationRepository
from app.modules.qa.application.records import (
    ConversationRecord,
    ConversationSummaryPage,
    ConversationSummaryRecord,
    MessageRecord,
)
from app.modules.qa.infrastructure.models import Conversation, ConversationLearningContext, Message
from app.modules.reports.infrastructure.models import Report


class SqlAlchemyConversationRepository(ConversationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _message_record(message: Message) -> MessageRecord:
        return MessageRecord(id=message.id, role=message.role, content=message.content, created_at=message.created_at)

    def _record(self, conversation: Conversation) -> ConversationRecord:
        return ConversationRecord(
            id=conversation.id,
            client_id=conversation.client_id,
            student_id=conversation.student_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=tuple(self._message_record(item) for item in conversation.messages),
            topic_codes=tuple(item.topic_code for item in conversation.learning_contexts),
        )

    def _load(self, statement) -> ConversationRecord | None:
        conversation = self._session.scalar(
            statement.options(selectinload(Conversation.messages), selectinload(Conversation.learning_contexts))
        )
        return self._record(conversation) if conversation is not None else None

    @staticmethod
    def _topic_filter(knowledge_point_code: str | None):
        if knowledge_point_code is None:
            return True
        return (
            select(ConversationLearningContext.id)
            .where(
                ConversationLearningContext.conversation_id == Conversation.id,
                ConversationLearningContext.topic_code == knowledge_point_code,
            )
            .exists()
        )

    def list_summaries(
        self, student_id: int, limit: int, offset: int, knowledge_point_code: str | None = None
    ) -> ConversationSummaryPage:
        message_count = (
            select(func.count(Message.id))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )
        message_preview = (
            select(func.substr(Message.content, 1, 160))
            .where(Message.conversation_id == Conversation.id)
            .order_by(Message.id.asc())
            .limit(1)
            .correlate(Conversation)
            .scalar_subquery()
        )
        filters = (Conversation.student_id == student_id, self._topic_filter(knowledge_point_code))
        total = self._session.scalar(select(func.count(Conversation.id)).where(*filters)) or 0
        rows = self._session.execute(
            select(Conversation, message_preview, message_count, Report.id, Report.status)
            .outerjoin(Report, Report.conversation_id == Conversation.id)
            .where(*filters)
            .options(selectinload(Conversation.learning_contexts))
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        items = tuple(
            ConversationSummaryRecord(
                id=conversation.id,
                client_id=conversation.client_id,
                message_preview=preview or "",
                message_count=count or 0,
                report_id=report_id,
                report_status=report_status,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                topic_codes=tuple(item.topic_code for item in conversation.learning_contexts),
            )
            for conversation, preview, count, report_id, report_status in rows
        )
        return ConversationSummaryPage(items=items, total=total, limit=limit, offset=offset)

    def find_by_client(self, client_id: str, student_id: int) -> ConversationRecord | None:
        return self._load(
            select(Conversation).where(
                Conversation.client_id == client_id,
                Conversation.student_id == student_id,
            )
        )

    def find_by_id(self, conversation_id: int, student_id: int) -> ConversationRecord | None:
        return self._load(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.student_id == student_id,
            )
        )

    def list_full(self, student_id: int, knowledge_point_code: str | None = None) -> tuple[ConversationRecord, ...]:
        conversations = self._session.scalars(
            select(Conversation)
            .where(Conversation.student_id == student_id, self._topic_filter(knowledge_point_code))
            .options(selectinload(Conversation.messages), selectinload(Conversation.learning_contexts))
            .order_by(Conversation.updated_at.desc())
        ).all()
        return tuple(self._record(item) for item in conversations)

    def set_topics(
        self, student_id: int, conversation_id: int, topic_codes: tuple[str, ...]
    ) -> ConversationRecord | None:
        conversation = self._session.scalar(
            select(Conversation)
            .where(Conversation.id == conversation_id, Conversation.student_id == student_id)
            .options(selectinload(Conversation.messages), selectinload(Conversation.learning_contexts))
        )
        if conversation is None:
            return None
        conversation.learning_contexts.clear()
        conversation.updated_at = datetime.now(UTC)
        self._session.flush()
        conversation.learning_contexts.extend(
            ConversationLearningContext(topic_code=topic_code, source="student_selected") for topic_code in topic_codes
        )
        self._session.flush()
        return self._record(conversation)

    def upsert(self, student_id: int, command: ConversationCommand) -> ConversationRecord:
        conversation = self._session.scalar(
            select(Conversation)
            .where(Conversation.client_id == command.client_id, Conversation.student_id == student_id)
            .options(selectinload(Conversation.messages), selectinload(Conversation.learning_contexts))
        )
        if conversation is None:
            conversation = Conversation(client_id=command.client_id, student_id=student_id)
            self._session.add(conversation)
            self._session.flush()
        conversation.messages.clear()
        conversation.learning_contexts.clear()
        conversation.updated_at = datetime.now(UTC)
        self._session.flush()
        for message in command.messages:
            conversation.messages.append(Message(role=message.role, content=message.content))
        for topic_code in command.topic_codes:
            conversation.learning_contexts.append(
                ConversationLearningContext(topic_code=topic_code, source="student_selected")
            )
        self._session.flush()
        return self._record(conversation)
