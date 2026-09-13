from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bootstrap.composition import study_application
from app.db import get_db
from app.dependencies import require_student
from app.modules.identity.infrastructure.models import User

router = APIRouter(tags=["study-paths"])


class StudyStart(BaseModel):
    client_id: str = Field(min_length=1, max_length=100)
    interaction_style: Literal["guided", "direct"] = "guided"
    new_round: bool = False


class PracticeStart(BaseModel):
    client_id: str = Field(min_length=1, max_length=100)
    cycle: Literal[1, 2] = 1


class PracticeAnswer(BaseModel):
    client_id: str = Field(min_length=1, max_length=100)
    question_index: int = Field(ge=0)
    selected_option: int = Field(ge=0)


class MaterialSection(BaseModel):
    title: str
    text: str


class StudyMaterialRead(BaseModel):
    version: str
    point_code: str
    title: str
    objective: str
    scenario: str
    background: list[MaterialSection]
    example: MaterialSection
    remediation: list[MaterialSection]
    reference: str
    review_status: Literal["unreviewed"]


class StudyPathRead(BaseModel):
    id: int
    point_code: str
    session_id: int
    material_version: str


class StudyRead(BaseModel):
    material: StudyMaterialRead
    path: StudyPathRead | None
    phase: str
    practice_unlocked: bool
    review_unlocked: bool
    legacy_access: bool
    summary: str
    lock_reason: str
    history: list[StudyPathRead]


class PracticeQuestionRead(BaseModel):
    index: int
    point_code: str
    prompt: str
    options: list[str]


class PracticeGroupRead(BaseModel):
    id: int
    path_id: int
    cycle: Literal[1, 2]
    status: Literal["generating", "ready", "failed"]
    failure: str | None
    questions: list[PracticeQuestionRead]
    attempts: list[dict]
    due_indexes: list[int]
    can_retest: bool
    exhausted: bool


class PracticeFeedback(BaseModel):
    id: int
    question_index: int
    selected_option: int
    correct: bool
    explanation: str
    reference_option: int
    due_at: datetime
    created_at: datetime


@router.get("/learning/knowledge-points/{point_code}/study", response_model=StudyRead)
def read_study(point_code: str, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return study_application(db).read(student.id, point_code)


@router.post("/learning/knowledge-points/{point_code}/study/start", response_model=StudyRead)
def start_study(
    point_code: str, payload: StudyStart, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return study_application(db).start(
        student.id, point_code, payload.client_id, payload.interaction_style, payload.new_round
    )


@router.get("/learning/study-paths/{path_id}/practices", response_model=list[PracticeGroupRead])
def practices(path_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return study_application(db).practices(student.id, path_id)


@router.post("/learning/study-paths/{path_id}/practices", response_model=PracticeGroupRead)
def start_practice(
    path_id: int, payload: PracticeStart, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return study_application(db).generate(student.id, path_id, payload.cycle, payload.client_id)


@router.get("/learning/self-practices/history", response_model=list[PracticeGroupRead])
def history(student: User = Depends(require_student), db: Session = Depends(get_db)):
    return study_application(db).practices(student.id)


@router.get("/learning/self-practices/{group_id}", response_model=PracticeGroupRead)
def practice(group_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return study_application(db).practice(student.id, group_id, answers=True)


@router.post("/learning/self-practices/{group_id}/answers", response_model=PracticeFeedback)
def answer(
    group_id: int, payload: PracticeAnswer, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return study_application(db).answer(
        student.id, group_id, payload.question_index, payload.selected_option, payload.client_id
    )
