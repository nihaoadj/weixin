from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database import Base

if TYPE_CHECKING:
    from app.modules.identity.infrastructure.models import User
    from app.modules.qa.infrastructure.models import Conversation


class Report(Base):
    """Reports-owned student report table."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_report_conversation"),
        Index("ix_reports_updated_id", "updated_at", "id"),
        Index("ix_reports_student_updated_id", "student_id", "updated_at", "id"),
        Index("ix_reports_class_status_updated_id", "class_id", "status", "updated_at", "id"),
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
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    # Submitting class and its name at submit time; drafts and unattributable
    # history stay NULL and remain student-only.
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    class_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="report")
    student: Mapped["User"] = relationship(back_populates="reports", foreign_keys=[student_id])
    knowledge_links: Mapped[list["ReportKnowledgeLink"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportKnowledgeLink(Base):
    """Teacher-selected, catalog-backed revision topics for a reviewed report."""

    __tablename__ = "report_knowledge_links"
    __table_args__ = (
        UniqueConstraint("report_id", "point_code", name="uq_report_knowledge_link"),
        Index("ix_report_knowledge_links_point", "point_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    point_code: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    report: Mapped["Report"] = relationship(back_populates="knowledge_links")


__all__ = ["Report", "ReportKnowledgeLink"]
