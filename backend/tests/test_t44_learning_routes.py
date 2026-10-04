"""End-to-end route authorization, transaction, progression and deterministic score."""

import pytest
from sqlalchemy import func, select, text

from app.modules.learning.infrastructure.evidence_models import LearningEvidenceEvent
from app.modules.learning.infrastructure.route_models import LearningRoute, RouteFinalTest, RouteTestAttempt
from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore
from app.modules.pbl.wiring import LocalMockGateway
from tests.test_pbl_api import _classroom, _headers, _login, _session_payload

POINT = "pathology.inflammation.vascular"
PHASES = ("pathology_recognition", "mechanism_explanation", "evidence_judgment", "summary_reflection")


class RouteGateway(LocalMockGateway):
    def __init__(self):
        self.tasks = []
        self.fail = None
        self.unsafe = False

    def execute_task(self, envelope):
        kind, data = envelope["task_kind"], envelope["input"]
        self.last_input = data
        self.tasks.append(kind)
        if self.fail == kind:
            raise TimeoutError()
        if kind == "learning_route_generation":
            codes = [p["code"] for p in data["goal_points"]]
            sources = [s["source_id"] for s in data["allowed_sources"]]
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
                                    "objective": f"{phase}专属目标",
                                    "completion_requirements": ["提供当前阶段病理依据"],
                                    "guidance_prompts": [f"{phase}专属提示"],
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
                        "stable_key": f"q-{point['code']}-{i}",
                        "primary_point_code": point["code"],
                        "prompt": f"病理证据判断 {i} {point['code']}",
                        "options": ["结合病理变化与机制", "忽略形态", "直接推定感染", "排除所有不确定性"],
                        "correct_option": 0,
                        "explanation": "应结合形态和机制推理。",
                        "linked_findings": [],
                        "source_ids": [data["allowed_sources"][0]["source_id"]],
                    }
                    for point in data["goal_points"]
                    for i in range(3)
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
                "safety_status": "needs_human_help" if self.unsafe else "educational",
                "safety_notice": "仅供教学",
                "phase_assessment": {
                    "phase": data["phase"],
                    "decision": "stay" if self.unsafe else ("complete" if data["phase"] == PHASES[-1] else "advance"),
                    "goal_checks": [
                        {"goal_id": g["goal_id"], "status": "needs_more_evidence" if self.unsafe else "satisfied"}
                        for g in data["phase_goals"]
                    ],
                    "evidence_message_ids": [data["current_student_message"]["message_id"]],
                    "missing_elements": ["需要教学支持"] if self.unsafe else [],
                },
            }
        return {"task_kind": kind, "schema_version": 1, "request_id": envelope["request_id"], "result": result}


def configure(monkeypatch):
    gateway = RouteGateway()
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


def test_pending_shell_and_published_route_resume_after_dispatch_interruptions(client, db, monkeypatch):
    from app.modules.learning.infrastructure.route_models import RouteFinalTest
    from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore

    gateway = configure(monkeypatch)
    student = _login(client, "student", "t44-dispatch-interrupt")

    def completed_without_dispatch(client_id):
        with monkeypatch.context() as patch:
            patch.setattr("app.modules.pbl.api.routes._dispatch_learning_route", lambda *_: None)
            created = client.post(
                "/student/learning-dialogues",
                headers=_headers(student),
                json={"client_session_id": client_id, "interaction_style": "guided", "goal_point_codes": [POINT]},
            )
            assert created.status_code == 201, created.text
            session_id = created.json()["session"]["id"]
            for index in range(4):
                reply = client.post(
                    f"/student/learning-dialogues/{session_id}/messages",
                    headers=_headers(student),
                    json={
                        "client_message_id": f"{client_id}-{index}",
                        "content": "结合病理形态、机制和组织依据完成本阶段分析。",
                    },
                )
                assert reply.status_code == 200, reply.text
        return reply.json()["learning_route_id"]

    first_id = completed_without_dispatch("shell-before-claim")
    first = db.scalar(select(LearningRoute).where(LearningRoute.public_id == first_id))
    first_test = db.scalar(select(RouteFinalTest).where(RouteFinalTest.route_id == first.id))
    assert first.generation_state == "pending" and first_test.generation_state == "pending"
    assert first.generation_claim_token is None and first_test.generation_claim_token is None
    resumed = client.post(
        f"/learning/routes/{first_id}/retry-generation",
        headers=_headers(student),
        json={"component": "route", "client_request_id": "resume-shell"},
    )
    assert resumed.status_code == 202, resumed.text
    db.expire_all()
    assert db.scalar(select(LearningRoute).where(LearningRoute.public_id == first_id)).generation_state == "published"
    assert db.scalar(select(RouteFinalTest).where(RouteFinalTest.route_id == first.id)).generation_state == "ready"

    second_id = completed_without_dispatch("published-before-test-claim")
    second = db.scalar(select(LearningRoute).where(LearningRoute.public_id == second_id))
    second_test = db.scalar(select(RouteFinalTest).where(RouteFinalTest.route_id == second.id))
    store = SqlLearningRouteStore(db)
    claim = store.claim_generation(second_id, "route")
    db.commit()
    assert claim["execute"]
    envelope = gateway.execute_task(
        {
            "task_kind": "learning_route_generation",
            "request_id": claim["token"],
            "input": store.generation_input(second_id, "route"),
        }
    )
    store.publish_generation(second_id, "route", claim, envelope["result"])
    db.commit()
    assert second.generation_state == "published" and second_test.generation_state == "pending"
    resumed_test = client.post(
        f"/learning/routes/{second_id}/retry-generation",
        headers=_headers(student),
        json={"component": "test", "client_request_id": "resume-test"},
    )
    assert resumed_test.status_code == 202, resumed_test.text
    db.expire_all()
    assert db.scalar(select(RouteFinalTest).where(RouteFinalTest.route_id == second.id)).generation_state == "ready"
    assert db.scalar(select(func.count(LearningRoute.id))) == 2
    assert db.scalar(select(func.count(RouteFinalTest.id))) == 2


def completed_route(client, student, *, session_id=None):
    if session_id is None:
        created = client.post(
            "/student/learning-dialogues",
            headers=_headers(student),
            json={"client_session_id": "t44-dialogue", "interaction_style": "guided", "goal_point_codes": [POINT]},
        )
        assert created.status_code == 201, created.text
        session_id = created.json()["session"]["id"]
    else:
        assert (
            client.post(
                f"/student/learning-dialogues/{session_id}/start",
                headers=_headers(student),
                json={"interaction_style": "guided"},
            ).status_code
            == 200
        )
    for i in range(4):
        reply = client.post(
            f"/student/learning-dialogues/{session_id}/messages",
            headers=_headers(student),
            json={"client_message_id": f"phase-{i}", "content": "描述形态变化，联系机制，并核对组织证据及其限制。"},
        )
        assert reply.status_code == 200, reply.text
    assert reply.json()["learning_route_id"]
    route_id = reply.json()["learning_route_id"]
    detail = client.get(f"/learning/routes/{route_id}", headers=_headers(student))
    assert detail.status_code == 200, detail.text
    assert detail.json()["summary"]["generation_state"] == "published", detail.text
    return route_id, detail.json()


def learn_route(client, student, route_id, detail):
    steps = detail["steps"]
    assert client.get(f"/learning/route-cases/{steps[-1]['case_id']}", headers=_headers(student)).status_code == 409
    for step in steps[:-1]:
        response = client.post(
            f"/learning/route-steps/{step['id']}/complete-reading",
            headers=_headers(student),
            json={"client_request_id": step["id"]},
        )
        assert response.status_code == 200, response.text
    case_id = steps[-1]["case_id"]
    for i in range(4):
        message = {
            "client_message_id": f"case-{i}",
            "content": "当前病理变化可联系形态、机制和证据。",
            "expected_revision": i,
        }
        reply = client.post(f"/learning/route-cases/{case_id}/messages", headers=_headers(student), json=message)
        assert reply.status_code == 200, reply.text
        replay = client.post(f"/learning/route-cases/{case_id}/messages", headers=_headers(student), json=message)
        assert replay.status_code == 200, replay.text
        assert replay.json()["request_revision"] == i + 1
    assert reply.json()["phase"] == "completed"
    return client.get(f"/learning/routes/{route_id}", headers=_headers(student)).json()


def test_autonomous_unique_result_rounding_privacy_and_answers(client, db, monkeypatch):
    gateway = configure(monkeypatch)
    student, outsider, teacher = [
        _login(client, role, key)
        for role, key in (("student", "t44-student"), ("student", "t44-other"), ("teacher", "t44-teacher"))
    ]
    route_id, detail = completed_route(client, student)
    test_id = detail["test_summary"]["id"]
    repeated = client.post(
        f"/student/learning-dialogues/{detail['summary']['session_locator']}/messages",
        headers=_headers(student),
        json={"client_message_id": "phase-3", "content": "描述形态变化，联系机制，并核对组织证据及其限制。"},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["learning_route_id"] == route_id
    assert gateway.tasks.count("learning_route_generation") == 1
    assert client.get(f"/learning/routes/{route_id}", headers=_headers(outsider)).status_code == 404
    assert client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).status_code == 404
    assert client.get(f"/learning/routes/{route_id}/final-test", headers=_headers(student)).status_code == 409
    assert (
        client.post(
            f"/learning/final-tests/{test_id}/start", headers=_headers(student), json={"client_request_id": "early"}
        ).status_code
        == 409
    )
    detail = learn_route(client, student, route_id, detail)
    assert detail["can_start_test"]
    response = client.post(
        f"/learning/final-tests/{test_id}/start", headers=_headers(student), json={"client_request_id": "start"}
    )
    assert response.status_code == 200, response.text
    test = response.json()
    assert "correct_option" not in test["questions"][0]
    answers = {q["id"]: (0 if i < 2 else 1) for i, q in enumerate(test["questions"])}
    payload = {
        "expected_version": 1,
        "released_digest": test["released_digest"],
        "answers": answers,
        "client_submission_id": "submit",
    }
    response = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["score"] == 66.7
    assert result["correct_count"] == 2
    replay = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
    assert replay.json()["id"] == result["id"]
    assert db.scalar(select(func.count(RouteTestAttempt.id))) == 1
    assert (
        db.scalar(
            select(func.count(LearningEvidenceEvent.id)).where(
                LearningEvidenceEvent.source_type == "private_final_test"
            )
        )
        == 1
    )
    assert not client.get(f"/learning/routes/{route_id}", headers=_headers(student)).json()["can_start_test"]
    assert (
        client.post(
            f"/learning/final-tests/{test_id}/start", headers=_headers(student), json={"client_request_id": "again"}
        ).status_code
        == 409
    )
    assert gateway.tasks.count("route_case_turn") == 4


@pytest.mark.seed_showcase
def test_classroom_requires_teacher_release_and_freezes_version(client, db, monkeypatch):
    configure(monkeypatch)
    teacher = _login(client, "teacher", "t44-owner")
    student = _login(client, "student", "t44-member")
    class_id = _classroom(client, teacher, "t44-member")
    created = client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db))
    assert created.status_code == 201, created.text
    route_id, detail = completed_route(client, student, session_id=created.json()["id"])
    test_id = detail["test_summary"]["id"]
    assert detail["test_summary"]["review_state"] == "pending_review"
    learn_route(client, student, route_id, detail)
    blocked = client.get(f"/learning/routes/{route_id}/final-test", headers=_headers(student))
    assert blocked.status_code == 409
    test = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).json()
    release = {
        "client_request_id": "release",
        "expected_version": test["version"],
        "draft_digest": test["draft_digest"],
    }
    response = client.post(f"/learning/teacher/final-tests/{test_id}/release", headers=_headers(teacher), json=release)
    assert response.status_code == 200, response.text
    response = client.put(
        f"/learning/teacher/final-tests/{test_id}",
        headers=_headers(teacher),
        json={
            "client_request_id": "save",
            "expected_version": test["version"],
            "questions": [{k: v for k, v in q.items() if k != "source_digest"} for q in test["questions"]],
        },
    )
    assert response.status_code == 409
    assert client.get(f"/learning/routes/{route_id}/final-test", headers=_headers(student)).status_code == 200
    attempt = client.post(
        f"/learning/final-tests/{test_id}/start", headers=_headers(student), json={"client_request_id": "start"}
    ).json()
    payload = {
        "expected_version": 1,
        "released_digest": attempt["released_digest"],
        "answers": {q["id"]: (0 if i < 2 else 1) for i, q in enumerate(attempt["questions"])},
        "client_submission_id": "submit",
    }
    result = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
    assert result.status_code == 200, result.text
    assert result.json()["score"] == 66.7
    overview = client.get(f"/analytics/overview?class_id={class_id}", headers=_headers(teacher))
    assert overview.status_code == 200, overview.text
    assert overview.json()["completed_tests"] == overview.json()["published_routes"] == 1
    assert overview.json()["completion_rate"] == 100
    assert overview.json()["knowledge"][0]["correct_count"] == 2
    assert overview.json()["knowledge"][0]["question_count"] == 3
    assert "dimensions" not in overview.json()
    dashboard = client.get(
        f"/classes/{class_id}/pbl-sessions/{created.json()['id']}/dashboard", headers=_headers(teacher)
    )
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["summary"]["completed_routes"] == 1
    assert dashboard.json()["students"][0]["score"] == 66.7
    assert (
        db.scalar(
            select(func.count(LearningEvidenceEvent.id)).where(
                LearningEvidenceEvent.source_type == "classroom_final_test"
            )
        )
        == 1
    )


def test_generation_failure_keeps_completion_and_pending_test_recoverable(client, db, monkeypatch):
    gateway = configure(monkeypatch)
    gateway.fail = "final_test_generation"
    student = _login(client, "student", "t44-failure")
    route_id, detail = completed_route(client, student)
    assert detail["summary"]["generation_state"] == "published"
    assert detail["test_summary"]["generation_state"] == "generation_failed"
    from app.modules.learning.infrastructure.route_models import RouteFinalTest

    pending = db.scalar(select(RouteFinalTest).where(RouteFinalTest.public_id == detail["test_summary"]["id"]))
    pending.generation_state = "pending"
    pending.generation_claim_expires_at = None
    pending.generation_execution_state = None
    db.commit()
    gateway.fail = None
    retry = client.post(
        f"/learning/routes/{route_id}/retry-generation",
        headers=_headers(student),
        json={"component": "test", "client_request_id": "recover"},
    )
    assert retry.status_code == 202, retry.text
    assert (
        client.get(f"/learning/routes/{route_id}", headers=_headers(student)).json()["test_summary"]["generation_state"]
        == "ready"
    )
    assert gateway.tasks.count("learning_route_generation") == 1
    assert db.scalar(select(func.count(LearningRoute.id))) == 1


def test_reading_lease_replay_and_no_minimum_duration(client, db, monkeypatch):
    configure(monkeypatch)
    student = _login(client, "student", "t44-reading")
    route_id, detail = completed_route(client, student)
    step_id = detail["steps"][0]["id"]
    reading = client.get(f"/learning/route-steps/{step_id}", headers=_headers(student))
    assert reading.status_code == 200, reading.text
    assert reading.json()["sections"][0]["text"]
    response = client.post(
        f"/learning/route-steps/{step_id}/reading-progress",
        headers=_headers(student),
        json={"client_request_id": "lease", "action": "start"},
    )
    assert response.status_code == 200, response.text
    lease = response.json()["lease_token"]
    payload = {"client_request_id": "heartbeat", "action": "heartbeat", "lease_token": lease}
    first = client.post(f"/learning/route-steps/{step_id}/reading-progress", headers=_headers(student), json=payload)
    second = client.post(f"/learning/route-steps/{step_id}/reading-progress", headers=_headers(student), json=payload)
    assert first.json()["accumulated_seconds"] == second.json()["accumulated_seconds"]
    new_lease = client.post(
        f"/learning/route-steps/{step_id}/reading-progress",
        headers=_headers(student),
        json={"client_request_id": "new-tab", "action": "start"},
    )
    assert new_lease.json()["lease_token"] != lease
    old_replay = client.post(
        f"/learning/route-steps/{step_id}/reading-progress",
        headers=_headers(student),
        json={"client_request_id": "lease", "action": "start"},
    )
    assert old_replay.json()["lease_token"] == lease
    stale_lease = client.post(
        f"/learning/route-steps/{step_id}/reading-progress",
        headers=_headers(student),
        json={"client_request_id": "old-tab", "action": "heartbeat", "lease_token": lease},
    )
    assert stale_lease.status_code == 409

    response = client.post(
        f"/learning/route-steps/{step_id}/complete-reading",
        headers=_headers(student),
        json={"client_request_id": "complete"},
    )
    assert response.status_code == 200
    assert response.json()["steps"][1]["status"] == "available"


def test_knowledge_material_and_new_discussion_do_not_use_retired_tables(client, db, monkeypatch):
    configure(monkeypatch)
    student = _login(client, "student", "t44-knowledge-entry")
    for table in (
        "study_practice_attempts",
        "study_practice_groups",
        "study_paths",
        "classroom_question_reviews",
        "t43_legacy_plan_mappings",
        "classroom_final_reports",
        "classroom_package_items",
        "classroom_task_packages",
        "teaching_command_receipts",
        "pbl_question_suggestions",
        "pbl_submissions",
        "pbl_teacher_feedbacks",
    ):
        db.execute(text(f"DROP TABLE IF EXISTS {table}"))
    db.commit()
    response = client.get(f"/learning/knowledge-points/{POINT}/study", headers=_headers(student))
    assert response.status_code == 200, response.text
    assert response.json()["sessions"] == []
    start = client.post(
        f"/learning/knowledge-points/{POINT}/study/start",
        headers=_headers(student),
        json={"client_id": "knowledge-start", "interaction_style": "guided"},
    )
    assert start.status_code == 200, start.text
    assert start.json()["session_id"] > 0
    assert "path_id" not in start.json()
    retired = client.post(
        "/learning/study-paths/1/practices", headers=_headers(student), json={"client_id": "retired", "cycle": 1}
    )
    assert retired.status_code == 409
    assert retired.json()["detail"]["reason"] == "RETIRED_FLOW"
    route_id, detail = completed_route(client, student)
    assert detail["summary"]["generation_state"] == "published"
    learn_route(client, student, route_id, detail)


def test_case_failed_turn_recovers_same_message_and_unsafe_does_not_advance(client, db, monkeypatch):
    gateway = configure(monkeypatch)
    student = _login(client, "student", "t44-case-recovery")
    route_id, detail = completed_route(client, student)
    step = detail["steps"][0]
    client.post(
        f"/learning/route-steps/{step['id']}/complete-reading",
        headers=_headers(student),
        json={"client_request_id": "read"},
    )
    case_id = detail["steps"][-1]["case_id"]
    payload = {
        "client_message_id": "recover-case",
        "content": "根据血管变化说明组织证据与机制。",
        "expected_revision": 0,
    }
    gateway.fail = "route_case_turn"
    failed = client.post(f"/learning/route-cases/{case_id}/messages", headers=_headers(student), json=payload)
    assert failed.status_code == 503, failed.text
    gateway.fail = None
    gateway.unsafe = True
    recovered = client.post(f"/learning/route-cases/{case_id}/messages", headers=_headers(student), json=payload)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["phase"] == PHASES[0]
    assert not client.get(f"/learning/routes/{route_id}", headers=_headers(student)).json()["can_start_test"]
    gateway.unsafe = False
    corrected = client.post(
        f"/learning/route-cases/{case_id}/messages",
        headers=_headers(student),
        json={**payload, "client_message_id": "correction", "expected_revision": 1},
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["phase"] == PHASES[1]
    stale = client.post(
        f"/learning/route-cases/{case_id}/messages",
        headers=_headers(student),
        json={**payload, "client_message_id": "stale"},
    )
    assert stale.status_code == 409, stale.text


def test_submission_rejects_partial_foreign_boolean_and_stale_digest(client, db, monkeypatch):
    configure(monkeypatch)
    student = _login(client, "student", "t44-invalid-answers")
    route_id, detail = completed_route(client, student)
    learn_route(client, student, route_id, detail)
    test_id = detail["test_summary"]["id"]
    attempt = client.post(
        f"/learning/final-tests/{test_id}/start", headers=_headers(student), json={"client_request_id": "start"}
    ).json()
    answers = {q["id"]: 0 for q in attempt["questions"]}
    base = {
        "expected_version": 1,
        "released_digest": attempt["released_digest"],
        "answers": answers,
        "client_submission_id": "invalid",
    }
    for payload in (
        {**base, "answers": {}},
        {**base, "answers": {**answers, "foreign": 0}},
        {**base, "answers": {k: True for k in answers}},
        {**base, "released_digest": "stale"},
    ):
        response = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
        assert response.status_code in (409, 422), response.text
    valid = client.post(
        f"/learning/final-tests/{test_id}/submit",
        headers=_headers(student),
        json={**base, "answers": {k: 1 for k in answers}, "client_submission_id": "valid"},
    )
    assert valid.status_code == 200, valid.text
    assert valid.json()["score"] == 0.0
    changed = client.post(
        f"/learning/final-tests/{test_id}/submit",
        headers=_headers(student),
        json={**base, "client_submission_id": "valid"},
    )
    assert changed.status_code == 409, changed.text


def test_generation_claim_expiry_and_late_reply_do_not_replace_content(client, db, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore

    gateway = configure(monkeypatch)
    gateway.fail = "learning_route_generation"
    student = _login(client, "student", "t44-route-claim")
    created = client.post(
        "/student/learning-dialogues",
        headers=_headers(student),
        json={"client_session_id": "claim-dialogue", "interaction_style": "guided", "goal_point_codes": [POINT]},
    ).json()
    for i in range(4):
        reply = client.post(
            f"/student/learning-dialogues/{created['session']['id']}/messages",
            headers=_headers(student),
            json={"client_message_id": f"phase-{i}", "content": "观察病理形态，解释机制并核对组织依据。"},
        )
    route_id = reply.json()["learning_route_id"]
    pending_route = db.scalar(select(LearningRoute).where(LearningRoute.public_id == route_id))
    pending_route.generation_state = "pending"
    pending_route.generation_claim_expires_at = None
    pending_route.generation_execution_state = None
    db.commit()
    store = SqlLearningRouteStore(db)
    first = store.claim_generation(route_id, "route")
    db.commit()
    assert first["execute"]
    assert not store.claim_generation(route_id, "route")["execute"]
    route = db.scalar(select(LearningRoute).where(LearningRoute.public_id == route_id))
    route.generation_claim_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    replacement = store.claim_generation(route_id, "route")
    db.commit()
    assert replacement["execute"] and replacement["token"] != first["token"]
    gateway.fail = None
    envelope = gateway.execute_task(
        {
            "task_kind": "learning_route_generation",
            "request_id": "claim",
            "input": store.generation_input(route_id, "route"),
        }
    )
    from app.shared.errors import AppError

    with pytest.raises(AppError):
        store.publish_generation(route_id, "route", first, envelope["result"])
    db.rollback()
    store.publish_generation(route_id, "route", replacement, envelope["result"])
    db.commit()
    assert store.detail(route_id)["summary"]["generation_state"] == "published"
    assert not store.claim_generation(route_id, "route")["execute"]


def test_evidence_failure_rolls_back_result_and_answer_submission(client, db, monkeypatch):
    from app.modules.learning.application.evidence import LearningEvidenceApplication
    from app.modules.learning.infrastructure.route_models import RouteLearningResult
    from app.shared.errors import AppError

    configure(monkeypatch)
    student = _login(client, "student", "t44-evidence-rollback")
    route_id, detail = completed_route(client, student)
    learn_route(client, student, route_id, detail)
    test_id = detail["test_summary"]["id"]
    attempt = client.post(
        f"/learning/final-tests/{test_id}/start", headers=_headers(student), json={"client_request_id": "start"}
    ).json()
    original = LearningEvidenceApplication.append

    def reject(self, command):
        raise AppError("STATE_CONFLICT", "证据暂不可写入", 409)

    monkeypatch.setattr(LearningEvidenceApplication, "append", reject)
    payload = {
        "expected_version": 1,
        "released_digest": attempt["released_digest"],
        "answers": {q["id"]: 0 for q in attempt["questions"]},
        "client_submission_id": "submit",
    }
    response = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
    assert response.status_code == 409
    db.expire_all()
    assert db.scalar(select(func.count(RouteLearningResult.id))) == 0
    assert db.scalar(select(RouteTestAttempt)).status == "in_progress"
    monkeypatch.setattr(LearningEvidenceApplication, "append", original)
    response = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["score"] == 100.0


@pytest.mark.seed_showcase
def test_teacher_locator_edit_conflict_inactive_scope_and_historical_read(client, db, monkeypatch):
    from app.modules.classroom.infrastructure.models import ClassRoom

    configure(monkeypatch)
    teacher = _login(client, "teacher", "t44-scope-owner")
    outsider = _login(client, "teacher", "t44-scope-outsider")
    student = _login(client, "student", "t44-scope-member")
    class_id = _classroom(client, teacher, "t44-scope-member")
    session = client.post(
        f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db)
    ).json()
    route_id, detail = completed_route(client, student, session_id=session["id"])
    test_id = detail["test_summary"]["id"]
    work = client.get("/teacher/pbl-work-items", headers=_headers(teacher)).json()["items"][0]
    assert work["final_test_id"] == test_id and work["learning_route_id"] == route_id
    dashboard = client.get(f"/classes/{class_id}/pbl-sessions/{session['id']}/dashboard", headers=_headers(teacher))
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["summary"]["published_routes"] == 1
    assert dashboard.json()["summary"]["completed_routes"] == 0
    assert dashboard.json()["students"][0]["score"] is None
    assert client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(outsider)).status_code == 404
    test = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).json()
    questions = [{k: v for k, v in q.items() if k != "source_digest"} for q in test["questions"]]
    from copy import deepcopy
    from uuid import uuid4

    for reason in ("duplicate_options", "foreign_question"):
        invalid = deepcopy(questions)
        if reason == "duplicate_options":
            invalid[0]["options"][1] = " " + invalid[0]["options"][0] + " "
        else:
            invalid[0]["id"] = str(uuid4())
        rejected = client.put(
            f"/learning/teacher/final-tests/{test_id}",
            headers=_headers(teacher),
            json={"client_request_id": reason, "expected_version": test["version"], "questions": invalid},
        )
        assert rejected.status_code == 422, rejected.text
        unchanged = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).json()
        assert unchanged["version"] == test["version"]
        assert unchanged["draft_digest"] == test["draft_digest"]
    questions[0]["prompt"] = "编辑后：应如何联系形态和机制？"
    save = client.put(
        f"/learning/teacher/final-tests/{test_id}",
        headers=_headers(teacher),
        json={"client_request_id": "edit", "expected_version": test["version"], "questions": questions},
    )
    assert save.status_code == 200, save.text
    assert save.json()["version"] == test["version"] + 1
    stale = {
        "client_request_id": "release-old",
        "expected_version": test["version"],
        "draft_digest": test["draft_digest"],
    }
    assert (
        client.post(
            f"/learning/teacher/final-tests/{test_id}/release", headers=_headers(teacher), json=stale
        ).status_code
        == 409
    )
    learn_route(client, student, route_id, detail)
    classroom = db.get(ClassRoom, class_id)
    classroom.status = "archived"
    db.commit()
    frozen = client.get(f"/learning/routes/{route_id}", headers=_headers(student))
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["summary"]["scope_status"] == "inactive"
    assert frozen.json()["summary"]["next_action"] == "contact_teacher"
    for component in ("route", "test"):
        forbidden_retry = client.post(
            f"/learning/routes/{route_id}/retry-generation",
            headers=_headers(student),
            json={"component": component, "client_request_id": "inactive-" + component},
        )
        assert forbidden_retry.status_code == 409, forbidden_retry.text
        assert forbidden_retry.json()["detail"]["reason"] == "CLASSROOM_SCOPE_INACTIVE"
    assert client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).status_code == 200
    current = save.json()
    release = {
        "client_request_id": "release",
        "expected_version": current["version"],
        "draft_digest": current["draft_digest"],
    }
    assert (
        client.post(
            f"/learning/teacher/final-tests/{test_id}/release", headers=_headers(teacher), json=release
        ).status_code
        == 409
    )
    classroom.status = "active"
    db.commit()
    assert (
        client.post(
            f"/learning/teacher/final-tests/{test_id}/release", headers=_headers(teacher), json=release
        ).status_code
        == 200
    )
    replayed_save = client.put(
        f"/learning/teacher/final-tests/{test_id}",
        headers=_headers(teacher),
        json={"client_request_id": "edit", "expected_version": test["version"], "questions": questions},
    )
    assert replayed_save.status_code == 200, replayed_save.text
    assert replayed_save.json() == save.json()
    classroom.status = "archived"
    db.commit()
    started = client.post(
        f"/learning/final-tests/{test_id}/start", headers=_headers(student), json={"client_request_id": "start"}
    )
    assert started.status_code == 200, started.text
    assert (
        client.get(f"/classes/{class_id}/pbl-sessions/{session['id']}/dashboard", headers=_headers(teacher)).status_code
        == 200
    )


def test_draft_recovery_receipt_and_transactional_notifications(client, db, monkeypatch):
    from app.modules.learning.infrastructure.models import StudentNotification

    configure(monkeypatch)
    student = _login(client, "student", "t44-draft")
    route_id, detail = completed_route(client, student)
    learn_route(client, student, route_id, detail)
    test_id = detail["test_summary"]["id"]
    attempt = client.post(
        f"/learning/final-tests/{test_id}/start", headers=_headers(student), json={"client_request_id": "start"}
    ).json()
    first_id = attempt["questions"][0]["id"]
    payload = {
        "client_request_id": "save",
        "expected_version": 1,
        "released_digest": attempt["released_digest"],
        "answers": {first_id: 2},
    }
    saved = client.put(f"/learning/final-tests/{test_id}/draft", headers=_headers(student), json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == 2
    loaded = client.get(f"/learning/routes/{route_id}/final-test", headers=_headers(student)).json()
    assert loaded["attempt"]["answers"] == {first_id: 2}
    payload2 = {**payload, "client_request_id": "save-again", "expected_version": 2, "answers": {first_id: 1}}
    assert (
        client.put(f"/learning/final-tests/{test_id}/draft", headers=_headers(student), json=payload2).status_code
        == 200
    )
    replay = client.put(f"/learning/final-tests/{test_id}/draft", headers=_headers(student), json=payload)
    assert replay.json() == saved.json()
    response = client.post(
        f"/learning/final-tests/{test_id}/submit",
        headers=_headers(student),
        json={
            "client_submission_id": "submit",
            "expected_version": 3,
            "released_digest": attempt["released_digest"],
            "answers": {q["id"]: 0 for q in attempt["questions"]},
        },
    )
    assert response.status_code == 200, response.text
    notifications = client.get("/notifications", headers=_headers(student))
    assert notifications.status_code == 200, notifications.text
    assert {row["type"] for row in notifications.json()["items"]} == {
        "learning_route_ready",
        "final_test_released",
        "learning_route_completed",
    }
    assert all(row["entity_id"] == route_id for row in notifications.json()["items"])
    assert (
        db.scalar(select(func.count(StudentNotification.id)).where(StudentNotification.entity_public_id == route_id))
        == 3
    )


@pytest.mark.parametrize("classroom", [False, True])
def test_completion_shell_failure_rolls_back_frozen_analysis_and_recovers(client, db, monkeypatch, classroom):
    from datetime import UTC, datetime, timedelta

    from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore
    from app.modules.pbl.infrastructure.models import PblDiagnosticSnapshot, PblMessage, PblParticipation
    from app.shared.errors import AppError

    gateway = configure(monkeypatch)
    student = _login(client, "student", "t44-shell-student")
    if classroom:
        teacher = _login(client, "teacher", "t44-shell-teacher")
        class_id = _classroom(client, teacher, "t44-shell-student")
        created = client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db))
        assert created.status_code == 201, created.text
        session_id = created.json()["id"]
        base = f"/student/pbl-sessions/{session_id}"
    else:
        created = client.post(
            "/student/learning-dialogues",
            headers=_headers(student),
            json={
                "client_session_id": "t44-shell-dialogue",
                "interaction_style": "guided",
                "goal_point_codes": [POINT],
            },
        )
        assert created.status_code == 201, created.text
        session_id = created.json()["session"]["id"]
        base = f"/student/learning-dialogues/{session_id}"
    for phase in range(3):
        reply = client.post(
            base + "/messages",
            headers=_headers(student),
            json={"client_message_id": f"shell-{phase}", "content": "依据病理形态解释机制并核对证据。"},
        )
        assert reply.status_code == 200, reply.text

    original = SqlLearningRouteStore.ensure_shell

    def fail_after_flush(store, context):
        original(store, context)
        raise AppError("SERVICE_ERROR", "学习计划暂不可用", 503)

    monkeypatch.setattr(SqlLearningRouteStore, "ensure_shell", fail_after_flush)
    failed = client.post(
        base + "/messages",
        headers=_headers(student),
        json={"client_message_id": "shell-final", "content": "综合形态、机制与证据，说明判断限制。"},
    )
    assert failed.status_code == 503, failed.text
    db.expire_all()
    participation = db.scalar(select(PblParticipation).where(PblParticipation.session_id == session_id))
    assert participation.phase_status != "completed"
    assert participation.completion_snapshot_id is None
    assert db.scalar(select(func.count(LearningRoute.id))) == 0
    assert (
        db.scalar(
            select(func.count(PblDiagnosticSnapshot.id)).where(PblDiagnosticSnapshot.phase_decision == "complete")
        )
        == 0
    )
    assert db.scalar(select(func.count(LearningEvidenceEvent.id))) == 0
    assert not gateway.tasks

    # Existing PBL timeout recovery settles the committed request key, allowing
    # a new response without freezing the failed completion or creating a route.
    pending = db.scalar(select(PblMessage).where(PblMessage.client_message_id == "shell-final"))
    assert pending.processing_status == "pending"
    pending.created_at = datetime.now(UTC) - timedelta(seconds=61)
    db.commit()
    monkeypatch.setattr(SqlLearningRouteStore, "ensure_shell", original)
    recovered = client.post(
        base + "/messages",
        headers=_headers(student),
        json={"client_message_id": "shell-recovered", "content": "综合形态、机制与证据，说明判断限制。"},
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["learning_route_id"]
    db.expire_all()
    assert db.scalar(select(func.count(LearningRoute.id))) == 1


def test_expired_case_claim_recovers_same_message_and_rejects_late_reply(client, db, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.modules.learning.infrastructure.route_models import RouteCaseMessage, RouteCasePhaseDecision
    from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore
    from app.shared.errors import AppError

    gateway = configure(monkeypatch)
    student = _login(client, "student", "t44-case-late")
    route_id, detail = completed_route(client, student)
    for step in detail["steps"][:-1]:
        completed = client.post(
            f"/learning/route-steps/{step['id']}/complete-reading",
            headers=_headers(student),
            json={"client_request_id": step["id"]},
        )
        assert completed.status_code == 200, completed.text
    case_id = detail["steps"][-1]["case_id"]
    store = SqlLearningRouteStore(db)
    claim = store.claim_case_message(case_id, "recover-expired", "当前形态变化与机制相互支持。", 0)
    assert claim["execute"]
    db.commit()
    pending = db.get(RouteCaseMessage, claim["message_id"])
    pending.processing_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    resumed = client.post(
        f"/learning/route-cases/{case_id}/messages",
        headers=_headers(student),
        json={
            "client_message_id": "recover-expired",
            "content": "当前形态变化与机制相互支持。",
            "expected_revision": 0,
        },
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["phase"] == "mechanism_explanation"
    assert resumed.json()["request_revision"] == 1
    db.expire_all()
    late = gateway.execute_task(
        {"task_kind": "route_case_turn", "request_id": claim["token"], "input": claim["input"]}
    )["result"]
    with pytest.raises(AppError) as conflict:
        store.save_case_reply(case_id, claim, late)
    assert conflict.value.reason == "VERSION_CONFLICT"
    db.rollback()
    assert db.scalar(select(func.count(RouteCasePhaseDecision.id))) == 1
    assert db.scalar(select(func.count(RouteCaseMessage.id)).where(RouteCaseMessage.role == "student")) == 1
    current = client.get(f"/learning/route-cases/{case_id}", headers=_headers(student))
    assert current.json()["phase"] == "mechanism_explanation"
    assert current.json()["revision"] == 1


def test_four_stage_chat_preserves_history_and_returns_original_message_phases(client, db, monkeypatch):
    gateway = configure(monkeypatch)
    student = _login(client, "student", "t45-chat")
    route_id, detail = completed_route(client, student)
    for step in detail["steps"][:-1]:
        assert (
            client.post(
                f"/learning/route-steps/{step['id']}/complete-reading",
                headers=_headers(student),
                json={"client_request_id": step["id"]},
            ).status_code
            == 200
        )
    case_id = detail["steps"][-1]["case_id"]
    for index, phase in enumerate(PHASES):
        current = client.get(f"/learning/route-cases/{case_id}", headers=_headers(student)).json()
        assert current["phase"] == phase
        assert [stage["phase"] for stage in current["stages"]] == list(PHASES)
        assert current["stages"][0]["goals"] == [
            {"goal_id": "pathology_recognition", "objective": "pathology_recognition专属目标"}
        ]
        assert current["stages"][0]["prompt"] == "pathology_recognition专属提示"
        assert current["stages"][3]["goals"][0]["goal_id"] == "summary_reflection.reasoning"
        assert current["goals"] == current["stages"][index]["goals"]
        assert current["next_prompt"] == current["stages"][index]["prompt"]
        assert "completion_requirements" not in str(current)
        reply = client.post(
            f"/learning/route-cases/{case_id}/messages",
            headers=_headers(student),
            json={
                "client_message_id": f"t45-{index}",
                "content": "根据事实解释病理机制，反思不确定之处并计划核对资料。",
                "expected_revision": index,
            },
        )
        assert reply.status_code == 200, reply.text
        assert gateway.last_input["phase"] == phase
        assert {m["phase"] for m in gateway.last_input["history"]} == set(PHASES[:index])
        assert all(
            m["message_id"] not in gateway.last_input["current_phase_evidence_message_ids"]
            for m in gateway.last_input["history"]
        )
        if phase == "evidence_judgment":
            assert reply.json()["phase"] == "summary_reflection"
            assert reply.json()["status"] != "completed"
    final = client.get(f"/learning/route-cases/{case_id}", headers=_headers(student)).json()
    assert final["phase"] == "completed"
    assert final["goals"] == []
    assert final["stages"][0]["prompt"] == "pathology_recognition专属提示"
    assert final["stages"][3]["goals"][1]["goal_id"] == "summary_reflection.improvement"
    assert [m["phase"] for m in final["messages"]] == [phase for phase in PHASES for _ in range(2)]
