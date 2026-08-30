from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.problem import ProblemAuthoringRead


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")


class ClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = Field(default=None, pattern="^(active|archived)$")

    @model_validator(mode="after")
    def require_change(self) -> "ClassUpdate":
        if self.name is None and self.status is None:
            raise ValueError("class update requires name or status")
        return self


class ClassMemberCreate(BaseModel):
    student_external_id: str = Field(min_length=1, max_length=80)


class ClassRead(BaseModel):
    id: int
    name: str
    code: str
    status: str
    teacher_id: int
    created_at: datetime


class ClassStudentRead(BaseModel):
    id: int
    nickname: str
    external_id: str
    joined_at: datetime


class ReviewSubmit(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_rejection_comment(self) -> "ReviewSubmit":
        if self.decision == "rejected" and len(self.comment.strip()) < 5:
            raise ValueError("rejected review requires at least 5 characters")
        return self


class MedicalReviewRead(BaseModel):
    id: int
    problem_id: int
    reviewer_id: int
    decision: str
    comment: str
    problem_version: int
    case_digest: str
    created_at: datetime


class MedicalReviewViewRead(ProblemAuthoringRead):
    current_digest: str
    author_nickname: str | None = None
    reviews: list[MedicalReviewRead] = Field(default_factory=list)


class AnalyticsScope(BaseModel):
    class_id: int | None = None
    class_name: str | None = None
    date_from: str
    date_to: str


class AnalyticsOverview(BaseModel):
    scope: AnalyticsScope
    student_count: int
    published_case_count: int
    eligible_pairs: int
    started_pairs: int
    completed_pairs: int
    completion_rate: float | None
    current_average_score: float | None
    average_improvement: float | None
    dimensions: list[dict]
    weak_dimensions: list[dict]
    cases: list[dict] = Field(default_factory=list)
    students: list[dict] = Field(default_factory=list)


class AnalyticsCaseRead(BaseModel):
    problem: dict
    eligible_pairs: int
    started_pairs: int
    completed_pairs: int
    completion_rate: float | None
    current_average_score: float | None
    average_improvement: float | None
    average_duration_minutes: float | None
    dimensions: list[dict]
    distribution: dict
    students: list[dict]


class AnalyticsStudentRead(BaseModel):
    student: dict
    assigned: int
    started: int
    completed: int
    completion_rate: float | None
    current_average_score: float | None
    average_improvement: float | None
    dimensions: list[dict]
    cases: list[dict]
    timeline: list[dict]
