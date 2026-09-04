"""Versioned, bounded model output. Context references are validated by the use case."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

DIMENSIONS = (
    "information_gathering",
    "problem_representation",
    "differential_diagnosis",
    "evidence_reasoning",
    "test_selection",
    "management_safety",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceFinding(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=500)
    evidence_message_ids: list[str] = Field(min_length=1, max_length=10)
    evidence_summary: str = Field(min_length=1, max_length=500)


class KnowledgeGap(EvidenceFinding):
    point_code: str = Field(min_length=1, max_length=120)
    confidence: Literal["low", "medium", "high"]


class ReasoningIssue(EvidenceFinding):
    dimension_id: Literal[
        "information_gathering",
        "problem_representation",
        "differential_diagnosis",
        "evidence_reasoning",
        "test_selection",
        "management_safety",
    ]
    issue_type: Literal["missing_evidence", "premature_conclusion", "causal_confusion", "other"]
    improvement: str = Field(min_length=1, max_length=500)


class RecommendedQuestion(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=2000)
    objective: str = Field(min_length=1, max_length=500)
    linked_findings: list[str] = Field(min_length=1, max_length=10)


class PhaseAssessment(StrictModel):
    phase: Literal["problem_framing", "hypothesis", "evidence", "synthesis"]
    decision: Literal["continue", "advance", "complete"]
    evidence_message_ids: list[str] = Field(min_length=1, max_length=10)
    evidence_summary: str = Field(min_length=1, max_length=500)
    missing_elements: list[str] = Field(default_factory=list, max_length=10)


class ProviderPayload(StrictModel):
    schema_version: Literal[3]
    assistant_reply: str = Field(min_length=1, max_length=4000)
    diagnostic_status: Literal["probing", "ready", "insufficient_evidence", "unavailable"]
    follow_up_question: str | None = Field(default=None, max_length=1000)
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list, max_length=10)
    reasoning_issues: list[ReasoningIssue] = Field(default_factory=list, max_length=10)
    recommended_questions: list[RecommendedQuestion] = Field(default_factory=list, max_length=5)
    safety_notice: str = Field(min_length=1, max_length=500)
    safety_status: Literal["educational", "needs_human_help"]
    phase_assessment: PhaseAssessment

    @model_validator(mode="after")
    def consistent_findings(self):
        findings = [*self.knowledge_gaps, *self.reasoning_issues]
        ids = {item.id for item in findings}
        if len(ids) != len(findings):
            raise PydanticCustomError("duplicate_finding_id", "duplicate finding id")
        if self.diagnostic_status == "ready" and (not findings or not self.recommended_questions):
            raise PydanticCustomError("ready_requires_findings_and_questions", "ready requires findings and questions")
        if self.diagnostic_status != "ready" and (findings or self.recommended_questions):
            raise PydanticCustomError(
                "unconfirmed_output_contains_findings", "unconfirmed output cannot contain findings"
            )
        if self.diagnostic_status == "probing" and not self.follow_up_question:
            raise PydanticCustomError("probing_requires_question", "probing requires a question")
        if self.safety_status == "needs_human_help" and self.diagnostic_status == "ready":
            raise PydanticCustomError("safety_cannot_diagnose", "safety diversion cannot diagnose")
        if self.diagnostic_status == "ready" and (
            self.phase_assessment.phase != "synthesis" or self.phase_assessment.decision != "complete"
        ):
            raise PydanticCustomError("ready_requires_synthesis", "ready requires synthesis completion")
        if self.phase_assessment.decision == "complete" and self.diagnostic_status != "ready":
            raise PydanticCustomError("complete_requires_ready", "phase completion requires ready diagnosis")
        if self.phase_assessment.decision != "complete" and self.diagnostic_status == "ready":
            raise PydanticCustomError("early_ready", "ready is only valid when completing synthesis")
        if any(not set(item.linked_findings).issubset(ids) for item in self.recommended_questions):
            raise PydanticCustomError("invalid_finding_reference", "invalid finding reference")
        return self
