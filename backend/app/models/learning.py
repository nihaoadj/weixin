from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Conversation(Base):
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
    report: Mapped["Report | None"] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_report_conversation"),
        Index("ix_reports_updated_id", "updated_at", "id"),
        Index("ix_reports_student_updated_id", "student_id", "updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    ai_score: Mapped[float] = mapped_column(Float, default=0)
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    ai_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    teacher_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    conversation: Mapped[Conversation] = relationship(back_populates="report")
    student: Mapped["User"] = relationship(back_populates="reports")
