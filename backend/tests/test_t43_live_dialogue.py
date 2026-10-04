import pytest
from sqlalchemy import func, select

from app.bootstrap.seed import seed_showcase_case
from app.modules.content.infrastructure.models import KnowledgeCardContribution, Problem
from app.modules.learning.infrastructure.route_models import LearningRoute, RouteFinalTest
from app.modules.pbl.infrastructure.models import PblSession
from tests.test_pbl_api import _headers, _login
from tests.test_t44_learning_routes import configure


@pytest.mark.parametrize("message_endpoint", ["pbl-sessions", "learning-dialogues"])
@pytest.mark.parametrize("no_clear_gaps", [False, True])
def test_new_classroom_dialogue_v8_builds_one_route_and_test_shell(
    client, db, monkeypatch, message_endpoint, no_clear_gaps
):
    seed_showcase_case(db)
    gateway = configure(monkeypatch)
    teacher = _login(client, "teacher", "demo_teacher")
    student = _login(client, "student", "demo_student")
    classroom = client.get("/classes", headers=_headers(teacher)).json()[0]
    case = db.scalar(select(Problem).where(Problem.slug == "pathology.inflammation-showcase"))
    created = client.post(
        f"/classes/{classroom['id']}/pbl-sessions",
        headers=_headers(teacher),
        json={
            "topic_code": "pathology.inflammation",
            "case_id": case.id,
            "goal_point_codes": ["pathology.inflammation.vascular"],
        },
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    assert db.get(PblSession, session_id).ai_schema_version == 8

    if message_endpoint == "learning-dialogues":
        started = client.post(
            f"/student/learning-dialogues/{session_id}/start",
            headers=_headers(student),
            json={"interaction_style": "guided"},
        )
        assert started.status_code == 200, started.text

    path = f"/student/{message_endpoint}/{session_id}/messages"
    answers = (
        "为什么出现红肿？",
        "提出血管扩张与通透性变化两个机制假设。",
        "形态证据支持充血与渗出，也存在限制。",
        "无明确薄弱点，已能解释血管反应与证据。"
        if no_clear_gaps
        else "仍需要巩固血管反应机制。",
    )
    response = None
    for index, answer in enumerate(answers):
        response = client.post(
            path,
            headers=_headers(student),
            json={"client_message_id": f"v8-{index}", "content": answer},
        )
        assert response.status_code == 200, response.text

    assert response is not None
    completion = response.json()
    diagnostic = completion["diagnostic"]
    assert diagnostic["schema_version"] == 8
    assert diagnostic["diagnostic_status"] == "ready"
    assert diagnostic["diagnosis_outcome"] == ("no_clear_gaps" if no_clear_gaps else "identified_gaps")
    assert completion["learning_route_id"]
    assert completion["final_test_id"]

    teacher_diagnostic = client.get(
        f"/teacher/pbl-diagnostics/{diagnostic['id']}", headers=_headers(teacher)
    )
    assert teacher_diagnostic.status_code == 200, teacher_diagnostic.text
    assert teacher_diagnostic.json()["diagnosis_outcome"] == diagnostic["diagnosis_outcome"]
    assert teacher_diagnostic.json()["recommended_questions"] == []

    db.expire_all()
    routes = db.scalars(select(LearningRoute)).all()
    tests = db.scalars(select(RouteFinalTest)).all()
    assert len(routes) == 1
    assert len(tests) == 1 and tests[0].route_id == routes[0].id
    assert routes[0].public_id == completion["learning_route_id"]
    assert routes[0].source_kind == "classroom"
    assert routes[0].generation_state == "published"
    assert tests[0].public_id == completion["final_test_id"]
    assert tests[0].generation_state == "ready"
    assert tests[0].review_state == "pending_review"
    assert gateway.tasks.count("learning_route_generation") == 1
    assert gateway.tasks.count("final_test_generation") == 1
    assert (
        db.scalar(
            select(func.count(KnowledgeCardContribution.id)).where(
                KnowledgeCardContribution.source_type == "pbl_ai"
            )
        )
        == 0
    )

    repeated = client.post(
        path,
        headers=_headers(student),
        json={"client_message_id": "v8-3", "content": answers[-1]},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["diagnostic"] == completion["diagnostic"]
    assert repeated.json()["learning_route_id"] == completion["learning_route_id"]
    assert repeated.json()["final_test_id"] == completion["final_test_id"]
    assert gateway.tasks.count("learning_route_generation") == 1
    assert gateway.tasks.count("final_test_generation") == 1
    db.expire_all()
    assert db.scalar(select(func.count(LearningRoute.id))) == 1
    assert db.scalar(select(func.count(RouteFinalTest.id))) == 1
    assert (
        db.scalar(
            select(func.count(KnowledgeCardContribution.id)).where(
                KnowledgeCardContribution.source_type == "pbl_ai"
            )
        )
        == 0
    )
