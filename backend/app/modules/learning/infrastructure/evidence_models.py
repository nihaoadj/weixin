from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database import Base


class LearningEvidenceEvent(Base):
    __tablename__ = "learning_evidence_events"
    __table_args__ = (
        CheckConstraint(
            "(visibility_scope = 'student_only' AND class_id IS NULL) OR "
            "(visibility_scope IN ('class_aggregate', 'class_detail') AND class_id IS NOT NULL)",
            name="ck_learning_evidence_visibility_class",
        ),
        CheckConstraint(
            "authority_level != 'personal_unverified' OR visibility_scope = 'student_only'",
            name="ck_learning_evidence_personal_visibility",
        ),
        UniqueConstraint("dedupe_key", name="uq_learning_evidence_event_dedupe"),
        Index("ix_learning_evidence_event_student_time", "student_id", "occurred_at", "id"),
        Index("ix_learning_evidence_event_class_time", "class_id", "occurred_at", "id"),
        Index("ix_learning_evidence_event_source", "source_type", "source_id"),
        Index(
            "ix_learning_evidence_event_authority_visibility_time", "authority_level", "visibility_scope", "occurred_at"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    authority_level: Mapped[str] = mapped_column(String(30), nullable=False)
    visibility_scope: Mapped[str] = mapped_column(String(30), nullable=False)
    event_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    contract_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    metrics: Mapped[list[LearningEvidenceMetric]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="LearningEvidenceMetric.id"
    )


class LearningEvidenceMetric(Base):
    __tablename__ = "learning_evidence_metrics"
    __table_args__ = (
        CheckConstraint(
            "normalized_score IS NULL OR (normalized_score >= 0 AND normalized_score <= 100)",
            name="ck_learning_evidence_metric_score",
        ),
        UniqueConstraint("event_id", "metric_kind", "metric_code", name="uq_learning_evidence_metric_code"),
        Index("ix_learning_evidence_metric_kind_code_event", "metric_kind", "metric_code", "event_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("learning_evidence_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[str] = mapped_column(String(24), nullable=False)
    evidence_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    event: Mapped[LearningEvidenceEvent] = relationship(back_populates="metrics")


__all__ = ["LearningEvidenceEvent", "LearningEvidenceMetric"]
