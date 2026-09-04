"""Content-owned validation contract for structured case-draft providers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.content.domain.templates import SAFETY_NOTICE

CASE_STAGES = ("history", "problem_representation", "differential", "tests", "management")
DIMENSION_SPECS = (
    ("information_gathering", "信息采集", 20, ("history",)),
    ("problem_representation", "问题表征", 15, ("problem_representation",)),
    ("differential_diagnosis", "鉴别诊断", 20, ("differential",)),
    ("evidence_reasoning", "证据推理", 15, ("differential",)),
    ("test_selection", "检查合理性", 15, ("tests",)),
    ("management_safety", "处置与安全意识", 15, ("management",)),
)
DIMENSIONS = {item[0] for item in DIMENSION_SPECS}
StageId = Literal["history", "problem_representation", "differential", "tests", "management"]
Priority = Literal["necessary", "optional", "avoid"]


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class CaseOpening(ProviderModel):
    setting: str = Field(min_length=1, max_length=200)
    patient_intro: str = Field(min_length=1, max_length=1000)
    chief_complaint: str = Field(min_length=1, max_length=300)


class CaseFact(ProviderModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    category: Literal["history", "exam", "test"]
    label: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=1000)
    triggers: list[str] = Field(min_length=1, max_length=12)
    reveal_stage: StageId


class ReferenceDifferential(ProviderModel):
    diagnosis: str = Field(min_length=1, max_length=300)
    supporting_fact_ids: list[str] = Field(default_factory=list, max_length=12)
    opposing_fact_ids: list[str] = Field(default_factory=list, max_length=12)
    priority: int = Field(ge=1, le=12)


class ReferenceTest(ProviderModel):
    name: str = Field(min_length=1, max_length=300)
    purpose: str = Field(min_length=1, max_length=1000)
    priority: Priority
    result_fact_id: str | None = Field(default=None, max_length=80)


class ReferenceManagement(ProviderModel):
    action: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=1000)
    priority: int = Field(ge=1, le=12)
    safety_critical: bool = False


class ReferenceReasoning(ProviderModel):
    problem_representation: str = Field(min_length=1, max_length=1000)
    differentials: list[ReferenceDifferential] = Field(min_length=2, max_length=12)
    tests: list[ReferenceTest] = Field(min_length=1, max_length=12)
    management: list[ReferenceManagement] = Field(min_length=1, max_length=12)


class PracticeCriterion(ProviderModel):
    id: str = Field(min_length=1, max_length=80)
    weight: int = Field(ge=0, le=100)
    keywords: list[str] = Field(min_length=1, max_length=12)
    feedback: str = Field(min_length=1, max_length=1000)
    critical: bool = False


class PracticeBlueprint(ProviderModel):
    id: str = Field(min_length=1, max_length=100)
    dimension_id: str
    stage_id: StageId
    learner_level: str = Field(min_length=1, max_length=40)
    public_instruction: str = Field(min_length=1, max_length=1000)
    allowed_variants: list[str] = Field(default_factory=list, max_length=12)
    fixed_facts: list[str] = Field(default_factory=list, max_length=20)
    fallback_prompt: str = Field(min_length=1, max_length=1000)
    reinforcement_prompt: str | None = Field(default=None, min_length=1, max_length=1000)
    reinforcement_variant_code: str | None = Field(default=None, min_length=1, max_length=160)
    answer_schema: Literal["short_text", "evidence_grid", "decision_cards"]
    criteria: list[PracticeCriterion] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_dimension(self) -> PracticeBlueprint:
        if self.dimension_id not in DIMENSIONS:
            raise ValueError("invalid capability dimension")
        if sum(item.weight for item in self.criteria) != 100:
            raise ValueError("blueprint criteria weights must total 100")
        return self


class CaseDefinition(ProviderModel):
    schema_version: Literal[1, 2, 3] = 1
    opening: CaseOpening
    stage_instructions: dict[StageId, str]
    facts: list[CaseFact] = Field(min_length=1, max_length=60)
    reference_reasoning: ReferenceReasoning
    practice_blueprints: list[PracticeBlueprint] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def validate_references(self) -> CaseDefinition:
        if set(self.stage_instructions) != set(CASE_STAGES):
            raise ValueError("stage_instructions must contain all five stages")
        fact_ids = {fact.id for fact in self.facts}
        if len(fact_ids) != len(self.facts):
            raise ValueError("fact ids must be unique")
        references = [
            *[
                fact_id
                for differential in self.reference_reasoning.differentials
                for fact_id in (*differential.supporting_fact_ids, *differential.opposing_fact_ids)
            ],
            *[test.result_fact_id for test in self.reference_reasoning.tests if test.result_fact_id],
        ]
        if not set(references).issubset(fact_ids):
            raise ValueError("reference reasoning points to an unknown fact")
        return self


class RubricCriterion(ProviderModel):
    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=200)
    keywords: list[str] = Field(min_length=1, max_length=12)
    feedback: str = Field(min_length=1, max_length=1000)
    critical: bool = False


class CaseRubricDimension(ProviderModel):
    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=100)
    weight: int = Field(ge=0, le=100)
    stage_ids: list[StageId] = Field(min_length=1, max_length=5)
    criteria: list[RubricCriterion] = Field(min_length=1, max_length=12)


class CaseRubric(ProviderModel):
    dimensions: list[CaseRubricDimension] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def fixed_dimensions(self) -> CaseRubric:
        expected = {item[0]: item for item in DIMENSION_SPECS}
        actual = {dimension.id: dimension for dimension in self.dimensions}
        if set(actual) != set(expected) or sum(item.weight for item in self.dimensions) != 100:
            raise ValueError("rubric must contain the six fixed dimensions with total weight 100")
        for key, (_, label, weight, stages) in expected.items():
            dimension = actual[key]
            if dimension.weight != weight or tuple(dimension.stage_ids) != stages:
                raise ValueError(f"rubric dimension {key} has fixed weight and stages")
            if not dimension.label.strip() or not label:
                raise ValueError("rubric label required")
        return self


class CaseDraftModel(ProviderModel):
    """Provider payload; transport metadata is owned by the application."""

    title: str
    description: str = ""
    specialty: str
    difficulty: str = "basic"
    estimated_minutes: int = 10
    case_definition: CaseDefinition
    rubric: CaseRubric
    generation_mode: Literal["model", "fallback"] = "model"
    safety_notice: str = SAFETY_NOTICE


__all__ = ["CaseDraftModel"]
