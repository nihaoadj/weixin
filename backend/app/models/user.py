from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    nickname: Mapped[str] = mapped_column(String(80))
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    class_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="student")
    reports: Mapped[list["Report"]] = relationship(back_populates="student")
    question_threads: Mapped[list["QuestionThread"]] = relationship(back_populates="student")
    case_attempts: Mapped[list["CaseAttempt"]] = relationship(back_populates="student")
