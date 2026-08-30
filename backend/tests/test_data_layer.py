from fastapi.testclient import TestClient
from sqlalchemy import event

from app.db import Base, engine
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def login(role: str, external_id: str) -> str:
    response = client.post(
        "/auth/demo-login",
        json={"role": role, "external_id": external_id, "nickname": external_id, "avatar_url": ""},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_conversation_and_report(
    student: str, client_id: str, content: str = "private medical answer"
) -> tuple[int, int]:
    conversation = client.post(
        "/conversations",
        headers=headers(student),
        json={"client_id": client_id, "messages": [{"role": "user", "content": content}]},
    )
    assert conversation.status_code == 200
    report = client.post(
        "/reports",
        headers=headers(student),
        json={"conversation_id": conversation.json()["id"], "ai_score": 80, "ai_summary": "summary"},
    )
    assert report.status_code == 200
    return conversation.json()["id"], report.json()["id"]


def create_question(teacher: str, title: str) -> int:
    created = client.post(
        "/problems",
        headers=headers(teacher),
        json={
            "type": "医学常识",
            "title": title,
            "description": "description",
            "target": "all",
            "target_label": "全体学生",
            "target_ids": [],
        },
    )
    assert created.status_code == 200
    problem_id = created.json()["id"]
    assert client.post(f"/problems/{problem_id}/publish", headers=headers(teacher)).status_code == 200
    return problem_id


def test_summary_and_direct_lookup_endpoints_do_not_return_full_messages() -> None:
    student = login("student", "summary-student")
    teacher = login("teacher", "summary-teacher")
    conversation_id, report_id = create_conversation_and_report(student, "client-summary")

    conversation_page = client.get("/conversations/summaries?limit=1&offset=0", headers=headers(student))
    assert conversation_page.status_code == 200
    assert conversation_page.json()["total"] == 1
    summary = conversation_page.json()["items"][0]
    assert "messages" not in summary
    assert summary["message_count"] == 1
    assert summary["report_status"] == "draft"

    by_client = client.get("/conversations/by-client/client-summary", headers=headers(student))
    assert by_client.status_code == 200
    assert by_client.json()["id"] == conversation_id

    assert client.post(f"/reports/{report_id}/submit", headers=headers(student)).status_code == 200
    report_page = client.get("/reports/summaries?limit=20&offset=0", headers=headers(teacher))
    assert report_page.status_code == 200
    assert "messages" not in report_page.json()["items"][0]
    assert report_page.json()["pending_count"] == 1
    direct = client.get(f"/reports/{report_id}", headers=headers(teacher))
    assert direct.status_code == 200
    assert direct.json()["messages"][0]["content"] == "private medical answer"
    by_conversation = client.get("/reports/by-conversation/client-summary", headers=headers(student))
    assert by_conversation.status_code == 200
    assert by_conversation.json()["id"] == report_id


def test_student_question_feed_reports_answer_state() -> None:
    student = login("student", "feed-student")
    teacher = login("teacher", "feed-teacher")
    problem_id = create_question(teacher, "Question one")

    initial = client.get("/student/questions", headers=headers(student))
    assert initial.status_code == 200
    assert initial.json() == [
        {
            "id": problem_id,
            "type": "医学常识",
            "title": "Question one",
            "description": "description",
            "published_at": initial.json()[0]["published_at"],
            "status": "unanswered",
        }
    ]
    assert (
        client.post(
            f"/problems/{problem_id}/thread",
            headers=headers(student),
            json={"messages": [{"role": "user", "content": "answer"}]},
        ).status_code
        == 200
    )
    answered = client.get("/student/questions", headers=headers(student))
    assert answered.json()[0]["status"] == "answered"


def test_student_question_feed_query_count_is_constant() -> None:
    student = login("student", "query-student")
    teacher = login("teacher", "query-teacher")
    create_question(teacher, "First")

    def count_selects() -> int:
        statements: list[str] = []

        def capture(_connection, _cursor, statement, _parameters, _context, _executemany) -> None:
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(engine, "before_cursor_execute", capture)
        try:
            assert client.get("/student/questions", headers=headers(student)).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        return len(statements)

    small = count_selects()
    for index in range(120):
        create_question(teacher, f"Question {index}")
    large = count_selects()
    assert large == small


def test_errors_use_stable_structured_contract() -> None:
    response = client.get("/conversations/summaries")
    assert response.status_code == 401
    assert response.json() == {"detail": {"code": "AUTH_REQUIRED", "message": "Missing bearer token"}}

    student = login("student", "validation-student")
    invalid = client.get("/conversations/not-an-integer", headers=headers(student))
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_encoded_client_identifiers_are_resolved_without_path_confusion() -> None:
    student = login("student", "encoded-student")
    _, report_id = create_conversation_and_report(student, "client/with space")
    response = client.get("/conversations/by-client/client%2Fwith%20space", headers=headers(student))
    assert response.status_code == 200
    assert response.json()["client_id"] == "client/with space"
    report = client.get("/reports/by-conversation/client%2Fwith%20space", headers=headers(student))
    assert report.status_code == 200
    assert report.json()["id"] == report_id


def test_unexpected_error_does_not_leak_medical_content(monkeypatch, caplog) -> None:
    from app.api import reports

    student = login("student", "error-student")

    def fail(*_args):
        raise RuntimeError("synthetic private medical text")

    monkeypatch.setattr(reports, "load_visible_report", fail)
    response = TestClient(app, raise_server_exceptions=False).get("/reports/1", headers=headers(student))
    assert response.status_code == 500
    assert response.json() == {"detail": {"code": "SERVICE_ERROR", "message": "服务暂时不可用"}}
    assert "synthetic private medical text" not in caplog.text


def test_summary_pagination_is_stable_and_role_scoped() -> None:
    student = login("student", "student-a")
    other = login("student", "student-b")
    teacher = login("teacher", "teacher")
    _, first = create_conversation_and_report(student, "shared-client", "x" * 500)
    _, second = create_conversation_and_report(other, "shared-client")
    assert client.get(f"/reports/{first}", headers=headers(other)).status_code == 404
    assert client.get(f"/reports/{first}", headers=headers(teacher)).status_code == 404
    assert client.get("/reports/summaries", headers=headers(teacher)).json()["total"] == 0
    assert client.get("/conversations/summaries", headers=headers(teacher)).status_code == 403
    assert client.get("/conversations/by-client/missing", headers=headers(student)).status_code == 404
    assert client.get("/reports/by-conversation/missing", headers=headers(student)).status_code == 404
    assert client.get("/conversations/summaries?limit=101", headers=headers(student)).status_code == 422
    assert client.get("/reports/summaries?offset=-1", headers=headers(student)).status_code == 422
    for token, report_id in [(student, first), (other, second)]:
        assert client.post(f"/reports/{report_id}/submit", headers=headers(token)).status_code == 200
    assert client.get("/reports/by-conversation/shared-client", headers=headers(teacher)).status_code == 409
    assert client.get("/reports/by-conversation/shared-client", headers=headers(student)).json()["id"] == first
    pages = [
        client.get(f"/reports/summaries?limit=1&offset={offset}", headers=headers(teacher)).json()
        for offset in range(3)
    ]
    assert all(page["total"] == 2 for page in pages)
    assert pages[0]["items"][0]["id"] != pages[1]["items"][0]["id"]
    assert pages[2]["items"] == []
    own = client.get("/conversations/summaries", headers=headers(student)).json()
    assert own["total"] == 1
    assert len(own["items"][0]["message_preview"]) == 160


def test_question_visibility_applies_before_pagination_and_direct_lookup() -> None:
    student = login("student", "visible-student")
    teacher = login("teacher", "question-teacher")
    question_id = create_question(teacher, "visible")
    hidden = client.post(
        "/problems",
        headers=headers(teacher),
        json={
            "type": "医学常识",
            "title": "private",
            "target": "individual",
            "target_label": "其他学生",
            "target_ids": ["other"],
        },
    ).json()["id"]
    assert client.post(f"/problems/{hidden}/publish", headers=headers(teacher)).status_code == 200
    page = client.get("/student/questions", headers=headers(student)).json()
    assert len(page) == 1
    assert page[0]["id"] == question_id
    assert client.get(f"/student/questions/{question_id}", headers=headers(student)).json()["status"] == "unanswered"
    assert client.get(f"/student/questions/{hidden}", headers=headers(student)).status_code == 404
    assert client.get("/student/questions", headers=headers(teacher)).status_code == 403


def test_summary_query_count_does_not_scale_with_messages_or_reports() -> None:
    student = login("student", "summary-performance-student")
    teacher = login("teacher", "summary-performance-teacher")

    def seed(index: int) -> None:
        _, report_id = create_conversation_and_report(student, f"client-{index}")
        assert client.post(f"/reports/{report_id}/submit", headers=headers(student)).status_code == 200

    def measure(path: str, token: str) -> int:
        statements: list[str] = []

        def capture(_connection, _cursor, statement, _parameters, _context, _executemany) -> None:
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(engine, "before_cursor_execute", capture)
        try:
            assert client.get(path, headers=headers(token)).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        return len(statements)

    seed(0)
    small = [measure("/conversations/summaries", student), measure("/reports/summaries", teacher)]
    for index in range(1, 25):
        seed(index)
    large = [measure("/conversations/summaries", student), measure("/reports/summaries", teacher)]
    assert small == large
