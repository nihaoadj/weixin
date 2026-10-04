from dataclasses import dataclass
from datetime import datetime
from typing import Literal

DiagnosticStatus = Literal["probing", "ready", "insufficient_evidence", "unavailable"]
PblTurnScope = Literal["evidence", "private_follow_up"]


@dataclass(frozen=True, slots=True)
class InferenceRequest:
    session_id: int
    topic_code: str
    question: str
    history: tuple[dict[str, str], ...]
    anonymous_user_ref: str | None = None
    conversation_ref: str | None = None
    message_id: str = ""
    case_context: dict[str, object] | None = None
    goal_point_codes: tuple[str, ...] = ()
    current_phase: str = "problem_framing"
    phase_started_revision: int = 0
    current_revision: int = 0
    interaction_style: Literal["guided", "direct"] = "guided"
    allowed_points: tuple[dict[str, str], ...] = ()
    session_kind: Literal["classroom", "student_initiated"] = "classroom"
    schema_version: int = 8
    allowed_resource_refs: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class LearningResponseRecord:
    opening: str
    key_points: tuple[str, ...]
    next_step: str


@dataclass(frozen=True, slots=True)
class InferenceResult:
    assistant_reply: str
    diagnostic_status: DiagnosticStatus
    follow_up_question: str | None = None
    knowledge_gaps: tuple[dict[str, object], ...] = ()
    reasoning_issues: tuple[dict[str, object], ...] = ()
    recommended_questions: tuple[dict[str, object], ...] = ()
    recommended_knowledge_cards: tuple[dict[str, object], ...] = ()
    provider_metadata: dict[str, object] | None = None
    fallback_used: bool = False
    failure_reason: str | None = None
    conversation_ref: str | None = None
    schema_version: int = 8
    interaction_style: Literal["guided", "direct"] = "guided"
    safety_notice: str = "仅供病理学教学，不能替代临床诊疗。"
    safety_status: str = "educational"
    phase_assessment: dict[str, object] | None = None
    response_sections: LearningResponseRecord | None = None
    diagnosis_outcome: Literal["identified_gaps", "no_clear_gaps"] | None = None
    candidate_tasks: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class PrivateFollowupRequest:
    session_ref: str
    participation_ref: str
    interaction_style: Literal["guided", "direct"]
    learning_topic: str
    learning_goals: tuple[str, ...]
    messages: tuple[dict[str, object], ...]
    latest_student_message_id: int
    evidence_locked: Literal[True] = True
    conversation_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PrivateFollowupResult:
    assistant_reply: str
    interaction_style: Literal["guided", "direct"]
    processing_status: Literal["completed", "unavailable"] = "completed"
    safety_status: Literal["normal", "needs_human_help"] = "normal"
    safety_notice: str | None = None
    provider_metadata: dict[str, object] | None = None
    fallback_used: bool = False
    failure_reason: str | None = None
    conversation_ref: str | None = None
    schema_version: int = 1
    response_sections: LearningResponseRecord | None = None


@dataclass(frozen=True, slots=True)
class PblSessionRecord:
    id: int
    class_id: int | None
    teacher_id: int | None
    topic_code: str
    provider: str
    invocation_mode: str | None
    status: str
    created_at: datetime
    closed_at: datetime | None
    case_id: int | None = None
    case_version: int | None = None
    case_digest: str | None = None
    case_context: dict[str, object] | None = None
    goal_point_codes: tuple[str, ...] = ()
    phase: str = "problem_framing"
    version: int = 1
    session_kind: Literal["classroom", "student_initiated"] = "classroom"
    created_by_student_id: int | None = None
    client_session_id: str | None = None
    ai_schema_version: int = 8


@dataclass(frozen=True, slots=True)
class PblParticipationRecord:
    id: int
    session_id: int
    student_id: int
    coze_user_ref: str | None
    coze_conversation_ref: str | None
    messages: tuple[dict[str, object], ...]
    revision: int
    current_phase: str = "problem_framing"
    phase_started_revision: int = 0
    phase_status: str = "active"
    phase_completed_at: datetime | None = None
    interaction_style: Literal["guided", "direct"] = "guided"
    style_selected_at: datetime | None = None
    completion_snapshot_id: int | None = None
    evidence_completed_revision: int | None = None

    @property
    def evidence_locked(self) -> bool:
        return self.phase_status == "completed" and self.completion_snapshot_id is not None

    @property
    def conversation_mode(self) -> PblTurnScope:
        return "private_follow_up" if self.evidence_locked else "evidence"


@dataclass(frozen=True, slots=True)
class PblSnapshotRecord:
    id: int
    participation_id: int
    revision: int
    status: str
    assistant_reply: str
    follow_up_question: str | None
    knowledge_gaps: tuple[dict[str, object], ...]
    reasoning_issues: tuple[dict[str, object], ...]
    provider_metadata: dict[str, object]
    failure_reason: str | None
    schema_version: int = 1
    safety_notice: str = ""
    safety_status: str = "educational"
    created_at: datetime | None = None
    phase: str | None = None
    phase_decision: str | None = None
    phase_evidence_message_ids: tuple[str, ...] = ()
    phase_evidence_summary: str = ""
    phase_missing_elements: tuple[str, ...] = ()
    interaction_style: Literal["guided", "direct"] = "guided"
    diagnosis_outcome: Literal["identified_gaps", "no_clear_gaps"] | None = None
    candidate_tasks: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class PblPrivateFollowUpResultRecord:
    id: int
    participation_id: int
    student_message_id: int
    assistant_message_id: int
    interaction_style: Literal["guided", "direct"]
    schema_version: int
    processing_status: Literal["completed", "unavailable"]
    safety_status: str
    safety_notice: str | None
    provider_name: str
    provider_mode: str | None
    fallback_used: bool
    failure_category: str | None
    assistant_reply: str
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PblMessageResultRecord:
    turn_scope: PblTurnScope
    snapshot: PblSnapshotRecord | None = None
    private_follow_up: PblPrivateFollowUpResultRecord | None = None


@dataclass(frozen=True, slots=True)
class PblMessageSubmissionRecord:
    participation: PblParticipationRecord
    diagnostic: PblSnapshotRecord
    response_kind: Literal["evidence_assessment", "private_follow_up"]
    turn_scope: PblTurnScope
    private_follow_up: PblPrivateFollowUpResultRecord | None = None
    learning_route_id: str | None = None
    final_test_id: str | None = None
    route_generation_state: str | None = None
    test_generation_state: str | None = None
    learning_route_created: bool = False


@dataclass(frozen=True, slots=True)
class PblSuggestionRecord:
    id: int
    snapshot_id: int
    title: str
    prompt: str
    linked_findings: tuple[str, ...]
    status: str
    version: int
    problem_id: int | None


@dataclass(frozen=True, slots=True)
class PblDiagnosticRecord:
    snapshot: PblSnapshotRecord
    suggestions: tuple[PblSuggestionRecord, ...]
    student_id: int = 0
    class_id: int = 0
    session_id: int = 0
    student_name: str = ""
    class_name: str = ""
    topic_code: str = ""
    session_kind: Literal["classroom", "student_initiated"] = "classroom"
    interaction_style: Literal["guided", "direct"] = "guided"
    goal_point_codes: tuple[str, ...] = ()
    completion_snapshot_id: int | None = None
    case_id: int | None = None


@dataclass(frozen=True, slots=True)
class PblReportParticipationRecord:
    session: PblSessionRecord
    participation: PblParticipationRecord
    snapshots: tuple[PblSnapshotRecord, ...]


@dataclass(frozen=True, slots=True)
class PblTeacherFeedbackRecord:
    id: int
    snapshot_id: int
    plan_id: int | None
    student_id: int
    class_id: int
    teacher_id: int
    action_type: str
    suggestion_id: int | None
    body: str
    client_feedback_id: str
    created_at: datetime | None
