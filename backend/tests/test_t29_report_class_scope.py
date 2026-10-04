"""T30 report scope: regular QA reports are retained as student-only history."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.qa.infrastructure.models import Conversation
from app.modules.reports.infrastructure.models import Report


def _login(client: TestClient, role: str, external_id: str) -> tuple[dict[str, str], dict]:
    response = client.post(
        "/auth/demo-login",
        json={"role": role, "external_id": external_id, "nickname": external_id, "avatar_url": ""},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, response.json()["user"]


def _history_report(db, student_id: int, client_id: str) -> Report:
    conversation = Conversation(client_id=client_id, student_id=student_id)
    db.add(conversation)
    db.flush()
    report = Report(
        conversation_id=conversation.id,
        student_id=student_id,
        status="reviewed",
        ai_score=75,
        ai_summary="保留的历史总结",
        teacher_score=80,
        teacher_feedback="保留的历史反馈",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def test_student_active_classes_endpoint_returns_only_own_membership(client) -> None:
    student_headers, _ = _login(client, "student", "t30-scope-student-a")
    teacher_headers, _ = _login(client, "teacher", "t30-scope-teacher")
    class_response = client.post(
        "/classes", headers=teacher_headers, json={"name": "范围一班", "code": "t30-scope-one"}
    )
    assert class_response.status_code == 200
    class_id = class_response.json()["id"]
    assert (
        client.post(
            f"/classes/{class_id}/members",
            headers=teacher_headers,
            json={"student_external_id": "t30-scope-student-a"},
        ).status_code
        == 204
    )

    mine = client.get("/classes/my-active", headers=student_headers)
    assert mine.status_code == 200, mine.text
    assert [(item["id"], item["code"]) for item in mine.json()] == [(class_id, "t30-scope-one")]
    assert set(mine.json()[0]) == {"id", "name", "code"}
    assert "teacher_id" not in mine.json()[0]
    assert client.get("/classes/my-active", headers=teacher_headers).status_code == 403


def test_regular_qa_report_writes_are_conflicts_and_history_is_student_only(client, db) -> None:
    student_headers, student = _login(client, "student", "t30-report-student")
    teacher_headers, _ = _login(client, "teacher", "t30-report-teacher")
    conversation = client.post(
        "/conversations",
        headers=student_headers,
        json={"client_id": "t30-report-new", "messages": [{"role": "user", "content": "新问题"}]},
    )
    assert conversation.status_code == 200
    before = db.query(Report).count()
    create = client.post(
        "/reports",
        headers=student_headers,
        json={"conversation_id": conversation.json()["id"], "ai_score": 75, "ai_summary": "不应新建"},
    )
    assert create.status_code == 409
    assert create.json()["detail"]["code"] == "STATE_CONFLICT"
    assert db.query(Report).count() == before

    report = _history_report(db, student["id"], "t30-report-history")
    own = client.get(f"/reports/{report.id}", headers=student_headers)
    assert own.status_code == 200
    assert own.json()["status"] == "reviewed"
    assert own.json()["class_id"] is None
    assert client.get("/reports/by-conversation/t30-report-history", headers=student_headers).status_code == 200
    assert client.get("/reports", headers=student_headers).json()[0]["id"] == report.id

    submit = client.post(f"/reports/{report.id}/submit", headers=student_headers, json={"class_id": 1})
    assert submit.status_code == 409
    assert submit.json()["detail"]["code"] == "STATE_CONFLICT"
    review = client.post(
        f"/reports/{report.id}/review",
        headers=teacher_headers,
        json={"teacher_score": 90, "teacher_feedback": "不应批阅"},
    )
    assert review.status_code == 409
    assert review.json()["detail"]["code"] == "STATE_CONFLICT"

    assert client.get(f"/reports/{report.id}", headers=teacher_headers).status_code == 404
    assert client.get("/reports/summaries?limit=20&offset=0", headers=teacher_headers).status_code == 404


def test_legacy_unattributed_report_remains_student_read_only_history(client, db) -> None:
    student_headers, student = _login(client, "student", "t30-legacy-student")
    teacher_headers, _ = _login(client, "teacher", "t30-legacy-teacher")
    report = _history_report(db, student["id"], "t30-legacy-history")
    report.class_id = None
    report.class_name_snapshot = None
    db.commit()

    assert client.get(f"/reports/{report.id}", headers=student_headers).status_code == 200
    assert client.get(f"/reports/{report.id}", headers=teacher_headers).status_code == 404
    review = client.post(
        f"/reports/{report.id}/review",
        headers=teacher_headers,
        json={"teacher_score": 60, "teacher_feedback": "不应可见"},
    )
    assert review.status_code == 409
