from app.modules.content.domain.knowledge_catalog import POINTS
from app.modules.content.public import study_material_view
from tests.test_pbl_api import _configure_gateway, _headers, _login

POINT = "pathology.inflammation.vascular"


def test_every_catalog_point_has_complete_versioned_study_material():
    assert len(POINTS) == 30
    materials = [study_material_view(point.code) for point in POINTS]
    assert all(
        material
        and material["version"]
        and material["objective"]
        and material["scenario"]
        and material["background"]
        and material["example"]
        and material["remediation"]
        and material["reference"]
        and material["review_status"] == "unreviewed"
        for material in materials
    )


def complete_path(client, token):
    start = client.post(
        f"/learning/knowledge-points/{POINT}/study/start",
        headers=_headers(token),
        json={
            "client_id": "study-path-1",
            "interaction_style": "guided",
        },
    )
    assert start.status_code == 200, start.text
    body = start.json()
    assert body["practice_unlocked"] is False
    session_id = body["path"]["session_id"]
    for index in range(4):
        response = client.post(
            f"/student/learning-dialogues/{session_id}/messages",
            headers=_headers(token),
            json={
                "client_message_id": f"study-phase-{index}",
                "content": "我先描述形态线索，再提出机制假设，并说明哪些证据支持或限制这个判断。",
            },
        )
        assert response.status_code == 200, response.text
    return body["path"]["id"], session_id


def test_study_path_gates_practice_and_preserves_unreviewed_separation(client, monkeypatch):
    _configure_gateway(monkeypatch)
    student = _login(client, "student", "study-student")
    initial = client.get(f"/learning/knowledge-points/{POINT}/study", headers=_headers(student))
    assert initial.status_code == 200
    assert initial.json()["practice_unlocked"] is False

    path_id, _ = complete_path(client, student)
    state = client.get(f"/learning/knowledge-points/{POINT}/study", headers=_headers(student)).json()
    assert state["practice_unlocked"] is True
    assert state["review_unlocked"] is False

    generated = client.post(
        f"/learning/study-paths/{path_id}/practices",
        headers=_headers(student),
        json={
            "client_id": "practice-one",
            "cycle": 1,
        },
    )
    assert generated.status_code == 200, generated.text
    group = generated.json()
    assert group["status"] == "ready"
    assert group["attempts"] == []
    assert "reference_option" not in group["questions"][0]
    answer = client.post(
        f"/learning/self-practices/{group['id']}/answers",
        headers=_headers(student),
        json={
            "client_id": "answer-one",
            "question_index": 0,
            "selected_option": 1,
        },
    )
    assert answer.status_code == 200
    assert answer.json()["correct"] is False
    assert answer.json()["reference_option"] == 0
    assert "AI 参考" in answer.json()["explanation"]
    detail = client.get(f"/learning/self-practices/{group['id']}", headers=_headers(student)).json()
    assert detail["attempts"][0]["correct"] is False
    state = client.get(f"/learning/knowledge-points/{POINT}/study", headers=_headers(student)).json()
    assert state["review_unlocked"] is True
    # This private exercise does not create a formal review-state/knowledge-map mastery record.
    knowledge_map = client.get("/learning/knowledge-map", headers=_headers(student)).json()["items"]
    assert next(item for item in knowledge_map if item["code"] == POINT)["status"] == "not_started"


def test_study_path_and_private_practice_are_student_scoped(client, monkeypatch):
    _configure_gateway(monkeypatch)
    one = _login(client, "student", "study-one")
    two = _login(client, "student", "study-two")
    path_id, _ = complete_path(client, one)
    group = client.post(
        f"/learning/study-paths/{path_id}/practices",
        headers=_headers(one),
        json={
            "client_id": "practice-one",
            "cycle": 1,
        },
    ).json()
    assert client.get(f"/learning/study-paths/{path_id}/practices", headers=_headers(two)).status_code == 200
    assert client.get(f"/learning/self-practices/{group['id']}", headers=_headers(two)).status_code == 404
