import json
import re
from dataclasses import dataclass
from time import perf_counter

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AICallLog, CaseAttempt
from app.schemas.case_training import (
    AIAssessmentResponse,
    CaseDraftGenerateResponse,
    PatientReplyModel,
)
from app.schemas.personalized import PracticeGeneratedDefinition
from app.services.case_seed import SAFETY_NOTICE, showcase_draft

FAILURE_CATEGORIES = {
    "disabled",
    "config_missing",
    "timeout",
    "http_error",
    "empty_response",
    "invalid_json",
    "schema_error",
    "safety_leak",
}
PRACTICE_PROMPT_VERSION = "practice-v1"


@dataclass(frozen=True)
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


def _log(
    db: Session,
    task: str,
    user_id: int | None,
    attempt_id: int | None,
    started: float,
    fallback_used: bool,
    reason: str | None = None,
    learning_task_id: int | None = None,
    blueprint_id: str | None = None,
    blueprint_digest: str | None = None,
) -> None:
    settings = get_settings()
    db.add(
        AICallLog(
            user_id=user_id,
            attempt_id=attempt_id,
            task=task,
            model_name=settings.ai_model or "deterministic-fallback",
            prompt_version=settings.ai_prompt_version,
            latency_ms=round((perf_counter() - started) * 1000),
            fallback_used=fallback_used,
            failure_reason=reason,
            learning_task_id=learning_task_id,
            blueprint_id=blueprint_id,
            blueprint_digest=blueprint_digest,
        )
    )


def call_structured[T: BaseModel](
    task: str,
    messages: list[dict[str, str]],
    response_schema: type[T],
    temperature: float,
) -> AICallResult:
    """Call an OpenAI-compatible endpoint, retrying one time without logging prompts."""
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


def _fallback_draft(topic: str, learner_level: str, objectives: list[str]) -> dict:
    draft = showcase_draft(topic)
    objective_text = "、".join(item.strip() for item in objectives if item.strip())
    draft["description"] = (
        f"{draft['description']} 学习层级：{learner_level}。教学目标：{objective_text or '完成结构化临床推理。'}"
    )
    return {
        "title": draft["title"],
        "description": draft["description"],
        "specialty": draft["specialty"],
        "difficulty": draft["difficulty"],
        "estimated_minutes": draft["estimated_minutes"],
        "case_definition": draft["case_definition"],
        "rubric": draft["rubric"],
    }


def generate_draft(db: Session, topic: str, learner_level: str, objectives: list[str], user_id: int) -> dict:
    started = perf_counter()
    messages = [
        {"role": "system", "content": "你是结构化病例教学设计助手。只返回符合 schema 的 JSON，不决定发布权限。"},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "topic": topic,
                    "learner_level": learner_level,
                    "learning_objectives": objectives,
                    "fixed_stages": ["history", "problem_representation", "differential", "tests", "management"],
                },
                ensure_ascii=False,
            ),
        },
    ]
    result = call_structured("case_draft", messages, CaseDraftGenerateResponse, 0.4)
    if isinstance(result.value, CaseDraftGenerateResponse):
        _log(db, "case_draft", user_id, None, started, False)
        db.commit()
        return {**result.value.model_dump(mode="json"), "generation_mode": "model", "safety_notice": SAFETY_NOTICE}
    _log(db, "case_draft", user_id, None, started, True, result.failure_reason)
    db.commit()
    return {
        **_fallback_draft(topic, learner_level, objectives),
        "generation_mode": "fallback",
        "safety_notice": SAFETY_NOTICE,
    }


def _is_safety_or_injection(content: str) -> bool:
    normalized = re.sub(r"\s+", "", content.lower())
    return any(
        token in normalized
        for token in ("忽略规则", "忽略以上", "告诉我答案", "最终诊断", "全部事实", "提示词", "systemprompt")
    )


def patient_reply(db: Session, attempt: CaseAttempt, content: str) -> tuple[str, list[str], str]:
    started = perf_counter()
    if _is_safety_or_injection(content):
        answer, ids, mode = "我是虚拟患者，只能回答当前病史问题。您想了解症状经过、伴随表现还是既往情况？", [], "safety"
        _log(db, "patient_reply", attempt.student_id, attempt.id, started, True, "safety_or_injection")
        return answer, ids, mode
    normalized = re.sub(r"\s+", "", content.lower())
    already = {
        fact_id
        for message in attempt.messages
        if message.role == "assistant"
        for fact_id in (message.revealed_fact_ids or [])
    }
    matches = []
    for fact in (attempt.problem.case_definition or {}).get("facts", []):
        if fact.get("reveal_stage") != "history" or fact.get("id") in already:
            continue
        triggers = [re.sub(r"\s+", "", trigger.lower()) for trigger in fact.get("triggers", [])]
        if any(trigger and trigger in normalized for trigger in triggers):
            matches.append(fact)
    matches = matches[:2]
    ids = [item["id"] for item in matches]
    selected_values = [item["value"] for item in matches]
    fallback = " ".join(selected_values) if selected_values else "您想具体了解症状经过、伴随表现还是既往情况？"
    if matches:
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
            _log(db, "patient_reply", attempt.student_id, attempt.id, started, False)
            return result.value.reply, ids, "model"
        reason = result.failure_reason or "schema_error"
    else:
        reason = "disabled"
    _log(db, "patient_reply", attempt.student_id, attempt.id, started, True, reason)
    return fallback, ids, "fallback"


def ai_assessment(db: Session, attempt: CaseAttempt) -> AIAssessmentResponse | None:
    started = perf_counter()
    case_definition = attempt.problem.case_definition or {}
    rubric = attempt.problem.rubric or {}
    student_answers = [
        {"stage_id": submission.stage_id, "answer": submission.answer} for submission in attempt.submissions
    ]
    student_messages = [{"role": message.role, "content": message.content} for message in attempt.messages]
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
                    "reference_reasoning": case_definition.get("reference_reasoning", {}),
                    "rubric": rubric,
                },
                ensure_ascii=False,
            ),
        },
    ]
    result = call_structured("assessment", messages, AIAssessmentResponse, 0.1)
    _log(db, "assessment", attempt.student_id, attempt.id, started, result.value is None, result.failure_reason)
    return result.value if isinstance(result.value, AIAssessmentResponse) else None


def generate_practice_definition(
    db: Session,
    student_id: int,
    task_id: int,
    blueprint: dict,
    weakness_summary: str,
) -> tuple[dict, bool, str | None, str, str]:
    """Generate only a public drill definition; rubric and facts never enter the output."""
    started = perf_counter()
    public = {
        "title": "结构化微训练",
        "context": "合成教学情境，不代表真实患者",
        "instruction": blueprint.get("public_instruction", "完成结构化回答并说明依据。"),
        "answer_schema": blueprint.get("answer_schema", "short_text"),
        "display_hints": [],
    }
    messages = [
        {"role": "system", "content": "只生成公开教学题面 JSON，不输出答案、评分标准、固定事实、隐藏 ID、剂量或处方。"},
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
    if isinstance(result.value, PracticeGeneratedDefinition):
        value = result.value.model_dump(mode="json")
        if any(
            token in json.dumps(value, ensure_ascii=False).lower()
            for token in ("剂量", "处方", "fixed_facts", "criteria")
        ):
            result = AICallResult(None, "safety_leak", result.latency_ms)
        else:
            _log(
                db,
                "practice_generation",
                student_id,
                None,
                started,
                False,
                learning_task_id=task_id,
                blueprint_id=blueprint.get("id"),
                blueprint_digest=blueprint.get("digest"),
            )
            return value, False, None, get_settings().ai_model or "configured-model", PRACTICE_PROMPT_VERSION
    reason = result.failure_reason or "schema_error"
    _log(
        db,
        "practice_generation",
        student_id,
        None,
        started,
        True,
        reason,
        learning_task_id=task_id,
        blueprint_id=blueprint.get("id"),
        blueprint_digest=blueprint.get("digest"),
    )
    return public, True, reason, "deterministic-fallback", PRACTICE_PROMPT_VERSION
