from dataclasses import dataclass
from datetime import datetime
from typing import Literal

DiagnosticStatus = Literal["probing", "ready", "insufficient_evidence", "unavailable"]


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


@dataclass(frozen=True, slots=True)
class InferenceResult:
    assistant_reply: str
    diagnostic_status: DiagnosticStatus
    follow_up_question: str | None = None
    knowledge_gaps: tuple[dict[str, object], ...] = ()
    reasoning_issues: tuple[dict[str, object], ...] = ()
    recommended_questions: tuple[dict[str, object], ...] = ()
    provider_metadata: dict[str, object] | None = None
    fallback_used: bool = False
    failure_reason: str | None = None
    conversation_ref: str | None = None
    schema_version: int = 3
    safety_notice: str = "仅供病理学教学，不能替代临床诊疗。"
    safety_status: str = "educational"
    phase_assessment: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class PblSessionRecord:
    id: int
    class_id: int
    teacher_id: int
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


@dataclass(frozen=True, slots=True)
class PblParticipationRecord:
    id: int
    session_id: int
    student_id: int
    coze_user_ref: str | None
    coze_conversation_ref: str | None
    messages: tuple[dict[str, str], ...]
    revision: int
    current_phase: str = "problem_framing"
    phase_started_revision: int = 0
    phase_status: str = "active"
    phase_completed_at: datetime | None = None


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


@dataclass(frozen=True, slots=True)
class PblReportParticipationRecord:
    session: PblSessionRecord
    participation: PblParticipationRecord
    snapshots: tuple[PblSnapshotRecord, ...]
