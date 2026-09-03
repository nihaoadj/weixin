from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database import Base

if TYPE_CHECKING:
    from app.modules.content.infrastructure.models import Problem
    from app.modules.identity.infrastructure.models import User
    from app.modules.reports.infrastructure.models import Report


class Conversation(Base):
    """QA-owned student conversation table."""

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("client_id", "student_id", name="uq_conversation_client_student"),
        Index("ix_conversations_updated_id", "updated_at", "id"),
        Index("ix_conversations_student_updated_id", "student_id", "updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[str] = mapped_column(String(100), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    learning_contexts: Mapped[list["ConversationLearningContext"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationLearningContext.topic_code"
    )
    report: Mapped["Report | None"] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ConversationLearningContext(Base):
    """Student-confirmed public knowledge context for a conversation."""

    __tablename__ = "conversation_learning_contexts"
    __table_args__ = (UniqueConstraint("conversation_id", "topic_code", name="uq_conversation_learning_topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    topic_code: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(30), default="student_selected")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="learning_contexts")


class QuestionThread(Base):
    """QA-owned ordinary-question thread."""

    __tablename__ = "question_threads"
    __table_args__ = (UniqueConstraint("problem_id", "student_id", name="uq_question_thread_problem_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    problem: Mapped["Problem"] = relationship(back_populates="question_threads")
    student: Mapped["User"] = relationship(back_populates="question_threads")
    messages: Mapped[list["QuestionThreadMessage"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )


class QuestionThreadMessage(Base):
    __tablename__ = "question_thread_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("question_threads.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped[QuestionThread] = relationship(back_populates="messages")


__all__ = ["Conversation", "ConversationLearningContext", "Message", "QuestionThread", "QuestionThreadMessage"]
