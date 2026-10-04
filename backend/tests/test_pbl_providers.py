import json
from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.pbl import wiring
from app.modules.pbl.application.records import InferenceRequest, PrivateFollowupRequest
from app.modules.pbl.infrastructure.checked_gateway import CheckedGateway
from app.modules.pbl.infrastructure.providers import CozeBotGateway, CozeWorkflowGateway, OpenAICompatibleGateway
from app.modules.pbl.infrastructure.providers.coze_parser import parse_private_follow_up_json, parse_provider_json
from app.modules.pbl.infrastructure.providers.request_builder import private_follow_up_messages, provider_messages

READY_V6 = json.dumps(
    {
        "schema_version": 6,
        "interaction_style": "guided",
        "safety_notice": "仅供教学",
        "safety_status": "educational",
        "learning_response": {
            "opening": "请比较急慢性炎症证据。",
            "key_points": ["合成教学要点"],
            "next_step": "研讨已完成。",
        },
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
        "recommended_knowledge_cards": [
            {
                "title": "炎症血管反应补充卡",
                "recall_prompt": "炎症早期的血流和通透性变化分别是什么？",
                "explanation": "先辨认血管扩张与通透性增高，再把形态证据和局部表现对应。",
                "point_code": "pathology.inflammation.vascular",
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
READY_V8 = json.dumps(
    {
        "schema_version": 8,
        "interaction_style": "guided",
        "safety_notice": "仅供教学",
        "safety_status": "educational",
        "learning_response": {
            "opening": "请比较急慢性炎症证据。",
            "key_points": ["合成教学要点"],
            "next_step": "研讨已完成。",
        },
        "diagnostic_status": "ready",
        "diagnosis_outcome": "identified_gaps",
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
        "phase_assessment": {
            "phase": "synthesis",
            "decision": "complete",
            "evidence_message_ids": ["2"],
            "evidence_summary": "学生完成了综合解释。",
            "missing_elements": [],
        },
    }
)
PRIVATE_READY = json.dumps(
    {
        "schema_version": 1,
        "response_kind": "private_follow_up",
        "interaction_style": "direct",
        "learning_response": {
            "opening": "渗出液富含蛋白，来自炎症时血管通透性升高。",
            "key_points": ["内皮间隙增大", "蛋白和液体外渗"],
            "next_step": "你可以再比较渗出液与漏出液。",
        },
        "safety": {"status": "normal", "notice": None},
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
        allowed_points=({"code": "pathology.inflammation.vascular", "title": "炎症血管反应"},),
        schema_version=8,
    )


def _private_request() -> PrivateFollowupRequest:
    return PrivateFollowupRequest(
        session_ref="session-hash",
        participation_ref="participant-hash",
        interaction_style="direct",
        learning_topic="pathology.inflammation",
        learning_goals=("pathology.inflammation.vascular",),
        messages=tuple(
            {
                "id": index,
                "sequence": index,
                "role": "assistant",
                "content": f"旧消息 {index}",
                "turn_scope": "evidence",
            }
            for index in range(1, 25)
        )
        + (
            {
                "id": 99,
                "sequence": 25,
                "role": "student",
                "content": "渗出液是什么？",
                "turn_scope": "private_follow_up",
                "client_message_id": "private-99",
            },
        ),
        latest_student_message_id=99,
    )


def test_coze_bot_and_workflow_map_same_completed_fixture() -> None:
    events = [
        {"event": "conversation.message.delta", "data": {"content": READY_V8}},
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
            return {"choices": [{"message": {"content": READY_V8}}]}

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
        allowed_points=({"code": "pathology.inflammation.vascular", "title": "炎症血管反应"},),
    )
    messages = provider_messages(request)
    assert len(messages) == 22
    assert json.loads(messages[1]["content"])["text"] == "历史 5"
    assert messages[1]["role"] == "user"
    assert all("identity" not in item for item in messages)
    assert all("anonymous-user" not in item["content"] for item in messages)


def test_private_follow_up_contract_is_independent_strict_and_bounded() -> None:
    request = _private_request()
    messages = private_follow_up_messages(request)
    assert len(messages) == 21
    assert json.loads(messages[-1]["content"]) == {
        "message_id": 99,
        "text": "渗出液是什么？",
        "turn_scope": "private_follow_up",
    }
    assert all("session-hash" not in item["content"] for item in messages)
    assert all("participant-hash" not in item["content"] for item in messages)
    result = parse_private_follow_up_json(PRIVATE_READY, {"provider": "test"}, interaction_style="direct")
    assert result.processing_status == "completed"
    assert result.assistant_reply.startswith("回应\n")

    for forbidden in (
        "phase_assessment",
        "knowledge_gaps",
        "reasoning_issues",
        "recommended_questions",
        "recommended_knowledge_cards",
    ):
        payload = json.loads(PRIVATE_READY)
        payload[forbidden] = []
        rejected = parse_private_follow_up_json(json.dumps(payload), {}, interaction_style="direct")
        assert rejected.processing_status == "unavailable"
        assert rejected.failure_reason == "invalid_private_follow_up_response"


def test_private_follow_up_checked_gateway_rejects_style_and_render_mismatch() -> None:
    valid = parse_private_follow_up_json(PRIVATE_READY, {}, interaction_style="direct")

    class _PrivateGateway:
        def private_follow_up(self, _request):
            return replace(valid, interaction_style="guided")

    rejected = CheckedGateway(_PrivateGateway()).private_follow_up(_private_request())
    assert rejected.processing_status == "unavailable"
    assert rejected.failure_reason == "invalid_private_follow_up_response"


def test_coze_and_openai_private_adapters_use_the_same_schema(monkeypatch) -> None:
    events = [
        {"event": "conversation.message.delta", "data": {"content": PRIVATE_READY}},
        {"event": "conversation.chat.completed", "data": {"conversation_id": "private-conversation"}},
    ]
    client = _Client(events)
    bot = CozeBotGateway(client, "bot", "v1").private_follow_up(_private_request())
    workflow = CozeWorkflowGateway(client, "workflow", "app", "app", "v1").private_follow_up(_private_request())
    assert bot.processing_status == workflow.processing_status == "completed"
    assert bot.assistant_reply == workflow.assistant_reply

    class _PrivateResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": PRIVATE_READY}}]}

    monkeypatch.setattr(httpx, "post", lambda *_args, **_kwargs: _PrivateResponse())
    compatible = OpenAICompatibleGateway("http://mock", "key", "model", 1, "v1").private_follow_up(_private_request())
    assert compatible.processing_status == "completed"


def test_schema_v8_carries_and_checks_direct_interaction_style() -> None:
    request = replace(
        _request(),
        interaction_style="direct",
        message_id="current",
        current_revision=1,
    )
    messages = provider_messages(request)
    assert '"interaction_style": "direct"' in messages[0]["content"]
    assert "先准确解释学生当前问题" in messages[0]["content"]

    class _MismatchedGateway:
        def infer(self, value):
            return replace(wiring.LocalMockGateway().infer(value), interaction_style="guided")

    result = CheckedGateway(_MismatchedGateway()).infer(request)
    assert result.diagnostic_status == "unavailable"
    assert result.failure_reason == "invalid_diagnostic_evidence"


def test_local_mock_never_invents_a_catalog_point_when_no_goal_is_requested() -> None:
    without_goal = wiring.LocalMockGateway().infer(replace(_request(), current_phase="synthesis"))
    assert without_goal.knowledge_gaps == ()

    with_goal = wiring.LocalMockGateway().infer(
        replace(
            _request(),
            current_phase="synthesis",
            goal_point_codes=("pathology.inflammation.vascular",),
        )
    )
    assert [gap["point_code"] for gap in with_goal.knowledge_gaps] == ["pathology.inflammation.vascular"]


@pytest.mark.parametrize(
    "sections",
    [
        {"key_points": ["point"], "next_step": "next"},
        {"opening": "opening", "key_points": [], "next_step": "next"},
        {"opening": "opening", "key_points": [" "], "next_step": "next"},
        {"opening": "opening", "key_points": ["x"] * 4, "next_step": "next"},
        {"opening": "x" * 1001, "key_points": ["point"], "next_step": "next"},
        {"opening": "opening", "key_points": ["x" * 501], "next_step": "next"},
        {"opening": "opening", "key_points": ["point"]},
    ],
)
def test_v6_rejects_invalid_sections_without_recording_content(sections):
    payload = json.loads(READY_V6)
    payload["learning_response"] = sections
    result = parse_provider_json(json.dumps(payload), {}, interaction_style="direct")
    assert result.diagnostic_status == "unavailable"
    assert result.interaction_style == "direct"
    assert result.fallback_used
    assert not result.knowledge_gaps and not result.recommended_questions
    assert all(set(issue) == {"path", "type"} for issue in result.provider_metadata["validation_issues"])


def test_mixed_history_and_assistant_evidence_are_not_student_evidence():
    request = replace(
        _request(),
        interaction_style="direct",
        message_id="current",
        current_revision=2,
        history=(
            {
                "id": "assistant",
                "role": "assistant",
                "content": "synthetic explanation",
                "request_revision": 1,
                "interaction_style": "guided",
            },
        ),
    )
    assert json.loads(provider_messages(request)[1]["content"])["interaction_style"] == "guided"

    class InvalidEvidence:
        def infer(self, value):
            result = wiring.LocalMockGateway().infer(value)
            return replace(result, phase_assessment={**result.phase_assessment, "evidence_message_ids": ["assistant"]})

    assert CheckedGateway(InvalidEvidence()).infer(request).diagnostic_status == "unavailable"


@pytest.mark.parametrize("count", [1, 3])
def test_renderer_maximum_fields_fit_without_truncation(count):
    from app.modules.pbl.infrastructure.provider_schema import LearningResponse
    from app.modules.pbl.infrastructure.providers.response_renderer import render_learning_response

    value = LearningResponse(opening="回" * 1000, key_points=["点" * 500] * count, next_step="问" * 1000)
    rendered = render_learning_response(value)
    assert len(rendered) <= 4000
    assert rendered.endswith("问" * 1000)
    assert rendered.count("• ") == count


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
