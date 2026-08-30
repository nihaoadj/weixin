import json
import re
from time import perf_counter

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AICallLog
from app.schemas import MedicalChatRequest

EMERGENCY_PATTERNS = [
    re.compile(r"胸.{0,6}(持续|突然|剧烈|压榨|闷).{0,8}(痛|疼)"),
    re.compile(r"呼吸(困难|急促)|喘不上气|不能呼吸"),
    re.compile(r"意识(不清|丧失)|昏迷|抽搐"),
    re.compile(r"大出血|止不住血"),
    re.compile(r"偏瘫|口角歪斜|言语不清"),
    re.compile(r"自杀|轻生|不想活"),
]


def is_emergency(content: str) -> bool:
    return any(pattern.search(content) for pattern in EMERGENCY_PATTERNS)


def _fallback_reply(request: MedicalChatRequest) -> str:
    if is_emergency(request.prompt):
        return (
            "你描述的情况可能包含急症风险信号。请立即停止线上问答并联系当地急救服务，"
            "中国大陆请拨打 120。本提示仅用于安全分流，不能替代急诊评估。"
        )
    if request.mode == "模拟诊疗":
        return "演示反馈：请继续询问起病时间、诱因、伴随症状、既往史和用药史，并说明鉴别诊断依据。"
    if request.mode == "病例分析":
        return "演示反馈：建议按主要问题、支持证据、鉴别诊断、检查计划和处理原则组织答案。"
    return "演示反馈：建议从定义、常见表现、鉴别要点和处理原则四部分梳理。医学内容仅用于教学。"


def _failure_reason(error: Exception) -> str:
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    if isinstance(error, httpx.HTTPError):
        return "http_error"
    if isinstance(error, json.JSONDecodeError):
        return "invalid_json"
    return "empty_response"


def _call_configured_model(request: MedicalChatRequest) -> tuple[str | None, str, int]:
    started = perf_counter()
    settings = get_settings()
    if not settings.ai_enabled:
        return None, "disabled", round((perf_counter() - started) * 1000)
    if not settings.ai_base_url or not settings.ai_api_key or not settings.ai_model:
        return None, "config_missing", round((perf_counter() - started) * 1000)

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
    payload = {
        "model": settings.ai_model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    last_reason = "empty_response"
    for _ in range(2):
        try:
            response = httpx.post(
                f"{settings.ai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.ai_api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=settings.ai_timeout_seconds,
            )
            if not 200 <= response.status_code < 300:
                last_reason = "http_error"
                continue
            body = response.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()[:8000], "", round((perf_counter() - started) * 1000)
            last_reason = "empty_response"
        except (httpx.HTTPError, json.JSONDecodeError, IndexError, KeyError, TypeError) as error:
            last_reason = _failure_reason(error)
    return None, last_reason, round((perf_counter() - started) * 1000)


def _write_ai_log(
    db: Session | None, user_id: int | None, fallback_used: bool, reason: str | None, latency_ms: int
) -> None:
    if db is None:
        return
    settings = get_settings()
    db.add(
        AICallLog(
            user_id=user_id,
            task="medical_chat",
            model_name=settings.ai_model or "deterministic-fallback",
            prompt_version=settings.ai_prompt_version,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            failure_reason=reason,
        )
    )
    db.commit()


def create_medical_reply(request: MedicalChatRequest, user_id: int | None = None, db: Session | None = None) -> str:
    if is_emergency(request.prompt):
        return _fallback_reply(request)
    content, reason, latency_ms = _call_configured_model(request)
    _write_ai_log(db, user_id, content is None, reason or None, latency_ms)
    return content or _fallback_reply(request)
