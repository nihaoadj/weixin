"""Persistence models for the single-round learning route domain."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database import Base


class LearningRoute(Base):
    __tablename__ = "learning_routes"
    __table_args__ = (
        UniqueConstraint("source_participation_id", name="uq_learning_route_participation"),
        UniqueConstraint("public_id", name="uq_learning_route_public_id"),
        CheckConstraint("source_kind IN ('classroom', 'autonomous')", name="ck_learning_route_source_kind"),
        CheckConstraint(
            "generation_state IN ('pending', 'generating', 'published', 'generation_failed')",
            name="ck_learning_route_generation_state",
        ),
        CheckConstraint(
            "(source_kind = 'classroom' AND class_id IS NOT NULL AND teacher_id IS NOT NULL) OR "
            "(source_kind = 'autonomous' AND class_id IS NULL AND teacher_id IS NULL)",
            name="ck_learning_route_source_scope",
        ),
        CheckConstraint("content_version IS NULL OR content_version >= 1", name="ck_learning_route_content_version"),
        Index("ix_learning_route_student_created", "student_id", "created_at"),
        Index("ix_learning_route_class_created", "class_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    source_participation_id: Mapped[int] = mapped_column(
        ForeignKey("pbl_participations.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(ForeignKey("pbl_sessions.id", ondelete="RESTRICT"), nullable=False)
    completion_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("pbl_diagnostic_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="学习计划", server_default="学习计划")
    goal_point_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    diagnosis_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    generation_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    generation_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending", server_default="pending"
    )
    generation_claim_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_claim_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_execution_state: Mapped[str | None] = mapped_column(String(12), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    content_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    route_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LearningRouteStep(Base):
    __tablename__ = "learning_route_steps"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_learning_route_step_public_id"),
        UniqueConstraint("route_id", "position", name="uq_learning_route_step_position"),
        CheckConstraint("position >= 1", name="ck_learning_route_step_position"),
        CheckConstraint("kind IN ('reading', 'case')", name="ck_learning_route_step_kind"),
        CheckConstraint(
            "status IN ('locked', 'available', 'in_progress', 'completed', 'blocked')",
            name="ck_learning_route_step_status",
        ),
        Index("ix_learning_route_steps_route_status", "route_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    route_id: Mapped[int] = mapped_column(ForeignKey("learning_routes.id", ondelete="RESTRICT"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="", server_default="")
    goal_point_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    source_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    public_definition: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    private_definition: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="locked", server_default="locked")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RouteReadingProgress(Base):
    __tablename__ = "route_reading_progress"
    __table_args__ = (
        UniqueConstraint("step_id", "student_id", name="uq_route_reading_step_student"),
        CheckConstraint("accumulated_seconds >= 0", name="ck_route_reading_accumulated_seconds"),
        Index("ix_route_reading_student", "student_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("learning_route_steps.id", ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    active_lease_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accumulated_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_request_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RouteCaseSession(Base):
    __tablename__ = "route_case_sessions"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_route_case_session_public_id"),
        UniqueConstraint("step_id", name="uq_route_case_session_step"),
        CheckConstraint(
            "phase IN ('pathology_recognition', 'mechanism_explanation', 'evidence_judgment', "
            "'summary_reflection', 'completed')",
            name="ck_route_case_session_phase",
        ),
        CheckConstraint("revision >= 0", name="ck_route_case_session_revision"),
        CheckConstraint("phase_started_revision >= 0", name="ck_route_case_session_phase_revision"),
        CheckConstraint("status IN ('in_progress', 'blocked', 'completed')", name="ck_route_case_session_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    step_id: Mapped[int] = mapped_column(ForeignKey("learning_route_steps.id", ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    phase: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pathology_recognition", server_default="pathology_recognition"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    phase_started_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress", server_default="in_progress")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RouteCaseMessage(Base):
    __tablename__ = "route_case_messages"
    __table_args__ = (
        UniqueConstraint("case_session_id", "sequence", name="uq_route_case_message_sequence"),
        UniqueConstraint("case_session_id", "client_message_id", name="uq_route_case_message_client_id"),
        CheckConstraint("sequence >= 1", name="ck_route_case_message_sequence"),
        CheckConstraint("role IN ('student', 'assistant')", name="ck_route_case_message_role"),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed', 'blocked')",
            name="ck_route_case_message_processing_status",
        ),
        CheckConstraint("request_revision >= 1", name="ck_route_case_message_revision"),
        Index("ix_route_case_message_session_revision", "case_session_id", "request_revision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_session_id: Mapped[int] = mapped_column(
        ForeignKey("route_case_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    client_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="completed", server_default="completed"
    )
    processing_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RouteCasePhaseDecision(Base):
    __tablename__ = "route_case_phase_decisions"
    __table_args__ = (
        UniqueConstraint("case_session_id", "revision", name="uq_route_case_decision_revision"),
        UniqueConstraint("message_id", name="uq_route_case_decision_message"),
        CheckConstraint(
            "phase IN ('pathology_recognition', 'mechanism_explanation', 'evidence_judgment', 'summary_reflection')",
            name="ck_route_case_decision_phase",
        ),
        CheckConstraint("decision IN ('stay', 'advance', 'complete')", name="ck_route_case_decision_value"),
        CheckConstraint("safety_status IN ('educational', 'unsafe')", name="ck_route_case_decision_safety"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_session_id: Mapped[int] = mapped_column(
        ForeignKey("route_case_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(ForeignKey("route_case_messages.id", ondelete="RESTRICT"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(12), nullable=False)
    evidence_message_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    satisfied_goal_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    missing_goal_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    safety_status: Mapped[str] = mapped_column(String(12), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RouteFinalTest(Base):
    __tablename__ = "route_final_tests"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_route_final_test_public_id"),
        UniqueConstraint("route_id", name="uq_route_final_test_route"),
        CheckConstraint(
            "generation_state IN ('pending', 'generating', 'ready', 'generation_failed')",
            name="ck_route_final_test_generation_state",
        ),
        CheckConstraint(
            "review_state IN ('pending_review', 'needs_changes', 'released')",
            name="ck_route_final_test_review_state",
        ),
        CheckConstraint("review_kind IN ('teacher', 'ai_direct')", name="ck_route_final_test_review_kind"),
        CheckConstraint("version >= 1", name="ck_route_final_test_version"),
        CheckConstraint(
            "format_version IN ('single_choice_v1', 'mixed_v2')", name="ck_route_final_test_format_version"
        ),
        CheckConstraint(
            "released_version IS NULL OR released_version >= 1", name="ck_route_final_test_released_version"
        ),
        CheckConstraint(
            "(review_kind = 'ai_direct' AND reviewer_id IS NULL AND review_state = 'released') OR "
            "(review_kind = 'teacher' AND (review_state != 'released' OR reviewer_id IS NOT NULL))",
            name="ck_route_final_test_reviewer_scope",
        ),
        Index("ix_route_final_test_generation_state", "generation_state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="最终测试", server_default="最终测试")
    route_id: Mapped[int] = mapped_column(ForeignKey("learning_routes.id", ondelete="RESTRICT"), nullable=False)
    generation_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending", server_default="pending"
    )
    generation_claim_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_claim_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_execution_state: Mapped[str | None] = mapped_column(String(12), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    review_state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending_review", server_default="pending_review"
    )
    review_kind: Mapped[str] = mapped_column(String(12), nullable=False, default="teacher", server_default="teacher")
    feedback_draft: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    format_version: Mapped[str] = mapped_column(
        String(24), nullable=False, default="single_choice_v1", server_default="single_choice_v1"
    )
    draft_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    released_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    released_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RouteTestQuestion(Base):
    __tablename__ = "route_test_questions"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_route_test_question_public_id"),
        UniqueConstraint("test_id", "stable_key", name="uq_route_test_question_stable_key"),
        UniqueConstraint("test_id", "position", name="uq_route_test_question_position"),
        CheckConstraint("position >= 1", name="ck_route_test_question_position"),
        CheckConstraint(
            "(question_type = 'single_choice' AND correct_option BETWEEN 0 AND 3) OR "
            "(question_type IN ('multiple_choice', 'short_answer') AND correct_option IS NULL)",
            name="ck_route_test_question_correct_option",
        ),
        Index("ix_route_test_question_test_point", "test_id", "primary_point_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    test_id: Mapped[int] = mapped_column(ForeignKey("route_final_tests.id", ondelete="RESTRICT"), nullable=False)
    stable_key: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_point_code: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="single_choice", server_default="single_choice"
    )
    options: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    correct_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    private_grading: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")


class RouteTestAttempt(Base):
    __tablename__ = "route_test_attempts"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_route_test_attempt_public_id"),
        UniqueConstraint("test_id", "student_id", name="uq_route_test_attempt_student"),
        CheckConstraint("draft_version >= 1", name="ck_route_test_attempt_draft_version"),
        CheckConstraint("status IN ('in_progress', 'grading', 'submitted')", name="ck_route_test_attempt_status"),
        CheckConstraint("correct_count IS NULL OR correct_count >= 0", name="ck_route_test_attempt_correct_count"),
        CheckConstraint("question_count IS NULL OR question_count > 0", name="ck_route_test_attempt_question_count"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="ck_route_test_attempt_score"),
        CheckConstraint(
            "(status = 'submitted' AND submission_id IS NOT NULL AND submission_digest IS NOT NULL "
            "AND correct_count IS NOT NULL AND question_count IS NOT NULL AND score IS NOT NULL "
            "AND submitted_at IS NOT NULL) OR "
            "(status = 'grading' AND submission_id IS NOT NULL AND submission_digest IS NOT NULL "
            "AND correct_count IS NOT NULL AND question_count IS NOT NULL AND score IS NULL "
            "AND submitted_at IS NOT NULL) OR status = 'in_progress'",
            name="ck_route_test_attempt_submission_fields",
        ),
        Index("ix_route_test_attempt_student", "student_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    test_id: Mapped[int] = mapped_column(ForeignKey("route_final_tests.id", ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    test_version: Mapped[int] = mapped_column(Integer, nullable=False)
    test_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    answers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress", server_default="in_progress")
    submission_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    submission_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    grading_claim_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grading_claim_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grading_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RouteLearningResult(Base):
    __tablename__ = "route_learning_results"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_route_learning_result_public_id"),
        UniqueConstraint("route_id", name="uq_route_learning_result_route"),
        UniqueConstraint("attempt_id", name="uq_route_learning_result_attempt"),
        CheckConstraint("source_kind IN ('classroom', 'autonomous')", name="ck_route_learning_result_source_kind"),
        CheckConstraint(
            "(source_kind = 'classroom' AND class_id IS NOT NULL AND teacher_id IS NOT NULL) OR "
            "(source_kind = 'autonomous' AND class_id IS NULL AND teacher_id IS NULL)",
            name="ck_route_learning_result_source_scope",
        ),
        Index("ix_route_learning_result_class_completed", "class_id", "completed_at"),
        Index("ix_route_learning_result_student_completed", "student_id", "completed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    route_id: Mapped[int] = mapped_column(ForeignKey("learning_routes.id", ondelete="RESTRICT"), nullable=False)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("route_test_attempts.id", ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    result_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RouteTestTutorSession(Base):
    __tablename__ = "route_test_tutor_sessions"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_route_test_tutor_session_public_id"),
        UniqueConstraint("result_id", name="uq_route_test_tutor_session_result"),
        CheckConstraint("revision >= 0", name="ck_route_test_tutor_session_revision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    result_id: Mapped[int] = mapped_column(ForeignKey("route_learning_results.id", ondelete="RESTRICT"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    claim_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    claim_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RouteTestTutorMessage(Base):
    __tablename__ = "route_test_tutor_messages"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_route_test_tutor_message_public_id"),
        UniqueConstraint("session_id", "sequence", name="uq_route_test_tutor_message_sequence"),
        UniqueConstraint("session_id", "turn_id", "role", name="uq_route_test_tutor_message_turn_role"),
        CheckConstraint("role IN ('student', 'assistant')", name="ck_route_test_tutor_message_role"),
        CheckConstraint("sequence >= 1", name="ck_route_test_tutor_message_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("route_test_tutor_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("route_test_questions.id", ondelete="RESTRICT"), nullable=False)
    turn_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RouteTestReviewEvent(Base):
    __tablename__ = "route_test_review_events"
    __table_args__ = (
        UniqueConstraint("test_id", "version", "action", name="uq_route_test_review_version_action"),
        CheckConstraint("action IN ('requested_changes', 'released')", name="ck_route_test_review_action"),
        CheckConstraint("version >= 1", name="ck_route_test_review_version"),
        CheckConstraint("feedback IS NULL OR length(feedback) <= 1000", name="ck_route_test_review_feedback_length"),
        Index("ix_route_test_review_teacher_created", "teacher_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("route_final_tests.id", ondelete="RESTRICT"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RouteCommandReceipt(Base):
    __tablename__ = "route_command_receipts"
    __table_args__ = (
        UniqueConstraint("actor_id", "operation", "client_request_id", name="uq_route_command_request"),
        CheckConstraint("result_version >= 1", name="ck_route_command_receipt_result_version"),
        Index("ix_route_command_receipt_resource", "resource_public_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    result_version: Mapped[int] = mapped_column(Integer, nullable=False)
    response_locator: Mapped[str | None] = mapped_column(String(200), nullable=True)
    response_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


__all__ = [
    "LearningRoute",
    "LearningRouteStep",
    "RouteReadingProgress",
    "RouteCaseSession",
    "RouteCaseMessage",
    "RouteCasePhaseDecision",
    "RouteFinalTest",
    "RouteTestQuestion",
    "RouteTestAttempt",
    "RouteLearningResult",
    "RouteTestReviewEvent",
    "RouteCommandReceipt",
]
