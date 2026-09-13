from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class PblSession(Base):
    __tablename__ = "pbl_sessions"
    __table_args__ = (
        CheckConstraint(
            "session_kind != 'classroom' OR (class_id IS NOT NULL AND teacher_id IS NOT NULL)",
            name="ck_pbl_classroom_scope",
        ),
        Index("ix_pbl_sessions_class_status", "class_id", "status"),
        UniqueConstraint("created_by_student_id", "client_session_id", name="uq_pbl_session_student_client"),
        CheckConstraint("session_kind IN ('classroom', 'student_initiated')", name="ck_pbl_session_kind"),
        CheckConstraint(
            "(session_kind = 'classroom' AND created_by_student_id IS NULL AND client_session_id IS NULL) OR "
            "(session_kind = 'student_initiated' AND created_by_student_id IS NOT NULL "
            "AND client_session_id IS NOT NULL)",
            name="ck_pbl_session_student_origin",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True, index=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    session_kind: Mapped[str] = mapped_column(String(30), default="classroom", server_default="classroom")
    created_by_student_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_pbl_session_created_student"), nullable=True, index=True
    )
    client_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    topic_code: Mapped[str] = mapped_column(String(120))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id", name="fk_pbl_session_case"), nullable=True)
    case_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    case_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    case_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    goal_point_codes: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    phase: Mapped[str] = mapped_column(String(40), default="problem_framing", server_default="problem_framing")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    provider: Mapped[str] = mapped_column(String(40))
    invocation_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PblParticipation(Base):
    __tablename__ = "pbl_participations"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_pbl_participation_student"),
        CheckConstraint("interaction_style IN ('guided', 'direct')", name="ck_pbl_participation_interaction_style"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("pbl_sessions.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    coze_user_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coze_conversation_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    interaction_style: Mapped[str] = mapped_column(String(20), default="guided", server_default="guided")
    style_selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_phase: Mapped[str] = mapped_column(
        String(40), default="problem_framing", server_default="problem_framing", nullable=False
    )
    phase_started_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    phase_status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", nullable=False)
    phase_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PblMessage(Base):
    __tablename__ = "pbl_messages"
    __table_args__ = (
        UniqueConstraint("participation_id", "client_message_id", name="uq_pbl_message_client_id"),
        UniqueConstraint("participation_id", "sequence", name="uq_pbl_message_sequence"),
        Index("ix_pbl_messages_participation_sequence", "participation_id", "sequence"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participation_id: Mapped[int] = mapped_column(ForeignKey("pbl_participations.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    request_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(20), default="pending", server_default="legacy")
    result_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PblDiagnosticSnapshot(Base):
    __tablename__ = "pbl_diagnostic_snapshots"
    __table_args__ = (UniqueConstraint("participation_id", "revision", name="uq_pbl_snapshot_revision"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participation_id: Mapped[int] = mapped_column(ForeignKey("pbl_participations.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    schema_version: Mapped[int] = mapped_column(Integer, default=3, server_default="1")
    phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    phase_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phase_evidence_message_ids: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    phase_evidence_summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    phase_missing_elements: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    safety_notice: Mapped[str] = mapped_column(Text, default="仅供病理学教学。", server_default="")
    safety_status: Mapped[str] = mapped_column(String(30), default="educational", server_default="educational")
    assistant_reply: Mapped[str] = mapped_column(Text)
    follow_up_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_gaps: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    reasoning_issues: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    provider_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PblQuestionSuggestion(Base):
    __tablename__ = "pbl_question_suggestions"
    __table_args__ = (Index("ix_pbl_suggestion_snapshot_status", "snapshot_id", "status"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("pbl_diagnostic_snapshots.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text)
    linked_findings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    version: Mapped[int] = mapped_column(Integer, default=1)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id"), nullable=True, unique=True)


class PblSubmission(Base):
    __tablename__ = "pbl_submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("pbl_sessions.id"), unique=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("pbl_diagnostic_snapshots.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    client_submission_id: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(30), default="student")
    preview_payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PblTeacherFeedback(Base):
    """Immutable teacher communication attached to a visible PBL snapshot or plan."""

    __tablename__ = "pbl_teacher_feedbacks"
    __table_args__ = (
        UniqueConstraint("teacher_id", "client_feedback_id", name="uq_pbl_teacher_feedback_client"),
        CheckConstraint(
            "action_type IN ('feedback_only', 'task_published', 'closed', 'follow_up')",
            name="ck_pbl_teacher_feedback_action",
        ),
        Index("ix_pbl_teacher_feedback_snapshot_created", "snapshot_id", "created_at"),
        Index("ix_pbl_teacher_feedback_student_created", "student_id", "created_at"),
        Index("ix_pbl_teacher_feedback_class_action_created", "class_id", "action_type", "created_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("pbl_diagnostic_snapshots.id"), nullable=False)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("learning_plans.id"), nullable=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    suggestion_id: Mapped[int | None] = mapped_column(ForeignKey("pbl_question_suggestions.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    client_feedback_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
