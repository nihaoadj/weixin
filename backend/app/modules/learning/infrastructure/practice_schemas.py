"""Validated provider-output schema owned by the learning generator adapter."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PracticeGeneratedDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    title: str = Field(min_length=1, max_length=160)
    context: str = Field(min_length=1, max_length=1200)
    instruction: str = Field(min_length=1, max_length=1200)
    answer_schema: Literal["short_text", "evidence_grid", "decision_cards"]
    display_hints: list[str] = Field(default_factory=list, max_length=6)
