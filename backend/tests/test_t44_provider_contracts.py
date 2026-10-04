from __future__ import annotations

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.modules.pbl.application.records import InferenceRequest
from app.modules.pbl.infrastructure.checked_gateway import CheckedGateway
from app.modules.pbl.infrastructure.provider_schema import ProviderPayloadV8, RouteCaseTurnInput
from app.modules.pbl.infrastructure.provider_tasks import ProviderTaskFailure
from app.modules.pbl.infrastructure.providers import CozeBotGateway, CozeWorkflowGateway
from app.modules.pbl.infrastructure.providers.coze_parser import parse_provider_json
from app.modules.pbl.infrastructure.providers.request_builder import provider_messages


def _v8_diagnostic() -> dict[str, object]:
    return {
        "schema_version": 8,
        "interaction_style": "guided",
        "learning_response": {
            "opening": "你已经完成本次综合讨论。",
            "key_points": ["证据支持了对炎症血管变化的解释。"],
            "next_step": "继续完成个人学习路线。",
        },
        "diagnostic_status": "ready",
        "diagnosis_outcome": "identified_gaps",
        "knowledge_gaps": [
            {
                "id": "gap-1",
                "point_code": "pathology.inflammation.vascular",
                "summary": "尚未说明内皮通透性变化的机制。",
                "confidence": "medium",
                "evidence_message_ids": ["student-1"],
                "evidence_summary": "学生将血管扩张和通透性变化混为一谈。",
            }
        ],
        "reasoning_issues": [],
        "safety_notice": "仅供病理学教学。",
        "safety_status": "educational",
        "phase_assessment": {
            "phase": "synthesis",
            "decision": "complete",
            "evidence_message_ids": ["student-1"],
            "evidence_summary": "学生完成综合解释。",
            "missing_elements": [],
        },
    }


def _v8_request() -> InferenceRequest:
    return InferenceRequest(
        session_id=12,
        topic_code="pathology.inflammation",
        question="我理解了这组血管变化。",
        history=(),
        message_id="student-1",
        current_phase="synthesis",
        phase_started_revision=0,
        current_revision=1,
        goal_point_codes=("pathology.inflammation.vascular",),
        allowed_points=({"code": "pathology.inflammation.vascular", "title": "炎症血管反应"},),
        schema_version=8,
    )


class _StubGateway:
    def __init__(self, inference_result=None, task_results=None):
        self.inference_result = inference_result
        self.task_results = task_results or {}
        self.received_task = None

    def infer(self, _request):
        return self.inference_result

    def execute_task(self, envelope):
        self.received_task = envelope
        return self.task_results[envelope["task_kind"]]


def test_v8_diagnostic_has_no_embedded_candidate_or_card_contract() -> None:
    data = _v8_diagnostic()
    payload = ProviderPayloadV8.model_validate(data)
    parsed = parse_provider_json(json.dumps(data, ensure_ascii=False), {}, schema_version=8)
    checked = CheckedGateway(_StubGateway(parsed)).infer(_v8_request())
    assert payload.schema_version == 8
    assert checked.diagnostic_status == "ready"
    assert checked.schema_version == 8
    assert checked.candidate_tasks == ()
    assert checked.recommended_questions == ()
    assert checked.recommended_knowledge_cards == ()
    schema_text = json.dumps(ProviderPayloadV8.model_json_schema())
    assert "candidate_tasks" not in schema_text
    assert "recommended_knowledge_cards" not in schema_text


def test_v8_diagnostic_rejects_candidate_or_compensatory_card_fields() -> None:
    for extra_field in ("candidate_tasks", "recommended_knowledge_cards"):
        data = _v8_diagnostic()
        data[extra_field] = []
        with pytest.raises(ValidationError):
            ProviderPayloadV8.model_validate(data)
        result = parse_provider_json(json.dumps(data), {}, schema_version=8)
        assert result.diagnostic_status == "unavailable"


def _allowed_sources() -> list[dict[str, str]]:
    return [
        {
            "source_id": "source-inflammation",
            "title": "炎症基础",
            "institution": "教学资源库",
            "version": "2026.1",
            "url": "https://example.invalid/inflammation",
            "summary": "急性炎症中血管反应和渗出的公开教学材料。",
        }
    ]


def _finding() -> dict[str, str]:
    return {
        "finding_id": "gap-1",
        "kind": "knowledge_gap",
        "target_code": "pathology.inflammation.vascular",
        "summary": "尚未说明通透性变化。",
        "evidence_summary": "学生把血管扩张和通透性变化混为一谈。",
    }


def _route_input() -> dict[str, object]:
    return {
        "source_kind": "autonomous",
        "findings": [_finding()],
        "goal_points": [{"code": "pathology.inflammation.vascular", "title": "炎症血管反应"}],
        "allowed_sources": _allowed_sources(),
    }


def _route_result() -> dict[str, object]:
    return {
        "version": 1,
        "title": "理解炎症血管反应",
        "goal_point_codes": ["pathology.inflammation.vascular"],
        "learning_rationale": "先辨析血流变化，再理解通透性变化与渗出的关系。",
        "reading_steps": [
            {
                "stable_key": "read-vessels",
                "target_point_codes": ["pathology.inflammation.vascular"],
                "linked_findings": ["gap-1"],
                "source_ids": ["source-inflammation"],
                "ai_guide": "阅读时分别标记血管扩张与通透性改变。",
                "explanation_segments": ["血流变化造成红热。", "内皮通透性变化促进液体和蛋白外渗。"],
                "learning_points": ["血流变化", "通透性变化"],
            }
        ],
        "synthetic_case": {
            "stable_key": "case-vessels",
            "title": "一处局部炎症",
            "public_scenario": "患者局部出现红、热和肿胀，组织切片显示微血管充血。",
            "target_point_codes": ["pathology.inflammation.vascular"],
            "case_facts": [{"fact_id": "fact-1", "text": "局部微血管扩张并有蛋白质丰富的液体外渗。"}],
            "phases": [
                {
                    "phase": "pathology_recognition",
                    "goals": [
                        {
                            "goal_id": "recognition-1",
                            "objective": "指出局部血管和组织的形态变化。",
                            "completion_requirements": ["分别指出血管扩张和水肿。"],
                            "guidance_prompts": ["哪些观察属于血管变化？"],
                        }
                    ],
                },
                {
                    "phase": "mechanism_explanation",
                    "goals": [
                        {
                            "goal_id": "mechanism-1",
                            "objective": "解释血管变化的基本机制。",
                            "completion_requirements": ["联系血流和通透性变化解释表现。"],
                            "guidance_prompts": ["血流与内皮通透性分别发生什么变化？"],
                        }
                    ],
                },
                {
                    "phase": "evidence_judgment",
                    "goals": [
                        {
                            "goal_id": "evidence-1",
                            "objective": "用切片和症状支持解释。",
                            "completion_requirements": ["将一条形态证据对应到一个临床表现。"],
                            "guidance_prompts": ["哪条证据支持你的解释？"],
                        }
                    ],
                },
            ],
        },
        "safety_status": "educational",
    }


def _test_input() -> dict[str, object]:
    return {
        "source_kind": "autonomous",
        "findings": [_finding()],
        "goal_points": [{"code": "pathology.inflammation.vascular", "title": "炎症血管反应"}],
        "allowed_sources": _allowed_sources(),
        "route_context": {
            "goal_point_codes": ["pathology.inflammation.vascular"],
            "reading_steps": [
                {
                    "stable_key": "read-vessels",
                    "target_point_codes": ["pathology.inflammation.vascular"],
                    "source_ids": ["source-inflammation"],
                    "learning_points": ["血流变化", "通透性变化"],
                }
            ],
        },
    }


def _test_result() -> dict[str, object]:
    questions = []
    for index, prompt in enumerate(
        (
            "急性炎症早期红和热主要与哪项变化相关？",
            "蛋白质丰富的渗出液最直接提示哪种变化？",
            "局部水肿与下列哪项血管改变关系最直接？",
        ),
        start=1,
    ):
        questions.append(
            {
                "stable_key": f"question-{index}",
                "primary_point_code": "pathology.inflammation.vascular",
                "prompt": prompt,
                "options": ["血管扩张", "血管闭塞", "血小板减少", "淋巴回流增加"],
                "correct_option": 0 if index == 1 else 0,
                "explanation": "血流增加可造成红热，通透性增加使液体和蛋白外渗。",
                "linked_findings": ["gap-1"],
                "source_ids": ["source-inflammation"],
            }
        )
    return {"version": 1, "questions": questions, "safety_status": "educational"}


def _case_input() -> dict[str, object]:
    return {
        "phase": "pathology_recognition",
        "phase_started_revision": 0,
        "current_revision": 2,
        "public_case_scenario": "一处局部炎症伴有红、热和肿胀。",
        "public_case_facts": ["局部发红、发热", "组织间隙有水肿"],
        "phase_goals": [
            {
                "goal_id": "recognition-1",
                "objective": "指出局部形态变化。",
                "completion_requirements": ["明确指出血管扩张", "明确指出组织水肿"],
            }
        ],
        "current_student_message": {"message_id": "case-student-2", "text": "微血管扩张且组织间隙有水肿。"},
        "history": [
            {
                "role": "student",
                "message_id": "case-student-1",
                "text": "局部组织发红。",
                "revision": 1,
                "phase": "pathology_recognition",
            }
        ],
        "current_phase_evidence_message_ids": ["case-student-1", "case-student-2"],
    }


def _case_result() -> dict[str, object]:
    return {
        "version": 1,
        "learning_response": {
            "opening": "你已经识别出主要形态变化。",
            "key_points": ["血管扩张与组织水肿是两项不同观察。"],
            "next_step": "接下来解释这些变化的形成机制。",
        },
        "phase_assessment": {
            "phase": "pathology_recognition",
            "decision": "advance",
            "goal_checks": [{"goal_id": "recognition-1", "status": "satisfied"}],
            "evidence_message_ids": ["case-student-2"],
            "missing_elements": [],
        },
        "safety_status": "educational",
        "safety_notice": "仅供病理学教学。",
    }


@pytest.mark.parametrize(
    ("task_kind", "input_payload", "result"),
    [
        ("learning_route_generation", _route_input(), _route_result()),
        ("final_test_generation", _test_input(), _test_result()),
        ("route_case_turn", _case_input(), _case_result()),
    ],
)
def test_checked_gateway_accepts_all_three_versioned_task_envelopes(task_kind, input_payload, result) -> None:
    candidate = {
        "task_kind": task_kind,
        "schema_version": 1,
        "request_id": "request-44",
        "result": result,
    }
    gateway = CheckedGateway(_StubGateway(task_results={task_kind: candidate}))
    checked = gateway.execute_task(task_kind, "request-44", input_payload)
    assert checked == candidate


def test_checked_gateway_rejects_mismatched_task_id_and_unauthorized_refs() -> None:
    wrong_id = {
        "task_kind": "learning_route_generation",
        "schema_version": 1,
        "request_id": "another-request",
        "result": _route_result(),
    }
    with pytest.raises(ProviderTaskFailure, match="provider_contract_failure"):
        CheckedGateway(_StubGateway(task_results={"learning_route_generation": wrong_id})).execute_task(
            "learning_route_generation", "request-44", _route_input()
        )

    bad_route = _route_result()
    bad_route["reading_steps"][0]["source_ids"] = ["not-allowed"]
    with pytest.raises(ProviderTaskFailure, match="provider_contract_failure"):
        CheckedGateway(
            _StubGateway(
                task_results={
                    "learning_route_generation": {
                        "task_kind": "learning_route_generation",
                        "schema_version": 1,
                        "request_id": "request-44",
                        "result": bad_route,
                    }
                }
            )
        ).execute_task("learning_route_generation", "request-44", _route_input())


def test_case_task_cannot_advance_without_current_revision_evidence() -> None:
    bad_case = _case_result()
    bad_case["phase_assessment"]["evidence_message_ids"] = ["case-student-1"]
    with pytest.raises(ProviderTaskFailure, match="provider_contract_failure"):
        CheckedGateway(
            _StubGateway(
                task_results={
                    "route_case_turn": {
                        "task_kind": "route_case_turn",
                        "schema_version": 1,
                        "request_id": "request-44",
                        "result": bad_case,
                    }
                }
            )
        ).execute_task("route_case_turn", "request-44", _case_input())


def test_case_task_requires_frozen_completion_requirements_per_goal() -> None:
    input_payload = _case_input()
    del input_payload["phase_goals"][0]["completion_requirements"]
    with pytest.raises(ValidationError):
        RouteCaseTurnInput.model_validate(input_payload)


def test_v8_provider_prompt_requests_the_standalone_schema() -> None:
    messages = provider_messages(_v8_request())
    system = messages[0]["content"]
    assert "schema_version=8" in system
    assert '"title": "ProviderPayloadV8"' in system
    assert "不得生成建议题、候选任务、补充知识卡" in system


class _TaskChat:
    def __init__(self, events):
        self.events = events
        self.parameters = None

    def stream(self, **parameters):
        self.parameters = parameters
        return self.events


class _TaskCozeClient:
    def __init__(self, events):
        self.chat = _TaskChat(events)
        self.workflows = type("Workflows", (), {"chat": _TaskChat(events)})()


def test_coze_bot_and_workflow_route_tasks_through_fresh_managed_transport() -> None:
    response = {
        "task_kind": "learning_route_generation",
        "schema_version": 1,
        "request_id": "request-44",
        "result": _route_result(),
    }
    events = [
        {"event": "conversation.message.delta", "data": {"content": json.dumps(response, ensure_ascii=False)}},
        {"event": "conversation.chat.completed", "data": {"conversation_id": "discarded-task-conversation"}},
    ]
    client = _TaskCozeClient(events)
    envelope = {
        "task_kind": "learning_route_generation",
        "schema_version": 1,
        "request_id": "request-44",
        "input": _route_input(),
    }
    bot = CozeBotGateway(client, "bot", "v1").execute_task(envelope)
    workflow = CozeWorkflowGateway(client, "workflow", "app", "app", "v1").execute_task(envelope)
    assert bot == workflow == response
    assert "conversation_id" not in client.chat.parameters
    assert "conversation_id" not in client.workflows.chat.parameters
    assert "task_kind" in client.chat.parameters["additional_messages"][1]["content"]
    assert client.chat.parameters["user_id"].startswith("pbl-task-")


def test_task_gateway_fails_closed_when_configured_provider_has_no_task_transport() -> None:
    class InferenceOnlyGateway:
        def infer(self, _request):
            raise AssertionError("task call must not be translated into a PBL inference")

    with pytest.raises(ProviderTaskFailure, match="provider_contract_failure"):
        CheckedGateway(InferenceOnlyGateway()).execute_task("learning_route_generation", "request-44", _route_input())


def test_legacy_pbl_schemas_are_decode_only_and_never_online_fallbacks() -> None:
    class SpyGateway:
        called = False

        def infer(self, _request):
            self.called = True
            raise AssertionError("legacy request must not reach the configured provider")

    for version in (6, 7):
        request = replace(_v8_request(), schema_version=version)
        provider = SpyGateway()
        result = CheckedGateway(provider).infer(request)
        assert result.diagnostic_status == "unavailable"
        assert result.failure_reason == "unsupported_provider_schema"
        assert not provider.called
        with pytest.raises(ValueError, match="unsupported provider schema"):
            provider_messages(request)
