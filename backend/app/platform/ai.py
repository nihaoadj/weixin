from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

FAILURE_CATEGORIES = {
    "disabled",
    "config_missing",
    "timeout",
    "http_error",
    "empty_response",
    "invalid_json",
    "schema_error",
}


@dataclass(frozen=True, slots=True)
class AICallResult:
    value: BaseModel | None
    failure_reason: str | None
    latency_ms: int


def _failure_category(error: Exception) -> str:
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    if isinstance(error, httpx.HTTPStatusError):
        return "http_error"
    if isinstance(error, json.JSONDecodeError):
        return "invalid_json"
    if isinstance(error, ValidationError):
        return "schema_error"
    return "empty_response"


def call_structured[T: BaseModel](
    task: str,
    messages: list[dict[str, str]],
    response_schema: type[T],
    temperature: float,
) -> AICallResult:
    """Call an OpenAI-compatible endpoint without logging prompts or responses."""
    del task
    started = perf_counter()
    settings = get_settings()
    if not settings.ai_enabled:
        return AICallResult(None, "disabled", round((perf_counter() - started) * 1000))
    if not settings.ai_base_url or not settings.ai_api_key or not settings.ai_model:
        return AICallResult(None, "config_missing", round((perf_counter() - started) * 1000))
    url = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    last_reason = "empty_response"
    for attempt_number in range(2):
        retry_messages = messages
        if attempt_number:
            retry_messages = [
                *messages,
                {"role": "user", "content": json.dumps({"retry_reason": last_reason}, ensure_ascii=False)},
            ]
        payload = {
            "model": settings.ai_model,
            "messages": retry_messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {settings.ai_api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=settings.ai_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content")
            if not content:
                raise ValueError("empty model response")
            value = response_schema.model_validate(json.loads(content))
            return AICallResult(value, None, round((perf_counter() - started) * 1000))
        except (httpx.HTTPError, json.JSONDecodeError, ValidationError, ValueError) as error:
            last_reason = _failure_category(error)
    return AICallResult(
        None,
        last_reason if last_reason in FAILURE_CATEGORIES else "empty_response",
        round((perf_counter() - started) * 1000),
    )
