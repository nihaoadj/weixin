"""Teacher resources are directly maintained; teaching history stays frozen."""

from copy import deepcopy

from sqlalchemy import select

from app.modules.content.infrastructure.models import Problem
from app.modules.content.infrastructure.question_bank_models import TeacherQuestionBankItem, TeacherQuestionBankRevision
from app.modules.identity.infrastructure.models import User
from app.modules.pbl.infrastructure.models import PblSession
from app.modules.training.infrastructure.models import CaseAttempt
from app.modules.training.infrastructure.repositories import SqlAlchemyTrainingRepository
from tests.test_pbl_api import _classroom, _headers, _login
from tests.test_t63_content_learning_pruning import _case_payload

POINT = "pathology.inflammation.vascular"


def _create(client, headers):
    payload = {**_case_payload(client, headers, "t64-own"), "knowledge_point_codes": [POINT]}
    response = client.post("/problems", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "published"
    assert response.json()["medical_review_status"] == "not_required"
    assert response.json()["allowed_actions"] == ["edit", "delete"]
    return response.json()["id"], payload


def test_case_save_edit_delete_permissions_and_retired_review(client, db):
    owner = _headers(_login(client, "teacher", "t64-owner"))
    other = _headers(_login(client, "teacher", "t64-other"))
    student = _headers(_login(client, "student", "t64-student"))
    reviewer = _headers(_login(client, "teacher", "demo_reviewer"))
    case_id, payload = _create(client, owner)
    for status in ("pending", "approved", "rejected"):
        db.get(Problem, case_id).medical_review_status = status
        db.commit()
        response = client.put(f"/problems/{case_id}", headers=owner, json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["medical_review_status"] == "not_required"
    assert client.put(f"/problems/{case_id}", headers=other, json=payload).status_code == 404
    assert client.delete(f"/problems/{case_id}", headers=other).status_code == 404
    assert client.delete(f"/problems/{case_id}", headers=student).status_code == 403
    assert client.delete(f"/problems/{case_id}").status_code == 401
    assert case_id not in [item["id"] for item in client.get("/problems", headers=other).json()]
    for path in ("publish", "reject", "clone-version", "medical-review/submit"):
        response = client.post(f"/problems/{case_id}/{path}", headers=owner)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "RETIRED_FLOW"
    decision = client.post(
        f"/problems/{case_id}/medical-review",
        headers=reviewer,
        json={"decision": "approved", "comment": "历史流程"},
    )
    assert decision.status_code == 409
    assert client.get("/problems/review-queue", headers=reviewer).json() == []
    assert client.delete(f"/problems/{case_id}", headers=owner).status_code == 204
    assert client.delete(f"/problems/{case_id}", headers=owner).status_code == 204
    for headers in (owner, student):
        assert client.get(f"/problems/{case_id}", headers=headers).status_code == 404
        assert case_id not in [item["id"] for item in client.get("/problems", headers=headers).json()]
    assert client.get(f"/problems/{case_id}/authoring", headers=owner).status_code == 404
    assert client.put(f"/problems/{case_id}", headers=owner, json=payload).status_code == 404
    assert client.post(f"/problems/{case_id}/attempts", headers=student, json={}).status_code == 404
    db.expire_all()
    assert db.get(Problem, case_id).status == "deleted"


def test_system_case_is_readonly_and_incomplete_save_rejected(client, db):
    owner = _headers(_login(client, "teacher", "t64-owner"))
    case_id, payload = _create(client, owner)
    db.get(Problem, case_id).author_id = None
    db.commit()
    assert client.get(f"/problems/{case_id}", headers=owner).json()["allowed_actions"] == []
    assert client.put(f"/problems/{case_id}", headers=owner, json=payload).status_code == 404
    assert client.delete(f"/problems/{case_id}", headers=owner).status_code == 404
    assert client.post("/problems", headers=owner, json={**payload, "case_definition": {}}).status_code == 422
    assert client.post("/problems", headers=owner, json={**payload, "rubric": {}}).status_code == 422
    assert (
        client.post(
            "/problems", headers=owner, json={**payload, "knowledge_point_codes": ["invalid.point"]}
        ).status_code
        == 422
    )


def test_case_update_omitted_knowledge_binding_is_preserved_and_explicit_change_is_owned(client, db):
    owner = _headers(_login(client, "teacher", "t64-binding-owner"))
    other = _headers(_login(client, "teacher", "t64-binding-other"))
    case_id, payload = _create(client, owner)
    legacy_update = {key: value for key, value in payload.items() if key != "knowledge_point_codes"}
    preserved = client.put(f"/problems/{case_id}", headers=owner, json=legacy_update)
    assert preserved.status_code == 200, preserved.text
    assert preserved.json()["knowledge_point_codes"] == [POINT]
    next_point = "pathology.cell-injury.reversible"
    changed_payload = {**legacy_update, "knowledge_point_codes": [next_point]}
    assert client.put(f"/problems/{case_id}", headers=other, json=legacy_update).status_code == 404
    assert client.put(f"/problems/{case_id}", headers=other, json=changed_payload).status_code == 404
    changed = client.put(f"/problems/{case_id}", headers=owner, json=changed_payload)
    assert changed.status_code == 200, changed.text
    assert changed.json()["knowledge_point_codes"] == [next_point]
    cleared = client.put(
        f"/problems/{case_id}",
        headers=owner,
        json={**legacy_update, "knowledge_point_codes": []},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["knowledge_point_codes"] == []
    db.expire_all()
    assert db.get(Problem, case_id).knowledge_point_codes == ()


def test_classroom_and_attempt_snapshots_survive_case_edit_and_delete(client, db):
    token = _login(client, "teacher", "t64-owner")
    owner = _headers(token)
    student = _headers(_login(client, "student", "t64-student"))
    class_id = _classroom(client, token, "t64-student")
    case_id, payload = _create(client, owner)

    def create_session():
        return client.post(
            f"/classes/{class_id}/pbl-sessions",
            headers=owner,
            json={"topic_code": "pathology.inflammation", "case_id": case_id, "goal_point_codes": [POINT]},
        )

    classroom = create_session()
    assert classroom.status_code == 201, classroom.text
    frozen_context = deepcopy(db.get(PblSession, classroom.json()["id"]).case_context)
    started = client.post(f"/problems/{case_id}/attempts", headers=student, json={})
    assert started.status_code == 200, started.text
    attempt_id = started.json()["id"]
    db.expire_all()
    attempt = db.get(CaseAttempt, attempt_id)
    assert attempt.problem_snapshot["case_definition"] == payload["case_definition"]
    frozen_snapshot = deepcopy(attempt.problem_snapshot)
    # Simulate a pre-T64 attempt: the first mutation must backfill its original definition.
    attempt.problem_snapshot = None
    db.commit()
    changed_definition = deepcopy(payload["case_definition"])
    changed_definition["opening"]["chief_complaint"] = "更新后的主诉"
    changed = {**payload, "title": "更新病例", "case_definition": changed_definition}
    assert client.put(f"/problems/{case_id}", headers=owner, json=changed).status_code == 200
    db.expire_all()
    assert db.get(CaseAttempt, attempt_id).problem_snapshot == frozen_snapshot
    assert db.get(PblSession, classroom.json()["id"]).case_context == frozen_context
    assert client.delete(f"/problems/{case_id}", headers=owner).status_code == 204
    assert create_session().status_code == 422
    historical = client.get(f"/attempts/{attempt_id}", headers=student)
    assert historical.status_code == 200, historical.text
    assert historical.json()["problem_id"] == case_id
    assert historical.json()["opening"] == frozen_snapshot["case_definition"]["opening"]
    persisted_attempt = db.get(CaseAttempt, attempt_id)
    scoring_input = SqlAlchemyTrainingRepository(db).find_attempt(persisted_attempt.student_id, attempt_id)
    assert scoring_input.problem.case_definition == frozen_snapshot["case_definition"]
    assert scoring_input.problem.rubric == frozen_snapshot["rubric"]
    assert "problem_snapshot" not in historical.json()
    assert (
        client.post(
            f"/attempts/{attempt_id}/messages", headers=student, json={"content": "请问症状多久了？"}
        ).status_code
        == 200
    )
    db.expire_all()
    assert db.get(CaseAttempt, attempt_id).problem_snapshot == frozen_snapshot


def test_case_classroom_selection_keeps_owner_target_and_topic_checks(client, db):
    token = _login(client, "teacher", "t64-owner")
    owner = _headers(token)
    _login(client, "student", "t64-student")
    class_id = _classroom(client, token, "t64-student")
    case_id, _ = _create(client, owner)
    case = db.get(Problem, case_id)
    original_owner = case.author_id
    other_id = db.scalar(select(User.id).where(User.external_id == "demo_reviewer"))
    if other_id is None:
        _login(client, "teacher", "demo_reviewer")
        other_id = db.scalar(select(User.id).where(User.external_id == "demo_reviewer"))

    def select_case():
        return client.post(
            f"/classes/{class_id}/pbl-sessions",
            headers=owner,
            json={"topic_code": "pathology.inflammation", "case_id": case_id, "goal_point_codes": [POINT]},
        )

    case.author_id = other_id
    db.commit()
    assert select_case().status_code == 422
    case.author_id = original_owner
    case.target = "class"
    case.target_ids = "another-class"
    db.commit()
    assert select_case().status_code == 422
    case.target = "all"
    case.knowledge_links.clear()
    db.commit()
    assert select_case().status_code == 422


def test_question_bank_delete_is_versioned_idempotent_and_hidden(client, db):
    owner = _headers(_login(client, "teacher", "t64-bank-owner"))
    other = _headers(_login(client, "teacher", "t64-bank-other"))
    student = _headers(_login(client, "student", "t64-bank-student"))
    owner_id = db.scalar(select(User.id).where(User.external_id == "t64-bank-owner"))
    item = TeacherQuestionBankItem(owner_teacher_id=owner_id, status="active", version=1)
    db.add(item)
    db.flush()
    revision = TeacherQuestionBankRevision(
        bank_item_id=item.id,
        version=1,
        source_kind="route_test_question",
        source_public_id="source",
        source_digest="0" * 64,
        task_type="retest",
        title="副本",
        prompt="题干",
        options=["A", "B"],
        answer={"correct_option": 0},
        explanation="解析",
        point_codes=[POINT],
        dimension_ids=[],
    )
    db.add(revision)
    db.flush()
    item.current_revision_id = revision.id
    db.commit()
    path = f"/teacher/question-bank/{item.id}"
    payload = {"version": 1, "client_request_id": "delete-once"}

    def delete(headers=None, body=payload):
        return client.request("DELETE", path, headers=headers, json=body)

    assert delete().status_code == 401
    assert delete(student).status_code == 403
    assert delete(other).status_code == 404
    assert delete(owner, {**payload, "version": 2}).status_code == 409
    assert delete(owner).status_code == 204
    assert delete(owner).status_code == 204
    assert delete(owner, {**payload, "client_request_id": "new-request"}).status_code == 409
    assert client.get(path, headers=owner).status_code == 404
    for status in ("active", "archived"):
        assert client.get(f"/teacher/question-bank?status={status}", headers=owner).json()["items"] == []
    update_payload = {
        "version": 2,
        "task_type": "retest",
        "title": "更新",
        "prompt": "更新题干",
        "options": ["A", "B"],
        "answer": {"correct_option": 0},
        "explanation": "解析",
        "point_codes": [POINT],
        "dimension_ids": [],
    }
    assert client.put(path, headers=owner, json=update_payload).status_code == 404
    db.expire_all()
    assert db.get(TeacherQuestionBankItem, item.id).status == "archived"
    assert db.get(TeacherQuestionBankRevision, revision.id).prompt == "题干"
