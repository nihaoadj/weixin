from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database import Base

if TYPE_CHECKING:
    from app.modules.content.infrastructure.models import Problem
    from app.modules.identity.infrastructure.models import User
    from app.modules.learning.infrastructure.models import LearningTask


class CaseAttempt(Base):
    """Training-owned case attempt aggregate."""

    __tablename__ = "case_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem_version: Mapped[int] = mapped_column(Integer)
    problem_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    current_stage: Mapped[str] = mapped_column(String(40), default="history")
    retry_of_id: Mapped[int | None] = mapped_column(ForeignKey("case_attempts.id"), nullable=True)
    focus_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    learning_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_tasks.id"), nullable=True, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    problem: Mapped["Problem"] = relationship(back_populates="case_attempts")
    student: Mapped["User"] = relationship(back_populates="case_attempts")
    messages: Mapped[list["CaseAttemptMessage"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")
    submissions: Mapped[list["StageSubmission"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")
    assessment: Mapped["CaseAssessment | None"] = relationship(
        back_populates="attempt", uselist=False, cascade="all, delete-orphan"
    )
    learning_task: Mapped["LearningTask | None"] = relationship(
        foreign_keys=[learning_task_id], primaryjoin="CaseAttempt.learning_task_id == LearningTask.id"
    )


class CaseAttemptMessage(Base):
    __tablename__ = "case_attempt_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("case_attempts.id", ondelete="CASCADE"), index=True)
    stage_id: Mapped[str] = mapped_column(String(40), default="history")
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    revealed_fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempt: Mapped[CaseAttempt] = relationship(back_populates="messages")


class StageSubmission(Base):
    __tablename__ = "stage_submissions"
    __table_args__ = (UniqueConstraint("attempt_id", "stage_id", name="uq_stage_submission_attempt_stage"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("case_attempts.id"), index=True)
    stage_id: Mapped[str] = mapped_column(String(40))
    answer: Mapped[dict] = mapped_column(JSON)
    feedback: Mapped[str] = mapped_column(Text, default="")
    inherited_from_id: Mapped[int | None] = mapped_column(ForeignKey("stage_submissions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempt: Mapped[CaseAttempt] = relationship(back_populates="submissions")


class CaseAssessment(Base):
    __tablename__ = "case_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("case_attempts.id"), unique=True)
    total_score: Mapped[float] = mapped_column(Float)
    dimensions: Mapped[list[dict]] = mapped_column(JSON)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list)
    next_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text)
    focus_stage: Mapped[str] = mapped_column(String(40))
    model_name: Mapped[str] = mapped_column(String(120), default="deterministic-fallback")
    prompt_version: Mapped[str] = mapped_column(String(80), default="case-v1")
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempt: Mapped[CaseAttempt] = relationship(back_populates="assessment")


class AICallLog(Base):
    __tablename__ = "ai_call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    attempt_id: Mapped[int | None] = mapped_column(ForeignKey("case_attempts.id"), nullable=True)
    learning_task_id: Mapped[int | None] = mapped_column(ForeignKey("learning_tasks.id"), nullable=True, index=True)
    blueprint_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    blueprint_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task: Mapped[str] = mapped_column(String(30))
    model_name: Mapped[str] = mapped_column(String(120), default="deterministic-fallback")
    prompt_version: Mapped[str] = mapped_column(String(80), default="case-v1")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = ["AICallLog", "CaseAssessment", "CaseAttempt", "CaseAttemptMessage", "StageSubmission"]
