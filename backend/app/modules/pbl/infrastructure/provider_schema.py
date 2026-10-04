"""Versioned, bounded model output. Context references are validated by the use case."""

from typing import Annotated, Literal

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


class RecommendedKnowledgeCard(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    recall_prompt: str = Field(min_length=1, max_length=1000)
    explanation: str = Field(min_length=1, max_length=2000)
    point_code: str = Field(min_length=1, max_length=120)
    linked_findings: list[str] = Field(min_length=1, max_length=10)


class PhaseAssessment(StrictModel):
    phase: Literal["problem_framing", "hypothesis", "evidence", "synthesis"]
    decision: Literal["continue", "advance", "complete"]
    evidence_message_ids: list[str] = Field(min_length=1, max_length=10)
    evidence_summary: str = Field(min_length=1, max_length=500)
    missing_elements: list[str] = Field(default_factory=list, max_length=10)


class LearningResponse(StrictModel):
    opening: str = Field(min_length=1, max_length=1000)
    key_points: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(min_length=1, max_length=3)
    next_step: str = Field(min_length=1, max_length=1000)


class ProviderPayload(StrictModel):
    schema_version: Literal[6]
    interaction_style: Literal["guided", "direct"]
    learning_response: LearningResponse
    diagnostic_status: Literal["probing", "ready", "insufficient_evidence", "unavailable"]
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list, max_length=10)
    reasoning_issues: list[ReasoningIssue] = Field(default_factory=list, max_length=10)
    recommended_questions: list[RecommendedQuestion] = Field(default_factory=list, max_length=5)
    recommended_knowledge_cards: list[RecommendedKnowledgeCard] = Field(default_factory=list, max_length=3)
    safety_notice: str = Field(min_length=1, max_length=500)
    safety_status: Literal["educational", "needs_human_help"]
    phase_assessment: PhaseAssessment

    @model_validator(mode="after")
    def consistent_findings(self):
        findings = [*self.knowledge_gaps, *self.reasoning_issues]
        ids = {item.id for item in findings}
        if len(ids) != len(findings):
            raise PydanticCustomError("duplicate_finding_id", "duplicate finding id")
        if self.diagnostic_status == "ready" and (
            not findings or not self.recommended_questions or not self.recommended_knowledge_cards
        ):
            raise PydanticCustomError(
                "ready_requires_findings_questions_and_cards",
                "ready requires findings, questions and knowledge cards",
            )
        if self.diagnostic_status != "ready" and (
            findings or self.recommended_questions or self.recommended_knowledge_cards
        ):
            raise PydanticCustomError(
                "unconfirmed_output_contains_findings", "unconfirmed output cannot contain findings"
            )
        if self.diagnostic_status == "probing" and not self.learning_response.next_step:
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
        if any(not set(item.linked_findings).issubset(ids) for item in self.recommended_knowledge_cards):
            raise PydanticCustomError("invalid_card_finding_reference", "invalid card finding reference")
        return self


class CandidateResourceRef(StrictModel):
    kind: Literal["knowledge_card", "reasoning_blueprint", "case"]
    id: int = Field(gt=0)
    version: int = Field(gt=0)
    digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class CandidateVariant(StrictModel):
    cycle_number: Literal[1, 2]
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=2000)
    objective: str = Field(min_length=1, max_length=500)
    options: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=list, max_length=6)
    answer: int | None = Field(default=None, strict=True, ge=0)
    explanation: str | None = Field(default=None, max_length=2000)
    resource_ref: CandidateResourceRef | None = None

    @model_validator(mode="after")
    def distinct_options(self):
        if len(set(self.options)) != len(self.options):
            raise PydanticCustomError("duplicate_candidate_option", "choice options must be distinct")
        return self


class CandidateTask(StrictModel):
    candidate_key: str = Field(min_length=1, max_length=100)
    purpose: Literal["remediation", "goal_verification"]
    task_type: Literal["knowledge_review", "retest", "micro_drill", "discussion", "focused_retry"]
    point_codes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=3)
    dimension_ids: list[
        Literal[
            "information_gathering",
            "problem_representation",
            "differential_diagnosis",
            "evidence_reasoning",
            "test_selection",
            "management_safety",
        ]
    ] = Field(default_factory=list, max_length=6)
    linked_findings: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=10
    )
    variants: list[CandidateVariant] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def valid_pair(self):
        if len(set(self.point_codes)) != len(self.point_codes) or len(set(self.dimension_ids)) != len(
            self.dimension_ids
        ):
            raise PydanticCustomError("duplicate_candidate_target", "candidate targets must be unique")
        if {variant.cycle_number for variant in self.variants} != {1, 2}:
            raise PydanticCustomError("missing_candidate_variant", "both cycle variants are required")
        for variant in self.variants:
            if self.task_type in {"knowledge_review", "retest"}:
                if not 2 <= len(variant.options) <= 6 or variant.answer is None:
                    raise PydanticCustomError("invalid_choice_candidate", "choice tasks need options and answer")
                if not 0 <= variant.answer < len(variant.options) or not variant.explanation:
                    raise PydanticCustomError("invalid_choice_answer", "choice answer and explanation are required")
            elif variant.options or variant.answer is not None:
                raise PydanticCustomError("unexpected_choice_answer", "non-choice tasks cannot contain a choice answer")
            if self.task_type in {"micro_drill", "focused_retry"} and variant.resource_ref is None:
                raise PydanticCustomError(
                    "missing_candidate_resource", "scored tasks need a reviewed resource reference"
                )
            if self.task_type == "discussion" and variant.resource_ref is not None:
                raise PydanticCustomError(
                    "discussion_has_scoring_resource", "discussion cannot carry a scoring resource"
                )
        if self.task_type == "micro_drill" and not self.dimension_ids:
            raise PydanticCustomError("missing_reasoning_dimension", "reasoning task needs a dimension")
        return self


class ProviderPayloadV7(StrictModel):
    schema_version: Literal[7]
    interaction_style: Literal["guided", "direct"]
    learning_response: LearningResponse
    diagnostic_status: Literal["probing", "ready", "insufficient_evidence", "unavailable"]
    diagnosis_outcome: Literal["identified_gaps", "no_clear_gaps"] | None = None
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list, max_length=10)
    reasoning_issues: list[ReasoningIssue] = Field(default_factory=list, max_length=10)
    candidate_tasks: list[CandidateTask] = Field(default_factory=list, max_length=30)
    recommended_knowledge_cards: list[RecommendedKnowledgeCard] = Field(default_factory=list, max_length=3)
    safety_notice: str = Field(min_length=1, max_length=500)
    safety_status: Literal["educational", "needs_human_help"]
    phase_assessment: PhaseAssessment

    @model_validator(mode="after")
    def consistent_diagnosis(self):
        findings = [*self.knowledge_gaps, *self.reasoning_issues]
        ids = {item.id for item in findings}
        if len(ids) != len(findings):
            raise PydanticCustomError("duplicate_finding_id", "duplicate finding id")
        if len({task.candidate_key for task in self.candidate_tasks}) != len(self.candidate_tasks):
            raise PydanticCustomError("duplicate_candidate_key", "duplicate candidate key")
        if self.diagnostic_status == "ready":
            if self.diagnosis_outcome is None:
                raise PydanticCustomError("missing_diagnosis_outcome", "ready diagnosis needs an outcome")
            if self.phase_assessment.phase != "synthesis" or self.phase_assessment.decision != "complete":
                raise PydanticCustomError("ready_requires_synthesis", "ready diagnosis needs synthesis completion")
            if self.diagnosis_outcome == "identified_gaps" and not findings:
                raise PydanticCustomError("missing_identified_finding", "identified gaps need evidence-backed findings")
            if self.diagnosis_outcome == "no_clear_gaps" and (findings or self.recommended_knowledge_cards):
                raise PydanticCustomError("false_no_clear_gaps", "no clear gaps cannot contain findings or cards")
        elif self.diagnosis_outcome is not None or findings or self.candidate_tasks or self.recommended_knowledge_cards:
            raise PydanticCustomError(
                "unconfirmed_diagnosis_content", "non-ready result cannot contain confirmed content"
            )
        if self.phase_assessment.decision == "complete" and self.diagnostic_status != "ready":
            raise PydanticCustomError("complete_requires_ready", "phase completion requires ready diagnosis")
        if self.safety_status == "needs_human_help" and self.diagnostic_status == "ready":
            raise PydanticCustomError("safety_cannot_diagnose", "safety diversion cannot diagnose")
        if any(not set(task.linked_findings).issubset(ids) for task in self.candidate_tasks):
            raise PydanticCustomError("invalid_candidate_finding", "candidate refers to an unknown finding")
        if any(task.purpose == "remediation" and not task.linked_findings for task in self.candidate_tasks):
            raise PydanticCustomError("unlinked_remediation", "remediation needs an identified finding")
        if self.diagnosis_outcome == "no_clear_gaps" and any(
            task.purpose != "goal_verification" for task in self.candidate_tasks
        ):
            raise PydanticCustomError("false_remediation", "no clear gaps cannot produce remediation")
        if any(not set(card.linked_findings).issubset(ids) for card in self.recommended_knowledge_cards):
            raise PydanticCustomError("invalid_card_finding_reference", "card refers to an unknown finding")
        return self


class ProviderPayloadV8(StrictModel):
    """Single-round PBL diagnostic. Follow-up learning tasks are separate jobs."""

    schema_version: Literal[8]
    interaction_style: Literal["guided", "direct"]
    learning_response: LearningResponse
    diagnostic_status: Literal["probing", "ready", "insufficient_evidence", "unavailable"]
    diagnosis_outcome: Literal["identified_gaps", "no_clear_gaps"] | None = None
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list, max_length=10)
    reasoning_issues: list[ReasoningIssue] = Field(default_factory=list, max_length=10)
    safety_notice: str = Field(min_length=1, max_length=500)
    safety_status: Literal["educational", "needs_human_help"]
    phase_assessment: PhaseAssessment

    @model_validator(mode="after")
    def consistent_diagnosis(self):
        findings = [*self.knowledge_gaps, *self.reasoning_issues]
        ids = {item.id for item in findings}
        if len(ids) != len(findings):
            raise PydanticCustomError("duplicate_finding_id", "duplicate finding id")
        if self.diagnostic_status == "ready":
            if self.diagnosis_outcome is None:
                raise PydanticCustomError("missing_diagnosis_outcome", "ready diagnosis needs an outcome")
            if self.phase_assessment.phase != "synthesis" or self.phase_assessment.decision != "complete":
                raise PydanticCustomError("ready_requires_synthesis", "ready diagnosis needs synthesis completion")
            if self.diagnosis_outcome == "identified_gaps" and not findings:
                raise PydanticCustomError("missing_identified_finding", "identified gaps need evidence-backed findings")
            if self.diagnosis_outcome == "no_clear_gaps" and findings:
                raise PydanticCustomError("false_no_clear_gaps", "no clear gaps cannot contain findings")
        elif self.diagnosis_outcome is not None or findings:
            raise PydanticCustomError(
                "unconfirmed_diagnosis_content", "non-ready result cannot contain confirmed findings"
            )
        if self.phase_assessment.decision == "complete" and self.diagnostic_status != "ready":
            raise PydanticCustomError("complete_requires_ready", "phase completion requires ready diagnosis")
        if self.safety_status == "needs_human_help" and self.diagnostic_status == "ready":
            raise PydanticCustomError("safety_cannot_diagnose", "safety diversion cannot diagnose")
        return self


class ProviderTaskFinding(StrictModel):
    finding_id: str = Field(min_length=1, max_length=80)
    kind: Literal["knowledge_gap", "reasoning_issue"]
    target_code: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    evidence_summary: str = Field(min_length=1, max_length=500)


class AllowedGoalPoint(StrictModel):
    code: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)


class AllowedPublicSource(StrictModel):
    source_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    institution: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=1, max_length=1000)
    summary: str = Field(min_length=1, max_length=1000)


class LearningRouteInput(StrictModel):
    source_kind: Literal["classroom", "autonomous"]
    findings: list[ProviderTaskFinding] = Field(default_factory=list, max_length=20)
    goal_points: list[AllowedGoalPoint] = Field(min_length=1, max_length=3)
    allowed_sources: list[AllowedPublicSource] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_input_references(self):
        if len({item.finding_id for item in self.findings}) != len(self.findings):
            raise PydanticCustomError("duplicate_finding_id", "finding ids must be unique")
        if len({item.code for item in self.goal_points}) != len(self.goal_points):
            raise PydanticCustomError("duplicate_goal_code", "goal codes must be unique")
        if len({item.source_id for item in self.allowed_sources}) != len(self.allowed_sources):
            raise PydanticCustomError("duplicate_source_id", "source ids must be unique")
        return self


class RouteReadingStep(StrictModel):
    stable_key: str = Field(min_length=1, max_length=80)
    target_point_codes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=3)
    linked_findings: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=20
    )
    source_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=10)
    ai_guide: str = Field(min_length=1, max_length=1000)
    explanation_segments: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(min_length=1, max_length=6)
    learning_points: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def unique_references(self):
        if any(
            len(values) != len(set(values))
            for values in (self.target_point_codes, self.linked_findings, self.source_ids)
        ):
            raise PydanticCustomError("duplicate_reading_reference", "reading step references must be unique")
        return self


class SyntheticCaseFact(StrictModel):
    fact_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=1000)


class SyntheticCaseGoal(StrictModel):
    goal_id: str = Field(min_length=1, max_length=80)
    objective: str = Field(min_length=1, max_length=500)
    completion_requirements: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1, max_length=3
    )
    guidance_prompts: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(min_length=1, max_length=3)


class SyntheticCasePhase(StrictModel):
    phase: Literal["pathology_recognition", "mechanism_explanation", "evidence_judgment"]
    goals: list[SyntheticCaseGoal] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_goals(self):
        if len({goal.goal_id for goal in self.goals}) != len(self.goals):
            raise PydanticCustomError("duplicate_case_goal", "case phase goal ids must be unique")
        return self


class SyntheticCase(StrictModel):
    stable_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    public_scenario: str = Field(min_length=1, max_length=3000)
    target_point_codes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=3)
    case_facts: list[SyntheticCaseFact] = Field(min_length=1, max_length=10)
    phases: list[SyntheticCasePhase] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def unique_case_references(self):
        if len(set(self.target_point_codes)) != len(self.target_point_codes):
            raise PydanticCustomError("duplicate_case_target", "case targets must be unique")
        if len({fact.fact_id for fact in self.case_facts}) != len(self.case_facts):
            raise PydanticCustomError("duplicate_case_fact", "case fact ids must be unique")
        return self


class LearningRoutePayload(StrictModel):
    version: Literal[1]
    title: str = Field(min_length=1, max_length=200)
    goal_point_codes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=3)
    learning_rationale: str = Field(min_length=1, max_length=2000)
    reading_steps: list[RouteReadingStep] = Field(min_length=1, max_length=3)
    synthetic_case: SyntheticCase
    safety_status: Literal["educational", "needs_human_help"]

    @model_validator(mode="after")
    def route_references_are_closed(self):
        if len(set(self.goal_point_codes)) != len(self.goal_point_codes):
            raise PydanticCustomError("duplicate_route_goal", "route goals must be unique")
        keys = [step.stable_key for step in self.reading_steps] + [self.synthetic_case.stable_key]
        if len(set(keys)) != len(keys):
            raise PydanticCustomError("duplicate_route_key", "route stable keys must be unique")
        fact_ids = [fact.fact_id for fact in self.synthetic_case.case_facts]
        goal_ids = [goal.goal_id for phase in self.synthetic_case.phases for goal in phase.goals]
        if len(set(fact_ids)) != len(fact_ids) or len(set(goal_ids)) != len(goal_ids):
            raise PydanticCustomError("duplicate_case_key", "case facts and goals need unique keys")
        if [phase.phase for phase in self.synthetic_case.phases] != [
            "pathology_recognition",
            "mechanism_explanation",
            "evidence_judgment",
        ]:
            raise PydanticCustomError("invalid_case_phase_order", "case phases must follow the required order")
        return self


class FrozenRouteReading(StrictModel):
    stable_key: str = Field(min_length=1, max_length=80)
    target_point_codes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=3)
    source_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=10)
    learning_points: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def unique_references(self):
        if len(set(self.target_point_codes)) != len(self.target_point_codes) or len(set(self.source_ids)) != len(
            self.source_ids
        ):
            raise PydanticCustomError("duplicate_route_context_reference", "route context references must be unique")
        return self


class FrozenRouteContext(StrictModel):
    goal_point_codes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=3)
    reading_steps: list[FrozenRouteReading] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_references(self):
        if len(set(self.goal_point_codes)) != len(self.goal_point_codes):
            raise PydanticCustomError("duplicate_route_context_goal", "route context goals must be unique")
        if len({step.stable_key for step in self.reading_steps}) != len(self.reading_steps):
            raise PydanticCustomError("duplicate_route_context_step", "route context reading keys must be unique")
        return self


class FinalTestInput(StrictModel):
    source_kind: Literal["classroom", "autonomous"]
    findings: list[ProviderTaskFinding] = Field(default_factory=list, max_length=20)
    goal_points: list[AllowedGoalPoint] = Field(min_length=1, max_length=3)
    allowed_sources: list[AllowedPublicSource] = Field(min_length=1, max_length=30)
    route_context: FrozenRouteContext

    @model_validator(mode="after")
    def unique_input_references(self):
        if len({item.finding_id for item in self.findings}) != len(self.findings):
            raise PydanticCustomError("duplicate_finding_id", "finding ids must be unique")
        if len({item.code for item in self.goal_points}) != len(self.goal_points):
            raise PydanticCustomError("duplicate_goal_code", "goal codes must be unique")
        if len({item.source_id for item in self.allowed_sources}) != len(self.allowed_sources):
            raise PydanticCustomError("duplicate_source_id", "source ids must be unique")
        return self


class FinalTestQuestion(StrictModel):
    stable_key: str = Field(min_length=1, max_length=80)
    primary_point_code: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=2000)
    options: tuple[
        Annotated[str, Field(min_length=1, max_length=500)],
        Annotated[str, Field(min_length=1, max_length=500)],
        Annotated[str, Field(min_length=1, max_length=500)],
        Annotated[str, Field(min_length=1, max_length=500)],
    ]
    correct_option: int = Field(strict=True, ge=0, le=3)
    explanation: str = Field(min_length=1, max_length=2000)
    linked_findings: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=20
    )
    source_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def distinct_options(self):
        if len({option.strip().casefold() for option in self.options}) != 4:
            raise PydanticCustomError("duplicate_test_option", "test options must be distinct")
        return self


class FinalTestPayload(StrictModel):
    version: Literal[1]
    questions: list[FinalTestQuestion] = Field(min_length=1, max_length=9)
    safety_status: Literal["educational", "needs_human_help"]

    @model_validator(mode="after")
    def unique_questions(self):
        if len({item.stable_key for item in self.questions}) != len(self.questions):
            raise PydanticCustomError("duplicate_test_key", "question keys must be unique")
        normalized = {item.prompt.strip().casefold() for item in self.questions}
        if len(normalized) != len(self.questions):
            raise PydanticCustomError("duplicate_test_prompt", "question prompts must be unique")
        return self


class MixedFinalTestInput(FinalTestInput):
    goal_points: list[AllowedGoalPoint] = Field(min_length=1, max_length=1)


class MixedQuestionBase(StrictModel):
    stable_key: str = Field(min_length=1, max_length=80)
    primary_point_code: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(min_length=1, max_length=2000)
    linked_findings: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=20
    )
    source_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=10)


class MixedChoiceQuestion(MixedQuestionBase):
    question_type: Literal["single_choice", "multiple_choice"]
    options: tuple[
        Annotated[str, Field(min_length=1, max_length=500)],
        Annotated[str, Field(min_length=1, max_length=500)],
        Annotated[str, Field(min_length=1, max_length=500)],
        Annotated[str, Field(min_length=1, max_length=500)],
    ]
    correct_option: int | None = Field(default=None, ge=0, le=3)
    correct_options: list[Annotated[int, Field(strict=True, ge=0, le=3)]] | None = Field(
        default=None, min_length=2, max_length=3
    )

    @model_validator(mode="after")
    def valid_choice(self):
        if len({item.strip().casefold() for item in self.options}) != 4:
            raise PydanticCustomError("duplicate_test_option", "test options must be distinct")
        if self.question_type == "single_choice" and (self.correct_option is None or self.correct_options is not None):
            raise PydanticCustomError("invalid_single_answer", "single choice requires one answer")
        if self.question_type == "multiple_choice" and (
            self.correct_option is not None
            or self.correct_options is None
            or len(set(self.correct_options)) != len(self.correct_options)
        ):
            raise PydanticCustomError("invalid_multiple_answer", "multiple choice requires distinct answers")
        return self


class ShortAnswerCriterion(StrictModel):
    criterion_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    max_points: Literal[10]


class MixedShortQuestion(MixedQuestionBase):
    question_type: Literal["short_answer"]
    reference_answer: str = Field(min_length=1, max_length=2000)
    rubric: tuple[ShortAnswerCriterion, ShortAnswerCriterion, ShortAnswerCriterion]

    @model_validator(mode="after")
    def distinct_criteria(self):
        if len({item.criterion_id for item in self.rubric}) != 3:
            raise PydanticCustomError("duplicate_rubric_criterion", "rubric criteria must be distinct")
        return self


class MixedFinalTestPayload(StrictModel):
    version: Literal[2]
    questions: list[MixedChoiceQuestion | MixedShortQuestion] = Field(min_length=5, max_length=5)
    safety_status: Literal["educational", "needs_human_help"]

    @model_validator(mode="after")
    def valid_test(self):
        if [item.question_type for item in self.questions] != [
            "single_choice", "single_choice", "single_choice", "multiple_choice", "short_answer"
        ]:
            raise PydanticCustomError(
                "invalid_mixed_test", "mixed test must have three single, one multiple, one short"
            )
        if len({item.stable_key for item in self.questions}) != 5:
            raise PydanticCustomError("duplicate_test_key", "question keys must be unique")
        if len({item.prompt.strip().casefold() for item in self.questions}) != 5:
            raise PydanticCustomError("duplicate_test_prompt", "question prompts must be unique")
        return self


class ShortAnswerGradeInput(StrictModel):
    question_id: str = Field(min_length=1, max_length=80)
    question_prompt: str = Field(min_length=1, max_length=2000)
    reference_answer: str = Field(min_length=1, max_length=2000)
    rubric: tuple[ShortAnswerCriterion, ShortAnswerCriterion, ShortAnswerCriterion]
    student_answer: str = Field(min_length=1, max_length=2000)


class ShortAnswerCriterionResult(StrictModel):
    criterion_id: str = Field(min_length=1, max_length=80)
    earned_points: int = Field(strict=True, ge=0, le=10)
    evidence: str = Field(min_length=1, max_length=500)


class ShortAnswerGradePayload(StrictModel):
    version: Literal[1]
    question_id: str = Field(min_length=1, max_length=80)
    criterion_results: tuple[ShortAnswerCriterionResult, ShortAnswerCriterionResult, ShortAnswerCriterionResult]
    feedback: str = Field(min_length=1, max_length=1000)
    safety_status: Literal["educational", "needs_human_help"]


class TestTutorMessage(StrictModel):
    role: Literal["student", "assistant"]
    question_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=2000)


class TestTutorInput(StrictModel):
    current_question_id: str = Field(min_length=1, max_length=80)
    question_results: list[dict[str, object]] = Field(min_length=1, max_length=12)
    conversation_summary: str = Field(default="", max_length=4000)
    history: list[TestTutorMessage] = Field(default_factory=list, max_length=30)
    student_message: str = Field(min_length=1, max_length=2000)


class TestTutorPayload(StrictModel):
    version: Literal[1]
    current_question_id: str = Field(min_length=1, max_length=80)
    reply: str = Field(min_length=1, max_length=2000)
    updated_summary: str = Field(min_length=1, max_length=4000)
    safety_status: Literal["educational", "needs_human_help"]


CasePhase = Literal["pathology_recognition", "mechanism_explanation", "evidence_judgment", "summary_reflection"]


class RouteCaseHistoryItem(StrictModel):
    role: Literal["student", "assistant"]
    message_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)
    revision: int = Field(strict=True, ge=1)
    phase: CasePhase


class RouteCaseStudentMessage(StrictModel):
    message_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)


class RouteCaseGoal(StrictModel):
    goal_id: str = Field(min_length=1, max_length=80)
    objective: str = Field(min_length=1, max_length=500)
    completion_requirements: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1, max_length=10
    )


class RouteCaseTurnInput(StrictModel):
    phase: CasePhase
    phase_started_revision: int = Field(strict=True, ge=0)
    current_revision: int = Field(strict=True, ge=1)
    public_case_scenario: str = Field(min_length=1, max_length=3000)
    public_case_facts: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(min_length=1, max_length=10)
    phase_goals: list[RouteCaseGoal] = Field(min_length=1, max_length=3)
    current_student_message: RouteCaseStudentMessage
    history: list[RouteCaseHistoryItem] = Field(max_length=20)
    current_phase_evidence_message_ids: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        min_length=1, max_length=20
    )

    @model_validator(mode="after")
    def history_is_scoped_and_bounded(self):
        ids = [item.message_id for item in self.history]
        if len(set(ids)) != len(ids) or self.current_student_message.message_id in ids:
            raise PydanticCustomError("duplicate_case_message_id", "case message ids must be unique")
        if len(set(self.current_phase_evidence_message_ids)) != len(self.current_phase_evidence_message_ids):
            raise PydanticCustomError("duplicate_case_evidence_id", "evidence ids must be unique")
        if self.current_revision <= self.phase_started_revision:
            raise PydanticCustomError("invalid_case_revision", "current revision must follow phase start")
        if self.current_student_message.message_id not in self.current_phase_evidence_message_ids:
            raise PydanticCustomError("missing_current_case_evidence", "current student message must be legal evidence")
        if len({goal.goal_id for goal in self.phase_goals}) != len(self.phase_goals):
            raise PydanticCustomError("duplicate_current_case_goal", "current phase goal ids must be unique")
        return self


class RouteCaseGoalCheck(StrictModel):
    goal_id: str = Field(min_length=1, max_length=80)
    status: Literal["satisfied", "needs_more_evidence"]


class RouteCasePhaseAssessment(StrictModel):
    phase: CasePhase
    decision: Literal["stay", "advance", "complete"]
    goal_checks: list[RouteCaseGoalCheck] = Field(min_length=1, max_length=3)
    evidence_message_ids: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(min_length=1, max_length=20)
    missing_elements: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list, max_length=10
    )

    @model_validator(mode="after")
    def unique_references(self):
        if len({item.goal_id for item in self.goal_checks}) != len(self.goal_checks):
            raise PydanticCustomError("duplicate_goal_check", "goal checks must be unique")
        if len(set(self.evidence_message_ids)) != len(self.evidence_message_ids):
            raise PydanticCustomError("duplicate_case_evidence", "case evidence references must be unique")
        return self


class RouteCaseTurnPayload(StrictModel):
    version: Literal[1]
    learning_response: LearningResponse
    phase_assessment: RouteCasePhaseAssessment
    safety_status: Literal["educational", "needs_human_help"]
    safety_notice: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def safe_decision(self):
        if self.safety_status == "needs_human_help" and self.phase_assessment.decision != "stay":
            raise PydanticCustomError("safety_case_cannot_advance", "safety diversion cannot advance a case phase")
        return self


class ProviderTaskEnvelope(StrictModel):
    task_kind: Literal[
        "learning_route_generation", "final_test_generation", "mixed_final_test_generation",
        "short_answer_grading", "test_result_tutor", "route_case_turn"
    ]
    schema_version: Literal[1]
    request_id: str = Field(min_length=1, max_length=120)
    input: dict[str, object]


class ProviderTaskResultEnvelope(StrictModel):
    task_kind: Literal[
        "learning_route_generation", "final_test_generation", "mixed_final_test_generation",
        "short_answer_grading", "test_result_tutor", "route_case_turn"
    ]
    schema_version: Literal[1]
    request_id: str = Field(min_length=1, max_length=120)
    result: dict[str, object]


PROVIDER_TASK_INPUT_MODELS = {
    "learning_route_generation": LearningRouteInput,
    "final_test_generation": FinalTestInput,
    "mixed_final_test_generation": MixedFinalTestInput,
    "short_answer_grading": ShortAnswerGradeInput,
    "test_result_tutor": TestTutorInput,
    "route_case_turn": RouteCaseTurnInput,
}

PROVIDER_TASK_RESULT_MODELS = {
    "learning_route_generation": LearningRoutePayload,
    "final_test_generation": FinalTestPayload,
    "mixed_final_test_generation": MixedFinalTestPayload,
    "short_answer_grading": ShortAnswerGradePayload,
    "test_result_tutor": TestTutorPayload,
    "route_case_turn": RouteCaseTurnPayload,
}


class PrivateSafety(StrictModel):
    status: Literal["normal", "needs_human_help"]
    notice: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def valid_notice(self):
        if self.status == "needs_human_help" and not self.notice:
            raise PydanticCustomError("human_help_requires_notice", "human help requires a safety notice")
        return self


class PrivateFollowupPayload(StrictModel):
    schema_version: Literal[1]
    response_kind: Literal["private_follow_up"]
    interaction_style: Literal["guided", "direct"]
    learning_response: LearningResponse
    safety: PrivateSafety
