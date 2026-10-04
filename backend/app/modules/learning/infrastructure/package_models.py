"""Learning-owned classroom package and final-report persistence facts."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class ClassroomTaskPackage(Base):
    __tablename__ = "classroom_task_packages"
    __table_args__ = (
        UniqueConstraint("student_id", "session_id", name="uq_classroom_package_student_session"),
        UniqueConstraint("completion_snapshot_id", name="uq_classroom_package_snapshot"),
        CheckConstraint("status IN ('draft', 'build_failed', 'published')", name="ck_classroom_package_status"),
        CheckConstraint("record_source IN ('runtime', 'legacy_verified')", name="ck_classroom_package_record_source"),
        CheckConstraint("version >= 1", name="ck_classroom_package_version"),
        CheckConstraint(
            "(status = 'published' AND plan_id IS NOT NULL AND published_at IS NOT NULL "
            "AND published_version IS NOT NULL AND due_at IS NOT NULL) OR "
            "(status != 'published' AND plan_id IS NULL AND published_at IS NULL "
            "AND published_version IS NULL AND due_at IS NULL)",
            name="ck_classroom_package_published_fields",
        ),
        Index("ix_classroom_package_class_session", "class_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("pbl_sessions.id", ondelete="RESTRICT"), nullable=False)
    completion_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("pbl_diagnostic_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    draft_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diagnosis_outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    feedback_draft: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    record_source: Mapped[str] = mapped_column(String(20), default="runtime", server_default="runtime", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClassroomPackageItem(Base):
    __tablename__ = "classroom_package_items"
    __table_args__ = (
        UniqueConstraint("package_id", "stable_key", "cycle_number", name="uq_classroom_package_item_variant"),
        UniqueConstraint("package_id", "position", name="uq_classroom_package_item_position"),
        CheckConstraint("cycle_number IN (1, 2)", name="ck_classroom_package_item_cycle"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_task_packages.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stable_key: Mapped[str] = mapped_column(String(100), nullable=False)
    candidate_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    primary_point_code: Mapped[str] = mapped_column(String(120), nullable=False)
    point_codes: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    dimension_ids: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_code: Mapped[str] = mapped_column(String(160), nullable=False)
    public_definition: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    private_rubric: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    source_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    medical_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    included_in_package: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)


class ClassroomFinalReport(Base):
    __tablename__ = "classroom_final_reports"
    __table_args__ = (
        CheckConstraint("result IN ('improved', 'needs_reinforcement')", name="ck_classroom_report_result"),
        CheckConstraint("record_source IN ('runtime', 'legacy_verified')", name="ck_classroom_report_record_source"),
        Index("ix_classroom_report_class_completed", "class_id", "completed_at"),
        Index("ix_classroom_report_student_completed", "student_id", "completed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_task_packages.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("pbl_sessions.id", ondelete="RESTRICT"), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    record_source: Mapped[str] = mapped_column(String(20), default="runtime", server_default="runtime", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TeachingCommandReceipt(Base):
    __tablename__ = "teaching_command_receipts"
    __table_args__ = (
        UniqueConstraint("teacher_id", "operation", "client_request_id", name="uq_teaching_command_request"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    result_version: Mapped[int] = mapped_column(Integer, nullable=False)
    response_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class T43LegacyPlanMapping(Base):
    __tablename__ = "t43_legacy_plan_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    legacy_plan_id: Mapped[int] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    package_id: Mapped[int] = mapped_column(
        ForeignKey("classroom_task_packages.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    converted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


__all__ = [
    "ClassroomTaskPackage",
    "ClassroomPackageItem",
    "ClassroomFinalReport",
    "TeachingCommandReceipt",
    "T43LegacyPlanMapping",
]
