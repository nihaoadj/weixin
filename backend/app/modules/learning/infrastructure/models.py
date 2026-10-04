from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database import Base


class LearningPlan(Base):
    __tablename__ = "learning_plans"
    __table_args__ = (UniqueConstraint("student_id", "source_type", "source_id", name="uq_learning_plan_source_v2"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("case_assessments.id"), unique=True, index=True, nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(30), default="case_assessment", server_default="case_assessment")
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_context: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    verification_status: Mapped[str] = mapped_column(String(30), default="not_ready", server_default="not_ready")
    verification_note: Mapped[str] = mapped_column(Text, default="", server_default="")
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", name="fk_learning_verifier"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    current_cycle: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    max_cycles: Mapped[int] = mapped_column(Integer, default=2, server_default="2", nullable=False)
    automation_exhausted: Mapped[bool] = mapped_column(default=False, server_default="0", nullable=False)
    decision_policy_version: Mapped[str] = mapped_column(
        String(80), default="pbl-mastery-v1", server_default="pbl-mastery-v1", nullable=False
    )
    decision_basis: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    evaluations: Mapped[list["LearningPlanEvaluation"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="LearningPlanEvaluation.cycle_number"
    )


class LearningPlanEvaluation(Base):
    __tablename__ = "learning_plan_evaluations"
    __table_args__ = (UniqueConstraint("plan_id", "cycle_number", name="uq_learning_plan_evaluation_cycle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("learning_plans.id", ondelete="CASCADE"), index=True)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    checks: Mapped[list[dict]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    failed_targets: Mapped[list[dict]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    automation_exhausted: Mapped[bool] = mapped_column(default=False, server_default="0", nullable=False)
    record_source: Mapped[str] = mapped_column(String(20), default="runtime", server_default="runtime", nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped[LearningPlan] = relationship(back_populates="evaluations")


class LearningTask(Base):
    __tablename__ = "learning_tasks"
    __table_args__ = (UniqueConstraint("plan_id", "position", name="uq_learning_task_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("learning_plans.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    cycle_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), default="discussion", server_default="discussion")
    target_code: Mapped[str] = mapped_column(String(160), default="discussion", server_default="discussion")
    variant_code: Mapped[str] = mapped_column(String(200), default="v1", server_default="v1")
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
    client_submission_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
    entity_public_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        UniqueConstraint("student_id", "source_type", "source_id", "point_code", name="uq_review_item_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    point_code: Mapped[str] = mapped_column(String(120), index=True)
    card_code: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(160))
    note: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReviewState(Base):
    __tablename__ = "review_states"
    __table_args__ = (UniqueConstraint("student_id", "card_code", name="uq_review_state_student_card"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_code: Mapped[str] = mapped_column(String(160), index=True)
    point_code: Mapped[str] = mapped_column(String(120), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    ease: Mapped[float] = mapped_column(default=2.5)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    last_rating: Mapped[str | None] = mapped_column(String(12), nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewAttempt(Base):
    __tablename__ = "review_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("review_states.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    selected_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct: Mapped[bool] = mapped_column(nullable=False)
    rating: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = [
    "LearningPlan",
    "LearningPlanEvaluation",
    "LearningTask",
    "LearningTaskAttempt",
    "ReviewAttempt",
    "ReviewItem",
    "ReviewState",
    "StudentNotification",
]
