from __future__ import annotations

import json
import re
from time import perf_counter

from app.core.config import get_settings
from app.modules.training.application.records import AssessmentGenerationResult, AttemptRecord, PatientReplyResult
from app.modules.training.domain.state import SAFETY_NOTICE, AssessmentCandidate
from app.modules.training.infrastructure.ai_schemas import AIAssessmentResponse, PatientReplyModel
from app.platform.ai import call_structured


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())


def _is_safety_or_injection(content: str) -> bool:
    normalized = _normalize(content)
    return any(
        token in normalized
        for token in ("忽略规则", "忽略以上", "告诉我答案", "最终诊断", "全部事实", "提示词", "systemprompt")
    )


class CaseAiGateway:
    """External AI adapter with deterministic, privacy-preserving fallbacks."""

    def reply(self, attempt: AttemptRecord, content: str) -> PatientReplyResult:
        started = perf_counter()
        settings = get_settings()
        if _is_safety_or_injection(content):
            return PatientReplyResult(
                reply="我是虚拟患者，只能回答当前病史问题。您想了解症状经过、伴随表现还是既往情况？",
                revealed_fact_ids=(),
                response_mode="safety",
                fallback_used=True,
                failure_reason="safety_or_injection",
                model_name="deterministic-fallback",
                prompt_version=settings.ai_prompt_version,
                latency_ms=round((perf_counter() - started) * 1000),
            )
        normalized = _normalize(content)
        already = {
            fact_id
            for message in attempt.messages
            if message.role == "assistant"
            for fact_id in message.revealed_fact_ids
        }
        matches = []
        for fact in (attempt.problem.case_definition or {}).get("facts", []):
            if fact.get("reveal_stage") != "history" or fact.get("id") in already:
                continue
            triggers = [_normalize(str(trigger)) for trigger in fact.get("triggers", [])]
            if any(trigger and trigger in normalized for trigger in triggers):
                matches.append(fact)
        matches = matches[:2]
        fact_ids = tuple(str(item["id"]) for item in matches)
        selected_values = [str(item["value"]) for item in matches]
        fallback = " ".join(selected_values) if selected_values else "您想具体了解症状经过、伴随表现还是既往情况？"
        if not matches:
            return PatientReplyResult(
                reply=fallback,
                revealed_fact_ids=(),
                response_mode="fallback",
                fallback_used=True,
                failure_reason="disabled",
                model_name="deterministic-fallback",
                prompt_version=settings.ai_prompt_version,
                latency_ms=round((perf_counter() - started) * 1000),
            )
        prompt = [
            {
                "role": "system",
                "content": "你是合成病例中的虚拟患者。只将给定事实改写为自然中文，不提供诊断、答案或未给出的数字。",
            },
            {
                "role": "user",
                "content": json.dumps({"selected_facts": selected_values, "question": content}, ensure_ascii=False),
            },
        ]
        result = call_structured("patient_reply", prompt, PatientReplyModel, 0.2)
        if (
            isinstance(result.value, PatientReplyModel)
            and result.value.reply
            and all(value not in result.value.reply for value in ("社区获得性肺炎", "肺栓塞"))
        ):
            return PatientReplyResult(
                reply=result.value.reply,
                revealed_fact_ids=fact_ids,
                response_mode="model",
                fallback_used=False,
                failure_reason=None,
                model_name=settings.ai_model or "configured-model",
                prompt_version=settings.ai_prompt_version,
                latency_ms=round((perf_counter() - started) * 1000),
            )
        return PatientReplyResult(
            reply=fallback,
            revealed_fact_ids=fact_ids,
            response_mode="fallback",
            fallback_used=True,
            failure_reason=result.failure_reason or "schema_error",
            model_name="deterministic-fallback",
            prompt_version=settings.ai_prompt_version,
            latency_ms=round((perf_counter() - started) * 1000),
        )

    def assess(self, attempt: AttemptRecord) -> AssessmentGenerationResult:
        settings = get_settings()
        student_answers = [
            {"stage_id": submission.stage_id, "answer": submission.answer} for submission in attempt.submissions
        ]
        student_messages = [
            {"role": message.role, "content": message.content} for message in attempt.messages if message.role == "user"
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "你是教学评价助手，只输出六维原始分、学生原文证据和反馈。"
                    "不得给出诊断或治疗建议；evidence 必须逐字来自 student_answers 或 student_messages。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "student_answers": student_answers,
                        "student_messages": student_messages,
                        "reference_reasoning": (attempt.problem.case_definition or {}).get("reference_reasoning", {}),
                        "rubric": attempt.problem.rubric,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        result = call_structured("assessment", messages, AIAssessmentResponse, 0.1)
        if not isinstance(result.value, AIAssessmentResponse):
            return AssessmentGenerationResult(
                candidates=(),
                fallback_used=True,
                failure_reason=result.failure_reason or "schema_error",
                model_name="deterministic-fallback",
                prompt_version=settings.ai_prompt_version,
                latency_ms=result.latency_ms,
            )
        candidates = tuple(
            AssessmentCandidate(
                dimension_id=item.dimension_id,
                score=item.score,
                evidence=tuple(item.evidence),
                feedback=item.feedback,
                next_step=item.next_step,
            )
            for item in result.value.dimensions
        )
        return AssessmentGenerationResult(
            candidates=candidates,
            fallback_used=False,
            failure_reason=None,
            model_name=settings.ai_model or "configured-model",
            prompt_version=settings.ai_prompt_version,
            latency_ms=result.latency_ms,
        )


def fallback_summary() -> str:
    return SAFETY_NOTICE
