from __future__ import annotations

from dataclasses import replace

from pydantic import ValidationError

from app.modules.pbl.application.records import (
    InferenceResult,
    LearningResponseRecord,
    PrivateFollowupResult,
)
from app.modules.pbl.infrastructure.provider_schema import (
    PrivateFollowupPayload,
    ProviderPayload,
    ProviderPayloadV7,
    ProviderPayloadV8,
)
from app.modules.pbl.infrastructure.providers.response_renderer import render_learning_response


def unavailable_result(reason: str, interaction_style: str = "guided") -> InferenceResult:
    sections = LearningResponseRecord(
        "暂时无法完成学习诊断。", ("本轮未生成诊断，也未推进阶段。",), "请稍后重新提问继续。"
    )
    return InferenceResult(
        render_learning_response(sections),
        "unavailable",
        failure_reason=reason,
        interaction_style=interaction_style,
        response_sections=sections,
        fallback_used=True,
    )


def unavailable_private_follow_up(reason: str, interaction_style: str = "guided") -> PrivateFollowupResult:
    sections = LearningResponseRecord(
        "暂时无法完成这次解释。",
        ("本轮不会改变已经冻结的学习证据或教师诊断。",),
        "请稍后使用同一条消息重试。",
    )
    return PrivateFollowupResult(
        assistant_reply=render_learning_response(sections),
        interaction_style=interaction_style,
        processing_status="unavailable",
        safety_status="normal",
        safety_notice="仅供病理学教学，不能替代临床诊疗。",
        fallback_used=True,
        failure_reason=reason,
        response_sections=sections,
    )


def parse_provider_json(
    raw: str,
    metadata: dict[str, object],
    conversation_ref: str | None = None,
    interaction_style: str = "guided",
    schema_version: int = 6,
) -> InferenceResult:
    try:
        if schema_version not in (6, 7, 8):
            raise ValueError("unsupported provider schema")
        model = {6: ProviderPayload, 7: ProviderPayloadV7, 8: ProviderPayloadV8}[schema_version]
        value = model.model_validate_json(raw)
        sections = LearningResponseRecord(
            value.learning_response.opening,
            tuple(value.learning_response.key_points),
            value.learning_response.next_step,
        )
        return InferenceResult(
            assistant_reply=render_learning_response(sections),
            diagnostic_status=value.diagnostic_status,
            follow_up_question=None
            if value.phase_assessment.decision == "complete" or value.safety_status == "needs_human_help"
            else sections.next_step,
            knowledge_gaps=tuple(item.model_dump() for item in value.knowledge_gaps),
            reasoning_issues=tuple(item.model_dump() for item in value.reasoning_issues),
            recommended_questions=(
                tuple(item.model_dump() for item in value.recommended_questions) if schema_version == 6 else ()
            ),
            recommended_knowledge_cards=(
                tuple(item.model_dump() for item in value.recommended_knowledge_cards)
                if schema_version in (6, 7)
                else ()
            ),
            diagnosis_outcome=value.diagnosis_outcome if schema_version in (7, 8) else None,
            candidate_tasks=tuple(item.model_dump() for item in value.candidate_tasks) if schema_version == 7 else (),
            provider_metadata=metadata,
            conversation_ref=conversation_ref,
            schema_version=schema_version,
            response_sections=sections,
            interaction_style=value.interaction_style,
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
        return replace(
            unavailable_result("invalid_provider_response", interaction_style),
            provider_metadata={"validation_issues": issues},
        )
    except (ValueError, TypeError):
        return unavailable_result("invalid_provider_response", interaction_style)


def parse_private_follow_up_json(
    raw: str,
    metadata: dict[str, object],
    conversation_ref: str | None = None,
    interaction_style: str = "guided",
) -> PrivateFollowupResult:
    try:
        value = PrivateFollowupPayload.model_validate_json(raw)
        sections = LearningResponseRecord(
            value.learning_response.opening,
            tuple(value.learning_response.key_points),
            value.learning_response.next_step,
        )
        return PrivateFollowupResult(
            assistant_reply=render_learning_response(sections),
            interaction_style=value.interaction_style,
            safety_status=value.safety.status,
            safety_notice=value.safety.notice,
            provider_metadata=metadata,
            conversation_ref=conversation_ref,
            response_sections=sections,
        )
    except ValidationError as error:
        issues = [
            {
                "path": ".".join(
                    str(part) for part in item["loc"] if isinstance(part, int) or str(part).replace("_", "").isalnum()
                )[:100],
                "type": item["type"],
            }
            for item in error.errors(include_input=False, include_url=False)[:8]
        ]
        return replace(
            unavailable_private_follow_up("invalid_private_follow_up_response", interaction_style),
            provider_metadata={"validation_issues": issues},
        )
    except (ValueError, TypeError):
        return unavailable_private_follow_up("invalid_private_follow_up_response", interaction_style)
