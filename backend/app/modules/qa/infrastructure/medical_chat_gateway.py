from __future__ import annotations

import json
from time import perf_counter

import httpx

from app.core.config import get_settings
from app.modules.qa.application.records import MedicalChatRequestRecord, MedicalChatResult
from app.modules.qa.domain.safety import fallback_reply, is_emergency


class MedicalChatHttpGateway:
    def reply(self, request: MedicalChatRequestRecord) -> MedicalChatResult:
        settings = get_settings()
        started = perf_counter()
        if is_emergency(request.prompt):
            return MedicalChatResult(
                content=fallback_reply(request.prompt, request.mode),
                fallback_used=True,
                failure_reason="emergency",
                model_name="deterministic-fallback",
                prompt_version=settings.ai_prompt_version,
                latency_ms=round((perf_counter() - started) * 1000),
            )
        if not settings.ai_enabled:
            return self._fallback(request, "disabled", started)
        if not settings.ai_base_url or not settings.ai_api_key or not settings.ai_model:
            return self._fallback(request, "config_missing", started)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是医学知识问答助手，专注于教学场景。请用准确、审慎的中文回答；"
                    "不要替代医生进行个体诊断、处方或剂量建议；遇到急症风险先建议联系当地急救服务。"
                ),
            },
            *[{"role": message.role, "content": message.content} for message in request.messages[-20:]],
            {"role": "user", "content": request.prompt},
        ]
        payload = {"model": settings.ai_model, "messages": messages, "temperature": 0.7, "max_tokens": 1024}
        reason = "empty_response"
        for _ in range(2):
            try:
                response = httpx.post(
                    f"{settings.ai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=settings.ai_timeout_seconds,
                )
                if not 200 <= response.status_code < 300:
                    reason = "http_error"
                    continue
                body = response.json()
                choices = body.get("choices")
                if not isinstance(choices, list):
                    raise TypeError("provider choices must be a list")
                content = choices[0].get("message", {}).get("content") if choices else None
                if isinstance(content, str) and content.strip():
                    return MedicalChatResult(
                        content=content.strip()[:8000],
                        fallback_used=False,
                        failure_reason=None,
                        model_name=settings.ai_model,
                        prompt_version=settings.ai_prompt_version,
                        latency_ms=round((perf_counter() - started) * 1000),
                    )
                reason = "empty_response"
            except httpx.TimeoutException:
                reason = "timeout"
            except httpx.HTTPError:
                reason = "http_error"
            except (json.JSONDecodeError, IndexError, KeyError, TypeError):
                reason = "invalid_json"
        return self._fallback(request, reason, started)

    @staticmethod
    def _fallback(request: MedicalChatRequestRecord, reason: str, started: float) -> MedicalChatResult:
        settings = get_settings()
        return MedicalChatResult(
            content=fallback_reply(request.prompt, request.mode),
            fallback_used=True,
            failure_reason=reason,
            model_name="deterministic-fallback",
            prompt_version=settings.ai_prompt_version,
            latency_ms=round((perf_counter() - started) * 1000),
        )
