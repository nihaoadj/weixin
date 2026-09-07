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


def test_student_dialogue_requires_active_class_and_lists_classes(client, monkeypatch) -> None:
    _configure_gateway(monkeypatch)
    student = _login(client, "student", "t17-no-class")
    assert client.get("/student/classes", headers=_headers(student)).json() == []
    assert _create_dialogue(client, student, 999).status_code == 404

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
    assert conflict.status_code == 409
    session_id = first.json()["session"]["id"]
    payload = {"client_message_id": "message-once", "content": "炎症为什么会局部红肿？"}
    sent = client.post(
        f"/student/learning-dialogues/{session_id}/messages", headers=_headers(student), json=payload
    )
    resent = client.post(
        f"/student/learning-dialogues/{session_id}/messages", headers=_headers(student), json=payload
    )
    assert sent.status_code == resent.status_code == 200
    assert gateway.calls == 1
    assert sent.json()["diagnostic"]["knowledge_gaps"] == []
    assert "先说明" in sent.json()["diagnostic"]["assistant_reply"]


def test_classroom_start_fixes_each_students_interaction_style(client, db, monkeypatch) -> None:
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t17-start-owner")
    student = _login(client, "student", "t17-start-student")
    class_id = _classroom(client, teacher, "t17-start-student")
    created = client.post(
        f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db)
    )
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
    assert changed.status_code == 409
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
    _configure_gateway(monkeypatch)
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
    diagnostic = next(item for item in queue.json()["items"] if item["session_id"] == session_id)
    assert diagnostic["schema_version"] == 4
    assert diagnostic["session_kind"] == "student_initiated"
    assert diagnostic["interaction_style"] == style
    suggestion = diagnostic["recommended_questions"][0]
    adopted = client.post(
        f"/teacher/pbl-question-suggestions/{suggestion['id']}/adopt-and-publish",
        headers=_headers(teacher),
        json={"version": suggestion["version"], "title": suggestion["title"], "prompt": suggestion["prompt"]},
    )
    assert adopted.status_code == 200
    plans = client.get("/student/pbl-learning-plans", headers=_headers(student))
    assert plans.status_code == 200
    assert len(plans.json()) == 1
    assert plans.json()[0]["source_context"]["session_id"] == session_id
    assert {task["cycle_number"] for task in plans.json()[0]["tasks"]} == {1, 2}
    assert all(task["public_definition"].get("target_label") for task in plans.json()[0]["tasks"])

    report_page = client.get("/student/pbl-learning-reports", headers=_headers(student))
    assert report_page.status_code == 200, report_page.text
    assert report_page.json()["summary"]["completed_personal_discussions"] == 1
    report = client.get(f"/student/pbl-learning-reports/{session_id}", headers=_headers(student))
    assert report.status_code == 200, report.text
    assert report.json()["diagnosis"]["created_at"] is not None
