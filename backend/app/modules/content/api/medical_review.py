from fastapi import APIRouter, Depends
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
        content_application(db).decide_review(
            Actor.from_user(reviewer), problem_id, payload.decision, payload.comment
        )
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
        review_record_view(item)
        for item in content_application(db).review_history(Actor.from_user(user), problem_id)
    ]
