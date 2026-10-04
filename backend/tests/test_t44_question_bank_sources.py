"""DB04: teacher-owned copies use the public UUID of a route test question."""

import pytest
from sqlalchemy import select

from app.modules.content.infrastructure.question_bank_models import (
    BankImportReceipt,
    TeacherQuestionBankRevision,
)
from app.modules.identity.infrastructure.models import User
from app.modules.learning.domain.learning_routes import digest
from app.modules.learning.infrastructure.route_models import LearningRoute, RouteFinalTest, RouteTestQuestion
from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore
from app.modules.learning.wiring import learning_route_result_read_port
from app.shared.errors import AppError
from tests.t44_route_support import complete_bank_route, configure_bank_route
from tests.test_pbl_api import _classroom, _headers, _login, _session_payload


def test_question_bank_import_uses_route_question_uuid_and_replays_by_source(client, db, monkeypatch):
    configure_bank_route(monkeypatch)
    teacher = _login(client, "teacher", "t44-bank-owner")
    student = _login(client, "student", "t44-bank-member")
    class_id = _classroom(client, teacher, "t44-bank-member")
    created = client.post(
        f"/classes/{class_id}/pbl-sessions",
        headers=_headers(teacher),
        json=_session_payload(db),
    )
    assert created.status_code == 201, created.text
    route_id, detail = complete_bank_route(client, student, session_id=created.json()["id"])
    test_id = detail["test_summary"]["id"]
    test = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher))
    assert test.status_code == 200, test.text
    question_id = test.json()["questions"][0]["id"]
    teacher_id = db.scalar(select(User.id).where(User.external_id == "t44-bank-owner"))
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
    payload = {
        "source_type": source["source_type"],
        "source_id": source["source_id"],
        "source_digest": source["source_digest"],
        "client_request_id": "t44-bank-import",
        "deidentified": True,
        **{key: source[key] for key in content_keys},
    }

    denied = client.post(
        "/teacher/question-bank/import",
        headers=_headers(_login(client, "teacher", "t44-other-bank-owner")),
        json=payload,
    )
    assert denied.status_code == 404

    imported = client.post("/teacher/question-bank/import", headers=_headers(teacher), json=payload)
    assert imported.status_code == 200, imported.text
    replay = client.post("/teacher/question-bank/import", headers=_headers(teacher), json=payload)
    assert replay.status_code == 200
    assert replay.json() == imported.json()

    other_request = client.post(
        "/teacher/question-bank/import",
        headers=_headers(teacher),
        json={**payload, "client_request_id": "t44-bank-import-again"},
    )
    assert other_request.status_code == 409
    changed_source_content = client.post(
        "/teacher/question-bank/import",
        headers=_headers(teacher),
        json={**payload, "client_request_id": "t44-bank-import-edited", "prompt": "被改写的来源题目"},
    )
    assert changed_source_content.status_code == 409

    changed_copy = client.put(
        f"/teacher/question-bank/{imported.json()['id']}",
        headers=_headers(teacher),
        json={
            **{key: source[key] for key in content_keys},
            "title": "教师自定义复习题",
            "prompt": "教师调整后的个人题库题干",
            "version": 1,
        },
    )
    assert changed_copy.status_code == 200, changed_copy.text
    assert changed_copy.json()["prompt"] == "教师调整后的个人题库题干"
    refreshed_test = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher))
    assert refreshed_test.json()["questions"] == test.json()["questions"]

    revision = db.scalar(select(TeacherQuestionBankRevision))
    receipt = db.scalar(select(BankImportReceipt))
    assert revision.source_kind == receipt.source_kind == "route_test_question"
    assert revision.source_public_id == receipt.source_public_id == question_id
    assert revision.source_package_item_id is None
    assert receipt.source_package_item_id is None
    assert route_id
    deleted = client.request(
        "DELETE",
        f"/teacher/question-bank/{imported.json()['id']}",
        headers=_headers(teacher),
        json={"version": changed_copy.json()["version"], "client_request_id": "t64-delete-imported"},
    )
    assert deleted.status_code == 204
    assert client.post("/teacher/question-bank/import", headers=_headers(teacher), json=payload).status_code == 404
    assert (
        client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).json()
        == refreshed_test.json()
    )


def test_bank_source_rejects_autonomous_route_question_for_teacher(client, db, monkeypatch):
    configure_bank_route(monkeypatch)
    teacher = _login(client, "teacher", "t44-private-bank-owner")
    student = _login(client, "student", "t44-private-bank-student")
    route_id, _ = complete_bank_route(client, student)
    route = db.scalar(select(LearningRoute).where(LearningRoute.public_id == route_id))
    test = db.scalar(select(RouteFinalTest).where(RouteFinalTest.route_id == route.id))
    question = db.scalar(select(RouteTestQuestion).where(RouteTestQuestion.test_id == test.id))
    teacher_id = db.scalar(select(User.id).where(User.external_id == "t44-private-bank-owner"))
    source_store = learning_route_result_read_port(db)
    with pytest.raises(AppError) as error:
        source_store.bank_source(teacher_id, question.public_id)
    assert error.value.status_code == 404

    payload = SqlLearningRouteStore(db)._bank_payload(question)
    response = client.post(
        "/teacher/question-bank/import",
        headers=_headers(teacher),
        json={
            **payload,
            "source_type": "route_test_question",
            "source_id": question.public_id,
            "source_digest": digest(payload),
            "client_request_id": "t44-private-bank-import",
            "deidentified": True,
        },
    )
    assert response.status_code == 404
