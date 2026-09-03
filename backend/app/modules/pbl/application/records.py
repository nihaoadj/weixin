from dataclasses import dataclass
from typing import Literal

DiagnosticStatus = Literal["probing", "ready", "insufficient_evidence", "unavailable"]


@dataclass(frozen=True, slots=True)
class InferenceRequest:
    session_id: int
    topic_code: str
    question: str
    history: tuple[dict[str, str], ...]


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
