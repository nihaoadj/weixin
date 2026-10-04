from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_student
from app.modules.identity.infrastructure.models import User
from app.modules.qa.api.question_schemas import StudentQuestionRead
from app.modules.qa.public import student_question_view
from app.modules.qa.wiring import questions_application
from app.shared.actor import Actor

router = APIRouter(prefix="/student/questions", tags=["student-questions"])


@router.get("", response_model=list[StudentQuestionRead])
def list_student_questions(
    student: User = Depends(require_student), db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    return [student_question_view(item) for item in questions_application().list(Actor.from_user(student))]


@router.get("/{problem_id}", response_model=StudentQuestionRead)
def get_student_question(
    problem_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    return student_question_view(questions_application().get(Actor.from_user(student), problem_id))
