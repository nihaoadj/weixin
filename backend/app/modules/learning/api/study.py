from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.bootstrap.composition import study_application
from app.db import get_db
from app.dependencies import require_student
from app.modules.identity.infrastructure.models import User

router = APIRouter(tags=["knowledge-study"])


class StudyStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str = Field(min_length=1, max_length=100)
    interaction_style: Literal["guided", "direct"] = "guided"


class MaterialSection(BaseModel):
    title: str
    text: str


class StudyMaterialRead(BaseModel):
    version: str
    point_code: str
    title: str
    objective: str
    learning_objectives: list[str] = Field(min_length=2)
    scenario: str
    background: list[MaterialSection]
    example: MaterialSection
    remediation: list[MaterialSection]
    reference: str
    evidence_status: str
    medical_review_status: str


class StudyStarted(BaseModel):
    session_id: int
    point_code: str
    phase: str
    learning_route_id: str | None


class StudyRead(BaseModel):
    material: StudyMaterialRead
    sessions: list[StudyStarted]


@router.get("/learning/knowledge-points/{point_code}/study", response_model=StudyRead)
def read_study(point_code: str, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return study_application(db).read(student.id, point_code)


@router.post("/learning/knowledge-points/{point_code}/study/start", response_model=StudyStarted)
def start_study(
    point_code: str, payload: StudyStart, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return study_application(db).start(student.id, point_code, payload.client_id, payload.interaction_style)


@router.get("/learning/study-paths/{path_id}/practices", response_model=list[dict])
def practices(path_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return _missing()


@router.post("/learning/study-paths/{path_id}/practices")
def start_practice(
    path_id: int, payload: dict | None = None, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return _retired()


@router.get("/learning/self-practices/history", response_model=list[dict])
def history(student: User = Depends(require_student), db: Session = Depends(get_db)):
    return []


@router.get("/learning/self-practices/{group_id}")
def practice(group_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return _missing()


@router.post("/learning/self-practices/{group_id}/answers")
def answer(
    group_id: int, payload: dict | None = None, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return _retired()


def _retired():
    from app.modules.learning.domain.learning_routes import conflict

    conflict("RETIRED_FLOW")


def _missing():
    from app.shared.errors import AppError

    raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
