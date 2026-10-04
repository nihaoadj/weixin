from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.modules.pbl.infrastructure.provider_schema import (
    PROVIDER_TASK_INPUT_MODELS,
    PROVIDER_TASK_RESULT_MODELS,
    FinalTestInput,
    FinalTestPayload,
    LearningRouteInput,
    LearningRoutePayload,
    MixedFinalTestInput,
    MixedFinalTestPayload,
    ProviderTaskEnvelope,
    ProviderTaskResultEnvelope,
    RouteCaseTurnInput,
    RouteCaseTurnPayload,
    ShortAnswerGradeInput,
    ShortAnswerGradePayload,
    TestTutorInput,
    TestTutorPayload,
)


class ProviderTaskFailure(RuntimeError):
    """Sanitized single-attempt provider failure code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def validate_task_input(task_kind: str, request_id: str, input_payload: dict[str, object]) -> ProviderTaskEnvelope:
    if task_kind not in PROVIDER_TASK_INPUT_MODELS:
        raise ProviderTaskFailure("provider_contract_failure")
    try:
        validated_input = PROVIDER_TASK_INPUT_MODELS[task_kind].model_validate(input_payload)
        envelope = ProviderTaskEnvelope.model_validate(
            {
                "task_kind": task_kind,
                "schema_version": 1,
                "request_id": request_id,
                "input": validated_input.model_dump(mode="json"),
            }
        )
        _validate_input_scope(envelope)
        return envelope
    except (ValidationError, ValueError, TypeError, KeyError):
        raise ProviderTaskFailure("invalid_task_request") from None


def validate_task_result(expected: ProviderTaskEnvelope, candidate: Any) -> dict[str, object]:
    try:
        envelope = (
            ProviderTaskResultEnvelope.model_validate_json(candidate)
            if isinstance(candidate, str)
            else ProviderTaskResultEnvelope.model_validate(candidate)
        )
        if (
            envelope.task_kind != expected.task_kind
            or envelope.schema_version != expected.schema_version
            or envelope.request_id != expected.request_id
        ):
            raise ValueError("task envelope mismatch")
        result_model = PROVIDER_TASK_RESULT_MODELS[expected.task_kind]
        result = result_model.model_validate(envelope.result)
        _validate_task_result_scope(expected, result)
        return {
            "task_kind": envelope.task_kind,
            "schema_version": envelope.schema_version,
            "request_id": envelope.request_id,
            "result": result.model_dump(mode="json"),
        }
    except (ValidationError, ValueError, TypeError, KeyError):
        raise ProviderTaskFailure("provider_contract_failure") from None


def parse_provider_task_json(raw: str, expected: ProviderTaskEnvelope) -> dict[str, object]:
    return validate_task_result(expected, raw)


def _validate_input_scope(envelope: ProviderTaskEnvelope) -> None:
    if envelope.task_kind == "learning_route_generation":
        value = LearningRouteInput.model_validate(envelope.input)
        codes = {item.code for item in value.goal_points}
        if any(item.kind == "knowledge_gap" and item.target_code not in codes for item in value.findings):
            raise ValueError("finding target outside allowed goals")
    elif envelope.task_kind in {"final_test_generation", "mixed_final_test_generation"}:
        input_model = MixedFinalTestInput if envelope.task_kind == "mixed_final_test_generation" else FinalTestInput
        value = input_model.model_validate(envelope.input)
        codes = {item.code for item in value.goal_points}
        if set(value.route_context.goal_point_codes) != codes:
            raise ValueError("route goals differ from test goals")
        if any(not set(step.target_point_codes).issubset(codes) for step in value.route_context.reading_steps):
            raise ValueError("route reading target outside allowed goals")
        allowed_sources = {item.source_id for item in value.allowed_sources}
        if any(not set(step.source_ids).issubset(allowed_sources) for step in value.route_context.reading_steps):
            raise ValueError("route source outside allowed sources")
        if any(item.kind == "knowledge_gap" and item.target_code not in codes for item in value.findings):
            raise ValueError("finding target outside allowed goals")
    elif envelope.task_kind == "route_case_turn":
        value = RouteCaseTurnInput.model_validate(envelope.input)
        evidence_ids = set(value.current_phase_evidence_message_ids)
        if any(
            item.message_id in evidence_ids
            and (item.role != "student" or item.phase != value.phase or item.revision <= value.phase_started_revision)
            for item in value.history
        ):
            raise ValueError("phase evidence must refer to current-phase students")
    elif envelope.task_kind == "short_answer_grading":
        value = ShortAnswerGradeInput.model_validate(envelope.input)
        if len({item.criterion_id for item in value.rubric}) != 3:
            raise ValueError("grading rubric criteria must be distinct")
    elif envelope.task_kind == "test_result_tutor":
        value = TestTutorInput.model_validate(envelope.input)
        question_ids = {item.get("id") for item in value.question_results}
        if value.current_question_id not in question_ids or any(
            item.question_id not in question_ids for item in value.history
        ):
            raise ValueError("tutor references a question outside the completed test")


def _validate_task_result_scope(expected: ProviderTaskEnvelope, result: Any) -> None:
    if expected.task_kind == "learning_route_generation":
        request = LearningRouteInput.model_validate(expected.input)
        value = LearningRoutePayload.model_validate(result.model_dump(mode="json"))
        goals = {item.code for item in request.goal_points}
        findings = {item.finding_id for item in request.findings}
        sources = {item.source_id for item in request.allowed_sources}
        if value.safety_status != "educational":
            raise ValueError("unsafe route cannot be released")
        if set(value.goal_point_codes) != goals or set(value.synthetic_case.target_point_codes) != goals:
            raise ValueError("route does not cover frozen goals")
        if any(
            not set(step.target_point_codes).issubset(goals)
            or not set(step.linked_findings).issubset(findings)
            or not set(step.source_ids).issubset(sources)
            for step in value.reading_steps
        ):
            raise ValueError("route reading step references unauthorized content")
        if not goals.issubset({code for step in value.reading_steps for code in step.target_point_codes}):
            raise ValueError("route reading does not cover every goal")
    elif expected.task_kind in {"final_test_generation", "mixed_final_test_generation"}:
        mixed = expected.task_kind == "mixed_final_test_generation"
        request = (MixedFinalTestInput if mixed else FinalTestInput).model_validate(expected.input)
        value = (MixedFinalTestPayload if mixed else FinalTestPayload).model_validate(result.model_dump(mode="json"))
        goals = {item.code for item in request.goal_points}
        findings = {item.finding_id for item in request.findings}
        sources = {item.source_id for item in request.allowed_sources}
        if value.safety_status != "educational":
            raise ValueError("unsafe test cannot be released")
        if not mixed and len(value.questions) != len(goals) * 3:
            raise ValueError("each goal must have exactly three questions")
        if any(
            item.primary_point_code not in goals
            or not set(item.linked_findings).issubset(findings)
            or not set(item.source_ids).issubset(sources)
            for item in value.questions
        ):
            raise ValueError("test references unauthorized content")
        if {item.primary_point_code for item in value.questions} != goals:
            raise ValueError("test does not cover every goal")
        if not mixed and any(sum(item.primary_point_code == goal for item in value.questions) != 3 for goal in goals):
            raise ValueError("test goal does not have three questions")
    elif expected.task_kind == "route_case_turn":
        request = RouteCaseTurnInput.model_validate(expected.input)
        value = RouteCaseTurnPayload.model_validate(result.model_dump(mode="json"))
        assessment = value.phase_assessment
        goal_ids = {item.goal_id for item in request.phase_goals}
        if assessment.phase != request.phase or {item.goal_id for item in assessment.goal_checks} != goal_ids:
            raise ValueError("case phase or goal mismatch")
        if not set(assessment.evidence_message_ids).issubset(request.current_phase_evidence_message_ids):
            raise ValueError("case assessment cites unknown evidence")
        if request.current_student_message.message_id not in assessment.evidence_message_ids:
            raise ValueError("case assessment does not cite this revision")
        all_satisfied = all(item.status == "satisfied" for item in assessment.goal_checks)
        if value.safety_status == "needs_human_help":
            if assessment.decision != "stay":
                raise ValueError("safety diversion must stay in the current phase")
        else:
            expected_decision = {
                "pathology_recognition": "advance",
                "mechanism_explanation": "advance",
                "evidence_judgment": "advance",
                "summary_reflection": "complete",
            }[request.phase]
            if all_satisfied and assessment.decision != expected_decision:
                raise ValueError("complete phase goals must produce the adjacent transition")
            if not all_satisfied and assessment.decision != "stay":
                raise ValueError("unsatisfied phase goals must stay in the current phase")
            if assessment.decision == "stay" and not assessment.missing_elements:
                raise ValueError("staying requires specific missing elements")
    elif expected.task_kind == "short_answer_grading":
        request = ShortAnswerGradeInput.model_validate(expected.input)
        value = ShortAnswerGradePayload.model_validate(result.model_dump(mode="json"))
        if value.safety_status != "educational" or value.question_id != request.question_id:
            raise ValueError("unsafe or mismatched short-answer grade")
        if {item.criterion_id for item in value.criterion_results} != {item.criterion_id for item in request.rubric}:
            raise ValueError("short-answer grade does not cover frozen rubric")
    elif expected.task_kind == "test_result_tutor":
        request = TestTutorInput.model_validate(expected.input)
        value = TestTutorPayload.model_validate(result.model_dump(mode="json"))
        if value.current_question_id != request.current_question_id:
            raise ValueError("tutor answered a different question")
