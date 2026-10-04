from dataclasses import asdict, replace

from app.modules.pbl.application.records import InferenceRequest, InferenceResult, PrivateFollowupRequest
from app.modules.pbl.infrastructure.provider_schema import (
    PrivateFollowupPayload,
    ProviderPayloadV8,
)
from app.modules.pbl.infrastructure.provider_tasks import ProviderTaskFailure, validate_task_input, validate_task_result
from app.modules.pbl.infrastructure.providers.coze_parser import unavailable_private_follow_up, unavailable_result
from app.modules.pbl.infrastructure.providers.response_renderer import render_learning_response


class CheckedGateway:
    def __init__(self, gateway):
        self._gateway = gateway

    def infer(self, request: InferenceRequest) -> InferenceResult:
        if request.schema_version != 8:
            return unavailable_result("unsupported_provider_schema", request.interaction_style)
        result = self._gateway.infer(request)
        if result.diagnostic_status == "unavailable":
            return replace(
                unavailable_result(result.failure_reason or "provider_unavailable", request.interaction_style),
                provider_metadata={"validation_issues": (result.provider_metadata or {}).get("validation_issues", [])},
            )
        try:
            payload = {
                "schema_version": result.schema_version,
                "interaction_style": result.interaction_style,
                "learning_response": asdict(result.response_sections) if result.response_sections else None,
                "diagnostic_status": result.diagnostic_status,
                "knowledge_gaps": result.knowledge_gaps,
                "reasoning_issues": result.reasoning_issues,
                "safety_notice": result.safety_notice,
                "safety_status": result.safety_status,
                "phase_assessment": result.phase_assessment,
            }
            if (
                result.schema_version != 8
                or result.recommended_questions
                or result.candidate_tasks
                or result.recommended_knowledge_cards
            ):
                raise ValueError("unsupported provider version or generated diagnostic task")
            value = ProviderPayloadV8.model_validate(
                {
                    **payload,
                    "diagnosis_outcome": result.diagnosis_outcome,
                }
            )
            self._validate_v8_scope(value, request)
            assessment = value.phase_assessment
            if value.interaction_style != request.interaction_style:
                raise ValueError("interaction style mismatch")
            if result.assistant_reply != render_learning_response(value.learning_response):
                raise ValueError("learning response render mismatch")
            if assessment.phase != request.current_phase:
                raise ValueError("phase mismatch")
            if assessment.decision == "complete" and request.current_phase != "synthesis":
                raise ValueError("early completion")
            allowed = {
                item["id"]
                for item in request.history
                if item.get("role") == "student"
                and item.get("id")
                and int(item.get("request_revision") or 0) > request.phase_started_revision
            }
            if request.current_revision > request.phase_started_revision:
                allowed.add(request.message_id)
            if not set(assessment.evidence_message_ids).issubset(allowed) or not assessment.evidence_message_ids:
                raise ValueError("invalid phase evidence")
            for finding in [*value.knowledge_gaps, *value.reasoning_issues]:
                if not set(finding.evidence_message_ids).issubset(allowed):
                    raise ValueError("invalid message reference")
            allowed_codes = {str(point.get("code", "")) for point in request.allowed_points}
            if any(gap.point_code not in allowed_codes for gap in value.knowledge_gaps):
                raise ValueError("invalid knowledge point")
            return result
        except (ValueError, TypeError, KeyError):
            return unavailable_result("invalid_diagnostic_evidence", request.interaction_style)

    def execute_task(self, task_kind: str, request_id: str, input_payload: dict[str, object]) -> dict[str, object]:
        """Run one isolated, schema-checked task using the configured provider only."""
        envelope = validate_task_input(task_kind, request_id, input_payload)
        handler = getattr(self._gateway, "execute_task", None)
        if handler is None:
            raise ProviderTaskFailure("provider_contract_failure")
        try:
            candidate = handler(envelope.model_dump(mode="json"))
        except ProviderTaskFailure:
            raise
        except TimeoutError:
            raise ProviderTaskFailure("provider_timeout") from None
        except Exception:
            raise ProviderTaskFailure("provider_error") from None
        return validate_task_result(envelope, candidate)

    @staticmethod
    def _validate_v8_scope(value: ProviderPayloadV8, request: InferenceRequest) -> None:
        if request.session_kind not in {"classroom", "student_initiated"}:
            raise ValueError("invalid session kind")
        allowed = {
            str(item.get("id"))
            for item in request.history
            if item.get("role") == "student"
            and item.get("id")
            and int(item.get("request_revision") or 0) > request.phase_started_revision
        }
        if request.current_revision > request.phase_started_revision:
            allowed.add(request.message_id)
        assessment = value.phase_assessment
        if not assessment.evidence_message_ids or not set(assessment.evidence_message_ids).issubset(allowed):
            raise ValueError("invalid v8 phase evidence")
        if any(
            not set(item.evidence_message_ids).issubset(allowed)
            for item in [*value.knowledge_gaps, *value.reasoning_issues]
        ):
            raise ValueError("invalid v8 finding evidence")
        allowed_codes = {str(point.get("code", "")) for point in request.allowed_points}
        if any(item.point_code not in allowed_codes for item in value.knowledge_gaps):
            raise ValueError("invalid v8 knowledge point")

    def run_task(self, task_kind: str, request_id: str, input_payload: dict[str, object]) -> dict[str, object]:
        """Compatibility alias for callers that name a task invocation as run_task."""
        return self.execute_task(task_kind, request_id, input_payload)

    def private_follow_up(self, request: PrivateFollowupRequest):
        if request.evidence_locked is not True:
            return unavailable_private_follow_up("invalid_private_follow_up_context", request.interaction_style)
        try:
            ids: set[int] = set()
            private_students: dict[int, dict[str, object]] = {}
            replied_to: set[int] = set()
            previous_sequence = 0
            for item in request.messages:
                message_id = int(item.get("id") or 0)
                sequence = int(item.get("sequence") or 0)
                role = item.get("role")
                scope = item.get("turn_scope")
                if (
                    message_id <= 0
                    or message_id in ids
                    or sequence <= previous_sequence
                    or role not in {"student", "assistant"}
                    or scope not in {"evidence", "private_follow_up"}
                ):
                    raise ValueError("invalid private history")
                ids.add(message_id)
                previous_sequence = sequence
                if scope == "private_follow_up" and role == "student":
                    if not item.get("client_message_id") or item.get("reply_to_message_id"):
                        raise ValueError("invalid private student message")
                    private_students[message_id] = item
                if scope == "private_follow_up" and role == "assistant":
                    reply_to = int(item.get("reply_to_message_id") or 0)
                    if reply_to not in private_students or reply_to in replied_to:
                        raise ValueError("invalid private reply link")
                    replied_to.add(reply_to)
        except (ValueError, TypeError):
            return unavailable_private_follow_up("invalid_private_follow_up_context", request.interaction_style)
        handler = getattr(self._gateway, "private_follow_up", None)
        if handler is None:
            return unavailable_private_follow_up("private_follow_up_not_configured", request.interaction_style)
        result = handler(request)
        if result.processing_status == "unavailable":
            return replace(
                unavailable_private_follow_up(
                    result.failure_reason or "provider_unavailable", request.interaction_style
                ),
                provider_metadata={"validation_issues": (result.provider_metadata or {}).get("validation_issues", [])},
            )
        try:
            value = PrivateFollowupPayload.model_validate(
                {
                    "schema_version": result.schema_version,
                    "response_kind": "private_follow_up",
                    "interaction_style": result.interaction_style,
                    "learning_response": asdict(result.response_sections) if result.response_sections else None,
                    "safety": {"status": result.safety_status, "notice": result.safety_notice},
                }
            )
            if value.interaction_style != request.interaction_style:
                raise ValueError("interaction style mismatch")
            if result.assistant_reply != render_learning_response(value.learning_response):
                raise ValueError("learning response render mismatch")
            if any(
                phrase in result.assistant_reply
                for phrase in ("已提交教师", "已更新学情", "已改变完成结论", "计入正式证据", "已发布正式任务")
            ):
                raise ValueError("private response claims a forbidden state change")
            latest = request.messages[-1] if request.messages else None
            if (
                latest is None
                or latest.get("role") != "student"
                or latest.get("turn_scope") != "private_follow_up"
                or int(latest.get("id") or 0) != request.latest_student_message_id
            ):
                raise ValueError("invalid latest private student message")
            return result
        except (ValueError, TypeError, KeyError):
            return unavailable_private_follow_up("invalid_private_follow_up_response", request.interaction_style)
