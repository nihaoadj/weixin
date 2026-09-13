from sqlalchemy import func, select

from app.modules.pbl.infrastructure.models import PblSubmission
from tests.test_pbl_api import _classroom, _configure_gateway, _headers, _login

POINT = "pathology.inflammation.vascular"


def complete(client, student, session_id):
    value = None
    for index in range(4):
        response = client.post(
            f"/student/learning-dialogues/{session_id}/messages",
            headers=_headers(student),
            json={"client_message_id": f"phase-{index}", "content": "观察形态和血流变化，比较不同机制并结合证据解释。"},
        )
        assert response.status_code == 200, response.text
        value = response.json()
    assert value["current_phase"] == "completed"
    return value["diagnostic"]["id"]


def create_private(client, student):
    response = client.post(
        "/student/learning-dialogues",
        headers=_headers(student),
        json={
            "client_session_id": "private-one",
            "interaction_style": "guided",
            "goal_point_codes": [POINT],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["session"]["class_id"] is None
    return response.json()["session"]["id"]


def test_no_class_private_then_explicit_submission(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    student = _login(client, "student", "t20-student")
    teacher = _login(client, "teacher", "t20-teacher")
    sid = create_private(client, student)
    assert client.get("/student/learning-dialogues", headers=_headers(student)).status_code == 200
    assert client.get(f"/student/learning-dialogues/{sid}/submission", headers=_headers(student)).status_code == 409
    snap = complete(client, student, sid)
    cid = _classroom(client, teacher, "t20-student")
    assert client.get("/teacher/pbl-diagnostics", headers=_headers(teacher)).json()["total"] == 0
    preview = client.get(f"/student/learning-dialogues/{sid}/submission", headers=_headers(student)).json()
    qid = preview["questions"][0]["id"]
    assert "messages" not in preview
    assert client.get(f"/teacher/pbl-diagnostics/{snap}", headers=_headers(teacher)).status_code == 404
    assert (
        client.patch(
            f"/teacher/pbl-suggestions/{qid}", headers=_headers(teacher), json={"version": 1, "title": "不允许"}
        ).status_code
        == 404
    )
    payload = {"snapshot_id": snap, "class_id": cid, "client_submission_id": "once"}
    for _ in range(2):
        response = client.post(f"/student/learning-dialogues/{sid}/submission", headers=_headers(student), json=payload)
        assert response.status_code == 200, response.text
    assert db.scalar(select(func.count(PblSubmission.id))) == 1
    submitted = client.get(f"/student/learning-dialogues/{sid}/submission", headers=_headers(student)).json()
    assert submitted["questions"][0]["title"] == preview["questions"][0]["title"]
    assert client.get("/teacher/pbl-diagnostics", headers=_headers(teacher)).json()["total"] == 1
    assert (
        client.patch(
            f"/teacher/pbl-question-suggestions/{qid}",
            headers=_headers(teacher),
            json={
                "version": 1,
                "title": "教师修改后的建议",
                "prompt": preview["questions"][0]["prompt"],
            },
        ).status_code
        == 200
    )
    # A teacher edit may affect later formal adoption, but cannot rewrite the
    # student's submitted evidence preview.
    assert (
        client.get(f"/student/learning-dialogues/{sid}/submission", headers=_headers(student)).json()["questions"][0][
            "title"
        ]
        == preview["questions"][0]["title"]
    )
    outsider = _login(client, "student", "t20-outsider")
    assert client.get(f"/student/learning-dialogues/{sid}", headers=_headers(outsider)).status_code == 404
    assert client.get(f"/student/learning-dialogues/{sid}/submission", headers=_headers(outsider)).status_code == 404
