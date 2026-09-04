import json

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.pbl import wiring
from app.modules.pbl.application.records import InferenceRequest
from app.modules.pbl.infrastructure.providers import CozeBotGateway, CozeWorkflowGateway, OpenAICompatibleGateway
from app.modules.pbl.infrastructure.providers.coze_parser import parse_provider_json
from app.modules.pbl.infrastructure.providers.request_builder import provider_messages

READY = json.dumps(
    {
        "schema_version": 3,
        "safety_notice": "仅供教学",
        "safety_status": "educational",
        "assistant_reply": "请比较急慢性炎症证据。",
        "diagnostic_status": "ready",
        "knowledge_gaps": [
            {
                "id": "gap",
                "point_code": "pathology.inflammation.vascular",
                "summary": "机制解释不完整",
                "confidence": "medium",
                "evidence_message_ids": ["2"],
                "evidence_summary": "学生未区分不同机制。",
            }
        ],
        "reasoning_issues": [],
        "recommended_questions": [
            {
                "title": "讨论炎症证据",
                "prompt": "请说明依据",
                "objective": "机制区别",
                "linked_findings": ["gap"],
            }
        ],
        "phase_assessment": {
            "phase": "synthesis",
            "decision": "complete",
            "evidence_message_ids": ["2"],
            "evidence_summary": "学生完成了综合解释。",
            "missing_elements": [],
        },
    }
)


class _Chat:
    def __init__(self, events):
        self.events = events
        self.parameters = None

    def stream(self, **parameters):
        self.parameters = parameters
        if isinstance(self.events, BaseException):
            raise self.events
        return self.events


class _Client:
    def __init__(self, events):
        self.chat = _Chat(events)

        class _Workflow:
            chat = _Chat(events)

        class _Workflows:
            chat = _Workflow.chat

        self.workflows = _Workflows()


def _request() -> InferenceRequest:
    return InferenceRequest(
        1,
        "pathology.inflammation",
        "为什么会红肿？",
        ({"role": "student", "content": "病例里有充血", "client_message_id": "old"},),
        "anonymous-user",
        "conversation-1",
    )


def test_coze_bot_and_workflow_map_same_completed_fixture() -> None:
    events = [
        {"event": "conversation.message.delta", "data": {"content": READY}},
        {"event": "conversation.chat.completed", "data": {"conversation_id": "conversation-2"}},
    ]
    client = _Client(events)
    bot = CozeBotGateway(client, "bot", "v1").infer(_request())
    workflow = CozeWorkflowGateway(client, "workflow", "app", "app", "v1").infer(_request())
    assert bot.diagnostic_status == workflow.diagnostic_status == "ready"
    assert bot.knowledge_gaps == workflow.knowledge_gaps
    assert bot.conversation_ref == workflow.conversation_ref == "conversation-2"
    assert client.chat.parameters["user_id"] == "anonymous-user"
    assert "conversation_id" in client.workflows.chat.parameters
    assert client.workflows.chat.parameters["app_id"] == "app"


def test_coze_interrupted_or_invalid_payload_is_unavailable() -> None:
    interrupted = _Client([{"event": "conversation.chat.interrupted", "data": {}}])
    assert CozeBotGateway(interrupted, "bot", "v1").infer(_request()).failure_reason == "coze_interrupted"
    workflow_interrupted = _Client([{"event": "workflow.interrupted", "data": {}}])
    assert (
        CozeWorkflowGateway(workflow_interrupted, "workflow", "app", "app", "v1").infer(_request()).failure_reason
        == "coze_interrupted"
    )
    assert CozeBotGateway(_Client([]), "bot", "v1").infer(_request()).failure_reason == "coze_incomplete_stream"
    assert CozeBotGateway(_Client(TimeoutError()), "bot", "v1").infer(_request()).failure_reason == "coze_timeout"
    assert (
        CozeBotGateway(_Client(RuntimeError("coze_rate_limited")), "bot", "v1").infer(_request()).failure_reason
        == "coze_rate_limited"
    )
    assert (
        CozeBotGateway(_Client(ValueError("SDK failure")), "bot", "v1").infer(_request()).failure_reason
        == "coze_sdk_error"
    )
    result = parse_provider_json("not json", {"provider": "coze"})
    assert result.diagnostic_status == "unavailable"
    assert not result.recommended_questions
    invalid_schema = parse_provider_json(
        json.dumps({"assistant_reply": "只有结论", "diagnostic_status": "ready"}), {"provider": "coze"}
    )
    assert invalid_schema.failure_reason == "invalid_provider_response"


def test_openai_compatible_maps_success_and_http_errors(monkeypatch) -> None:
    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": READY}}]}

    monkeypatch.setattr(httpx, "post", lambda *_args, **_kwargs: _Response())
    gateway = OpenAICompatibleGateway("http://mock", "key", "model", 1, "v1")
    assert gateway.infer(_request()).diagnostic_status == "ready"

    def _error(*_args, **_kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(httpx, "post", _error)
    assert gateway.infer(_request()).failure_reason == "openai_compatible_timeout"

    monkeypatch.setattr(httpx, "post", lambda *_args, **_kwargs: _ResponseWithoutChoices())
    assert gateway.infer(_request()).failure_reason == "openai_compatible_invalid_choices"


class _ResponseWithoutChoices:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": []}


def test_provider_messages_are_deidentified_and_history_is_bounded() -> None:
    request = InferenceRequest(
        1,
        "pathology.inflammation",
        "当前问题",
        tuple({"role": "student", "content": f"历史 {index}", "identity": "must-not-leak"} for index in range(25)),
        "anonymous-user",
        "conversation-1",
    )
    messages = provider_messages(request)
    assert len(messages) == 22
    assert json.loads(messages[1]["content"])["text"] == "历史 5"
    assert messages[1]["role"] == "user"
    assert all("identity" not in item for item in messages)
    assert all("anonymous-user" not in item["content"] for item in messages)


def test_provider_configuration_matrix_has_no_cross_provider_fallback(monkeypatch) -> None:
    monkeypatch.setattr(wiring, "build_coze_client", lambda *_args: object())

    with pytest.raises(ValidationError, match="生产环境"):
        Settings(app_env="production", pbl_ai_enabled=True, pbl_ai_provider="openai_compatible")
    with pytest.raises(ValidationError, match="COZE_BOT_ID"):
        Settings(pbl_ai_enabled=True, pbl_ai_provider="coze", coze_api_token="token", coze_invocation_mode="bot")
    with pytest.raises(ValidationError, match="Workflow"):
        Settings(
            pbl_ai_enabled=True,
            pbl_ai_provider="coze",
            coze_api_token="token",
            coze_invocation_mode="workflow",
            coze_workflow_id="workflow",
            coze_app_id="app",
            coze_bot_id="bot",
        )
    with pytest.raises(ValidationError, match="PBL_MOCK_ENABLED"):
        Settings(app_env="development", pbl_mock_enabled=True)

    monkeypatch.setattr(
        wiring,
        "get_settings",
        lambda: Settings(
            pbl_ai_enabled=True,
            pbl_ai_provider="openai_compatible",
            pbl_openai_base_url="http://mock",
            pbl_openai_api_key="key",
            pbl_openai_model="model",
        ),
    )
    gateway, provider, mode = wiring._gateway()
    assert provider == "openai_compatible" and mode is None
    assert isinstance(gateway, OpenAICompatibleGateway)
