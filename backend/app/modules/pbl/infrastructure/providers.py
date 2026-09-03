import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.modules.pbl.application.records import InferenceRequest, InferenceResult


class _Payload(BaseModel):
    assistant_reply: str = Field(min_length=1, max_length=4000)
    diagnostic_status: str
    follow_up_question: str | None = Field(default=None, max_length=1000)
    knowledge_gaps: list[dict[str, Any]] = Field(default_factory=list, max_length=10)
    reasoning_issues: list[dict[str, Any]] = Field(default_factory=list, max_length=10)
    recommended_questions: list[dict[str, Any]] = Field(default_factory=list, max_length=5)

    def result(self, metadata: dict[str, object]) -> InferenceResult:
        if self.diagnostic_status not in {"probing", "ready", "insufficient_evidence", "unavailable"}:
            raise ValueError("invalid status")
        if self.diagnostic_status == "probing" and (
            not self.follow_up_question or self.knowledge_gaps or self.reasoning_issues
        ):
            raise ValueError("invalid probing")
        if self.diagnostic_status == "ready" and not (self.knowledge_gaps or self.reasoning_issues):
            raise ValueError("empty ready")
        return InferenceResult(
            self.assistant_reply,
            self.diagnostic_status,
            self.follow_up_question,
            tuple(self.knowledge_gaps),
            tuple(self.reasoning_issues),
            tuple(self.recommended_questions),
            metadata,
        )


def parse_provider_json(raw: str, metadata: dict[str, object]) -> InferenceResult:
    try:
        return _Payload.model_validate(json.loads(raw)).result(metadata)
    except (ValueError, ValidationError, TypeError):
        return InferenceResult(
            "暂时无法完成学习诊断，请稍后重试。", "unavailable", failure_reason="invalid_provider_response"
        )


class CozeBotGateway:
    def __init__(self, client: Any, bot_id: str, prompt_version: str) -> None:
        self.client, self.bot_id, self.prompt_version = client, bot_id, prompt_version

    def infer(self, request: InferenceRequest) -> InferenceResult:
        try:
            return parse_provider_json(
                _stream_text(
                    self.client.chat.stream(
                        bot_id=self.bot_id,
                        user_id=f"pbl-{request.session_id}",
                        additional_messages=[{"role": "user", "content": request.question}],
                    )
                ),
                {"provider": "coze", "mode": "bot", "resource_id": self.bot_id, "prompt_version": self.prompt_version},
            )
        except Exception:
            return InferenceResult("暂时无法连接教学助手。", "unavailable", failure_reason="coze_sdk_error")


class CozeWorkflowGateway:
    def __init__(self, client: Any, workflow_id: str, resource_id: str, prompt_version: str) -> None:
        self.client, self.workflow_id, self.resource_id, self.prompt_version = (
            client,
            workflow_id,
            resource_id,
            prompt_version,
        )

    def infer(self, request: InferenceRequest) -> InferenceResult:
        try:
            return parse_provider_json(
                _stream_text(
                    self.client.workflows.chat.stream(
                        workflow_id=self.workflow_id,
                        bot_id=self.resource_id or None,
                        additional_messages=[{"role": "user", "content": request.question}],
                    )
                ),
                {
                    "provider": "coze",
                    "mode": "workflow",
                    "resource_id": self.workflow_id,
                    "prompt_version": self.prompt_version,
                },
            )
        except Exception:
            return InferenceResult("暂时无法连接教学助手。", "unavailable", failure_reason="coze_sdk_error")


class OpenAICompatibleGateway:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int, prompt_version: str) -> None:
        self.base_url, self.api_key, self.model, self.timeout, self.prompt_version = (
            base_url,
            api_key,
            model,
            timeout,
            prompt_version,
        )

    def infer(self, request: InferenceRequest) -> InferenceResult:
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": [{"role": "user", "content": request.question}]},
                timeout=self.timeout,
            )
            response.raise_for_status()
            choices = response.json().get("choices", [])
            raw = choices[0]["message"]["content"] if choices else ""
            return parse_provider_json(raw, {"provider": "openai_compatible", "prompt_version": self.prompt_version})
        except Exception:
            return InferenceResult("暂时无法连接教学助手。", "unavailable", failure_reason="openai_compatible_error")


def _stream_text(events: Any) -> str:
    texts = []
    for event in events:
        value = getattr(event, "content", None) or (event.get("content") if isinstance(event, dict) else None)
        if value:
            texts.append(str(value))
    return "".join(texts)
