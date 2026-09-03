"""Validated provider-output schemas owned by the training AI adapter."""

from pydantic import BaseModel, ConfigDict, Field


class ProviderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class PatientReplyModel(ProviderOutput):
    reply: str = Field(min_length=1, max_length=2000)


class AIAssessmentDimension(ProviderOutput):
    dimension_id: str
    score: float = Field(ge=0, le=100)
    evidence: list[str] = Field(default_factory=list, max_length=3)
    feedback: str = Field(min_length=1, max_length=1000)
    next_step: str = Field(min_length=1, max_length=1000)


class AIAssessmentResponse(ProviderOutput):
    dimensions: list[AIAssessmentDimension] = Field(min_length=6, max_length=6)
