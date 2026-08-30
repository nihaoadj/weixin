from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Problem(Base):
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


class QuestionThread(Base):
    __tablename__ = "question_threads"
    __table_args__ = (UniqueConstraint("problem_id", "student_id", name="uq_question_thread_problem_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    problem: Mapped[Problem] = relationship(back_populates="question_threads")
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
