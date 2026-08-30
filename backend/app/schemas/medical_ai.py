from pydantic import BaseModel, Field

from app.schemas.conversation import MessageIn


class MedicalChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    mode: str | None = Field(default=None, max_length=40)
    messages: list[MessageIn] = Field(default_factory=list, max_length=20)


class MedicalChatResponse(BaseModel):
    content: str
