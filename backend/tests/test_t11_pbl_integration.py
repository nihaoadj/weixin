"""API-mode synthetic end-to-end evidence. Network is blocked by T01 fixtures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.bootstrap.seed import seed_showcase_case
from app.modules.content.domain.card_blueprints import CARDS, RECALL_CARDS
from app.modules.content.infrastructure.knowledge_catalog_repository import SqlAlchemyKnowledgeCatalogRepository
from app.modules.content.infrastructure.models import Problem, ProblemKnowledgeLink, ProblemOrigin
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.models import LearningPlan
from app.modules.pbl.application.records import InferenceResult
from app.modules.pbl.infrastructure.models import PblMessage, PblParticipation, PblSession
from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository
from app.modules.pbl.wiring import LocalMockGateway
from app.modules.qa.infrastructure.models import Conversation, Message
from app.testing_resources import cleanup_managed_database, create_managed_database
from scripts.transition_pathology import backup_verified, clean_retired_content, connect, fingerprint, inventory


def login(client, role, external_id):
    response = client.post(
        "/auth/demo-login", json={"role": role, "external_id": external_id, "nickname": external_id, "avatar_url": ""}
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.fixture
def context(client, db, monkeypatch):
    seed_showcase_case(db)
    teacher = login(client, "teacher", "demo_teacher")
    student = login(client, "student", "demo_student")
    outsider = login(client, "student", "outsider")
    other_teacher = login(client, "teacher", "other_teacher")
    gateway = LocalMockGateway()
    monkeypatch.setattr("app.modules.pbl.wiring._gateway", lambda: (gateway, "local_mock", "test"))
    classroom = client.get("/classes", headers=teacher).json()[0]
    case = db.scalar(select(Problem).where(Problem.slug == "pathology.inflammation-showcase"))
    payload = {
        "topic_code": "pathology.inflammation",
        "case_id": case.id,
        "goal_point_codes": ["pathology.inflammation.vascular"],
    }
    created = client.post(f"/classes/{classroom['id']}/pbl-sessions", headers=teacher, json=payload)
    assert created.status_code == 201, created.text
    assert db.get(PblSession, created.json()["id"]).ai_schema_version == 8
    return teacher, student, outsider, other_teacher, classroom, created.json(), gateway


def discussion(client, context):
    teacher, student, _, _, _, session, _ = context
    path = f"/student/pbl-sessions/{session['id']}/messages"
    first = client.post(path, headers=student, json={"client_message_id": "first", "content": "为什么红肿？"})
    assert first.status_code == 200, first.text
    assert first.json()["diagnostic"]["diagnostic_status"] == "probing"
    responses = [first]
    for message_id, content in (
        ("second", "我提出血管扩张与通透性升高两个机制假设，但仍不确定。"),
        ("third", "充血支持血流增加，渗出支持通透性变化，但形态证据有限。"),
        ("fourth", "综合来看两种机制共同解释红肿，仍需更多形态证据复核。"),
    ):
        response = client.post(path, headers=student, json={"client_message_id": message_id, "content": content})
        assert response.status_code == 200, response.text
        responses.append(response)
    second = responses[-1]
    assert second.json()["diagnostic"]["diagnostic_status"] == "ready"
    queue = client.get("/teacher/pbl-diagnostics", headers=teacher)
    assert queue.status_code == 200, queue.text
    assert queue.json()["items"][0]["recommended_questions"] == []
    return path, first.json(), second.json(), queue.json()["items"][0]


def publish(client, context):
    path = "/teacher/pbl-question-suggestions/1/adopt-and-publish"
    payload = {}
    return path, payload, client.post(path, headers=context[0], json=payload)


def test_legacy_suggestion_actions_do_not_create_learning_plans(client, db, context):
    path, first, second, diagnostic = discussion(client, context)
    teacher, student, _, other_teacher, classroom, session, _ = context
    assert diagnostic["student_name"] == "demo_student"
    assert diagnostic["class_name"] == classroom["name"]
    assert diagnostic["session_id"] == session["id"]
    if diagnostic["knowledge_gaps"]:
        assert diagnostic["knowledge_gaps"][0]["evidence_message_ids"] == [second["messages"][-2]["id"]]
    assert diagnostic["recommended_questions"] == []
    assert client.get("/teacher/pbl-diagnostics", headers=other_teacher).json()["items"] == []
    assert client.get(f"/teacher/pbl-diagnostics/{diagnostic['id']}", headers=other_teacher).status_code == 404
    assert client.get("/teacher/pbl-diagnostics?limit=21", headers=teacher).status_code == 422
    assert client.get("/teacher/pbl-diagnostics?offset=20", headers=teacher).json()["items"] == []
    assert client.get("/teacher/pbl-diagnostics?class_id=999", headers=teacher).json()["total"] == 0
    edit_path = "/teacher/pbl-question-suggestions/1"
    edit = client.patch(
        edit_path,
        headers=teacher,
        json={},
    )
    assert edit.status_code == 409
    assert edit.json()["detail"]["reason"] == "RETIRED_FLOW"
    adopt_path, payload, adopted = publish(client, context)
    assert adopted.status_code == 409
    assert adopted.json()["detail"]["reason"] == "RETIRED_FLOW"
    repeated = client.post(adopt_path, headers=teacher, json=payload)
    assert repeated.status_code == 409 and repeated.json()["detail"]["reason"] == "RETIRED_FLOW"
    assert client.post(adopt_path, headers=other_teacher, json=payload).json()["detail"]["reason"] == "RETIRED_FLOW"
    assert client.get("/student/pbl-learning-plans", headers=student).json() == []
    assert db.scalar(select(func.count(LearningPlan.id))) == 0
    # Retrying the first message after a later diagnostic must return its original result.
    repeated = client.post(path, headers=student, json={"client_message_id": "first", "content": "为什么红肿？"})
    assert repeated.json()["diagnostic"] == first["diagnostic"]


def test_t11_closed_history_scope_phase_and_private_follow_up(client, db, context):
    teacher, student, outsider, other_teacher, classroom, session, _ = context
    path, _, completed, diagnostic = discussion(client, context)
    phase_path = f"/classes/{classroom['id']}/pbl-sessions/{session['id']}/phase"
    assert client.patch(phase_path, headers=teacher, json={"phase": "evidence", "version": 1}).status_code == 409
    assert client.patch(phase_path, headers=teacher, json={"phase": "synthesis", "version": 1}).status_code == 409
    db.expire_all()
    assert (
        client.post(f"/classes/{classroom['id']}/pbl-sessions/{session['id']}/close", headers=teacher).status_code
        == 200
    )
    assert client.get(f"/student/pbl-sessions/{session['id']}/participation", headers=student).status_code == 200
    assert client.get(f"/student/pbl-sessions/{session['id']}/participation", headers=outsider).status_code == 404
    private = client.post(path, headers=student, json={"client_message_id": "closed-new", "content": "新消息"})
    assert private.status_code == 200
    assert private.json()["response_kind"] == "private_follow_up"
    assert private.json()["diagnostic"] == completed["diagnostic"]
    assert private.json()["phase_started_revision"] == completed["phase_started_revision"]
    assert private.json()["completion_snapshot_id"] == completed["completion_snapshot_id"]
    assert client.get("/student/pbl-sessions", headers=student).json()[0]["status"] == "closed"
    assert publish(client, context)[2].status_code == 409


@pytest.mark.parametrize("kind", ["point", "evidence", "schema", "failure"])
def test_t11_invalid_diagnosis_never_enters_queue(client, context, monkeypatch, kind):
    gateway = context[-1]
    original = gateway.infer

    def invalid(request):
        result = original(request)
        if result.diagnostic_status != "ready":
            return result
        if kind == "failure":
            return replace(result, diagnostic_status="unavailable", failure_reason="timeout")
        if kind == "schema":
            return replace(result, schema_version=1)
        gap = dict(result.knowledge_gaps[0])
        if kind == "point":
            gap["point_code"] = "respiratory.cap"
        if kind == "evidence":
            gap["evidence_message_ids"] = ["another-students-message"]
        return replace(result, knowledge_gaps=(gap,))

    monkeypatch.setattr(gateway, "infer", invalid)
    path = f"/student/pbl-sessions/{context[5]['id']}/messages"
    for index in range(4):
        response = client.post(
            path, headers=context[1], json={"client_message_id": str(index), "content": "合成病理学问题"}
        )
        assert response.status_code == 200
    assert response.json()["diagnostic"]["diagnostic_status"] == "unavailable"
    assert response.json()["diagnostic"]["knowledge_gaps"] == []
    assert client.get("/teacher/pbl-diagnostics", headers=context[0]).json()["total"] == 0


def test_t11_catalog_integrity_and_old_codes(client, db, context):
    points = SqlAlchemyKnowledgeCatalogRepository(db).tree_view()
    assert len(points) == 30 and len(CARDS) == 120 and len(RECALL_CARDS) == 30
    codes = {str(point["code"]) for point in points}
    graph = {str(point["code"]): tuple(point["prerequisite_codes"]) for point in points}

    def visit(code, ancestors):
        assert code not in ancestors
        for dependency in graph[code]:
            assert dependency in codes
            visit(dependency, ancestors | {code})

    for point in points:
        code = str(point["code"])
        visit(code, set())
        assert set(point["related_codes"]) <= codes
        own = [card for card in CARDS if card.point_code == code]
        assert len(own) == 4 and len({card.prompt for card in own}) == 4
        assert all(0 <= card.correct_option < len(card.options) for card in own)
    tree = client.get("/knowledge/tree", headers=context[1]).json()
    assert tree["catalog_version"] == "pathology-general-v4" and len(tree["items"]) == 30
    assert sum(len(point["dependencies"]) for point in tree["items"]) == 34
    assert "correct_option" not in str(tree)
    assert client.get("/knowledge/points/respiratory.cap", headers=context[1]).status_code == 404


def test_t11_interrupted_message_recovers_original_result(client, db, context):
    teacher, student, _, _, _, session, _ = context
    client.get(f"/student/pbl-sessions/{session['id']}/participation", headers=student)
    part = db.scalar(select(PblParticipation).where(PblParticipation.session_id == session["id"]))
    repo = SqlAlchemyPblRepository(db)
    pending = repo.append_student_message(part.id, "interrupted", "讨论被中断")
    message = db.scalar(select(PblMessage).where(PblMessage.participation_id == part.id))
    message.created_at = datetime.now(UTC) - timedelta(seconds=61)
    db.commit()
    path = f"/student/pbl-sessions/{session['id']}/messages"
    payload = {"client_message_id": "interrupted", "content": "讨论被中断"}
    response = client.post(path, headers=student, json=payload)
    assert response.status_code == 200
    assert response.json()["diagnostic"]["diagnostic_status"] == "unavailable"
    assert client.post(path, headers=student, json=payload).json() == response.json()
    assert (
        repo.save_result(part.id, pending.revision, InferenceResult("迟到结果", "probing", follow_up_question="问题"))
        is None
    )
    assert client.get("/teacher/pbl-diagnostics", headers=teacher).json()["total"] == 0


def test_legacy_case_retry_cannot_create_a_plan(client, db, context):
    discussion(client, context)
    retired = publish(client, context)[2]
    assert retired.status_code == 409 and retired.json()["detail"]["reason"] == "RETIRED_FLOW"
    student = context[1]
    assert client.get("/student/pbl-learning-plans", headers=student).json() == []
    assert db.scalar(select(func.count(LearningPlan.id))) == 0


def test_legacy_publish_cannot_activate_either_task_cycle(client, db, context):
    discussion(client, context)
    retired = publish(client, context)[2]
    assert retired.status_code == 409 and retired.json()["detail"]["reason"] == "RETIRED_FLOW"
    student = context[1]
    assert client.get("/student/pbl-learning-plans", headers=student).json() == []
    assert db.scalar(select(func.count(LearningPlan.id))) == 0


def test_t11_conversion_preserves_pbl_mixed_and_original_records(client, db, context):
    discussion(client, context)
    # A legacy PBL-origin question with an exact seed id is retained, with only its old association removed.
    problem = Problem(
        type="题目",
        title="历史 PBL 建议题",
        description="仅用于迁移兼容测试。",
        target="all",
        target_label="全体学生",
        target_ids="",
        status="published",
        slug="demo-question-001",
    )
    db.add(problem)
    db.flush()
    db.add(ProblemOrigin(problem_id=problem.id, source_type="pbl_suggestion", source_id=1))
    db.add(ProblemKnowledgeLink(problem_id=problem.id, point_code="respiratory.cap"))
    student = db.scalar(select(User).where(User.external_id == "demo_student"))
    original = Conversation(client_id="original-non-example", student_id=student.id)
    db.add(original)
    db.flush()
    db.add(Message(conversation_id=original.id, role="user", content="合成原始回答保留"))
    db.commit()
    source = Path(db.bind.url.database).resolve()
    resource = create_managed_database("t11-conversion-test")
    target = resource.database_path
    try:
        backup_verified(source, target)
        with connect(target) as copy_db:
            before = inventory(copy_db)
            clean_retired_content(copy_db)
            after = inventory(copy_db)
            for table in (
                "users",
                "classes",
                "class_members",
                "pbl_sessions",
                "pbl_participations",
                "pbl_messages",
                "learning_plans",
                "learning_tasks",
                "conversations",
                "messages",
            ):
                assert fingerprint(before[table]) == fingerprint(after[table])
            assert any(row["id"] == problem.id for row in after["problems"])
            assert not any(row["point_code"] == "respiratory.cap" for row in after["problem_knowledge_links"])
            assert not copy_db.execute("PRAGMA foreign_key_check").fetchall()
        # Conversion of a copy cannot modify the owned test source.
        with connect(source, readonly=True) as original_db:
            assert fingerprint(inventory(original_db)) == fingerprint(before)
    finally:
        cleanup_managed_database(resource)
