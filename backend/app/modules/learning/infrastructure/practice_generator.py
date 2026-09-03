from __future__ import annotations

import json

from app.core.config import get_settings
from app.modules.learning.application.records import PracticeGenerationResult
from app.modules.learning.infrastructure.practice_schemas import PracticeGeneratedDefinition
from app.platform.ai import call_structured


class PracticeDefinitionGenerator:
    """Generates only public drill copy; hidden rubric/facts never enter the model output."""

    def generate(self, blueprint: dict[str, object], weakness_summary: str) -> PracticeGenerationResult:
        messages = [
            {
                "role": "system",
                "content": "只生成公开教学题面 JSON，不输出答案、评分标准、固定事实、隐藏 ID、剂量或处方。",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "dimension_id": blueprint.get("dimension_id"),
                        "stage_id": blueprint.get("stage_id"),
                        "learner_level": blueprint.get("learner_level"),
                        "public_instruction": blueprint.get("public_instruction"),
                        "allowed_variants": blueprint.get("allowed_variants", []),
                        "weakness_summary": weakness_summary[:500],
                        "answer_schema": blueprint.get("answer_schema"),
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        result = call_structured("practice_generation", messages, PracticeGeneratedDefinition, 0.2)
        settings = get_settings()
        if isinstance(result.value, PracticeGeneratedDefinition):
            value = result.value.model_dump(mode="json")
            serialized = json.dumps(value, ensure_ascii=False).lower()
            if not any(token in serialized for token in ("剂量", "处方", "fixed_facts", "criteria")):
                return PracticeGenerationResult(
                    public_definition=value,
                    fallback_used=False,
                    failure_reason=None,
                    model_name=settings.ai_model or "configured-model",
                    prompt_version="practice-v1",
                    latency_ms=result.latency_ms,
                )
            reason = "safety_leak"
        else:
            reason = result.failure_reason or "schema_error"
        public = {
            "title": blueprint.get("title", "结构化微训练"),
            "context": blueprint.get("context", "合成教学情境，不代表真实患者"),
            "instruction": blueprint.get("public_instruction", "完成结构化回答并说明依据。"),
            "answer_schema": blueprint.get("answer_schema", "short_text"),
            "display_hints": [],
        }
        return PracticeGenerationResult(
            public_definition=public,
            fallback_used=True,
            failure_reason=reason,
            model_name="deterministic-fallback",
            prompt_version="practice-v1",
            latency_ms=result.latency_ms,
        )
