from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.bootstrap.composition import knowledge_review_application
from app.core.config import get_settings
from app.db import get_db
from app.dependencies import require_student
from app.modules.content.wiring import content_application
from app.modules.identity.infrastructure.models import User
from app.modules.learning.api.schemas import (
    CaptureReviewItemRequest,
    ExitQuizRead,
    ExitQuizRequest,
    GradeReviewCardRead,
    GradeReviewCardRequest,
    KnowledgeMapRead,
    RateRecallCardRequest,
    RecallRevealRead,
    ReviewCardRead,
    ReviewDashboardRead,
    ReviewItemRead,
)
from app.modules.learning.application.review_records import SupplementalChoiceCard
from app.modules.learning.public import (
    knowledge_map_view,
    review_card_view,
    review_dashboard_view,
    review_item_view,
    review_result_view,
)
from app.shared.actor import Actor
from app.shared.errors import AppError

router = APIRouter(tags=["knowledge-review"])


def _visible_choice_cards(student: User, db: Session) -> tuple[SupplementalChoiceCard, ...]:
    return tuple(
        SupplementalChoiceCard(
            card_code=f"teacher-choice:{card.id}",
            point_code=card.point_code,
            prompt=card.prompt,
            options=card.options,
            correct_option=card.correct_option,
            explanation=card.explanation,
        )
        for card in content_application(db).list_knowledge_cards(Actor.from_user(student), None)
        if card.card_type == "single_choice" and card.correct_option is not None
    )


def _visible_choice_card(card_code: str, student: User, db: Session) -> SupplementalChoiceCard | None:
    return next((card for card in _visible_choice_cards(student, db) if card.card_code == card_code), None)


@router.post("/learning/exit-quiz", response_model=ExitQuizRead)
def create_exit_quiz(
    payload: ExitQuizRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    if not get_settings().t08_exit_quiz_enabled:
        raise AppError("FEATURE_DISABLED", "结束小测当前未开放", 409)
    cards = knowledge_review_application(db).exit_quiz(
        Actor.from_user(student), tuple(dict.fromkeys(payload.topic_codes)), _visible_choice_cards(student, db)
    )
    return {"cards": [review_card_view(card) for card in cards]}


@router.get("/learning/review-dashboard", response_model=ReviewDashboardRead)
def read_review_dashboard(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, object]:
    return review_dashboard_view(knowledge_review_application(db).dashboard(Actor.from_user(student)))


@router.get("/learning/knowledge-map", response_model=KnowledgeMapRead)
def read_knowledge_map(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, object]:
    return knowledge_map_view(knowledge_review_application(db).knowledge_map(Actor.from_user(student)))


@router.get("/learning/reviews/due", response_model=list[ReviewCardRead])
def read_due_reviews(
    limit: int = Query(default=15, ge=1, le=15),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    cards = knowledge_review_application(db).due(Actor.from_user(student), limit, _visible_choice_cards(student, db))
    return [review_card_view(card) for card in cards]


@router.post("/learning/reviews/{card_code}/grade", response_model=GradeReviewCardRead)
def grade_review_card(
    card_code: str,
    payload: GradeReviewCardRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if not get_settings().t08_review_capture_enabled:
        raise AppError("FEATURE_DISABLED", "复习记录当前未开放", 409)
    supplemental = _visible_choice_card(card_code, student, db)
    result = (
        knowledge_review_application(db).grade_supplemental(
            Actor.from_user(student), supplemental, payload.selected_option, payload.confidence
        )
        if supplemental is not None
        else knowledge_review_application(db).grade(
            Actor.from_user(student), card_code, payload.selected_option, payload.confidence
        )
    )
    return review_result_view(result)


def _visible_recall_card(card_id: int, student: User, db: Session):
    card = next(
        (
            item
            for item in content_application(db).list_knowledge_cards(Actor.from_user(student), None)
            if item.id == card_id and item.card_type == "recall"
        ),
        None,
    )
    if card is None:
        raise AppError("RESOURCE_NOT_FOUND", "回忆卡不存在或当前不可见", 404)
    return card


@router.post("/learning/recall-cards/{card_id}/reveal", response_model=RecallRevealRead)
def reveal_recall_card(
    card_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    card = _visible_recall_card(card_id, student, db)
    return {
        "card_code": f"teacher-recall:{card.id}",
        "point_code": card.point_code,
        "prompt": card.prompt,
        "explanation": card.explanation,
    }


@router.post("/learning/recall-cards/{card_id}/rate", response_model=GradeReviewCardRead)
def rate_recall_card(
    card_id: int,
    payload: RateRecallCardRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if not get_settings().t08_review_capture_enabled:
        raise AppError("FEATURE_DISABLED", "复习记录当前未开放", 409)
    card = _visible_recall_card(card_id, student, db)
    return review_result_view(
        knowledge_review_application(db).rate_recall(
            Actor.from_user(student), f"teacher-recall:{card.id}", card.point_code, payload.rating
        )
    )


@router.get("/learning/review-items", response_model=ReviewDashboardRead)
def list_review_items(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, object]:
    return review_dashboard_view(knowledge_review_application(db).dashboard(Actor.from_user(student)))


@router.post("/learning/review-items", response_model=ReviewItemRead, status_code=status.HTTP_201_CREATED)
def capture_review_item(
    payload: CaptureReviewItemRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if not get_settings().t08_review_capture_enabled:
        raise AppError("FEATURE_DISABLED", "复习记录当前未开放", 409)
    item = knowledge_review_application(db).capture(
        Actor.from_user(student), payload.point_code, payload.source_type, payload.source_id, payload.note
    )
    return review_item_view(item)


@router.post("/learning/review-items/{item_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_review_item(item_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> None:
    knowledge_review_application(db).dismiss(Actor.from_user(student), item_id)
