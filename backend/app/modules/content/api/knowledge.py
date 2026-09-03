from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user, require_permission, require_teacher
from app.modules.content.api.schemas import (
    KnowledgeCardContributionRead,
    KnowledgeCardContributionWrite,
    KnowledgeCardReviewDecision,
)
from app.modules.content.application.records import KnowledgeCardContributionCommand
from app.modules.content.domain.knowledge_catalog import point_view, tree_view
from app.modules.content.public import knowledge_card_contribution_view
from app.modules.content.wiring import content_application
from app.modules.identity.infrastructure.models import User
from app.shared.actor import Actor
from app.shared.errors import AppError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/tree")
def knowledge_tree(_user: User = Depends(get_current_user)) -> dict[str, object]:
    return {"catalog_version": "internal-medicine-v1", "items": tree_view()}


@router.get("/points/{code}")
def knowledge_point(code: str, _user: User = Depends(get_current_user)) -> dict[str, object]:
    point = point_view(code)
    if point is None:
        raise AppError("RESOURCE_NOT_FOUND", "知识点不存在", 404)
    return point


def _card_command(payload: KnowledgeCardContributionWrite) -> KnowledgeCardContributionCommand:
    return KnowledgeCardContributionCommand(
        point_code=payload.point_code,
        class_code=payload.class_code,
        card_type=payload.card_type,
        prompt=payload.prompt,
        options=tuple(payload.options),
        correct_option=payload.correct_option,
        explanation=payload.explanation,
        reference=payload.reference,
    )


@router.get("/cards", response_model=list[KnowledgeCardContributionRead])
def list_knowledge_cards(
    point_code: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    actor = Actor.from_user(user)
    return [
        knowledge_card_contribution_view(card, student_view=actor.role == "student")
        for card in content_application(db).list_knowledge_cards(actor, point_code)
    ]


@router.post("/teacher/cards", response_model=KnowledgeCardContributionRead)
def create_knowledge_card(
    payload: KnowledgeCardContributionWrite,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return knowledge_card_contribution_view(
        content_application(db).create_knowledge_card(Actor.from_user(teacher), _card_command(payload))
    )


@router.get("/review-queue", response_model=list[KnowledgeCardContributionRead])
def knowledge_card_review_queue(
    reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return [
        knowledge_card_contribution_view(card)
        for card in content_application(db).knowledge_card_review_queue(Actor.from_user(reviewer))
    ]


@router.put("/teacher/cards/{card_id}", response_model=KnowledgeCardContributionRead)
def update_knowledge_card(
    card_id: int,
    payload: KnowledgeCardContributionWrite,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return knowledge_card_contribution_view(
        content_application(db).update_knowledge_card(Actor.from_user(teacher), card_id, _card_command(payload))
    )


@router.post("/teacher/cards/{card_id}/submit", response_model=KnowledgeCardContributionRead)
def submit_knowledge_card(
    card_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return knowledge_card_contribution_view(
        content_application(db).submit_knowledge_card(Actor.from_user(teacher), card_id)
    )


@router.post("/teacher/cards/{card_id}/review", response_model=KnowledgeCardContributionRead)
def decide_knowledge_card(
    card_id: int,
    payload: KnowledgeCardReviewDecision,
    reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return knowledge_card_contribution_view(
        content_application(db).decide_knowledge_card(
            Actor.from_user(reviewer), card_id, payload.decision, payload.comment
        )
    )


@router.post("/teacher/cards/{card_id}/disable", response_model=KnowledgeCardContributionRead)
def disable_knowledge_card(
    card_id: int,
    reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return knowledge_card_contribution_view(
        content_application(db).disable_knowledge_card(Actor.from_user(reviewer), card_id)
    )
