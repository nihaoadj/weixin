from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
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

    @property
    def knowledge_point_codes(self) -> tuple[str, ...]:
        return tuple(link.point_code for link in self.knowledge_links)


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
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_snapshot_id",
            "source_position",
            name="uq_knowledge_card_pbl_source",
        ),
        Index("ix_knowledge_card_source_status", "source_type", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_card_code: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True)
    point_code: Mapped[str] = mapped_column(String(120), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    class_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    ai_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_finding_ids: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    origin_student_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    origin_student_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_student_ids: Mapped[list[int]] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
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


class KnowledgeCatalog(Base):
    """Versioned, persisted knowledge catalog; runtime code must not synthesize it."""

    __tablename__ = "knowledge_catalogs"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_knowledge_catalog_status"),
        CheckConstraint(
            "evidence_status IN ('source_supported', 'insufficient')",
            name="ck_knowledge_catalog_evidence_status",
        ),
        CheckConstraint(
            "medical_review_status IN ('pending_expert_review', 'expert_reviewed', 'rejected')",
            name="ck_knowledge_catalog_medical_review_status",
        ),
        Index(
            "uq_knowledge_catalog_single_active",
            "status",
            unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), index=True)
    reference_note: Mapped[str] = mapped_column(String(500))
    evidence_status: Mapped[str] = mapped_column(String(30))
    medical_review_status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeModule(Base):
    __tablename__ = "knowledge_modules"
    __table_args__ = (
        UniqueConstraint("catalog_id", "code", name="uq_knowledge_module_catalog_code"),
        UniqueConstraint("catalog_id", "position", name="uq_knowledge_module_catalog_position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_id: Mapped[int] = mapped_column(ForeignKey("knowledge_catalogs.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(120), index=True)
    label: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    __table_args__ = (
        UniqueConstraint("catalog_id", "code", name="uq_knowledge_point_catalog_code"),
        UniqueConstraint("module_id", "position", name="uq_knowledge_point_module_position"),
        CheckConstraint(
            "evidence_status IN ('source_supported', 'insufficient')",
            name="ck_knowledge_point_evidence_status",
        ),
        CheckConstraint(
            "medical_review_status IN ('pending_expert_review', 'expert_reviewed', 'rejected')",
            name="ck_knowledge_point_medical_review_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_id: Mapped[int] = mapped_column(ForeignKey("knowledge_catalogs.id", ondelete="CASCADE"), index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("knowledge_modules.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(160))
    objective: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    case_slug: Mapped[str] = mapped_column(String(160))
    position: Mapped[int] = mapped_column(Integer)
    evidence_status: Mapped[str] = mapped_column(String(30))
    medical_review_status: Mapped[str] = mapped_column(String(30))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeStudyMaterial(Base):
    __tablename__ = "knowledge_study_materials"
    __table_args__ = (
        UniqueConstraint("catalog_id", "point_id", name="uq_knowledge_material_catalog_point"),
        CheckConstraint(
            "evidence_status IN ('source_supported', 'insufficient')",
            name="ck_knowledge_material_evidence_status",
        ),
        CheckConstraint(
            "medical_review_status IN ('pending_expert_review', 'expert_reviewed', 'rejected')",
            name="ck_knowledge_material_medical_review_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_id: Mapped[int] = mapped_column(ForeignKey("knowledge_catalogs.id", ondelete="CASCADE"), index=True)
    point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id", ondelete="CASCADE"), unique=True)
    version: Mapped[str] = mapped_column(String(80))
    learning_objectives: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scenario: Mapped[str] = mapped_column(Text)
    background: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    example: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    remediation: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    reference_note: Mapped[str] = mapped_column(String(500))
    evidence_status: Mapped[str] = mapped_column(String(30))
    medical_review_status: Mapped[str] = mapped_column(String(30))


class KnowledgeDependency(Base):
    __tablename__ = "knowledge_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "catalog_id", "prerequisite_point_id", "dependent_point_id", name="uq_knowledge_dependency_edge"
        ),
        CheckConstraint("prerequisite_point_id <> dependent_point_id", name="ck_knowledge_dependency_no_self"),
        CheckConstraint(
            "relation_kind IN ('response_continuum', 'mechanistic_basis', 'structural_component', "
            "'specialized_pattern', 'repair_phase_basis', 'assessment_framework', 'common_source', "
            "'occlusive_mechanism', 'outcome_definition', 'classification_basis', 'grading_basis', "
            "'staging_basis')",
            name="ck_knowledge_dependency_relation_kind",
        ),
        CheckConstraint("confidence IN ('high', 'moderate')", name="ck_knowledge_dependency_confidence"),
        CheckConstraint(
            "evidence_status IN ('source_supported', 'insufficient')",
            name="ck_knowledge_dependency_evidence_status",
        ),
        CheckConstraint(
            "medical_review_status IN ('pending_expert_review', 'expert_reviewed', 'rejected')",
            name="ck_knowledge_dependency_medical_review_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_id: Mapped[int] = mapped_column(ForeignKey("knowledge_catalogs.id", ondelete="CASCADE"), index=True)
    prerequisite_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), index=True
    )
    dependent_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id", ondelete="CASCADE"), index=True)
    relation_kind: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)
    limitation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20))
    evidence_status: Mapped[str] = mapped_column(String(30))
    medical_review_status: Mapped[str] = mapped_column(String(30))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    position: Mapped[int] = mapped_column(Integer)


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('government', 'peer_reviewed', 'academic_reference')",
            name="ck_knowledge_source_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    publisher: Mapped[str] = mapped_column(String(160))
    url: Mapped[str] = mapped_column(String(1000))
    source_type: Mapped[str] = mapped_column(String(40))
    accessed_on: Mapped[str] = mapped_column(String(10))


class KnowledgePointSource(Base):
    __tablename__ = "knowledge_point_sources"
    __table_args__ = (UniqueConstraint("point_id", "source_id", name="uq_knowledge_point_source"),)

    point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), primary_key=True)


class KnowledgeDependencySource(Base):
    __tablename__ = "knowledge_dependency_sources"
    __table_args__ = (UniqueConstraint("dependency_id", "source_id", name="uq_knowledge_dependency_source"),)

    dependency_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_dependencies.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), primary_key=True)


__all__ = [
    "KnowledgeCardContribution",
    "KnowledgeCatalog",
    "KnowledgeDependency",
    "KnowledgeDependencySource",
    "KnowledgeModule",
    "KnowledgePoint",
    "KnowledgePointSource",
    "KnowledgeSource",
    "KnowledgeStudyMaterial",
    "Problem",
    "ProblemKnowledgeLink",
    "ProblemOrigin",
]
