from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.training.api.schemas import DIMENSION_SPECS, CaseDefinition, CaseOpening, CaseRubric


class ProblemCreate(BaseModel):
    type: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    target: str = Field(default="all", pattern="^(all|class|individual)$")
    target_label: str = Field(default="全体学生", max_length=200)
    target_ids: list[str] = Field(default_factory=list, max_length=200)
    content_type: str = Field(default="question", pattern="^(question|guided_case)$")
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    specialty: str = Field(default="", max_length=80)
    difficulty: str = Field(default="basic", max_length=30)
    estimated_minutes: int = Field(default=10, ge=1, le=180)
    version: int = Field(default=1, ge=1)
    parent_problem_id: int | None = Field(default=None, gt=0)
    case_definition: CaseDefinition | None = None
    rubric: CaseRubric | None = None
    capability_tags: list[str] = Field(default_factory=list, max_length=6)
    knowledge_point_codes: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def validate_case(self) -> "ProblemCreate":
        if self.content_type == "guided_case" and (self.case_definition is None or self.rubric is None):
            raise ValueError("guided_case requires case_definition and rubric")
        if self.content_type == "guided_case" and not self.slug:
            raise ValueError("guided_case requires slug")
        if self.content_type == "question" and (self.case_definition is not None or self.rubric is not None):
            raise ValueError("question cannot include case fields")
        if any(tag not in {item[0] for item in DIMENSION_SPECS} for tag in self.capability_tags):
            raise ValueError("invalid capability tag")
        return self


class ProblemUpdate(ProblemCreate):
    status: str | None = Field(default=None, pattern="^(draft|published|rejected)$")

    @model_validator(mode="after")
    def reject_guided_status_override(self) -> "ProblemUpdate":
        if self.content_type == "guided_case" and self.status is not None:
            raise ValueError("guided_case status is controlled by review and publish endpoints")
        return self


class ProblemRead(BaseModel):
    id: int
    type: str
    title: str
    description: str = ""
    target: str
    target_label: str
    target_ids: list[str] = Field(default_factory=list)
    status: str
    created_at: datetime
    published_at: datetime | None = None
    answer_count: int = 0
    content_type: str = "question"
    slug: str | None = None
    specialty: str = ""
    difficulty: str = "basic"
    estimated_minutes: int = 10
    version: int = 1
    parent_problem_id: int | None = None
    author_id: int | None = None
    medical_review_status: str = "not_submitted"
    opening: CaseOpening | None = None
    capability_tags: list[str] = Field(default_factory=list)
    knowledge_point_codes: list[str] = Field(default_factory=list)


class ProblemAuthoringRead(ProblemRead):
    case_definition: CaseDefinition | None = None
    rubric: CaseRubric | None = None


class KnowledgeCardContributionWrite(BaseModel):
    point_code: str = Field(min_length=1, max_length=120)
    class_code: str | None = Field(default=None, min_length=1, max_length=80)
    card_type: str = Field(pattern="^(single_choice|recall)$")
    prompt: str = Field(min_length=1, max_length=1000)
    options: list[str] = Field(default_factory=list, max_length=6)
    correct_option: int | None = Field(default=None, ge=0)
    explanation: str = Field(default="", max_length=2000)
    reference: str = Field(default="", max_length=500)


class KnowledgeCardContributionRead(BaseModel):
    id: int
    point_code: str
    class_code: str | None = None
    version: int
    card_type: str
    prompt: str
    options: list[str] = Field(default_factory=list)
    correct_option: int | None = None
    explanation: str = ""
    reference: str = ""
    status: str
    reviewer_id: int | None = None
    review_comment: str = ""
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeCardReviewDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=1000)
