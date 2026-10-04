from datetime import UTC, date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


class UTCModel(BaseModel):
    @field_validator("*", mode="after")
    @classmethod
    def utc_datetime(cls, value):
        if isinstance(value, datetime):
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return value


RequestIdentity = Annotated[str, Field(min_length=1, max_length=100, pattern=r".*\S.*")]
Option = Annotated[StrictInt, Field(ge=0, le=3)]
TestAnswer = Option | list[Option] | str


class Command(UTCModel):
    model_config = ConfigDict(extra="forbid")
    client_request_id: RequestIdentity


class ReadingCommand(Command):
    action: Literal["start", "heartbeat", "pause"]
    lease_token: str | None = None


class RetryCommand(Command):
    component: Literal["route", "test"]


class CaseCommand(UTCModel):
    model_config = ConfigDict(extra="forbid")
    client_message_id: RequestIdentity
    content: str = Field(min_length=1, max_length=2000, pattern=r".*\S.*")
    expected_revision: Annotated[StrictInt, Field(ge=0)]


class DraftCommand(Command):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    released_digest: str = Field(min_length=64, max_length=64)
    answers: dict[str, TestAnswer]


class SubmitCommand(UTCModel):
    model_config = ConfigDict(extra="forbid")
    client_submission_id: RequestIdentity
    expected_version: Annotated[StrictInt, Field(ge=1)]
    released_digest: str = Field(min_length=64, max_length=64)
    answers: dict[str, TestAnswer]


class RubricCriterion(UTCModel):
    criterion_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    max_points: Literal[10]


class EditableQuestion(UTCModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    position: Annotated[StrictInt, Field(ge=1)]
    primary_point_code: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=2000)
    question_type: Literal["single_choice", "multiple_choice", "short_answer"] = "single_choice"
    options: list[str] = Field(default_factory=list, max_length=4)
    correct_option: Option | None = None
    correct_options: list[Option] | None = None
    reference_answer: str | None = Field(default=None, max_length=2000)
    rubric: list[RubricCriterion] | None = None
    explanation: str = Field(min_length=1, max_length=2000)


class TeacherSave(Command):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    questions: list[EditableQuestion] = Field(min_length=1, max_length=12)
    feedback_draft: str = Field(default="", max_length=1000)


class ReviewCommand(Command):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    note: str = Field(default="", max_length=1000)


class ReleaseCommand(Command):
    expected_version: Annotated[StrictInt, Field(ge=1)]
    draft_digest: str = Field(min_length=64, max_length=64)
    feedback: str = Field(default="", max_length=1000)


class ReadingProgress(UTCModel):
    lease_token: str | None
    accumulated_seconds: int
    last_seen_at: datetime | None


class TestSummary(UTCModel):
    id: str
    title: str
    question_count: int
    generation_state: str
    review_state: str
    review_kind: str | None
    can_start: bool
    lock_reason: str | None
    claim_expires_at: datetime | None = None
    retry_allowed: bool = False


class RouteProgress(UTCModel):
    completed_steps: int
    total_steps: int


class RouteSummary(UTCModel):
    scope_status: Literal["active", "inactive"] = "active"
    id: str
    title: str
    source_kind: Literal["classroom", "autonomous"]
    session_locator: str
    goal_point_codes: list[str]
    status: str
    next_action: str
    progress: RouteProgress
    updated_at: datetime
    test_summary: TestSummary
    result_id: str | None
    generation_state: str
    claim_expires_at: datetime | None = None
    retry_allowed: bool = False


class RoutePage(UTCModel):
    items: list[RouteSummary]
    total: int
    limit: int
    offset: int


class StudentInsightAction(UTCModel):
    kind: Literal["discussion", "route", "result"]
    session_id: str
    route_id: str | None = None
    label: str


class StudentInsightDashboardTrend(UTCModel):
    period_start: date
    period_end: date
    score: float | None
    sample_count: int


class StudentInsightWeakness(UTCModel):
    target_type: Literal["knowledge", "reasoning"]
    target_code: str
    label: str
    occurrences: int
    mastery_percentage: float | None


class StudentInsightDashboard(UTCModel):
    data_basis: Literal["learning_route_results", "synthetic_demo"]
    period_start: date
    period_end: date
    mastery_score: float | None
    mastery_delta: float | None
    mastery_sample_count: int
    study_minutes: int
    study_duration_basis: Literal["recorded_reading"]
    plan_completion_rate: float | None
    tested_knowledge_count: int
    ai_diagnostic_count: int
    status_label: str
    trend: list[StudentInsightDashboardTrend]
    weaknesses: list[StudentInsightWeakness]
    ai_summary: str


class StudentInsightSession(UTCModel):
    id: str
    topic_label: str
    case_title: str


class StudentInsightItem(UTCModel):
    id: str
    session: StudentInsightSession
    summary_text: str
    updated_at: datetime
    action: StudentInsightAction


class StudentInsightSummary(UTCModel):
    dashboard: StudentInsightDashboard
    next_action: StudentInsightAction | None = None


class StudentInsightPage(UTCModel):
    summary: StudentInsightSummary
    items: list[StudentInsightItem]
    total: int
    limit: int
    offset: int


class StepSummary(UTCModel):
    id: str
    position: int
    kind: Literal["reading", "case"]
    title: str
    goal_point_codes: list[str]
    status: str
    case_id: str | None
    completed_at: datetime | None


class RouteDetail(UTCModel):
    summary: RouteSummary
    diagnosis_summary: dict
    steps: list[StepSummary]
    test_summary: TestSummary
    can_start_test: bool
    lock_reasons: list[str]
    route_version: int


class ReadingStep(StepSummary):
    route_id: str
    sources: list[dict]
    ai_guide: str
    sections: list[dict]
    learning_points: list[str]
    reading_progress: ReadingProgress


class AttemptRead(UTCModel):
    id: str
    status: str
    version: int
    answers: dict[str, TestAnswer]
    saved_at: datetime | None
    submitted_at: datetime | None


class StudentQuestion(UTCModel):
    id: str
    position: int
    point_code: str
    prompt: str
    question_type: Literal["single_choice", "multiple_choice", "short_answer"] = "single_choice"
    options: list[str]


class StudentTest(UTCModel):
    id: str
    title: str
    review_kind: str | None
    format_version: Literal["single_choice_v1", "mixed_v2"] = "single_choice_v1"
    released_version: int
    released_digest: str
    questions: list[StudentQuestion]
    attempt: AttemptRead | None


class ResultQuestion(StudentQuestion):
    selected_option: int | None = None
    selected_options: list[int] | None = None
    selected_text: str | None = None
    correct_option: int | None = None
    correct_options: list[int] | None = None
    reference_answer: str | None = None
    points_awarded: int | None = None
    points_possible: int | None = None
    grading_feedback: str | None = None
    rubric_results: list[dict] | None = None
    explanation: str


class LearningResult(UTCModel):
    id: str
    route_id: str
    source_kind: str
    goal_point_codes: list[str]
    route_summary: dict
    correct_count: int
    question_count: int
    score: float
    submitted_at: datetime
    questions: list[ResultQuestion]
    review_kind: str | None
    format_version: Literal["single_choice_v1", "mixed_v2"] = "single_choice_v1"


class GradingStatus(UTCModel):
    status: Literal["grading", "completed"]
    test_id: str
    route_id: str
    result_id: str | None
    retry_allowed: bool
    error_code: str | None


class TutorCommand(UTCModel):
    model_config = ConfigDict(extra="forbid")
    client_message_id: RequestIdentity
    question_id: UUID
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    content: str = Field(min_length=1, max_length=2000, pattern=r".*\S.*")


class TutorMessage(UTCModel):
    id: str
    role: Literal["student", "assistant"]
    question_id: str
    content: str
    sequence: int
    created_at: datetime


class TutorRead(UTCModel):
    result_id: str
    revision: int
    processing_state: Literal["idle", "processing", "retry_allowed"]
    pending_message_id: str | None
    messages: list[TutorMessage]


class TeacherLearningResult(LearningResult):
    student_id: int
    class_id: int
    session_id: int


class TeacherResultPage(UTCModel):
    items: list[TeacherLearningResult]
    total: int
    limit: int
    offset: int


class TeacherQuestion(EditableQuestion):
    id: UUID
    source_digest: str


class TeacherTest(UTCModel):
    id: str
    route_id: str
    title: str
    source_kind: Literal["classroom"]
    class_id: int
    session_id: int
    student_id: int
    diagnosis_summary: dict
    goal_point_codes: list[str]
    generation_state: str
    review_state: str
    review_kind: str | None
    current_scope_active: bool
    format_version: Literal["single_choice_v1", "mixed_v2"] = "single_choice_v1"
    version: int
    draft_digest: str
    questions: list[TeacherQuestion]
    released_at: datetime | None
    feedback_draft: str


class TeacherTestPage(UTCModel):
    items: list[TeacherTest]
    total: int
    limit: int
    offset: int


class TeacherReviewQueueItem(UTCModel):
    id: UUID
    route_id: UUID
    title: str
    class_id: int
    class_name: str
    session_id: int
    student_id: int
    student_name: str
    generation_state: Literal["ready", "generation_failed"]
    review_state: Literal["pending_review", "needs_changes"]
    updated_at: datetime
    can_review: bool
    can_retry: bool
    action_reason: Literal["REVIEW_READY", "GENERATION_FAILED"]


class TeacherReviewQueueCounts(UTCModel):
    pending_review: int
    needs_changes: int
    generation_failed: int


class TeacherReviewQueuePage(UTCModel):
    items: list[TeacherReviewQueueItem]
    counts: TeacherReviewQueueCounts
    total: int
    limit: int
    offset: int
    as_of: datetime


class ReleaseReceipt(UTCModel):
    test_id: str
    released_version: int
    released_digest: str
    released_at: datetime


class RetryReceipt(UTCModel):
    route_id: str
    component: str
    generation_state: str
    claim_expires_at: datetime | None


class CaseMessage(UTCModel):
    id: str
    role: Literal["student", "assistant"]
    content: str
    revision: int
    phase: Literal["pathology_recognition", "mechanism_explanation", "evidence_judgment", "summary_reflection"]


class PendingMessage(UTCModel):
    client_message_id: str
    request_revision: int
    processing_state: str
    retry_allowed: bool
    claim_expires_at: datetime | None


class CaseGoalRead(UTCModel):
    goal_id: str
    objective: str


class CaseStageRead(UTCModel):
    phase: Literal["pathology_recognition", "mechanism_explanation", "evidence_judgment", "summary_reflection"]
    goals: list[CaseGoalRead]
    prompt: str


class CaseRead(UTCModel):
    id: str
    route_id: str
    step_id: str
    synthetic_case: dict
    phase: str
    revision: int
    status: str
    goals: list[CaseGoalRead]
    stages: list[CaseStageRead]
    messages: list[CaseMessage]
    next_prompt: str
    safety_notice: str
    pending_message: PendingMessage | None


class CaseMessageResult(UTCModel):
    client_message_id: str
    request_revision: int
    processing_state: str
    retry_allowed: bool
    reply: str | None
    phase: str
    revision: int
    decision: str | None
    missing_elements: list[str]
    status: str
