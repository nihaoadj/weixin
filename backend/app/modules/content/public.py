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
from app.modules.content.domain.knowledge_catalog import (
    KnowledgeCard,
    card_for_code,
    cards_for_points,
    point_view,
    tree_view,
)


@dataclass(frozen=True, slots=True)
class PublishQuestionCommand:
    teacher_id: int
    source_id: int
    title: str
    prompt: str
    class_code: str
    target_external_ids: tuple[str, ...] = ()
    point_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PublishedQuestionRecord:
    problem_id: int


class QuestionPublicationPort(Protocol):
    def case_context(self, case_id: int, class_code: str, topic_code: str) -> dict[str, object]: ...
    def task_resources(
        self, case_id: int | None, point_codes: tuple[str, ...], dimensions: tuple[str, ...]
    ) -> tuple[dict[str, object], ...]: ...

    def adopt_open_question(self, command: PublishQuestionCommand) -> PublishedQuestionRecord: ...


def knowledge_point_view(code: str) -> dict[str, object] | None:
    """Stable read-only catalog lookup for other module contracts."""

    return point_view(code)


def knowledge_tree_view() -> list[dict[str, object]]:
    """Return the versioned catalog through the stable content contract."""

    return tree_view()


def knowledge_card_for_code(code: str) -> KnowledgeCard | None:
    return card_for_code(code)


def knowledge_cards_for_topics(topic_codes: tuple[str, ...]) -> tuple[KnowledgeCard, ...]:
    return cards_for_points(topic_codes)


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
    }


def problem_view(problem: ProblemRecord, *, public_for_student: bool = False) -> dict[str, object]:
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
        "medical_review_status": "approved"
        if public_for_student and problem.content_type == "guided_case"
        else problem.medical_review_status,
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
