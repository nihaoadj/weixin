from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DIMENSIONS = (
    "information_gathering",
    "problem_representation",
    "differential_diagnosis",
    "evidence_reasoning",
    "test_selection",
    "management_safety",
)
TaskType = Literal["focused_retry", "micro_drill", "cross_case_transfer"]
TaskStatus = Literal["pending", "in_progress", "completed"]


class PracticeBlueprint(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    dimension_id: str
    stage_id: str
    learner_level: str = Field(min_length=1, max_length=40)
    public_instruction: str = Field(min_length=1, max_length=1000)
    allowed_variants: list[str] = Field(default_factory=list, max_length=12)
    fixed_facts: list[str] = Field(default_factory=list, max_length=20)
    fallback_prompt: str = Field(min_length=1, max_length=1000)
    answer_schema: Literal["short_text", "evidence_grid", "decision_cards"]
    criteria: list[dict] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_dimension(self) -> "PracticeBlueprint":
        if self.dimension_id not in DIMENSIONS:
            raise ValueError("invalid capability dimension")
        if sum(float(item.get("weight", 0)) for item in self.criteria) != 100:
            raise ValueError("blueprint criteria weights must total 100")
        return self


class PracticeGeneratedDefinition(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    context: str = Field(min_length=1, max_length=1200)
    instruction: str = Field(min_length=1, max_length=1200)
    answer_schema: Literal["short_text", "evidence_grid", "decision_cards"]
    display_hints: list[str] = Field(default_factory=list, max_length=6)


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
    source_assessment_id: int
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


class LearningTaskStartRead(BaseModel):
    mode: Literal["case_attempt", "micro_drill"]
    task: LearningTaskPublic
    attempt: dict


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


class LearningTaskSubmit(BaseModel):
    answer: dict = Field(default_factory=dict)


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: Literal["learning_plan_ready", "learning_plan_due", "learning_plan_completed"]
    entity_type: Literal["learning_plan"]
    entity_id: int
    title: str
    body: str
    read_at: datetime | None = None
    created_at: datetime


class NotificationListRead(BaseModel):
    items: list[NotificationRead]
    unread_count: int


class NotificationMarkRead(BaseModel):
    marked: int
