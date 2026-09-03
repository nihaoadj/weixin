from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_student, require_teacher
from app.modules.identity.infrastructure.models import User
from app.modules.pbl.infrastructure.models import (
    PblDiagnosticSnapshot,
    PblQuestionSuggestion,
    PblSession,
)
from app.modules.pbl.wiring import pbl_application

router = APIRouter(tags=["pbl"])


class Create(BaseModel):
    topic_code: str


class Message(BaseModel):
    client_message_id: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2000)


class Edit(BaseModel):
    version: int = Field(ge=1)
    title: str = ""
    prompt: str = ""
    reject: bool = False


def _session(x: PblSession):
    return {
        "id": x.id,
        "class_id": x.class_id,
        "topic_code": x.topic_code,
        "status": x.status,
        "created_at": x.created_at,
    }


def _snapshot(x: PblDiagnosticSnapshot, teacher: bool = False):
    return {
        "id": x.id,
        "revision": x.revision,
        "diagnostic_status": x.status,
        "assistant_reply": x.assistant_reply,
        "follow_up_question": x.follow_up_question,
        "knowledge_gaps": x.knowledge_gaps,
        "reasoning_issues": x.reasoning_issues,
        **({"provider_metadata": x.provider_metadata, "failure_reason": x.failure_reason} if teacher else {}),
    }


def _suggestion(x: PblQuestionSuggestion):
    return {
        "id": x.id,
        "title": x.title,
        "prompt": x.prompt,
        "linked_findings": x.linked_findings,
        "status": x.status,
        "version": x.version,
        "problem_id": x.problem_id,
    }


@router.post("/classes/{class_id}/pbl-sessions")
def create(class_id: int, payload: Create, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _session(pbl_application(db).create_session(teacher.id, class_id, payload.topic_code))


@router.post("/classes/{class_id}/pbl-sessions/{session_id}/close")
def close(class_id: int, session_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _session(pbl_application(db).close_session(teacher.id, class_id, session_id))


@router.get("/student/pbl-sessions")
def active(student: User = Depends(require_student), db: Session = Depends(get_db)):
    return [_session(x) for x in pbl_application(db).active_for_student(student.id)]


@router.get("/student/pbl-sessions/{session_id}/participation")
def participation(session_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    part, snap = pbl_application(db).participation(student.id, session_id)
    return {
        "session_id": session_id,
        "messages": part.messages,
        "revision": part.revision,
        "diagnostic": _snapshot(snap) if snap else None,
    }


@router.post("/student/pbl-sessions/{session_id}/messages")
def message(session_id: int, payload: Message, student: User = Depends(require_student), db: Session = Depends(get_db)):
    part, snap = pbl_application(db).message(student.id, session_id, payload.client_message_id, payload.content)
    return {"messages": part.messages, "diagnostic": _snapshot(snap)}


@router.get("/teacher/pbl-diagnostics")
def diagnostics(teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    app = pbl_application(db)
    values = []
    for snap in app.diagnostics(teacher.id):
        suggestions = db.query(PblQuestionSuggestion).filter(PblQuestionSuggestion.snapshot_id == snap.id).all()
        values.append({**_snapshot(snap, True), "recommended_questions": [_suggestion(x) for x in suggestions]})
    return values


@router.patch("/teacher/pbl-question-suggestions/{suggestion_id}")
def edit(suggestion_id: int, payload: Edit, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _suggestion(
        pbl_application(db).edit_suggestion(
            teacher.id, suggestion_id, payload.version, payload.title, payload.prompt, payload.reject
        )
    )


@router.post("/teacher/pbl-question-suggestions/{suggestion_id}/adopt-and-publish")
def adopt(suggestion_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _suggestion(pbl_application(db).adopt(teacher.id, suggestion_id))
