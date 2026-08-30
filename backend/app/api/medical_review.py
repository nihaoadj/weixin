import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.problems import serialize_problem
from app.db import get_db
from app.dependencies import require_permission, require_teacher
from app.models import MedicalReview, Problem, User
from app.schemas.case_training import CaseDefinition, CaseRubric
from app.schemas.classroom import MedicalReviewRead, MedicalReviewViewRead, ReviewSubmit
from app.schemas.problem import ProblemRead

router = APIRouter(prefix="/problems", tags=["medical-review"])


def case_digest(problem: Problem) -> str:
    target_ids = [item for item in (problem.target_ids or "").split(",") if item]
    return hashlib.sha256(
        json.dumps(
            {
                "title": problem.title,
                "description": problem.description,
                "specialty": problem.specialty,
                "difficulty": problem.difficulty,
                "estimated_minutes": problem.estimated_minutes,
                "target": problem.target,
                "target_ids": target_ids,
                "case_definition": problem.case_definition,
                "rubric": problem.rubric,
                "capability_tags": problem.capability_tags or [],
                "schema_version": (problem.case_definition or {}).get("schema_version"),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _case(problem_id: int, db: Session) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None or problem.content_type != "guided_case":
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return problem


def _review_view(problem: Problem, db: Session) -> dict:
    author = db.get(User, problem.author_id) if problem.author_id else None
    reviews = list(
        db.scalars(select(MedicalReview).where(MedicalReview.problem_id == problem.id).order_by(MedicalReview.id)).all()
    )
    data = serialize_problem(problem)
    data.update(
        {
            "case_definition": CaseDefinition.model_validate(problem.case_definition),
            "rubric": CaseRubric.model_validate(problem.rubric),
            "current_digest": case_digest(problem),
            "author_nickname": author.nickname if author else None,
            "reviews": reviews,
        }
    )
    return data


@router.get("/review-queue", response_model=list[ProblemRead])
def review_queue(
    status: str = "pending",
    _reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> list[dict]:
    problems = db.scalars(
        select(Problem)
        .where(Problem.content_type == "guided_case", Problem.medical_review_status == status)
        .order_by(Problem.created_at)
    ).all()
    return [serialize_problem(problem) for problem in problems]


@router.post("/{problem_id}/medical-review/submit", response_model=ProblemRead)
def submit_for_review(
    problem_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    problem = _case(problem_id, db)
    if problem.author_id != teacher.id:
        raise HTTPException(status_code=403, detail="ROLE_REQUIRED")
    if problem.medical_review_status == "approved":
        raise HTTPException(status_code=409, detail="STATE_CONFLICT")
    if not problem.case_definition or not problem.rubric:
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR")
    problem.medical_review_status = "pending"
    db.commit()
    db.refresh(problem)
    return serialize_problem(problem)


@router.post("/{problem_id}/medical-review", response_model=ProblemRead)
def decide_review(
    problem_id: int,
    payload: ReviewSubmit,
    reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> dict:
    problem = _case(problem_id, db)
    if problem.author_id == reviewer.id:
        raise HTTPException(status_code=409, detail="Authors cannot review their own case")
    if problem.medical_review_status != "pending":
        raise HTTPException(status_code=409, detail="STATE_CONFLICT")
    review = MedicalReview(
        problem_id=problem.id,
        reviewer_id=reviewer.id,
        decision=payload.decision,
        comment=payload.comment,
        problem_version=problem.version,
        case_digest=case_digest(problem),
    )
    db.add(review)
    problem.medical_review_status = "approved" if payload.decision == "approved" else "rejected"
    db.commit()
    db.refresh(problem)
    return serialize_problem(problem)


@router.get("/{problem_id}/medical-review-view", response_model=MedicalReviewViewRead)
def review_view(
    problem_id: int,
    _reviewer: User = Depends(require_permission("medical_review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review_view(_case(problem_id, db), db)


@router.get("/{problem_id}/medical-reviews", response_model=list[MedicalReviewRead])
def review_history(
    problem_id: int,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> list[MedicalReview]:
    problem = _case(problem_id, db)
    if problem.author_id != user.id and "medical_review" not in (user.permissions or []):
        raise HTTPException(status_code=403, detail="ROLE_REQUIRED")
    return list(
        db.scalars(select(MedicalReview).where(MedicalReview.problem_id == problem_id).order_by(MedicalReview.id)).all()
    )
