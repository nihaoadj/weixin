from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LearningPlan(Base):
    __tablename__ = "learning_plans"
    __table_args__ = (UniqueConstraint("student_id", "source_assessment_id", name="uq_learning_plan_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_assessment_id: Mapped[int] = mapped_column(ForeignKey("case_assessments.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    target_dimension_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(30), default="deterministic")
    model_name: Mapped[str] = mapped_column(String(120), default="deterministic-fallback")
    prompt_version: Mapped[str] = mapped_column(String(80), default="practice-v1")
    fallback_used: Mapped[bool] = mapped_column(default=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tasks: Mapped[list["LearningTask"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="LearningTask.position"
    )


class LearningTask(Base):
    __tablename__ = "learning_tasks"
    __table_args__ = (UniqueConstraint("plan_id", "position", name="uq_learning_task_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("learning_plans.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    task_type: Mapped[str] = mapped_column(String(30))
    dimension_id: Mapped[str] = mapped_column(String(50))
    stage_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id"), nullable=True, index=True)
    source_attempt_id: Mapped[int | None] = mapped_column(ForeignKey("case_attempts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    public_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    private_rubric: Mapped[dict] = mapped_column(JSON, default=dict)
    blueprint_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    blueprint_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped[LearningPlan] = relationship(back_populates="tasks")
    attempt: Mapped["LearningTaskAttempt | None"] = relationship(
        back_populates="task", uselist=False, cascade="all, delete-orphan"
    )


class LearningTaskAttempt(Base):
    __tablename__ = "learning_task_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("learning_tasks.id", ondelete="CASCADE"), unique=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    answer: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float | None] = mapped_column(nullable=True)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    feedback: Mapped[str] = mapped_column(Text, default="")
    next_step: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(String(120), default="deterministic-fallback")
    prompt_version: Mapped[str] = mapped_column(String(80), default="practice-v1")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    fallback_used: Mapped[bool] = mapped_column(default=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped[LearningTask] = relationship(back_populates="attempt")


class StudentNotification(Base):
    __tablename__ = "student_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    entity_type: Mapped[str] = mapped_column(String(40), default="learning_plan")
    entity_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
