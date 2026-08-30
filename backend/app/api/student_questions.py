from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_student
from app.models import Problem, QuestionThread, User
from app.schemas import StudentQuestionRead
from app.services.access_control import student_class_codes, student_problem_filter

router = APIRouter(prefix="/student/questions", tags=["student-questions"])


@router.get("", response_model=list[StudentQuestionRead])
def list_student_questions(
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[dict]:
    # One scoped feed query regardless of question count. No message bodies are loaded.
    answered = (
        select(QuestionThread.id)
        .where(
            QuestionThread.problem_id == Problem.id,
            QuestionThread.student_id == student.id,
        )
        .exists()
    )
    rows = (
        db.execute(
            select(
                Problem.id,
                Problem.type,
                Problem.title,
                Problem.description,
                func.coalesce(Problem.published_at, Problem.created_at).label("published_at"),
                answered.label("answered"),
            )
            .where(
                student_problem_filter(student, student_class_codes(db, student)),
                Problem.content_type == "question",
            )
            .order_by(Problem.published_at.desc(), Problem.id.desc())
        )
        .mappings()
        .all()
    )
    return [
        {
            "id": row["id"],
            "type": row["type"],
            "title": row["title"],
            "description": row["description"],
            "published_at": row["published_at"],
            "status": "answered" if row["answered"] else "unanswered",
        }
        for row in rows
    ]


@router.get("/{problem_id}", response_model=StudentQuestionRead)
def get_student_question(
    problem_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict:
    problem = db.scalar(
        select(Problem).where(
            Problem.id == problem_id,
            Problem.content_type == "question",
            student_problem_filter(student, student_class_codes(db, student)),
        )
    )
    if problem is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    answered = (
        db.scalar(
            select(QuestionThread.id).where(
                QuestionThread.problem_id == problem.id,
                QuestionThread.student_id == student.id,
            )
        )
        is not None
    )
    return {
        "id": problem.id,
        "type": problem.type,
        "title": problem.title,
        "description": problem.description,
        "published_at": problem.published_at or problem.created_at,
        "status": "answered" if answered else "unanswered",
    }
