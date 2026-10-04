"""Teacher-owned question bank; no classwide publishing in this release."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_teacher
from app.modules.content.wiring import teacher_question_bank_application
from app.modules.identity.infrastructure.models import User
from app.modules.learning.wiring import learning_route_result_read_port

router = APIRouter(prefix="/teacher/question-bank", tags=["teacher-question-bank"])


class BankContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: Literal["retest", "knowledge_review", "discussion", "micro_drill"]
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=2000)
    options: list[str] = Field(default_factory=list, max_length=6)
    answer: dict = Field(default_factory=dict)
    explanation: str = Field(default="", max_length=2000)
    point_codes: list[str] = Field(min_length=1, max_length=3)
    dimension_ids: list[str] = Field(default_factory=list, max_length=6)


class BankImportRequest(BankContent):
    source_type: Literal["route_test_question"]
    source_id: UUID
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    client_request_id: str = Field(min_length=1, max_length=100)
    deidentified: Literal[True]


class BankUpdateRequest(BankContent):
    version: int = Field(ge=1)


class BankSourceResponse(BankContent):
    source_type: Literal["route_test_question"]
    source_id: UUID
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class BankArchiveRequest(BaseModel):
    version: int = Field(ge=1)
    client_request_id: str = Field(min_length=1, max_length=100)


class BankItemResponse(BaseModel):
    id: int
    version: int
    status: Literal["active", "archived"]
    task_type: str
    title: str
    prompt: str
    options: list[str]
    answer: dict
    explanation: str
    point_codes: list[str]
    dimension_ids: list[str]
    medical_review_status: str | None
    updated_at: datetime


class BankPageResponse(BaseModel):
    items: list[BankItemResponse]
    total: int
    limit: int
    offset: int


_CONTENT_FIELDS = ("task_type", "title", "prompt", "options", "answer", "explanation", "point_codes", "dimension_ids")


def _content(payload: BankContent) -> dict[str, object]:
    return payload.model_dump(include=set(_CONTENT_FIELDS))


@router.get("/sources/route-test-questions/{question_id}", response_model=BankSourceResponse)
def bank_source(
    question_id: UUID,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return teacher_question_bank_application(db, learning_route_result_read_port(db)).source(
        teacher.id, str(question_id)
    )


@router.post("/import", response_model=BankItemResponse)
def import_bank_item(
    payload: BankImportRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return teacher_question_bank_application(db, learning_route_result_read_port(db)).import_item(
        teacher.id,
        payload.source_type,
        str(payload.source_id),
        payload.source_digest,
        payload.client_request_id,
        payload.deidentified,
        _content(payload),
    )


@router.get("", response_model=BankPageResponse)
def teacher_bank(
    status: Literal["active", "archived"] = "active",
    point_code: str | None = None,
    task_type: str | None = None,
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return teacher_question_bank_application(db, learning_route_result_read_port(db)).list(
        teacher.id, status, point_code, task_type, q, limit, offset
    )


@router.get("/{bank_item_id}", response_model=BankItemResponse)
def teacher_bank_item(bank_item_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return teacher_question_bank_application(db, learning_route_result_read_port(db)).get(teacher.id, bank_item_id)


@router.put("/{bank_item_id}", response_model=BankItemResponse)
def update_bank_item(
    bank_item_id: int,
    payload: BankUpdateRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return teacher_question_bank_application(db, learning_route_result_read_port(db)).update(
        teacher.id, bank_item_id, payload.version, _content(payload)
    )


@router.post("/{bank_item_id}/archive", response_model=BankItemResponse)
def archive_bank_item(
    bank_item_id: int,
    payload: BankArchiveRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return teacher_question_bank_application(db, learning_route_result_read_port(db)).archive(
        teacher.id, bank_item_id, payload.version, payload.client_request_id
    )


@router.delete("/{bank_item_id}", status_code=204)
def delete_bank_item(
    bank_item_id: int,
    payload: BankArchiveRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> Response:
    teacher_question_bank_application(db, learning_route_result_read_port(db)).archive(
        teacher.id, bank_item_id, payload.version, payload.client_request_id
    )
    return Response(status_code=204)
