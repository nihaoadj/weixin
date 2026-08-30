from datetime import datetime

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class MessageRead(MessageIn):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationUpsert(BaseModel):
    client_id: str = Field(min_length=1, max_length=100)
    messages: list[MessageIn] = Field(default_factory=list, max_length=100)


class ConversationRead(BaseModel):
    id: int
    client_id: str
    student_id: int
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = []

    model_config = {"from_attributes": True}


class ConversationSummaryRead(BaseModel):
    id: int
    client_id: str
    message_preview: str = ""
    message_count: int = 0
    report_id: int | None = None
    report_status: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationSummaryPage(BaseModel):
    items: list[ConversationSummaryRead]
    total: int
    limit: int
    offset: int
