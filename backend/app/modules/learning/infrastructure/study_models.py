from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class StudyPath(Base):
    __tablename__ = "study_paths"
    __table_args__ = (UniqueConstraint("student_id", "client_id"), UniqueConstraint("session_id", "point_code"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    point_code: Mapped[str] = mapped_column(String(120))
    session_id: Mapped[int] = mapped_column(ForeignKey("pbl_sessions.id"))
    client_id: Mapped[str] = mapped_column(String(100))
    material_version: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudyPracticeGroup(Base):
    __tablename__ = "study_practice_groups"
    __table_args__ = (UniqueConstraint("path_id", "cycle"), CheckConstraint("cycle IN (1, 2)"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("study_paths.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("pbl_diagnostic_snapshots.id"))
    cycle: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="generating")
    claim: Mapped[str] = mapped_column(String(100))
    questions: Mapped[list[dict]] = mapped_column(JSON, default=list)
    failure: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudyPracticeAttempt(Base):
    __tablename__ = "study_practice_attempts"
    __table_args__ = (UniqueConstraint("student_id", "client_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("study_practice_groups.id"), index=True)
    question_index: Mapped[int] = mapped_column(Integer)
    client_id: Mapped[str] = mapped_column(String(100))
    selected_option: Mapped[int] = mapped_column(Integer)
    correct: Mapped[bool] = mapped_column(Boolean)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
