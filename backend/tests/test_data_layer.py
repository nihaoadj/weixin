from fastapi.testclient import TestClient
from sqlalchemy import event

from app.db import engine
from app.main import app

client = TestClient(app)


def login(role: str, external_id: str) -> str:
    response = client.post(
        "/auth/demo-login",
        json={"role": role, "external_id": external_id, "nickname": external_id, "avatar_url": ""},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_conversation(student: str, client_id: str, content: str = "private medical answer") -> int:
    conversation = client.post(
        "/conversations",
        headers=headers(student),
        json={"client_id": client_id, "messages": [{"role": "user", "content": content}]},
    )
    assert conversation.status_code == 200
    return conversation.json()["id"]


def create_question(teacher: str, title: str) -> int:
    # Retained history is seeded directly; the retired authoring API cannot create it.
    from app.db import SessionLocal
    from app.modules.content.infrastructure.models import Problem

    with SessionLocal() as db:
        problem = Problem(type="医学常识", title=title, description="description", status="published")
        db.add(problem)
        db.commit()
        return problem.id


def test_summary_and_direct_lookup_endpoints_do_not_return_full_messages() -> None:
    student = login("student", "summary-student")
    teacher = login("teacher", "summary-teacher")
    conversation_id = create_conversation(student, "client-summary")

    conversation_page = client.get("/conversations/summaries?limit=1&offset=0", headers=headers(student))
    assert conversation_page.status_code == 200
    assert conversation_page.json()["total"] == 1
    summary = conversation_page.json()["items"][0]
    assert "messages" not in summary
    assert summary["message_count"] == 1
    assert summary["report_status"] is None

    by_client = client.get("/conversations/by-client/client-summary", headers=headers(student))
    assert by_client.status_code == 200
    assert by_client.json()["id"] == conversation_id

    report_page = client.get("/reports/summaries?limit=20&offset=0", headers=headers(teacher))
    assert report_page.status_code == 404
    create = client.post(
        "/reports",
        headers=headers(student),
        json={"conversation_id": conversation_id, "ai_score": 80, "ai_summary": "不应新建"},
    )
    assert create.status_code == 409
    by_conversation = client.get("/reports/by-conversation/client-summary", headers=headers(student))
    assert by_conversation.status_code == 404


def test_student_question_feed_hides_retained_discussion_history() -> None:
    student = login("student", "feed-student")
    teacher = login("teacher", "feed-teacher")
    problem_id = create_question(teacher, "Question one")
    assert client.get("/student/questions", headers=headers(student)).json() == []
    assert client.get(f"/student/questions/{problem_id}", headers=headers(student)).status_code == 404
    response = client.post(
        f"/problems/{problem_id}/thread",
        headers=headers(student),
        json={"messages": [{"role": "user", "content": "answer"}]},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "RETIRED_FLOW"


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
    conversation_id = create_conversation(student, "client/with space")
    response = client.get("/conversations/by-client/client%2Fwith%20space", headers=headers(student))
    assert response.status_code == 200
    assert response.json()["client_id"] == "client/with space"
    report = client.get("/reports/by-conversation/client%2Fwith%20space", headers=headers(student))
    assert report.status_code == 404
    assert client.get(f"/conversations/{conversation_id}", headers=headers(student)).status_code == 200


def test_unexpected_error_does_not_leak_medical_content(monkeypatch, caplog) -> None:
    from app.api import reports

    student = login("student", "error-student")

    def fail(*_args):
        raise RuntimeError("synthetic private medical text")

    monkeypatch.setattr(reports, "load_visible_report", fail)
    with TestClient(app, raise_server_exceptions=False) as error_client:
        response = error_client.get("/reports/1", headers=headers(student))
    assert response.status_code == 500
    assert response.json() == {"detail": {"code": "SERVICE_ERROR", "message": "服务暂时不可用"}}
    assert "synthetic private medical text" not in caplog.text


def test_summary_pagination_is_stable_and_role_scoped() -> None:
    student = login("student", "student-a")
    other = login("student", "student-b")
    teacher = login("teacher", "teacher")

    class_response = client.post("/classes", headers=headers(teacher), json={"name": "分页班", "code": "pager-class"})
    assert class_response.status_code == 200
    class_id = class_response.json()["id"]
    for external in ("student-a", "student-b"):
        assert (
            client.post(
                f"/classes/{class_id}/members", headers=headers(teacher), json={"student_external_id": external}
            ).status_code
            == 204
        )

    first = create_conversation(student, "shared-client", "x" * 500)
    create_conversation(other, "shared-client")
    assert client.get(f"/reports/{first}", headers=headers(other)).status_code == 404
    assert client.get(f"/reports/{first}", headers=headers(teacher)).status_code == 404
    assert client.get("/reports/summaries", headers=headers(teacher)).status_code == 404
    assert client.get("/conversations/summaries", headers=headers(teacher)).status_code == 403
    assert client.get("/conversations/by-client/missing", headers=headers(student)).status_code == 404
    assert client.get("/reports/by-conversation/missing", headers=headers(student)).status_code == 404
    assert client.get("/conversations/summaries?limit=101", headers=headers(student)).status_code == 422
    assert client.get("/reports/summaries?offset=-1", headers=headers(student)).status_code == 422
    assert (
        client.post(f"/reports/{first}/submit", headers=headers(student), json={"class_id": class_id}).status_code
        == 409
    )
    assert client.get("/reports/by-conversation/shared-client", headers=headers(teacher)).status_code == 404
    assert client.get("/reports/by-conversation/shared-client", headers=headers(student)).status_code == 404
    own = client.get("/conversations/summaries", headers=headers(student)).json()
    assert own["total"] == 1
    assert len(own["items"][0]["message_preview"]) == 160


def test_retired_question_lookup_keeps_student_role_boundary() -> None:
    student = login("student", "visible-student")
    teacher = login("teacher", "question-teacher")
    question_id = create_question(teacher, "retained")
    assert client.get("/student/questions", headers=headers(student)).json() == []
    assert client.get(f"/student/questions/{question_id}", headers=headers(student)).status_code == 404
    assert client.get("/student/questions", headers=headers(teacher)).status_code == 403


def test_summary_query_count_does_not_scale_with_messages_or_reports() -> None:
    student = login("student", "summary-performance-student")

    def seed(index: int) -> None:
        create_conversation(student, f"client-{index}")

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
    small = [measure("/conversations/summaries", student)]
    for index in range(1, 25):
        seed(index)
    large = [measure("/conversations/summaries", student)]
    assert small == large
