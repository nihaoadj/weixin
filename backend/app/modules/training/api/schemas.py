from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CASE_STAGES = ("history", "problem_representation", "differential", "tests", "management")
StageId = Literal["history", "problem_representation", "differential", "tests", "management"]
PRIORITIES = ("necessary", "optional", "avoid")
DIMENSION_SPECS = (
    ("information_gathering", "信息采集", 20, ("history",)),
    ("problem_representation", "问题表征", 15, ("problem_representation",)),
    ("differential_diagnosis", "鉴别诊断", 20, ("differential",)),
    ("evidence_reasoning", "证据推理", 15, ("differential",)),
    ("test_selection", "检查合理性", 15, ("tests",)),
    ("management_safety", "处置与安全意识", 15, ("management",)),
)
DIMENSIONS = (
    "information_gathering",
    "problem_representation",
    "differential_diagnosis",
    "evidence_reasoning",
    "test_selection",
    "management_safety",
)


class PracticeBlueprint(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    dimension_id: str
    stage_id: str
    learner_level: str = Field(min_length=1, max_length=40)
    public_instruction: str = Field(min_length=1, max_length=1000)
    allowed_variants: list[str] = Field(default_factory=list, max_length=12)
    fixed_facts: list[str] = Field(default_factory=list, max_length=20)
    fallback_prompt: str = Field(min_length=1, max_length=1000)
    reinforcement_prompt: str | None = Field(default=None, min_length=1, max_length=1000)
    reinforcement_variant_code: str | None = Field(default=None, min_length=1, max_length=160)
    answer_schema: Literal["short_text", "evidence_grid", "decision_cards"]
    criteria: list[dict] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_dimension(self) -> "PracticeBlueprint":
        if self.dimension_id not in DIMENSIONS:
            raise ValueError("invalid capability dimension")
        if sum(float(item.get("weight", 0)) for item in self.criteria) != 100:
            raise ValueError("blueprint criteria weights must total 100")
        return self


class TrimmedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class CaseOpening(TrimmedModel):
    setting: str = Field(min_length=1, max_length=200)
    patient_intro: str = Field(min_length=1, max_length=1000)
    chief_complaint: str = Field(min_length=1, max_length=300)


class CaseFact(TrimmedModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    category: Literal["history", "exam", "test"]
    label: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=1000)
    triggers: list[str] = Field(min_length=1, max_length=12)
    reveal_stage: StageId


class ReferenceDifferential(TrimmedModel):
    diagnosis: str = Field(min_length=1, max_length=300)
    supporting_fact_ids: list[str] = Field(default_factory=list, max_length=12)
    opposing_fact_ids: list[str] = Field(default_factory=list, max_length=12)
    priority: int = Field(ge=1, le=12)


class ReferenceTest(TrimmedModel):
    name: str = Field(min_length=1, max_length=300)
    purpose: str = Field(min_length=1, max_length=1000)
    priority: Literal["necessary", "optional", "avoid"]
    result_fact_id: str | None = Field(default=None, max_length=80)


class ReferenceManagement(TrimmedModel):
    action: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=1000)
    priority: int = Field(ge=1, le=12)
    safety_critical: bool = False


class ReferenceReasoning(TrimmedModel):
    problem_representation: str = Field(min_length=1, max_length=1000)
    differentials: list[ReferenceDifferential] = Field(min_length=2, max_length=12)
    tests: list[ReferenceTest] = Field(min_length=1, max_length=12)
    management: list[ReferenceManagement] = Field(min_length=1, max_length=12)


class CaseDefinition(TrimmedModel):
    schema_version: Literal[1, 2, 3] = 1
    opening: CaseOpening
    stage_instructions: dict[StageId, str]
    facts: list[CaseFact] = Field(min_length=1, max_length=60)
    reference_reasoning: ReferenceReasoning
    practice_blueprints: list[PracticeBlueprint] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def validate_references(self) -> "CaseDefinition":
        if set(self.stage_instructions) != set(CASE_STAGES):
            raise ValueError("stage_instructions must contain all five stages")
        fact_ids = {fact.id for fact in self.facts}
        if len(fact_ids) != len(self.facts):
            raise ValueError("fact ids must be unique")
        references = [
            *[
                item
                for differential in self.reference_reasoning.differentials
                for item in differential.supporting_fact_ids
            ],
            *[
                item
                for differential in self.reference_reasoning.differentials
                for item in differential.opposing_fact_ids
            ],
            *[test.result_fact_id for test in self.reference_reasoning.tests if test.result_fact_id],
        ]
        if not set(references).issubset(fact_ids):
            raise ValueError("reference reasoning points to an unknown fact")
        return self


class RubricCriterion(TrimmedModel):
    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=200)
    keywords: list[str] = Field(min_length=1, max_length=12)
    feedback: str = Field(min_length=1, max_length=1000)
    critical: bool = False


class CaseRubricDimension(TrimmedModel):
    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=100)
    weight: int = Field(ge=0, le=100)
    stage_ids: list[StageId] = Field(min_length=1, max_length=5)
    criteria: list[RubricCriterion] = Field(min_length=1, max_length=12)


class CaseRubric(TrimmedModel):
    dimensions: list[CaseRubricDimension] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def fixed_dimensions(self) -> "CaseRubric":
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


class HistoryAnswer(TrimmedModel):
    stage_id: Literal["history"] = "history"
    summary: str = Field(min_length=1, max_length=1000)
    key_findings: list[str] = Field(default_factory=list, max_length=12)


class ProblemRepresentationAnswer(TrimmedModel):
    stage_id: Literal["problem_representation"] = "problem_representation"
    summary: str = Field(min_length=1, max_length=1000)


class DifferentialItem(TrimmedModel):
    diagnosis: str = Field(min_length=1, max_length=300)
    supporting_evidence: list[str] = Field(default_factory=list, max_length=12)
    opposing_evidence: list[str] = Field(default_factory=list, max_length=12)


class DifferentialAnswer(TrimmedModel):
    stage_id: Literal["differential"] = "differential"
    items: list[DifferentialItem] = Field(min_length=2, max_length=12)


class TestItem(TrimmedModel):
    test_name: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=1000)
    priority: Literal["necessary", "optional", "avoid"]


class TestsAnswer(TrimmedModel):
    stage_id: Literal["tests"] = "tests"
    items: list[TestItem] = Field(min_length=1, max_length=12)


class ManagementItem(TrimmedModel):
    action: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=1000)


class ManagementAnswer(TrimmedModel):
    stage_id: Literal["management"] = "management"
    items: list[ManagementItem] = Field(min_length=1, max_length=12)
    safety_considerations: list[str] = Field(default_factory=list, max_length=12)


StageAnswer = Annotated[
    HistoryAnswer | ProblemRepresentationAnswer | DifferentialAnswer | TestsAnswer | ManagementAnswer,
    Field(discriminator="stage_id"),
]


class CaseDraftGenerateRequest(TrimmedModel):
    topic: str = Field(min_length=1, max_length=100)
    learner_level: str = Field(min_length=1, max_length=80)
    learning_objectives: list[str] = Field(min_length=1, max_length=5)


class CaseDraftGenerateResponse(TrimmedModel):
    title: str
    description: str = ""
    specialty: str
    difficulty: str = "basic"
    estimated_minutes: int = 10
    case_definition: CaseDefinition
    rubric: CaseRubric
    generation_mode: Literal["model", "fallback"]
    safety_notice: str


class CaseAttemptCreate(TrimmedModel):
    retry_of_id: int | None = Field(default=None, gt=0)


class PatientMessageCreate(TrimmedModel):
    content: str = Field(min_length=1, max_length=1000)


class PatientMessageRead(TrimmedModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    response_mode: Literal["model", "fallback", "safety"] | None = None
    generation_mode: Literal["model", "fallback"] | None = None


class StageSubmissionCreate(TrimmedModel):
    answer: StageAnswer


class StageSubmissionRead(TrimmedModel):
    id: int
    stage_id: StageId
    answer: dict
    feedback: str
    inherited_from_id: int | None = None
    created_at: datetime


class CaseAttemptRead(TrimmedModel):
    id: int
    problem_id: int
    problem_version: int
    status: str
    current_stage: str
    focus_stage: str | None = None
    retry_of_id: int | None = None
    opening: CaseOpening
    messages: list[PatientMessageRead] = Field(default_factory=list)
    submissions: list[StageSubmissionRead] = Field(default_factory=list)
    assessment_ready: bool = False
    started_at: datetime


class CaseAttemptSummaryRead(TrimmedModel):
    id: int
    problem_id: int
    status: str
    current_stage: str
    focus_stage: str | None = None
    total_score: float | None = None
    started_at: datetime


class AssessmentDimensionRead(TrimmedModel):
    dimension_id: str
    label: str
    score: float
    weighted_score: float
    evidence: list[str] = Field(default_factory=list)
    feedback: str
    next_step: str


class AssessmentComparisonItem(TrimmedModel):
    dimension_id: str
    previous_score: float
    current_score: float
    delta: float


class AssessmentComparisonRead(TrimmedModel):
    total_delta: float
    dimensions: list[AssessmentComparisonItem] = Field(default_factory=list)


class CaseAssessmentRead(TrimmedModel):
    attempt_id: int
    total_score: float
    dimensions: list[AssessmentDimensionRead]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    summary: str
    focus_stage: StageId
    model_name: str
    prompt_version: str
    fallback_used: bool
    comparison: AssessmentComparisonRead | None = None
