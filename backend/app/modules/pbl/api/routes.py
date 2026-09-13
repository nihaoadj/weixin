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


class DialogueCreate(BaseModel):
    client_session_id: str = Field(min_length=1, max_length=100)
    class_id: int | None = Field(default=None, gt=0)
    interaction_style: Literal["guided", "direct"]
    goal_point_codes: list[str] = Field(min_length=1, max_length=3)


class DialogueStart(BaseModel):
    interaction_style: Literal["guided", "direct"]


class Edit(BaseModel):
    version: int = Field(ge=1)
    title: str = ""
    prompt: str = ""
    reject: bool = False


class SessionResponse(BaseModel):
    id: int
    class_id: int | None
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
    student_phase: str | None = None
    phase_status: str | None = None
    phase_counts: dict[str, int] | None = None
    session_kind: Literal["classroom", "student_initiated"] = "classroom"
    interaction_style: Literal["guided", "direct"] | None = None
    style_selected_at: datetime | None = None


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
    phase: str | None = None
    phase_decision: str | None = None
    phase_evidence_summary: str = ""
    phase_missing_elements: list[str] = Field(default_factory=list)


class TeacherDiagnosticResponse(StudentDiagnosticResponse):
    student_id: int
    student_name: str
    class_id: int
    class_name: str
    session_id: int
    topic_code: str
    failure_reason: str | None
    recommended_questions: list["SuggestionResponse"]
    session_kind: Literal["classroom", "student_initiated"]
    interaction_style: Literal["guided", "direct"]


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
    current_phase: str
    phase_started_revision: int
    phase_status: str
    phase_completed_at: datetime | None
    interaction_style: Literal["guided", "direct"]
    style_selected_at: datetime | None


class StudentClassResponse(BaseModel):
    id: int
    name: str
    code: str


class DialogueDetailResponse(BaseModel):
    session: SessionResponse
    participation: ParticipationResponse | None


class DialoguePageResponse(BaseModel):
    items: list[SessionResponse]
    total: int
    limit: int
    offset: int


class MessageSubmissionResponse(BaseModel):
    messages: list[MessageResponse]
    diagnostic: StudentDiagnosticResponse
    current_phase: str
    phase_status: str
    phase_completed_at: datetime | None
    interaction_style: Literal["guided", "direct"]
    style_selected_at: datetime | None


class DiagnosticPageResponse(BaseModel):
    items: list[TeacherDiagnosticResponse]
    total: int
    limit: int
    offset: int


class TeacherFeedbackRequest(BaseModel):
    client_feedback_id: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=1000)
    action_type: Literal["feedback_only", "task_published", "closed"]
    suggestion_id: int | None = Field(default=None, gt=0)
    suggestion_version: int | None = Field(default=None, ge=1)
    title: str = Field(default="", max_length=200)
    prompt: str = Field(default="", max_length=2000)
    target_student_ids: list[int] = Field(default_factory=list, max_length=500)
    whole_class: bool = False
    include_case_retry: bool = False


class FollowUpFeedbackRequest(BaseModel):
    client_feedback_id: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=1000)


class TeacherFeedbackResponse(BaseModel):
    id: int
    snapshot_id: int
    plan_id: int | None
    action_type: str
    body: str
    created_at: datetime | None


class WorkItemPageResponse(BaseModel):
    items: list["WorkItemResponse"]
    total: int
    limit: int
    offset: int
    summary: dict[str, int]


class WorkItemActor(BaseModel):
    id: int
    name: str


class WorkItemResponse(BaseModel):
    snapshot_id: int
    session_id: int
    source: Literal["student_submission", "classroom_diagnostic"]
    status: Literal["pending", "responded", "task_published", "closed"]
    student: WorkItemActor
    classroom: WorkItemActor = Field(alias="class")
    topic: str
    entered_at: datetime | None
    last_activity_at: datetime | None
    knowledge_gap_count: int
    reasoning_issue_count: int
    next_action: str

    model_config = {"populate_by_name": True}


class WorkItemDetailResponse(BaseModel):
    work_item: WorkItemResponse | None
    diagnostic: TeacherDiagnosticResponse
    feedbacks: list[TeacherFeedbackResponse]


class TeacherSessionListItem(BaseModel):
    id: int
    class_id: int
    class_name: str
    topic_code: str
    status: str
    created_at: datetime
    closed_at: datetime | None


class TeacherSessionPageResponse(BaseModel):
    items: list[TeacherSessionListItem]
    total: int
    limit: int
    offset: int


class FailedTargetResponse(BaseModel):
    target_type: str
    target_code: str
    label: str | None = None


class FollowUpListItem(BaseModel):
    plan_id: int
    student_id: int
    student_name: str
    class_id: int
    class_name: str
    session_id: int
    session_topic: str
    status: Literal["in_progress", "cycle_2", "support_needed", "improved"]
    current_cycle: int
    verification_status: str
    automation_exhausted: bool
    failed_targets: list[FailedTargetResponse]


class FollowUpPageResponse(BaseModel):
    items: list[FollowUpListItem]
    total: int
    limit: int
    offset: int


class FollowUpSourceContext(BaseModel):
    teacher_id: int
    class_id: int
    class_name: str
    session_id: int
    snapshot_id: int
    suggestion_id: int
    point_codes: list[str]
    dimension_ids: list[str]
    topic_code: str


class FollowUpPublicDefinition(BaseModel):
    prompt: str
    options: list[str] | None = None
    point_code: str | None = None
    card_code: str | None = None
    target_label: str | None = None
    reference: str | None = None


class FollowUpTaskResult(BaseModel):
    score: float | None
    feedback: str
    evidence: list[str]
    answer: dict[str, object]
    submitted_at: datetime | None


class FollowUpTaskResponse(BaseModel):
    id: int
    position: int
    task_type: str
    status: str
    problem_id: int | None
    public_definition: FollowUpPublicDefinition
    result: FollowUpTaskResult | None
    cycle_number: int
    target_type: str
    target_code: str
    variant_code: str


class FollowUpCheckResponse(BaseModel):
    target_type: str
    target_code: str
    label: str | None = None
    threshold: float | None
    score: float | None
    evidence_present: bool
    passed: bool


class FollowUpEvaluationResponse(BaseModel):
    id: int
    cycle_number: int
    policy_version: str
    result: str
    checks: list[FollowUpCheckResponse]
    failed_targets: list[FailedTargetResponse]
    automation_exhausted: bool
    record_source: str
    evaluated_at: datetime


class FollowUpDecisionBasis(BaseModel):
    result: str | None = None
    cycle: int | None = None
    offline_support_required: bool | None = None
    failed_targets: list[FailedTargetResponse] = Field(default_factory=list)
    checks: list[FollowUpCheckResponse] = Field(default_factory=list)


class FollowUpPlanResponse(BaseModel):
    id: int
    student_id: int
    source_context: FollowUpSourceContext
    status: str
    verification_status: str
    current_cycle: int
    max_cycles: int
    automation_exhausted: bool
    decision_basis: FollowUpDecisionBasis
    tasks: list[FollowUpTaskResponse]
    evaluations: list[FollowUpEvaluationResponse]


class FollowUpDetailResponse(BaseModel):
    plan: FollowUpPlanResponse
    feedbacks: list[TeacherFeedbackResponse]


class DashboardStudentRow(BaseModel):
    student_id: int
    student_name: str
    current_phase: str
    phase_status: str
    last_activity_at: datetime | None
    snapshot_id: int | None
    work_item_status: str | None
    task_progress: "TaskProgressResponse"
    current_cycle: int | None
    verification_status: str | None


class TaskProgressResponse(BaseModel):
    completed: int
    total: int


class DashboardSessionResponse(BaseModel):
    id: int
    class_id: int
    status: str


class DashboardSummaryResponse(BaseModel):
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
    phase_counts: dict[str, int]
    automation_exhausted: int


class DashboardResponse(BaseModel):
    session: DashboardSessionResponse
    summary: DashboardSummaryResponse
    students: list[DashboardStudentRow]


def _session(value: PblSessionRecord, participation=None, phase_counts=None) -> dict[str, object]:
    result = {
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
    if participation is not None:
        result.update(
            {
                "student_phase": participation.current_phase,
                "phase_status": participation.phase_status,
                "interaction_style": participation.interaction_style,
                "style_selected_at": participation.style_selected_at,
            }
        )
    if phase_counts is not None:
        result["phase_counts"] = phase_counts
    result["session_kind"] = value.session_kind
    return result


def _snapshot(value: PblSnapshotRecord, *, teacher: bool = False) -> dict[str, object]:
    response: dict[str, object] = {
        "id": value.id,
        "revision": value.revision,
        "diagnostic_status": value.status,
        "assistant_reply": value.assistant_reply,
        "follow_up_question": value.follow_up_question,
        "knowledge_gaps": value.knowledge_gaps if value.schema_version in {3, 4} else [],
        "reasoning_issues": value.reasoning_issues if value.schema_version in {3, 4} else [],
        "schema_version": value.schema_version,
        "safety_notice": value.safety_notice,
        "safety_status": value.safety_status,
        "created_at": value.created_at,
        "legacy_findings": {"knowledge_gaps": value.knowledge_gaps, "reasoning_issues": value.reasoning_issues}
        if value.schema_version not in {3, 4}
        else None,
        "phase": value.phase,
        "phase_decision": value.phase_decision,
        "phase_evidence_summary": value.phase_evidence_summary,
        "phase_missing_elements": value.phase_missing_elements,
    }
    if teacher:
        response["failure_reason"] = value.failure_reason
    return response


def _participation(value, snapshot: PblSnapshotRecord | None) -> dict[str, object]:
    return {
        "session_id": value.session_id,
        "messages": value.messages,
        "revision": value.revision,
        "diagnostic": _snapshot(snapshot) if snapshot else None,
        "current_phase": value.current_phase,
        "phase_started_revision": value.phase_started_revision,
        "phase_status": value.phase_status,
        "phase_completed_at": value.phase_completed_at,
        "interaction_style": value.interaction_style,
        "style_selected_at": value.style_selected_at,
    }


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
    app = pbl_application(db)
    return [
        _session(value, phase_counts=app.phase_counts(teacher.id, class_id, value.id))
        for value in app.sessions_for_teacher(teacher.id, class_id)
    ]


@router.post("/classes/{class_id}/pbl-sessions/{session_id}/close", response_model=SessionResponse)
def close(class_id: int, session_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return _session(pbl_application(db).close_session(teacher.id, class_id, session_id))


@router.get("/student/classes", response_model=list[StudentClassResponse])
def student_classes(student: User = Depends(require_student), db: Session = Depends(get_db)):
    return [
        {"id": item.id, "name": item.name, "code": item.code}
        for item in pbl_application(db).classes_for_student(student.id)
    ]


@router.get("/student/learning-dialogues", response_model=DialoguePageResponse)
def learning_dialogues(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    app = pbl_application(db)
    values = app.active_for_student(student.id)
    items = []
    for value in values[offset : offset + limit]:
        _, participation_value, _ = app.dialogue(student.id, value.id)
        items.append(_session(value, participation=participation_value))
    return {"items": items, "total": len(values), "limit": limit, "offset": offset}


@router.post("/student/learning-dialogues", response_model=DialogueDetailResponse, status_code=status.HTTP_201_CREATED)
def create_learning_dialogue(
    payload: DialogueCreate,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    app = pbl_application(db)
    session_value, participation_value = app.create_student_dialogue(
        student.id,
        payload.client_session_id,
        payload.class_id,
        payload.interaction_style,
        tuple(payload.goal_point_codes),
    )
    return {
        "session": _session(session_value, participation=participation_value),
        "participation": _participation(participation_value, None),
    }


@router.post("/student/learning-dialogues/{session_id}/start", response_model=DialogueDetailResponse)
def start_learning_dialogue(
    session_id: int,
    payload: DialogueStart,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    session_value, participation_value, snapshot = pbl_application(db).start_dialogue(
        student.id, session_id, payload.interaction_style
    )
    return {
        "session": _session(session_value, participation=participation_value),
        "participation": _participation(participation_value, snapshot),
    }


@router.get("/student/learning-dialogues/{session_id}", response_model=DialogueDetailResponse)
def learning_dialogue(
    session_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    session_value, participation_value, snapshot = pbl_application(db).dialogue(student.id, session_id)
    return {
        "session": _session(session_value, participation=participation_value),
        "participation": _participation(participation_value, snapshot) if participation_value else None,
    }


@router.post("/student/learning-dialogues/{session_id}/messages", response_model=MessageSubmissionResponse)
def learning_dialogue_message(
    session_id: int,
    payload: Message,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    value, snapshot = pbl_application(db).message(student.id, session_id, payload.client_message_id, payload.content)
    return {
        "messages": value.messages,
        "diagnostic": _snapshot(snapshot),
        "current_phase": value.current_phase,
        "phase_status": value.phase_status,
        "phase_completed_at": value.phase_completed_at,
        "interaction_style": value.interaction_style,
        "style_selected_at": value.style_selected_at,
    }


@router.get("/student/pbl-sessions", response_model=list[SessionResponse], deprecated=True)
def active(student: User = Depends(require_student), db: Session = Depends(get_db)):
    app = pbl_application(db)
    result = []
    for value in app.active_for_student(student.id):
        participation_value, _ = app.participation(student.id, value.id)
        result.append(_session(value, participation=participation_value))
    return result


@router.get("/student/pbl-sessions/{session_id}/participation", response_model=ParticipationResponse, deprecated=True)
def participation(session_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    value, snapshot = pbl_application(db).participation(student.id, session_id)
    return _participation(value, snapshot)


@router.post("/student/pbl-sessions/{session_id}/messages", response_model=MessageSubmissionResponse, deprecated=True)
def message(session_id: int, payload: Message, student: User = Depends(require_student), db: Session = Depends(get_db)):
    value, snapshot = pbl_application(db).message(
        student.id,
        session_id,
        payload.client_message_id,
        payload.content,
        allow_implicit_guided_start=True,
    )
    return {
        "messages": value.messages,
        "diagnostic": _snapshot(snapshot),
        "current_phase": value.current_phase,
        "phase_status": value.phase_status,
        "phase_completed_at": value.phase_completed_at,
        "interaction_style": value.interaction_style,
        "style_selected_at": value.style_selected_at,
    }


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
        "session_kind": value.session_kind,
        "interaction_style": value.interaction_style,
    }


def _feedback(value) -> dict[str, object]:
    return {
        "id": value.id,
        "snapshot_id": value.snapshot_id,
        "plan_id": value.plan_id,
        "action_type": value.action_type,
        "body": value.body,
        "created_at": value.created_at,
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


@router.get("/teacher/pbl-work-items", response_model=WorkItemPageResponse)
def work_items(
    class_id: int | None = Query(default=None, gt=0),
    source: Literal["student_submission", "classroom_diagnostic"] | None = None,
    status: Literal["pending", "responded", "task_published", "closed"] | None = None,
    session_id: int | None = Query(default=None, gt=0),
    student_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    values = pbl_application(db).work_items(
        teacher.id,
        limit,
        offset,
        {
            "class_id": class_id,
            "session_id": session_id,
            "student_id": student_id,
            "source": source,
            "work_status": status,
        },
    )
    return values


@router.get("/teacher/pbl-work-items/{snapshot_id}", response_model=WorkItemDetailResponse)
def work_item(snapshot_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    value = pbl_application(db).work_item(teacher.id, snapshot_id)
    return {
        "work_item": value["work_item"],
        "diagnostic": _diagnostic(value["diagnostic"]),
        "feedbacks": [_feedback(item) for item in value["feedbacks"]],
    }


@router.post("/teacher/pbl-work-items/{snapshot_id}/feedback", response_model=TeacherFeedbackResponse)
def work_item_feedback(
    snapshot_id: int,
    payload: TeacherFeedbackRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return _feedback(
        pbl_application(db).feedback(
            teacher.id,
            snapshot_id,
            payload.client_feedback_id,
            payload.body,
            payload.action_type,
            payload.suggestion_id,
            payload.suggestion_version,
            payload.title,
            payload.prompt,
            tuple(payload.target_student_ids),
            payload.whole_class,
            payload.include_case_retry,
        )
    )


@router.get("/teacher/pbl-follow-ups", response_model=FollowUpPageResponse)
def follow_ups(
    class_id: int | None = Query(default=None, gt=0),
    session_id: int | None = Query(default=None, gt=0),
    student_id: int | None = Query(default=None, gt=0),
    status: Literal["in_progress", "cycle_2", "support_needed", "improved"] | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return pbl_application(db).follow_ups(
        teacher.id,
        limit,
        offset,
        {"class_id": class_id, "session_id": session_id, "student_id": student_id, "status": status},
    )


@router.get("/teacher/pbl-follow-ups/{plan_id}", response_model=FollowUpDetailResponse)
def follow_up(plan_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    value = pbl_application(db).follow_up(teacher.id, plan_id)
    return {"plan": value["plan"], "feedbacks": [_feedback(item) for item in value["feedbacks"]]}


@router.post("/teacher/pbl-follow-ups/{plan_id}/feedback", response_model=TeacherFeedbackResponse)
def follow_up_feedback(
    plan_id: int,
    payload: FollowUpFeedbackRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return _feedback(
        pbl_application(db).follow_up_feedback(teacher.id, plan_id, payload.client_feedback_id, payload.body)
    )


@router.get("/teacher/pbl-sessions", response_model=TeacherSessionPageResponse)
def teacher_sessions(
    class_id: int | None = Query(default=None, gt=0),
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return pbl_application(db).teacher_sessions(teacher.id, limit, offset, class_id, status)


@router.get("/classes/{class_id}/pbl-sessions/{session_id}/dashboard", response_model=DashboardResponse)
def session_dashboard(
    class_id: int, session_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return pbl_application(db).session_dashboard(teacher.id, class_id, session_id)


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


@router.patch("/classes/{class_id}/pbl-sessions/{session_id}/phase", response_model=SessionResponse, deprecated=True)
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
    cycle_number: int
    target_type: str
    target_code: str
    variant_code: str


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
    current_cycle: int
    max_cycles: int
    automation_exhausted: bool
    decision_policy_version: str
    decision_basis: dict
    evaluated_at: datetime | None


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
    phase_counts: dict[str, int]
    automation_exhausted: int


ReportStatus = Literal[
    "discussing", "awaiting_learning", "learning_cycle_1", "learning_cycle_2", "improved", "support_needed"
]


class ReportSession(BaseModel):
    id: int
    topic_code: str
    topic_label: str
    case_title: str
    status: str
    created_at: datetime
    closed_at: datetime | None


class ReportAction(BaseModel):
    kind: Literal["discussion", "tasks", "none"]
    label: str


class ReportTaskProgress(BaseModel):
    completed: int
    total: int


class ReportRecurringTarget(BaseModel):
    target_type: str
    target_code: str
    label: str
    occurrences: int


class ReportPageAction(ReportAction):
    session_id: int
    case_title: str


class ReportListItem(BaseModel):
    session: ReportSession
    status: ReportStatus
    current_phase: str | None
    phase_status: str | None
    knowledge_gap_count: int
    reasoning_issue_count: int
    task_progress: ReportTaskProgress
    summary_text: str
    next_action: ReportAction
    updated_at: datetime


class ReportPageSummary(BaseModel):
    total_reports: int
    completed_personal_discussions: int
    status_counts: dict[str, int]
    recurring_targets: list[ReportRecurringTarget]
    next_action: ReportPageAction | None


class ReportPageResponse(BaseModel):
    summary: ReportPageSummary
    items: list[ReportListItem]
    total: int
    limit: int
    offset: int


class ReportPhaseProgress(BaseModel):
    phase: str
    label: str
    state: Literal["completed", "current", "pending"]
    evidence_summary: str
    missing_elements: list[str]
    evidenced_at: datetime | None


class ReportTask(BaseModel):
    id: int
    task_type: str
    status: str
    cycle_number: int
    target_type: str
    target_code: str
    target_label: str
    prompt: str
    reference: str | None
    score: float | None
    feedback: str
    evidence_present: bool
    submitted_at: datetime | None


class ReportCheck(BaseModel):
    target_type: str
    target_code: str
    label: str
    threshold: float | None
    score: float | None
    evidence_present: bool
    passed: bool


class ReportFailedTarget(BaseModel):
    target_type: str
    target_code: str
    label: str


class ReportEvaluation(BaseModel):
    cycle_number: int
    policy_version: str
    result: Literal["improved", "next_cycle_activated", "needs_reinforcement"]
    checks: list[ReportCheck]
    failed_targets: list[ReportFailedTarget]
    automation_exhausted: bool
    record_source: Literal["runtime", "backfill", "legacy"]
    evaluated_at: datetime


class ReportPlan(BaseModel):
    id: int
    assignment_basis: Literal["personal", "classroom"]
    status: str
    verification_status: str
    current_cycle: int
    max_cycles: int
    automation_exhausted: bool
    decision_policy_version: str
    due_at: datetime
    created_at: datetime
    tasks: list[ReportTask]
    evaluations: list[ReportEvaluation]


class ReportKnowledgeGap(BaseModel):
    id: str
    point_code: str
    label: str
    summary: str
    confidence: str
    evidence_summary: str


class ReportReasoningIssue(BaseModel):
    id: str
    dimension_id: str
    label: str
    summary: str
    issue_type: str
    improvement: str
    evidence_summary: str


class ReportDiagnosis(BaseModel):
    created_at: datetime | None
    knowledge_gaps: list[ReportKnowledgeGap]
    reasoning_issues: list[ReportReasoningIssue]


class ReportCycleCheck(ReportCheck):
    cycle_number: int


class ReportTargetProgress(BaseModel):
    plan_id: int
    target_type: str
    target_code: str
    label: str
    cycles: list[ReportCycleCheck]


class ReportTimelineItem(BaseModel):
    type: str
    label: str
    cycle_number: int | None = None
    occurred_at: datetime


class ReportDetailResponse(BaseModel):
    session: ReportSession
    status: ReportStatus
    current_phase: str | None
    phase_status: str | None
    phase_progress: list[ReportPhaseProgress]
    diagnosis: ReportDiagnosis
    plans: list[ReportPlan]
    target_progress: list[ReportTargetProgress]
    task_progress: ReportTaskProgress
    summary_text: str
    next_action: ReportAction
    timeline: list[ReportTimelineItem]
    updated_at: datetime


@router.get("/student/pbl-learning-plans", response_model=list[PlanResponse])
def learning_plans(student: User = Depends(require_student), db: Session = Depends(get_db)):
    return pbl_application(db).learning_plans(student.id)


@router.get("/student/pbl-learning-reports", response_model=ReportPageResponse)
def learning_reports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    return pbl_application(db).learning_report_page(student.id, limit, offset)


@router.get("/student/pbl-learning-reports/{session_id}", response_model=ReportDetailResponse)
def learning_report(session_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return pbl_application(db).learning_report(student.id, session_id)


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


@router.post("/teacher/pbl-learning-results/{plan_id}/verify", response_model=PlanResponse, deprecated=True)
def verify_result(
    plan_id: int, payload: Verify, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    return pbl_application(db).verify_learning(teacher.id, plan_id, payload.version, payload.decision, payload.note)


@router.get("/classes/{class_id}/pbl-sessions/{session_id}/summary", response_model=Summary)
def summary(class_id: int, session_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    return pbl_application(db).summary(teacher.id, class_id, session_id)


class SubmissionRequest(BaseModel):
    snapshot_id: int = Field(gt=0)
    class_id: int = Field(gt=0)
    client_submission_id: str = Field(min_length=1, max_length=100)


class PreviewQuestion(BaseModel):
    id: int
    title: str
    prompt: str


class SharedSubmission(BaseModel):
    session_id: int
    snapshot_id: int
    class_id: int
    source: str
    submitted_at: datetime | None


class StudentTeacherFeedback(BaseModel):
    id: int
    action_type: Literal["feedback_only", "task_published", "closed", "follow_up"]
    body: str
    created_at: datetime | None
    plan_id: int | None


class SubmissionPreview(BaseModel):
    session_id: int
    snapshot_id: int
    knowledge_gaps: list[KnowledgeGap]
    reasoning_issues: list[ReasoningIssue]
    evidence_summary: str
    questions: list[PreviewQuestion]
    submission: SharedSubmission | None
    teacher_status: Literal["pending", "responded", "task_published", "closed"] | None = None
    feedbacks: list[StudentTeacherFeedback] = Field(default_factory=list)
    next_action: str = ""


@router.get("/student/learning-dialogues/{session_id}/submission", response_model=SubmissionPreview)
def submission_preview(session_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    return pbl_application(db).submission_preview(student.id, session_id)


@router.post("/student/learning-dialogues/{session_id}/submission", response_model=SubmissionPreview)
def submit_dialogue(
    session_id: int, payload: SubmissionRequest, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    return pbl_application(db).submit_to_teacher(
        student.id, session_id, payload.snapshot_id, payload.class_id, payload.client_submission_id
    )
