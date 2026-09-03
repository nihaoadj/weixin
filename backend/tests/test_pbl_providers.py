from app.modules.pbl.application.records import InferenceRequest
from app.modules.pbl.infrastructure.providers import CozeBotGateway, CozeWorkflowGateway, parse_provider_json

READY = (
    '{"assistant_reply":"请比较急慢性炎症证据。","diagnostic_status":"ready",'
    '"knowledge_gaps":[{"code":"pathology.inflammation"}],"reasoning_issues":[],'
    '"recommended_questions":[{"title":"讨论炎症证据","prompt":"请说明依据",'
    '"linked_findings":["pathology.inflammation"]}]}'
)


class _Chat:
    def stream(self, **_kwargs):
        return [{"content": READY}]


class _WorkflowChat:
    def stream(self, **_kwargs):
        return [{"content": READY}]


class _Client:
    chat = _Chat()

    class workflows:
        chat = _WorkflowChat()


def test_coze_bot_and_workflow_map_same_fixture() -> None:
    request = InferenceRequest(1, "pathology.inflammation", "为什么会红肿？", ())
    bot = CozeBotGateway(_Client(), "bot", "v1").infer(request)
    workflow = CozeWorkflowGateway(_Client(), "workflow", "bot", "v1").infer(request)
    assert bot.diagnostic_status == workflow.diagnostic_status == "ready"
    assert bot.knowledge_gaps == workflow.knowledge_gaps
    assert bot.provider_metadata and workflow.provider_metadata


def test_invalid_provider_payload_is_unavailable() -> None:
    result = parse_provider_json("not json", {"provider": "coze"})
    assert result.diagnostic_status == "unavailable"
    assert not result.recommended_questions
