from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.bootstrap.composition import knowledge_review_application
from app.db import get_db
from app.dependencies import require_student
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
from app.modules.learning.public import knowledge_map_view
from app.shared.actor import Actor
from app.shared.errors import AppError

router = APIRouter(tags=["knowledge-review"])


def _retired_review_flow() -> None:
    raise AppError("RETIRED_FLOW", "独立知识复习已退役，请打开学习计划", 409)


@router.post("/learning/exit-quiz", response_model=ExitQuizRead)
def create_exit_quiz(
    payload: ExitQuizRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    _retired_review_flow()


@router.get("/learning/review-dashboard", response_model=ReviewDashboardRead)
def read_review_dashboard(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, object]:
    return {"due_count": 0, "weak_point_codes": [], "items": []}


@router.get("/learning/knowledge-map", response_model=KnowledgeMapRead)
def read_knowledge_map(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, object]:
    return knowledge_map_view(knowledge_review_application(db).knowledge_map(Actor.from_user(student)))


@router.get("/learning/reviews/due", response_model=list[ReviewCardRead])
def read_due_reviews(
    limit: int = Query(default=15, ge=1, le=15),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return []


@router.post("/learning/reviews/{card_code}/grade", response_model=GradeReviewCardRead)
def grade_review_card(
    card_code: str,
    payload: GradeReviewCardRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _retired_review_flow()


@router.post("/learning/recall-cards/{card_id}/reveal", response_model=RecallRevealRead)
def reveal_recall_card(
    card_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    _retired_review_flow()


@router.post("/learning/recall-cards/{card_id}/rate", response_model=GradeReviewCardRead)
def rate_recall_card(
    card_id: int,
    payload: RateRecallCardRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _retired_review_flow()


@router.get("/learning/review-items", response_model=ReviewDashboardRead)
def list_review_items(student: User = Depends(require_student), db: Session = Depends(get_db)) -> dict[str, object]:
    return {"due_count": 0, "weak_point_codes": [], "items": []}


@router.post("/learning/review-items", response_model=ReviewItemRead, status_code=status.HTTP_201_CREATED)
def capture_review_item(
    payload: CaptureReviewItemRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _retired_review_flow()


@router.post("/learning/review-items/{item_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_review_item(item_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)) -> None:
    _retired_review_flow()
