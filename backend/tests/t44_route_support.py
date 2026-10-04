"""Deterministic route generation helpers for question-bank source tests."""

from sqlalchemy import select

from app.modules.learning.infrastructure.route_models import LearningRoute, RouteFinalTest
from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore
from app.modules.pbl.wiring import LocalMockGateway
from tests.test_pbl_api import _headers

POINT = "pathology.inflammation.vascular"
PHASES = ("pathology_recognition", "mechanism_explanation", "evidence_judgment", "summary_reflection")


class BankRouteGateway(LocalMockGateway):
    def execute_task(self, envelope):
        kind, data = envelope["task_kind"], envelope["input"]
        if kind == "learning_route_generation":
            codes = [point["code"] for point in data["goal_points"]]
            sources = [source["source_id"] for source in data["allowed_sources"]]
            result = {
                "version": 1,
                "title": "机制与证据学习计划",
                "goal_point_codes": codes,
                "learning_rationale": "依据已完成研讨学习",
                "safety_status": "educational",
                "reading_steps": [
                    {
                        "stable_key": "reading",
                        "target_point_codes": codes,
                        "linked_findings": [],
                        "source_ids": sources,
                        "ai_guide": "结合来源区分形态与机制。",
                        "explanation_segments": ["观察变化，再解释机制。"],
                        "learning_points": ["区分观察与推断"],
                    }
                ],
                "synthetic_case": {
                    "stable_key": "case",
                    "title": "合成炎症病例",
                    "public_scenario": "合成教学情境：观察充血与渗出。",
                    "target_point_codes": codes,
                    "case_facts": [{"fact_id": "f1", "text": "组织可见血管扩张与渗出"}],
                    "phases": [
                        {
                            "phase": phase,
                            "goals": [
                                {
                                    "goal_id": phase,
                                    "objective": "联系形态、机制和证据",
                                    "completion_requirements": ["提供当前阶段病理依据"],
                                    "guidance_prompts": ["请解释所见变化的依据。"],
                                }
                            ],
                        }
                        for phase in PHASES[:3]
                    ],
                },
            }
        elif kind == "final_test_generation":
            result = {
                "version": 1,
                "safety_status": "educational",
                "questions": [
                    {
                        "stable_key": f"q-{point['code']}-{index}",
                        "primary_point_code": point["code"],
                        "prompt": f"病理证据判断 {index} {point['code']}",
                        "options": ["结合病理变化与机制", "忽略形态", "直接推定感染", "排除所有不确定性"],
                        "correct_option": 0,
                        "explanation": "应结合形态和机制推理。",
                        "linked_findings": [],
                        "source_ids": [data["allowed_sources"][0]["source_id"]],
                    }
                    for point in data["goal_points"]
                    for index in range(3)
                ],
            }
        else:
            result = {
                "version": 1,
                "learning_response": {
                    "opening": "已收到当前阶段依据。",
                    "key_points": ["联系变化与机制"],
                    "next_step": "请继续下一阶段。",
                },
                "safety_status": "educational",
                "safety_notice": "仅供教学",
                "phase_assessment": {
                    "phase": data["phase"],
                    "decision": "complete" if data["phase"] == PHASES[-1] else "advance",
                    "goal_checks": [
                        {"goal_id": goal["goal_id"], "status": "satisfied"} for goal in data["phase_goals"]
                    ],
                    "evidence_message_ids": [data["current_student_message"]["message_id"]],
                    "missing_elements": [],
                },
            }
        return {"task_kind": kind, "schema_version": 1, "request_id": envelope["request_id"], "result": result}


def configure_bank_route(monkeypatch):
    gateway = BankRouteGateway()
    monkeypatch.setattr("app.modules.pbl.wiring._gateway", lambda: (gateway, "local_mock", "test"))
    original_ensure_shell = SqlLearningRouteStore.ensure_shell

    def legacy_shell(store, context):
        result = original_ensure_shell(store, context)
        route = store.db.scalar(select(LearningRoute).where(LearningRoute.public_id == result["route_id"]))
        test = store.db.scalar(select(RouteFinalTest).where(RouteFinalTest.route_id == route.id))
        test.format_version = "single_choice_v1"
        store.db.flush()
        return result

    monkeypatch.setattr(SqlLearningRouteStore, "ensure_shell", legacy_shell)
    return gateway


def complete_bank_route(client, student, *, session_id=None):
    if session_id is None:
        created = client.post(
            "/student/learning-dialogues",
            headers=_headers(student),
            json={"client_session_id": "bank-route-source", "interaction_style": "guided", "goal_point_codes": [POINT]},
        )
        assert created.status_code == 201, created.text
        session_id = created.json()["session"]["id"]
    else:
        started = client.post(
            f"/student/learning-dialogues/{session_id}/start",
            headers=_headers(student),
            json={"interaction_style": "guided"},
        )
        assert started.status_code == 200, started.text
    for index in range(4):
        reply = client.post(
            f"/student/learning-dialogues/{session_id}/messages",
            headers=_headers(student),
            json={
                "client_message_id": f"bank-phase-{index}",
                "content": "描述形态变化，联系机制，并核对组织证据及其限制。",
            },
        )
        assert reply.status_code == 200, reply.text
    route_id = reply.json()["learning_route_id"]
    assert route_id
    detail = client.get(f"/learning/routes/{route_id}", headers=_headers(student))
    assert detail.status_code == 200, detail.text
    assert detail.json()["summary"]["generation_state"] == "published", detail.text
    return route_id, detail.json()
