"""HTTP schemas for student question threads owned by QA."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.qa.api.schemas import MessageIn, MessageRead


class QuestionThreadUpsert(BaseModel):
    messages: list[MessageIn] = Field(default_factory=list, max_length=100)


class QuestionThreadRead(BaseModel):
    question_id: int
    messages: list[MessageRead] = []
    updated_at: datetime


class StudentQuestionRead(BaseModel):
    id: int
    type: str
    title: str
    description: str = ""
    published_at: datetime
    status: str = Field(pattern="^(answered|unanswered)$")
    topic_codes: list[str] = Field(default_factory=list)


class StudentQuestionPage(BaseModel):
    items: list[StudentQuestionRead]
    total: int
    limit: int
    offset: int
