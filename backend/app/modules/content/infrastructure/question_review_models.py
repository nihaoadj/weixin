"""Content-owned medical decisions for exact classroom question revisions."""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class ClassroomQuestionReview(Base):
    __tablename__ = "classroom_question_reviews"
    __table_args__ = (
        UniqueConstraint("package_item_id", "content_digest", name="uq_classroom_question_review_revision"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_classroom_question_review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_item_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_package_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    content_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending", nullable=False)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    review_comment: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["ClassroomQuestionReview"]
