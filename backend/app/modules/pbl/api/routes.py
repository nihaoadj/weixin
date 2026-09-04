from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_student, require_teacher
from app.modules.identity.infrastructure.models import User
from app.modules.pbl.application.records import (
    PblDiagnosticRecord,
    PblSessionRecord,
    PblSnapshotRecord,
    PblSuggestionRecord,
)
from app.modules.pbl.infrastructure.provider_schema import KnowledgeGap, ReasoningIssue
from app.modules.pbl.wiring import pbl_application

router = APIRouter(tags=["pbl"])


class Create(BaseModel):
    topic_code: str = Field(min_length=1, max_length=120)
    case_id: int = Field(gt=0)
    goal_point_codes: list[str] = Field(min_length=1, max_length=3)


class Phase(BaseModel):
    phase: Literal["problem_framing", "hypothesis", "evidence", "synthesis"]
    version: int = Field(ge=1)


class Adopt(BaseModel):
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=2000)
    target_student_ids: list[int] = Field(default_factory=list, max_length=500)
    whole_class: bool = False
    include_case_retry: bool = False


class Message(BaseModel):
    client_message_id: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2000)


class Edit(BaseModel):
    version: int = Field(ge=1)
    title: str = ""
    prompt: str = ""
    reject: bool = False


class SessionResponse(BaseModel):
    id: int
    class_id: int
    topic_code: str
    status: str
    created_at: datetime
    closed_at: datetime | None
    case_id: int | None
    case_version: int | None
    case_context: dict | None
    goal_point_codes: list[str]
    phase: str
    version: int


class MessageResponse(BaseModel):
    id: str
    sequence: int
    processing_status: str
    role: str
    content: str
    client_message_id: str | None = None


class StudentDiagnosticResponse(BaseModel):
    id: int
    revision: int
    diagnostic_status: str
    assistant_reply: str
    follow_up_question: str | None
    knowledge_gaps: list[KnowledgeGap]
    reasoning_issues: list[ReasoningIssue]
    schema_version: int
    safety_notice: str
    safety_status: str
    created_at: datetime | None
    legacy_findings: dict | None = None


class TeacherDiagnosticResponse(StudentDiagnosticResponse):
    student_id: int
    student_name: str
    class_id: int
    class_name: str
    session_id: int
    topic_code: str
    failure_reason: str | None
    recommended_questions: list["SuggestionResponse"]


class SuggestionResponse(BaseModel):
    id: int
    title: str
    prompt: str
    linked_findings: list[str]
    status: str
    version: int
    problem_id: int | None


class ParticipationResponse(BaseModel):
    session_id: int
    messages: list[MessageResponse]
    revision: int
    diagnostic: StudentDiagnosticResponse | None


class MessageSubmissionResponse(BaseModel):
    messages: list[MessageResponse]
    diagnostic: StudentDiagnosticResponse


class DiagnosticPageResponse(BaseModel):
    items: list[TeacherDiagnosticResponse]
    total: int
    limit: int
    offset: int


def _session(value: PblSessionRecord) -> dict[str, object]:
    return {
        "id": value.id,
        "class_id": value.class_id,
        "topic_code": value.topic_code,
        "status": value.status,
        "created_at": value.created_at,
        "closed_at": value.closed_at,
        "case_id": value.case_id,
        "case_version": value.case_version,
        "case_context": value.case_context,
        "goal_point_codes": value.goal_point_codes,
        "phase": value.phase,
        "version": value.version,
    }


def _snapshot(value: PblSnapshotRecord, *, teacher: bool = False) -> dict[str, object]:
    response: dict[str, object] = {
        "id": value.id,
        "revision": value.revision,
        "diagnostic_status": value.status,
        "assistant_reply": value.assistant_reply,
        "follow_up_question": value.follow_up_question,
        "knowledge_gaps": value.knowledge_gaps if value.schema_version == 2 else [],
        "reasoning_issues": value.reasoning_issues if value.schema_version == 2 else [],
        "schema_version": value.schema_version,
        "safety_notice": value.safety_notice,
        "safety_status": value.safety_status,
        "created_at": value.created_at,
        "legacy_findings": {"knowledge_gaps": value.knowledge_gaps, "reasoning_issues": value.reasoning_issues}
        if value.schema_version != 2
        else None,
    }
    if teacher:
        response["failure_reason"] = value.failure_reason
    return response


def _suggestion(value: PblSuggestionRecord) -> dict[str, object]:
    return {
        "id": value.id,
        "title": value.title,
        "prompt": value.prompt,
        "linked_findings": value.linked_findings,
        "status": value.status,
        "version": value.version,
        "problem_id": value.problem_id,
    }


@router.post("/classes/{class_id}/pbl-sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create(class_id: int, payload: Create, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _session(
        pbl_application(db).create_session(
            teacher.id, class_id, payload.topic_code, payload.case_id, tuple(payload.goal_point_codes)
        )
    )


@router.get("/classes/{class_id}/pbl-sessions", response_model=list[SessionResponse])
def sessions(class_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return [_session(value) for value in pbl_application(db).sessions_for_teacher(teacher.id, class_id)]


@router.post("/classes/{class_id}/pbl-sessions/{session_id}/close", response_model=SessionResponse)
def close(class_id: int, session_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _session(pbl_application(db).close_session(teacher.id, class_id, session_id))


@router.get("/student/pbl-sessions", response_model=list[SessionResponse])
def active(student: User = Depends(require_student), db: Session = Depends(get_db)):
    return [_session(value) for value in pbl_application(db).active_for_student(student.id)]


@router.get("/student/pbl-sessions/{session_id}/participation", response_model=ParticipationResponse)
def participation(session_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    value, snapshot = pbl_application(db).participation(student.id, session_id)
    return {
        "session_id": session_id,
        "messages": value.messages,
        "revision": value.revision,
        "diagnostic": _snapshot(snapshot) if snapshot else None,
    }


@router.post("/student/pbl-sessions/{session_id}/messages", response_model=MessageSubmissionResponse)
def message(session_id: int, payload: Message, student: User = Depends(require_student), db: Session = Depends(get_db)):
    value, snapshot = pbl_application(db).message(student.id, session_id, payload.client_message_id, payload.content)
    return {"messages": value.messages, "diagnostic": _snapshot(snapshot)}


def _diagnostic(value: PblDiagnosticRecord) -> dict[str, object]:
    return {
        **_snapshot(value.snapshot, teacher=True),
        "recommended_questions": [_suggestion(item) for item in value.suggestions],
        "student_id": value.student_id,
        "student_name": value.student_name,
        "class_id": value.class_id,
        "class_name": value.class_name,
        "session_id": value.session_id,
        "topic_code": value.topic_code,
    }


@router.get("/teacher/pbl-diagnostics", response_model=DiagnosticPageResponse)
def diagnostics(
    class_id: int | None = Query(default=None, gt=0),
    session_id: int | None = Query(default=None, gt=0),
    student_id: int | None = Query(default=None, gt=0),
    status: Literal["proposed", "edited", "published", "rejected", "superseded"] | None = None,
    limit: int = Query(default=20, ge=1, le=20),
    offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    values, total = pbl_application(db).diagnostics(
        teacher.id,
        limit,
        offset,
        {"class_id": class_id, "session_id": session_id, "student_id": student_id, "status": status},
    )
    return {"items": [_diagnostic(value) for value in values], "total": total, "limit": limit, "offset": offset}


@router.get("/teacher/pbl-diagnostics/{snapshot_id}", response_model=TeacherDiagnosticResponse)
def diagnostic(snapshot_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _diagnostic(pbl_application(db).diagnostic(teacher.id, snapshot_id))


@router.patch("/teacher/pbl-question-suggestions/{suggestion_id}", response_model=SuggestionResponse)
def edit(suggestion_id: int, payload: Edit, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _suggestion(
        pbl_application(db).edit_suggestion(
            teacher.id, suggestion_id, payload.version, payload.title, payload.prompt, payload.reject
        )
    )


@router.post("/teacher/pbl-question-suggestions/{suggestion_id}/adopt-and-publish", response_model=SuggestionResponse)
def adopt(suggestion_id: int, payload: Adopt, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _suggestion(
        pbl_application(db).adopt(
            teacher.id,
            suggestion_id,
            payload.version,
            payload.title,
            payload.prompt,
            tuple(payload.target_student_ids),
            payload.whole_class,
            payload.include_case_retry,
        )
    )


@router.patch("/classes/{class_id}/pbl-sessions/{session_id}/phase", response_model=SessionResponse)
def phase(
    class_id: int,
    session_id: int,
    payload: Phase,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return _session(pbl_application(db).phase(teacher.id, class_id, session_id, payload.phase, payload.version))


@router.get("/teacher/pbl-diagnostics/{snapshot_id}/revisions", response_model=list[TeacherDiagnosticResponse])
def revisions(snapshot_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return [_diagnostic(item) for item in pbl_application(db).revisions(teacher.id, snapshot_id)]


class TaskResult(BaseModel):
    score: float | None
    feedback: str
    evidence: list[str]
    answer: dict
    submitted_at: datetime | None


class TaskResponse(BaseModel):
    id: int
    position: int
    task_type: Literal["discussion", "knowledge_review", "retest", "micro_drill", "focused_retry"]
    status: str
    problem_id: int | None
    public_definition: dict
    result: TaskResult | None


class PlanResponse(BaseModel):
    id: int
    student_id: int
    source_type: Literal["pbl_suggestion"]
    source_id: int
    source_context: dict
    status: str
    verification_status: Literal["not_ready", "pending_teacher", "improved", "needs_reinforcement"]
    verification_note: str
    verified_at: datetime | None
    version: int
    due_at: datetime
    tasks: list[TaskResponse]


class SubmitTask(BaseModel):
    client_submission_id: str = Field(min_length=1, max_length=100)
    answer: dict


class Verify(BaseModel):
    version: int = Field(ge=1)
    decision: Literal["improved", "needs_reinforcement"]
    note: str = Field(min_length=1, max_length=1000)


class Summary(BaseModel):
    participants: int
    diagnoses: int
    published_suggestions: int
    plans: int
    tasks: int
    completed_tasks: int
    pending_verification: int
    improved: int
    needs_reinforcement: int
    objective_retest_count: int
    objective_retest_average: float | None


@router.get("/student/pbl-learning-plans", response_model=list[PlanResponse])
def learning_plans(student: User = Depends(require_student), db: Session = Depends(get_db)):
    return pbl_application(db).learning_plans(student.id)


@router.post("/student/pbl-learning-tasks/{task_id}/submit", response_model=PlanResponse)
def submit_task(
    task_id: int, payload: SubmitTask, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return pbl_application(db).submit_task(student.id, task_id, payload.client_submission_id, payload.answer)


@router.get("/teacher/pbl-learning-results", response_model=list[PlanResponse])
def learning_results(
    session_id: int | None = None, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return pbl_application(db).learning_results(teacher.id, session_id)


@router.post("/teacher/pbl-learning-results/{plan_id}/verify", response_model=PlanResponse)
def verify_result(
    plan_id: int, payload: Verify, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return pbl_application(db).verify_learning(teacher.id, plan_id, payload.version, payload.decision, payload.note)


@router.get("/classes/{class_id}/pbl-sessions/{session_id}/summary", response_model=Summary)
def summary(class_id: int, session_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return pbl_application(db).summary(teacher.id, class_id, session_id)
