from __future__ import annotations

from dataclasses import replace

from pydantic import ValidationError

from app.modules.pbl.application.records import InferenceResult
from app.modules.pbl.infrastructure.provider_schema import ProviderPayload


def unavailable_result(reason: str) -> InferenceResult:
    return InferenceResult("暂时无法完成学习诊断，请稍后重试。", "unavailable", failure_reason=reason)


def parse_provider_json(raw: str, metadata: dict[str, object], conversation_ref: str | None = None) -> InferenceResult:
    try:
        value = ProviderPayload.model_validate_json(raw)
        return InferenceResult(
            assistant_reply=value.assistant_reply,
            diagnostic_status=value.diagnostic_status,
            follow_up_question=value.follow_up_question,
            knowledge_gaps=tuple(item.model_dump() for item in value.knowledge_gaps),
            reasoning_issues=tuple(item.model_dump() for item in value.reasoning_issues),
            recommended_questions=tuple(item.model_dump() for item in value.recommended_questions),
            provider_metadata=metadata,
            conversation_ref=conversation_ref,
            schema_version=3,
            safety_notice=value.safety_notice,
            safety_status=value.safety_status,
            phase_assessment=value.phase_assessment.model_dump(),
        )
    except ValidationError as error:
        # Only schema locations/types are retained; never input values or provider text.
        issues = [
            {
                "path": ".".join(
                    str(part) for part in item["loc"] if isinstance(part, int) or str(part).replace("_", "").isalnum()
                )[:100],
                "type": item["type"],
            }
            for item in error.errors(include_input=False, include_url=False)[:8]
        ]
        return replace(unavailable_result("invalid_provider_response"), provider_metadata={"validation_issues": issues})
    except (ValueError, TypeError):
        return unavailable_result("invalid_provider_response")
