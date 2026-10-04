"""Teacher-owned bank lifecycle sourced from route-test UUIDs."""

from sqlalchemy import func, select

from app.modules.content.infrastructure.question_bank_models import (
    BankArchiveReceipt,
    BankImportReceipt,
    TeacherQuestionBankRevision,
)
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.route_models import RouteFinalTest, RouteTestQuestion
from app.modules.learning.wiring import learning_route_result_read_port
from tests.t44_route_support import complete_bank_route, configure_bank_route
from tests.test_pbl_api import _classroom, _headers, _login, _session_payload


def test_teacher_question_bank_import_edit_archive_and_deidentify_from_route_source(client, db, monkeypatch):
    configure_bank_route(monkeypatch)
    teacher = _login(client, "teacher", "t43-route-bank-owner")
    outsider = _login(client, "teacher", "t43-route-bank-outsider")
    student = _login(client, "student", "t43-route-bank-student")
    class_id = _classroom(client, teacher, "t43-route-bank-student")
    created = client.post(
        f"/classes/{class_id}/pbl-sessions",
        headers=_headers(teacher),
        json=_session_payload(db),
    )
    assert created.status_code == 201, created.text
    _, detail = complete_bank_route(client, student, session_id=created.json()["id"])
    test_id = detail["test_summary"]["id"]
    test_view = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher))
    assert test_view.status_code == 200, test_view.text
    question_id = test_view.json()["questions"][0]["id"]
    teacher_id = db.scalar(select(User.id).where(User.external_id == "t43-route-bank-owner"))
    source = learning_route_result_read_port(db).bank_source(teacher_id, question_id)
    content_keys = (
        "task_type",
        "title",
        "prompt",
        "options",
        "answer",
        "explanation",
        "point_codes",
        "dimension_ids",
    )
    content = {key: source[key] for key in content_keys}
    request = {
        **content,
        "source_type": "route_test_question",
        "source_id": question_id,
        "source_digest": source["source_digest"],
        "client_request_id": "t43-route-bank-import",
        "deidentified": True,
    }

    assert client.get("/teacher/question-bank", headers=_headers(teacher)).json()["total"] == 0
    assert client.post("/teacher/question-bank/import", headers=_headers(outsider), json=request).status_code == 404
    assert (
        client.post(
            "/teacher/question-bank/import", headers=_headers(teacher), json={**request, "deidentified": False}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/teacher/question-bank/import",
            headers=_headers(teacher),
            json={
                **request,
                "client_request_id": "t43-route-bank-sensitive",
                "prompt": "学生姓名：张同学的诊断是什么？",
            },
        ).status_code
        == 422
    )

    imported = client.post("/teacher/question-bank/import", headers=_headers(teacher), json=request)
    assert imported.status_code == 200, imported.text
    bank_id = imported.json()["id"]
    assert (
        client.post("/teacher/question-bank/import", headers=_headers(teacher), json=request).json() == imported.json()
    )
    conflict = client.post(
        "/teacher/question-bank/import",
        headers=_headers(teacher),
        json={**request, "client_request_id": "t43-route-bank-conflict", "prompt": "篡改来源题目"},
    )
    assert conflict.status_code == 409
    assert db.scalar(select(func.count()).select_from(BankImportReceipt)) == 1
    assert db.scalar(select(func.count()).select_from(TeacherQuestionBankRevision)) == 1
    assert client.get(f"/teacher/question-bank/{bank_id}", headers=_headers(outsider)).status_code == 404
    assert client.get("/teacher/question-bank", headers=_headers(outsider)).json()["total"] == 0

    edited_content = {**content, "prompt": "教师调整后的个人题库副本。"}
    edited = client.put(
        f"/teacher/question-bank/{bank_id}",
        headers=_headers(teacher),
        json={**edited_content, "version": 1},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["version"] == 2
    assert edited.json()["medical_review_status"] == "not_required"
    assert (
        client.put(
            f"/teacher/question-bank/{bank_id}",
            headers=_headers(outsider),
            json={**edited_content, "version": 2},
        ).status_code
        == 404
    )
    assert db.scalar(select(func.count()).select_from(TeacherQuestionBankRevision)) == 2

    archived = client.post(
        f"/teacher/question-bank/{bank_id}/archive",
        headers=_headers(teacher),
        json={"version": 2, "client_request_id": "t43-route-bank-archive"},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"
    replay = client.post(
        f"/teacher/question-bank/{bank_id}/archive",
        headers=_headers(teacher),
        json={"version": 2, "client_request_id": "t43-route-bank-archive"},
    )
    assert replay.status_code == 200
    assert replay.json() == archived.json()
    assert (
        client.post(
            f"/teacher/question-bank/{bank_id}/archive",
            headers=_headers(outsider),
            json={"version": 2, "client_request_id": "t43-route-bank-other-archive"},
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/teacher/question-bank/{bank_id}",
            headers=_headers(teacher),
            json={**edited_content, "version": 3},
        ).status_code
        == 404
    )
    assert db.scalar(select(func.count()).select_from(BankArchiveReceipt)) == 1
    assert client.get("/teacher/question-bank", headers=_headers(teacher)).json()["total"] == 0
    assert (
        client.get("/teacher/question-bank", headers=_headers(teacher), params={"status": "archived"}).json()["total"]
        == 0
    )

    question = db.scalar(select(RouteTestQuestion).where(RouteTestQuestion.public_id == question_id))
    final_test = db.get(RouteFinalTest, question.test_id)
    before = client.get(f"/learning/teacher/final-tests/{final_test.public_id}", headers=_headers(teacher)).json()
    assert before["questions"][0]["id"] == question_id
    assert before["questions"][0]["prompt"] == source["prompt"]
