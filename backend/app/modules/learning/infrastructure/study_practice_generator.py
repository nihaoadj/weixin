from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.pbl.public import PracticeJsonPort


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PracticeQuestion(Strict):
    point_code: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=1000)
    options: list[str] = Field(min_length=2, max_length=4)
    reference_option: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=1, max_length=1200)

    def valid_answer(self):
        if self.reference_option >= len(self.options):
            raise ValueError("reference option outside options")
        return self


class PracticePayload(Strict):
    schema_version: Literal[1]
    questions: list[PracticeQuestion] = Field(min_length=1, max_length=3)
    safety_status: Literal["educational", "needs_human_help"]


class StudyPracticeGenerator:
    def __init__(self, transport: PracticeJsonPort):
        self._transport = transport

    def generate(self, context: dict) -> list[dict]:
        raw = self._transport.practice_json(context, PracticePayload.model_json_schema())
        value = PracticePayload.model_validate_json(raw)
        if value.safety_status != "educational":
            raise ValueError("practice safety diversion")
        point = context["point_code"]
        result = []
        for question in value.questions:
            question.valid_answer()
            if question.point_code != point:
                raise ValueError("practice point mismatch")
            result.append(question.model_dump())
        return result
