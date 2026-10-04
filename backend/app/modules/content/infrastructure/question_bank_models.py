"""Teacher-owned, versioned question-bank copies."""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class TeacherQuestionBankItem(Base):
    __tablename__ = "teacher_question_bank_items"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_teacher_question_bank_status"),
        CheckConstraint("version >= 1", name="ck_teacher_question_bank_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    current_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TeacherQuestionBankRevision(Base):
    __tablename__ = "teacher_question_bank_revisions"
    __table_args__ = (UniqueConstraint("bank_item_id", "version", name="uq_teacher_bank_revision_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_item_id: Mapped[int] = mapped_column(
        ForeignKey("teacher_question_bank_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    answer: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    point_codes: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    dimension_ids: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    source_kind: Mapped[str] = mapped_column(String(30), nullable=False, default="legacy_detached")
    source_public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_package_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    medical_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BankImportReceipt(Base):
    __tablename__ = "bank_import_receipts"
    __table_args__ = (
        UniqueConstraint("teacher_id", "source_package_item_id", "source_digest", name="uq_bank_import_source"),
        UniqueConstraint(
            "teacher_id", "source_kind", "source_public_id", "source_digest", name="uq_bank_import_public_source"
        ),
        UniqueConstraint("teacher_id", "client_request_id", name="uq_bank_import_request"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(30), nullable=False, default="legacy_detached")
    source_public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_package_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    bank_item_id: Mapped[int] = mapped_column(
        ForeignKey("teacher_question_bank_items.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BankArchiveReceipt(Base):
    __tablename__ = "bank_archive_receipts"
    __table_args__ = (UniqueConstraint("teacher_id", "client_request_id", name="uq_bank_archive_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    bank_item_id: Mapped[int] = mapped_column(
        ForeignKey("teacher_question_bank_items.id", ondelete="RESTRICT"), nullable=False
    )
    client_request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_version: Mapped[int] = mapped_column(Integer, nullable=False)
    result_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


__all__ = ["TeacherQuestionBankItem", "TeacherQuestionBankRevision", "BankImportReceipt", "BankArchiveReceipt"]
