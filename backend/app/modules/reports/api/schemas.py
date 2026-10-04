from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.modules.qa.api.schemas import MessageRead

ReportAnalysisText = Annotated[str, Field(min_length=1, max_length=2000)]

ReportKind = Literal["qa_learning_report"]


class ReportAnalysisIssue(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    suggestion: str = Field(default="", max_length=2000)


class ReportAnalysis(BaseModel):
    errors: list[ReportAnalysisIssue] = Field(default_factory=list, max_length=20)
    strengths: list[ReportAnalysisText] = Field(default_factory=list, max_length=20)
    general_suggestions: list[ReportAnalysisText] = Field(default_factory=list, max_length=20)


class ReportCreate(BaseModel):
    conversation_id: int
    ai_score: float = Field(ge=0, le=100)
    ai_summary: str = Field(max_length=2000)
    analysis: ReportAnalysis | None = None


class ReportSubmit(BaseModel):
    class_id: int = Field(gt=0)


class ReportReview(BaseModel):
    teacher_score: float = Field(ge=0, le=100)
    teacher_feedback: str = Field(default="", max_length=2000)
    review_topic_codes: list[str] = Field(default_factory=list, max_length=3)


class ReportRead(BaseModel):
    id: int
    conversation_id: int
    conversation_client_id: str | None = None
    student_id: int
    student_name: str | None = None
    status: str
    report_kind: ReportKind
    ai_score: float
    ai_summary: str
    analysis: ReportAnalysis | None = None
    messages: list[MessageRead] = []
    teacher_score: float | None = None
    teacher_feedback: str | None = None
    reviewer_id: int | None = None
    review_topic_codes: list[str] = Field(default_factory=list)
    class_id: int | None = None
    class_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportSummaryRead(BaseModel):
    id: int
    conversation_id: int
    conversation_client_id: str
    student_id: int
    student_name: str
    status: str
    report_kind: ReportKind
    ai_score: float
    teacher_score: float | None = None
    message_preview: str = ""
    message_count: int = 0
    class_id: int | None = None
    class_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ReportSummaryPage(BaseModel):
    items: list[ReportSummaryRead]
    total: int
    pending_count: int
    reviewed_count: int
    limit: int
    offset: int
