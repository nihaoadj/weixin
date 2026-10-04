"""PBL stable contracts are exposed through API and wiring only."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.modules.pbl.application.ports import PblInferenceGateway


@dataclass(frozen=True, slots=True)
class PblStudentInsightRecord:
    participation_id: int
    session_id: int
    topic_code: str
    case_title: str
    session_kind: str
    goal_point_codes: tuple[str, ...]
    current_phase: str
    phase_status: str
    participation_created_at: datetime
    updated_at: datetime
    phase_completed_at: datetime | None
    diagnosis_created_at: datetime | None
    diagnosis_outcome: str | None
    knowledge_gap_codes: tuple[str, ...]
    reasoning_issue_codes: tuple[str, ...]


class PblClassroomParticipationPort(Protocol):
    """Read a classroom session's participant identities without conversation content."""

    def classroom_participants(self, class_id: int, session_id: int) -> tuple[int, ...] | None: ...


class PblStudentInsightReadPort(Protocol):
    """Read a student's own participation and verified completion diagnosis only."""

    def student_insight_records(self, student_id: int) -> tuple[PblStudentInsightRecord, ...]: ...


@dataclass(frozen=True, slots=True)
class PblTeacherFinding:
    code: str
    summary: str


@dataclass(frozen=True, slots=True)
class PblTeacherDiagnosisRecord:
    participation_id: int
    session_id: int
    class_id: int
    student_id: int
    completed_at: datetime
    knowledge_gap_codes: tuple[str, ...]
    reasoning_issue_codes: tuple[str, ...]
    knowledge_gaps: tuple[PblTeacherFinding, ...] = ()
    reasoning_issues: tuple[PblTeacherFinding, ...] = ()


@dataclass(frozen=True, slots=True)
class PblTeacherDiscussionRecord:
    participation_id: int
    session_id: int
    class_id: int
    student_id: int
    phase: str
    status: str
    started_at: datetime
    completed_at: datetime | None


class PblTeacherDiagnosisReadPort(Protocol):
    def teacher_discussions(
        self, teacher_id: int, class_ids: tuple[int, ...], start: datetime, end: datetime, session_id: int | None = None
    ) -> tuple[PblTeacherDiscussionRecord, ...]: ...

    def teacher_diagnoses(
        self,
        teacher_id: int,
        class_ids: tuple[int, ...],
        start: datetime,
        end: datetime,
        session_id: int | None = None,
    ) -> tuple[PblTeacherDiagnosisRecord, ...]: ...


class StudyDialoguePort(Protocol):
    def list_for_point(self, student_id: int, point_code: str) -> list[dict]: ...
    def start(self, student_id: int, point_code: str, client_id: str, style: str) -> int: ...
    def state(self, student_id: int, session_id: int) -> dict: ...


class PracticeJsonPort(Protocol):
    def practice_json(self, context: dict, schema: dict) -> str: ...


__all__ = [
    "PblInferenceGateway",
    "PblClassroomParticipationPort",
    "PblStudentInsightRecord",
    "PblStudentInsightReadPort",
    "PblTeacherDiagnosisRecord",
    "PblTeacherDiscussionRecord",
    "PblTeacherFinding",
    "PblTeacherDiagnosisReadPort",
    "StudyDialoguePort",
    "PracticeJsonPort",
]
