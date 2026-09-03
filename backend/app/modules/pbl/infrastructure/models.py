from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class PblSession(Base):
    __tablename__ = "pbl_sessions"
    __table_args__ = (Index("ix_pbl_sessions_class_status", "class_id", "status"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_code: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(40))
    invocation_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PblParticipation(Base):
    __tablename__ = "pbl_participations"
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_pbl_participation_student"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("pbl_sessions.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    coze_user_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coze_conversation_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    messages: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PblDiagnosticSnapshot(Base):
    __tablename__ = "pbl_diagnostic_snapshots"
    __table_args__ = (UniqueConstraint("participation_id", "revision", name="uq_pbl_snapshot_revision"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participation_id: Mapped[int] = mapped_column(ForeignKey("pbl_participations.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    assistant_reply: Mapped[str] = mapped_column(Text)
    follow_up_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_gaps: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    reasoning_issues: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PblQuestionSuggestion(Base):
    __tablename__ = "pbl_question_suggestions"
    __table_args__ = (Index("ix_pbl_suggestion_snapshot_status", "snapshot_id", "status"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("pbl_diagnostic_snapshots.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text)
    linked_findings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    version: Mapped[int] = mapped_column(Integer, default=1)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id"), nullable=True, unique=True)
