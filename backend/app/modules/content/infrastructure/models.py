from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database import Base

if TYPE_CHECKING:
    from app.modules.qa.infrastructure.models import QuestionThread
    from app.modules.training.infrastructure.models import CaseAttempt


class Problem(Base):
    """Content-owned problem/case table."""

    __tablename__ = "problems"
    __table_args__ = (UniqueConstraint("slug", "version", name="uq_problem_slug_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    target: Mapped[str] = mapped_column(String(30), default="all")
    target_label: Mapped[str] = mapped_column(String(200), default="全体学生")
    target_ids: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    content_type: Mapped[str] = mapped_column(String(30), default="question", server_default="question", index=True)
    specialty: Mapped[str] = mapped_column(String(80), default="", server_default="")
    difficulty: Mapped[str] = mapped_column(String(30), default="basic", server_default="basic")
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    parent_problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id"), nullable=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    medical_review_status: Mapped[str] = mapped_column(String(30), default="not_submitted", index=True)
    capability_tags: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    case_definition: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rubric: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    question_threads: Mapped[list["QuestionThread"]] = relationship(back_populates="problem")
    case_attempts: Mapped[list["CaseAttempt"]] = relationship(back_populates="problem")
    parent_problem: Mapped["Problem | None"] = relationship(remote_side="Problem.id")
    knowledge_links: Mapped[list["ProblemKnowledgeLink"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan"
    )


class ProblemKnowledgeLink(Base):
    __tablename__ = "problem_knowledge_links"
    __table_args__ = (UniqueConstraint("problem_id", "point_code", name="uq_problem_knowledge_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    point_code: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    problem: Mapped[Problem] = relationship(back_populates="knowledge_links")


class ProblemOrigin(Base):
    """Idempotent source-to-published-problem relation owned by content."""

    __tablename__ = "problem_origins"
    __table_args__ = (UniqueConstraint("source_type", "source_id", name="uq_problem_origin_source"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[int] = mapped_column(Integer)


class KnowledgeCardContribution(Base):
    """Teacher-authored card attached to a fixed system knowledge point."""

    __tablename__ = "knowledge_card_contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_card_code: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True)
    point_code: Mapped[str] = mapped_column(String(120), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    class_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    card_type: Mapped[str] = mapped_column(String(20), default="single_choice")
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    correct_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    reference: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_comment: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


__all__ = ["KnowledgeCardContribution", "Problem", "ProblemKnowledgeLink", "ProblemOrigin"]
