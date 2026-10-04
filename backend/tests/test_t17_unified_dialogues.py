import pytest
from sqlalchemy import func, select

from app.modules.pbl.infrastructure.models import PblParticipation, PblSession
from tests.test_pbl_api import _classroom, _configure_gateway, _headers, _login, _session_payload


def _create_dialogue(client, token: str, class_id: int, client_id: str = "dialogue-1", style: str = "direct"):
    return client.post(
        "/student/learning-dialogues",
        headers=_headers(token),
        json={
            "client_session_id": client_id,
            "class_id": class_id,
            "interaction_style": style,
            "goal_point_codes": ["pathology.inflammation.vascular"],
        },
    )


def test_student_dialogue_is_private_without_a_class_and_classroom_lists_remain_scoped(client, monkeypatch) -> None:
    _configure_gateway(monkeypatch)
    student = _login(client, "student", "t17-no-class")
    assert client.get("/student/classes", headers=_headers(student)).json() == []
    created = _create_dialogue(client, student, 999)
    assert created.status_code == 201
    assert created.json()["session"]["class_id"] is None

    teacher = _login(client, "teacher", "t17-class-owner")
    first_id = _classroom(client, teacher, "t17-no-class")
    second = client.post("/classes", headers=_headers(teacher), json={"name": "PBL 二班", "code": "t17-b"})
    assert second.status_code == 200
    added = client.post(
        f"/classes/{second.json()['id']}/members",
        headers=_headers(teacher),
        json={"student_external_id": "t17-no-class"},
    )
    assert added.status_code == 204
    classes = client.get("/student/classes", headers=_headers(student))
    assert classes.status_code == 200
    assert [item["id"] for item in classes.json()] == [first_id, second.json()["id"]]


def test_student_dialogue_creation_style_and_message_are_idempotent(client, db, monkeypatch) -> None:
    gateway = _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t17-idempotent-owner")
    student = _login(client, "student", "t17-idempotent-student")
    class_id = _classroom(client, teacher, "t17-idempotent-student")

    first = _create_dialogue(client, student, class_id)
    repeated = _create_dialogue(client, student, class_id)
    assert first.status_code == repeated.status_code == 201
    assert first.json()["session"]["id"] == repeated.json()["session"]["id"]
    assert first.json()["session"]["session_kind"] == "student_initiated"
    assert first.json()["participation"]["interaction_style"] == "direct"
    assert db.scalar(select(func.count(PblSession.id))) == 1
    assert db.scalar(select(func.count(PblParticipation.id))) == 1

    conflict = _create_dialogue(client, student, class_id, style="guided")
    assert conflict.status_code == 201
    assert conflict.json()["participation"]["interaction_style"] == "direct"
    session_id = first.json()["session"]["id"]
    payload = {"client_message_id": "message-once", "content": "炎症为什么会局部红肿？"}
    sent = client.post(f"/student/learning-dialogues/{session_id}/messages", headers=_headers(student), json=payload)
    resent = client.post(f"/student/learning-dialogues/{session_id}/messages", headers=_headers(student), json=payload)
    assert sent.status_code == resent.status_code == 200
    assert gateway.calls == 1
    assert sent.json()["diagnostic"]["knowledge_gaps"] == []
    reply = sent.json()["diagnostic"]["assistant_reply"]
    assert reply.startswith("回应\n合成教学演示")
    assert "关键要点" in reply and "下一步" in reply


def test_classroom_start_updates_next_turn_preference(client, db, monkeypatch) -> None:
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t17-start-owner")
    student = _login(client, "student", "t17-start-student")
    class_id = _classroom(client, teacher, "t17-start-student")
    created = client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db))
    session_id = created.json()["id"]

    before = client.get(f"/student/learning-dialogues/{session_id}", headers=_headers(student))
    assert before.status_code == 200 and before.json()["participation"] is None
    start = client.post(
        f"/student/learning-dialogues/{session_id}/start",
        headers=_headers(student),
        json={"interaction_style": "guided"},
    )
    repeated = client.post(
        f"/student/learning-dialogues/{session_id}/start",
        headers=_headers(student),
        json={"interaction_style": "guided"},
    )
    changed = client.post(
        f"/student/learning-dialogues/{session_id}/start",
        headers=_headers(student),
        json={"interaction_style": "direct"},
    )
    assert start.status_code == repeated.status_code == 200
    assert changed.status_code == 200
    assert changed.json()["participation"]["interaction_style"] == "direct"
    assert changed.json()["participation"]["revision"] == 0
    assert start.json()["participation"]["style_selected_at"]


def test_student_initiated_dialogue_is_private_to_creator_and_owner(client, monkeypatch) -> None:
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t17-private-owner")
    creator = _login(client, "student", "t17-private-creator")
    peer = _login(client, "student", "t17-private-peer")
    class_id = _classroom(client, teacher, "t17-private-creator")
    added = client.post(
        f"/classes/{class_id}/members",
        headers=_headers(teacher),
        json={"student_external_id": "t17-private-peer"},
    )
    assert added.status_code == 204
    created = _create_dialogue(client, creator, class_id)
    session_id = created.json()["session"]["id"]

    creator_list = client.get("/student/learning-dialogues", headers=_headers(creator)).json()["items"]
    peer_list = client.get("/student/learning-dialogues", headers=_headers(peer)).json()["items"]
    assert any(item["id"] == session_id for item in creator_list)
    assert all(item["id"] != session_id for item in peer_list)
    assert client.get(f"/student/learning-dialogues/{session_id}", headers=_headers(peer)).status_code == 404


def test_student_dialogue_rejects_mixed_topic_points(client, monkeypatch) -> None:
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t17-topic-owner")
    student = _login(client, "student", "t17-topic-student")
    class_id = _classroom(client, teacher, "t17-topic-student")
    response = client.post(
        "/student/learning-dialogues",
        headers=_headers(student),
        json={
            "client_session_id": "mixed-topic",
            "class_id": class_id,
            "interaction_style": "guided",
            "goal_point_codes": ["pathology.inflammation.vascular", "pathology.repair.regeneration"],
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("style", ["guided", "direct"])
def test_both_styles_enter_the_same_teacher_and_learning_loop(client, monkeypatch, style: str) -> None:
    from tests.test_t44_learning_routes import configure as configure_route_gateway

    configure_route_gateway(monkeypatch)
    teacher = _login(client, "teacher", f"t17-loop-owner-{style}")
    student = _login(client, "student", f"t17-loop-student-{style}")
    class_id = _classroom(client, teacher, f"t17-loop-student-{style}")
    created = _create_dialogue(client, student, class_id, client_id=f"loop-{style}", style=style)
    session_id = created.json()["session"]["id"]
    for index, content in enumerate(("明确病理问题", "提出机制假设", "比较支持与反对证据", "整合机制与证据")):
        sent = client.post(
            f"/student/learning-dialogues/{session_id}/messages",
            headers=_headers(student),
            json={"client_message_id": f"{style}-{index}", "content": content},
        )
        assert sent.status_code == 200
    assert sent.json()["phase_status"] == "completed"

    queue = client.get("/teacher/pbl-diagnostics", headers=_headers(teacher))
    assert queue.status_code == 200
    assert all(item["session_id"] != session_id for item in queue.json()["items"])
    preview = client.get(f"/student/learning-dialogues/{session_id}/submission", headers=_headers(student))
    assert preview.status_code == 404
    submitted = client.post(
        f"/student/learning-dialogues/{session_id}/submission",
        headers=_headers(student),
        json={
            "snapshot_id": sent.json()["diagnostic"]["id"],
            "class_id": class_id,
            "client_submission_id": f"loop-share-{style}",
        },
    )
    assert submitted.status_code == 409
    assert submitted.json()["detail"]["reason"] == "RETIRED_FLOW"
    queue = client.get("/teacher/pbl-diagnostics", headers=_headers(teacher))
    assert all(item["session_id"] != session_id for item in queue.json()["items"])
    plans = client.get("/student/pbl-learning-plans", headers=_headers(student))
    assert plans.status_code == 200 and plans.json() == []

    route_id = sent.json()["learning_route_id"]
    assert route_id
    routes = client.get("/learning/routes", headers=_headers(student))
    assert routes.status_code == 200, routes.text
    assert routes.json()["total"] == 1
    assert routes.json()["items"][0]["id"] == route_id
    route = client.get(f"/learning/routes/{route_id}", headers=_headers(student))
    assert route.status_code == 200, route.text
    assert route.json()["summary"]["generation_state"] == "published"

    report_page = client.get("/student/pbl-learning-reports", headers=_headers(student))
    assert report_page.status_code == 200, report_page.text
    assert report_page.json()["items"] == [] and report_page.json()["total"] == 0
    report = client.get(f"/student/pbl-learning-reports/{session_id}", headers=_headers(student))
    assert report.status_code == 404
