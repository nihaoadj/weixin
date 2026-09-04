from app.modules.content.public import knowledge_point_view
from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.infrastructure.provider_schema import ProviderPayload


class CheckedGateway:
    def __init__(self, gateway):
        self._gateway = gateway

    def infer(self, request: InferenceRequest) -> InferenceResult:
        result = self._gateway.infer(request)
        if result.diagnostic_status == "unavailable":
            return InferenceResult(result.assistant_reply, "unavailable", failure_reason=result.failure_reason,
                provider_metadata={"validation_issues": (result.provider_metadata or {}).get("validation_issues", [])})
        try:
            value = ProviderPayload.model_validate(
                {
                    "schema_version": result.schema_version,
                    "assistant_reply": result.assistant_reply,
                    "diagnostic_status": result.diagnostic_status,
                    "follow_up_question": result.follow_up_question,
                    "knowledge_gaps": result.knowledge_gaps,
                    "reasoning_issues": result.reasoning_issues,
                    "recommended_questions": result.recommended_questions,
                    "safety_notice": result.safety_notice,
                    "safety_status": result.safety_status,
                }
            )
            allowed = {item["id"] for item in request.history if item.get("role") == "student" and item.get("id")}
            allowed.add(request.message_id)
            if value.diagnostic_status == "ready" and (len(allowed) < 2 or not request.message_id):
                raise ValueError("multi-turn evidence required")
            for finding in [*value.knowledge_gaps, *value.reasoning_issues]:
                if not set(finding.evidence_message_ids).issubset(allowed):
                    raise ValueError("invalid message reference")
            if any(knowledge_point_view(gap.point_code) is None for gap in value.knowledge_gaps):
                raise ValueError("invalid knowledge point")
            return result
        except (ValueError, TypeError, KeyError):
            return InferenceResult(
                "本次诊断缺少可核对的依据，请重新说明你的理解。",
                "unavailable",
                failure_reason="invalid_diagnostic_evidence",
            )
