from pydantic import BaseModel, Field

from app.modules.qa.api.schemas import MessageIn


class MedicalChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    mode: str | None = Field(default=None, max_length=40)
    messages: list[MessageIn] = Field(default_factory=list, max_length=20)
    topic_codes: list[str] = Field(default_factory=list, max_length=3)


class MedicalChatResponse(BaseModel):
    content: str
