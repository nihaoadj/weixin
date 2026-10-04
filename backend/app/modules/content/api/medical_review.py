from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_permission, require_teacher
from app.modules.classroom.api.schemas import MedicalReviewRead, MedicalReviewViewRead, ReviewSubmit
from app.modules.content.api.schemas import ProblemRead
from app.modules.content.public import problem_view, review_record_view
from app.modules.content.public import review_view as review_view_mapper
from app.modules.content.wiring import content_application
from app.modules.identity.infrastructure.models import User
from app.shared.actor import Actor

router = APIRouter(prefix="/problems", tags=["medical-review"])
question_router = APIRouter(prefix="/medical-review/classroom-questions", tags=["medical-review"])


class ClassroomQuestionReviewResponse(BaseModel):
    id: int
    package_item_id: int
    content_digest: str
    content_snapshot: dict
    status: Literal["pending", "approved", "rejected"]
    submitted_by: int
    submitted_at: datetime
    reviewer_id: int | None
    review_comment: str
    reviewed_at: datetime | None


class ClassroomQuestionDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str = Field(default="", max_length=1000)


@question_router.get("", response_model=list[ClassroomQuestionReviewResponse])
def classroom_question_queue(
    status: Literal["pending", "approved", "rejected"] = "pending",
    _reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
):
    return []


@question_router.get("/{review_id}", response_model=ClassroomQuestionReviewResponse)
def classroom_question_review(
    review_id: int,
    _reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
):
    from app.shared.errors import AppError

    raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)


@question_router.post("/{review_id}/decision", response_model=ClassroomQuestionReviewResponse)
def decide_classroom_question(
    review_id: int,
    payload: ClassroomQuestionDecision,
    reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
):
    from app.modules.learning.public import retired_learning_flow

    retired_learning_flow()


@router.get("/review-queue", response_model=list[ProblemRead])
def review_queue(
    status: str = "pending",
    reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    actor = Actor.from_user(reviewer)
    return [problem_view(item) for item in content_application(db).review_queue(actor, status)]


@router.post("/{problem_id}/medical-review/submit", response_model=ProblemRead)
def submit_for_review(
    problem_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return problem_view(content_application(db).submit_review(Actor.from_user(teacher), problem_id))


@router.post("/{problem_id}/medical-review", response_model=ProblemRead)
def decide_review(
    problem_id: int,
    payload: ReviewSubmit,
    reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return problem_view(
        content_application(db).decide_review(Actor.from_user(reviewer), problem_id, payload.decision, payload.comment)
    )


@router.get("/{problem_id}/medical-review-view", response_model=MedicalReviewViewRead)
def review_view(
    problem_id: int,
    reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    problem, author_nickname, reviews = content_application(db).review_view(Actor.from_user(reviewer), problem_id)
    return review_view_mapper(problem, author_nickname, reviews)


@router.get("/{problem_id}/medical-reviews", response_model=list[MedicalReviewRead])
def review_history(
    problem_id: int,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return [
        review_record_view(item) for item in content_application(db).review_history(Actor.from_user(user), problem_id)
    ]
