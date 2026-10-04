from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.content.application.records import (
    CaseDraftResult,
    KnowledgeCardContributionRecord,
    ProblemRecord,
    ReviewRecord,
)
from app.modules.content.domain.digest import case_digest


@dataclass(frozen=True, slots=True)
class CatalogCardRecord:
    code: str
    point_code: str
    prompt: str
    options: tuple[str, ...]
    correct_option: int
    explanation: str
    reference: str
    card_type: str = "single_choice"


class KnowledgeCatalogPort(Protocol):
    """Stable cross-module read contract for the active persisted catalog."""

    def catalog_version(self) -> str: ...

    def tree_view(self) -> tuple[dict[str, object], ...]: ...

    def point_view(self, code: str) -> dict[str, object] | None: ...

    def module_labels(self) -> dict[str, str]: ...

    def study_material_view(self, point_code: str) -> dict[str, object] | None: ...

    def card_for_code(self, code: str) -> CatalogCardRecord | None: ...

    def cards_for_points(self, point_codes: tuple[str, ...]) -> tuple[CatalogCardRecord, ...]: ...

    def contains_points(self, point_codes: tuple[str, ...]) -> bool: ...


class QuestionPublicationPort(Protocol):
    def case_context(self, case_id: int, class_code: str, topic_code: str, teacher_id: int) -> dict[str, object]: ...


def knowledge_card_contribution_view(
    card: KnowledgeCardContributionRecord, *, student_view: bool = False
) -> dict[str, object]:
    return {
        "id": card.id,
        "point_code": card.point_code,
        "class_code": card.class_code,
        "version": card.version,
        "card_type": card.card_type,
        "prompt": card.prompt,
        "options": list(card.options),
        "correct_option": None if student_view else card.correct_option,
        "explanation": "" if student_view else card.explanation,
        "reference": card.reference,
        "status": card.status,
        "reviewer_id": None if student_view else card.reviewer_id,
        "review_comment": "" if student_view else card.review_comment,
        "reviewed_at": None if student_view else card.reviewed_at,
        "created_at": card.created_at,
        "updated_at": card.updated_at,
        "ai_title": card.ai_title,
        "source_type": None if student_view else card.source_type,
        "source_snapshot_id": None if student_view else card.source_snapshot_id,
        "source_position": None if student_view else card.source_position,
        "source_finding_ids": [] if student_view else list(card.source_finding_ids),
        "origin_student_id": None if student_view else card.origin_student_id,
        "origin_student_name": None if student_view else card.origin_student_name,
        "target_student_ids": [] if student_view else list(card.target_student_ids),
    }


def problem_view(
    problem: ProblemRecord, *, public_for_student: bool = False, allowed_actions: tuple[str, ...] = ()
) -> dict[str, object]:
    return {
        "id": problem.id,
        "type": problem.type,
        "title": problem.title,
        "description": problem.description,
        "target": problem.target,
        "target_label": "已分配学习内容" if public_for_student and problem.target != "all" else problem.target_label,
        "target_ids": [] if public_for_student else list(problem.target_ids),
        "status": problem.status,
        "created_at": problem.created_at,
        "published_at": problem.published_at,
        "answer_count": problem.answer_count,
        "content_type": problem.content_type,
        "slug": problem.slug,
        "specialty": problem.specialty,
        "difficulty": problem.difficulty,
        "estimated_minutes": problem.estimated_minutes,
        "version": problem.version,
        "parent_problem_id": problem.parent_problem_id,
        "author_id": None if public_for_student else problem.author_id,
        "allowed_actions": [] if public_for_student else list(allowed_actions),
        "medical_review_status": problem.medical_review_status,
        "capability_tags": [] if public_for_student else list(problem.capability_tags),
        "knowledge_point_codes": list(problem.knowledge_point_codes),
        "case_definition": None,
        "rubric": None,
        "opening": (problem.case_definition or {}).get("opening") if problem.content_type == "guided_case" else None,
    }


def authoring_problem_view(problem: ProblemRecord) -> dict[str, object]:
    value = problem_view(problem)
    value["case_definition"] = problem.case_definition
    value["rubric"] = problem.rubric
    return value


def draft_view(result: CaseDraftResult) -> dict[str, object]:
    return {
        **result.payload,
        "generation_mode": result.generation_mode,
        "safety_notice": result.safety_notice,
    }


def review_view(
    problem: ProblemRecord, author_nickname: str | None, reviews: tuple[ReviewRecord, ...]
) -> dict[str, object]:
    value = authoring_problem_view(problem)
    value.update(
        {
            "current_digest": case_digest(problem),
            "author_nickname": author_nickname,
            "reviews": [
                {
                    "id": item.id,
                    "problem_id": item.problem_id,
                    "reviewer_id": item.reviewer_id,
                    "decision": item.decision,
                    "comment": item.comment,
                    "problem_version": item.problem_version,
                    "case_digest": item.case_digest,
                    "created_at": item.created_at,
                }
                for item in reviews
            ],
        }
    )
    return value


def review_record_view(review: ReviewRecord) -> dict[str, object]:
    return {
        "id": review.id,
        "problem_id": review.problem_id,
        "reviewer_id": review.reviewer_id,
        "decision": review.decision,
        "comment": review.comment,
        "problem_version": review.problem_version,
        "case_digest": review.case_digest,
        "created_at": review.created_at,
    }
