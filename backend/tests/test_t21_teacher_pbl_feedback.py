"""T30 PBL feedback: only classroom diagnostics are actionable."""

from sqlalchemy import select

from app.modules.learning.infrastructure.models import LearningPlan
from tests.test_pbl_api import _classroom, _configure_gateway, _headers, _login, _session_payload


def _completed_classroom(client, db, teacher: str, student: str, class_id: int, prefix: str) -> tuple[int, int]:
    created = client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db))
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    for index in range(4):
        response = client.post(
            f"/student/pbl-sessions/{session_id}/messages",
            headers=_headers(student),
            json={"client_message_id": f"{prefix}-{index}", "content": f"第 {index + 1} 阶段课堂证据"},
        )
        assert response.status_code == 200, response.text
    items = client.get("/teacher/pbl-work-items?source=classroom_diagnostic", headers=_headers(teacher))
    assert items.status_code == 200
    snapshot_id = next(item["snapshot_id"] for item in items.json()["items"] if item["session_id"] == session_id)
    return session_id, snapshot_id


def test_t30_diagnostic_feedback_is_read_only_and_legacy_report_reads_are_empty(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t30-feedback-owner")
    other = _login(client, "teacher", "t30-feedback-other")
    student = _login(client, "student", "t30-feedback-student")
    class_id = _classroom(client, teacher, "t30-feedback-student")
    session_id, snapshot_id = _completed_classroom(client, db, teacher, student, class_id, "t30-feedback")

    assert client.get(f"/teacher/pbl-work-items/{snapshot_id}", headers=_headers(other)).status_code == 404
    payload = {
        "client_feedback_id": "t30-feedback-once",
        "body": "请先重新核对形态证据与机制解释。",
        "action_type": "feedback_only",
    }
    first = client.post(f"/teacher/pbl-work-items/{snapshot_id}/feedback", headers=_headers(teacher), json=payload)
    second = client.post(f"/teacher/pbl-work-items/{snapshot_id}/feedback", headers=_headers(teacher), json=payload)
    assert first.status_code == second.status_code == 409
    assert first.json()["detail"]["reason"] == second.json()["detail"]["reason"] == "RETIRED_FLOW"
    assert db.scalars(select(LearningPlan)).all() == []
    old_reports = client.get("/student/pbl-learning-reports", headers=_headers(student))
    assert old_reports.status_code == 200
    assert old_reports.json()["items"] == [] and old_reports.json()["total"] == 0
    assert client.get(f"/student/pbl-learning-reports/{session_id}", headers=_headers(student)).status_code == 404
    old_follow_ups = client.get("/teacher/pbl-follow-ups", headers=_headers(teacher))
    assert old_follow_ups.status_code == 200
    assert old_follow_ups.json()["items"] == [] and old_follow_ups.json()["total"] == 0
    assert client.get("/teacher/pbl-follow-ups/1", headers=_headers(teacher)).status_code == 404
    changed = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={**payload, "body": "不同正文"},
    )
    assert changed.status_code == 409
    assert changed.json()["detail"]["reason"] == "RETIRED_FLOW"
    work = client.get("/teacher/pbl-work-items", headers=_headers(teacher)).json()
    assert any(row["snapshot_id"] == snapshot_id and row["status"] == "pending" for row in work["items"])


def test_legacy_single_question_publish_is_rejected_for_a_schema_v8_classroom(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t30-publish-owner")
    student = _login(client, "student", "t30-publish-student")
    class_id = _classroom(client, teacher, "t30-publish-student")
    _, snapshot_id = _completed_classroom(client, db, teacher, student, class_id, "t30-publish")
    item = client.get(f"/teacher/pbl-work-items/{snapshot_id}", headers=_headers(teacher))
    assert item.status_code == 200
    assert item.json()["work_item"]["source"] == "classroom_diagnostic"
    assert item.json()["diagnostic"]["recommended_questions"] == []
    response = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["reason"] == "RETIRED_FLOW"
    assert db.scalars(select(LearningPlan)).all() == []
    work = client.get("/teacher/pbl-work-items", headers=_headers(teacher)).json()
    assert any(row["snapshot_id"] == snapshot_id and row["status"] == "pending" for row in work["items"])


def test_classroom_dashboard_tracks_work_item_status(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t30-dashboard-owner")
    student = _login(client, "student", "t30-dashboard-student")
    class_id = _classroom(client, teacher, "t30-dashboard-student")
    session_id, snapshot_id = _completed_classroom(client, db, teacher, student, class_id, "t30-dashboard")
    dashboard = client.get(f"/classes/{class_id}/pbl-sessions/{session_id}/dashboard", headers=_headers(teacher))
    assert dashboard.status_code == 200
    assert dashboard.json()["students"][0]["work_item_status"] == "pending"
    feedback = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={
            "client_feedback_id": "t30-dashboard-feedback",
            "body": "请把形态观察与推理依据逐项对应。",
            "action_type": "feedback_only",
        },
    )
    assert feedback.status_code == 409
    dashboard = client.get(f"/classes/{class_id}/pbl-sessions/{session_id}/dashboard", headers=_headers(teacher))
    assert dashboard.json()["students"][0]["work_item_status"] == "pending"
