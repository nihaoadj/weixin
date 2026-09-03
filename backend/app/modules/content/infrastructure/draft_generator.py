from __future__ import annotations

import json

from app.core.config import get_settings
from app.modules.content.application.records import CaseDraftResult
from app.modules.content.domain.defaults import deterministic_case_draft
from app.modules.content.domain.templates import SAFETY_NOTICE
from app.modules.content.infrastructure.ai_schemas import CaseDraftModel
from app.platform.ai import call_structured


class CaseDraftAiGateway:
    """Call the structured provider and preserve the approved deterministic fallback."""

    def generate(self, topic: str, learner_level: str, objectives: list[str], _teacher_id: int) -> CaseDraftResult:
        messages = [
            {
                "role": "system",
                "content": "你是结构化病例教学设计助手。只返回符合 schema 的 JSON，不决定发布权限。",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "topic": topic,
                        "learner_level": learner_level,
                        "learning_objectives": objectives,
                        "fixed_stages": [
                            "history",
                            "problem_representation",
                            "differential",
                            "tests",
                            "management",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        result = call_structured("case_draft", messages, CaseDraftModel, 0.4)
        settings = get_settings()
        if isinstance(result.value, CaseDraftModel):
            payload = result.value.model_dump(mode="json", exclude={"generation_mode", "safety_notice"})
            return CaseDraftResult(
                payload=payload,
                generation_mode="model",
                safety_notice=SAFETY_NOTICE,
                model_name=settings.ai_model or "deterministic-fallback",
                prompt_version=settings.ai_prompt_version,
                fallback_used=False,
                latency_ms=result.latency_ms,
            )

        return CaseDraftResult(
            payload=deterministic_case_draft(topic, learner_level, objectives),
            generation_mode="fallback",
            safety_notice=SAFETY_NOTICE,
            model_name="deterministic-fallback",
            prompt_version=settings.ai_prompt_version,
            fallback_used=True,
            failure_reason=result.failure_reason or "schema_error",
            latency_ms=result.latency_ms,
        )


# Kept as an import-compatible name for the non-production legacy facade.
DeterministicCaseDraftGenerator = CaseDraftAiGateway


__all__ = ["CaseDraftAiGateway", "DeterministicCaseDraftGenerator"]
