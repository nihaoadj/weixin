from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.conversation import MessageRead

ReportAnalysisText = Annotated[str, Field(min_length=1, max_length=2000)]


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


class ReportReview(BaseModel):
    teacher_score: float = Field(ge=0, le=100)
    teacher_feedback: str = Field(default="", max_length=2000)


class ReportRead(BaseModel):
    id: int
    conversation_id: int
    conversation_client_id: str | None = None
    student_id: int
    student_name: str | None = None
    status: str
    ai_score: float
    ai_summary: str
    analysis: ReportAnalysis | None = None
    messages: list[MessageRead] = []
    teacher_score: float | None = None
    teacher_feedback: str | None = None
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
    ai_score: float
    teacher_score: float | None = None
    message_preview: str = ""
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ReportSummaryPage(BaseModel):
    items: list[ReportSummaryRead]
    total: int
    pending_count: int
    reviewed_count: int
    limit: int
    offset: int
