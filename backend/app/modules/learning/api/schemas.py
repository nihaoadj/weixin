from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.training.api.schemas import CaseAttemptRead

DIMENSIONS = (
    "information_gathering",
    "problem_representation",
    "differential_diagnosis",
    "evidence_reasoning",
    "test_selection",
    "management_safety",
)
TaskType = Literal["focused_retry", "micro_drill", "cross_case_transfer", "discussion", "knowledge_review", "retest"]
TaskStatus = Literal["pending", "in_progress", "completed"]


class LearningTaskPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    position: int
    task_type: TaskType
    dimension_id: str
    stage_id: str | None = None
    problem_id: int | None = None
    status: TaskStatus
    public_definition: dict
    started_at: datetime | None = None
    completed_at: datetime | None = None


class LearningPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    status: Literal["active", "completed", "superseded"]
    source_assessment_id: int | None
    source_type: Literal["case_assessment", "pbl_suggestion"]
    source_id: int | None
    target_dimension_ids: list[str]
    due_at: datetime
    generation_mode: str
    model_name: str
    prompt_version: str
    fallback_used: bool
    failure_reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    superseded_at: datetime | None = None
    tasks: list[LearningTaskPublic] = Field(default_factory=list)


class LearningProfileRead(BaseModel):
    formal_dimensions: list[dict] = Field(default_factory=list)
    recent_assessments: list[dict] = Field(default_factory=list)
    practice_mastery: dict = Field(default_factory=dict)
    active_plan: LearningPlanRead | None = None
    unread_count: int = 0


class LearningTaskAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    status: Literal["in_progress", "assessed"]
    answer: dict = Field(default_factory=dict)
    public_definition: dict = Field(default_factory=dict)
    score: float | None = None
    evidence: list[str] = Field(default_factory=list)
    feedback: str = ""
    next_step: str = ""
    created_at: datetime
    assessed_at: datetime | None = None


class LearningTaskStartRead(BaseModel):
    mode: Literal["case_attempt", "micro_drill"]
    task: LearningTaskPublic
    attempt: CaseAttemptRead | LearningTaskAttemptRead


class LearningTaskSubmit(BaseModel):
    answer: dict = Field(default_factory=dict)


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: Literal[
        "learning_route_ready",
        "final_test_released",
        "learning_route_completed",
        "learning_plan_ready",
        "learning_plan_due",
        "learning_plan_completed",
        "pbl_mastery_improved",
        "pbl_reinforcement_activated",
        "pbl_automation_exhausted",
        "pbl_teacher_feedback",
    ]
    entity_type: Literal["learning_plan", "pbl_session", "learning_route"]
    entity_id: int | str
    title: str
    body: str
    read_at: datetime | None = None
    created_at: datetime


class NotificationListRead(BaseModel):
    items: list[NotificationRead]
    unread_count: int


class NotificationMarkRead(BaseModel):
    marked: int


class ExitQuizRequest(BaseModel):
    topic_codes: list[str] = Field(min_length=1, max_length=3)


class ReviewCardRead(BaseModel):
    card_code: str
    point_code: str
    prompt: str
    options: list[str]
    due_at: datetime | None = None


class ExitQuizRead(BaseModel):
    cards: list[ReviewCardRead]


class GradeReviewCardRequest(BaseModel):
    selected_option: int = Field(ge=0)
    confidence: Literal["low", "medium", "high"]


class GradeReviewCardRead(BaseModel):
    card_code: str
    correct: bool
    rating: Literal["again", "hard", "good", "easy"]
    explanation: str
    due_at: datetime


class RecallRevealRead(BaseModel):
    card_code: str
    point_code: str
    prompt: str
    explanation: str


class RateRecallCardRequest(BaseModel):
    rating: Literal["again", "hard", "good", "easy"]


class CaptureReviewItemRequest(BaseModel):
    point_code: str = Field(min_length=1, max_length=120)
    source_type: str = Field(min_length=1, max_length=40)
    source_id: str = Field(min_length=1, max_length=160)
    note: str = Field(default="", max_length=300)


class ReviewItemRead(BaseModel):
    id: int
    point_code: str
    card_code: str | None = None
    source_type: str
    source_id: str
    note: str
    active: bool
    created_at: datetime
    updated_at: datetime


class ReviewDashboardRead(BaseModel):
    due_count: int
    weak_point_codes: list[str]
    items: list[ReviewItemRead]


class KnowledgeMapPointRead(BaseModel):
    code: str
    status: Literal["not_started", "weak", "learning", "due", "stable"]


class KnowledgeMapRead(BaseModel):
    items: list[KnowledgeMapPointRead]
