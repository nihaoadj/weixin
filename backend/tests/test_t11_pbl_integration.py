"""API-mode synthetic end-to-end evidence. Network is blocked by T01 fixtures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.bootstrap.composition import learning_application
from app.bootstrap.seed import seed_showcase_case
from app.bootstrap.test_seed import _seed_assessed_attempt
from app.modules.content.domain.knowledge_catalog import CARDS, POINTS, RECALL_CARDS
from app.modules.content.infrastructure.models import Problem, ProblemKnowledgeLink, ProblemOrigin
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.models import LearningPlan, LearningTask, LearningTaskAttempt, ReviewAttempt
from app.modules.pbl.application.records import InferenceResult
from app.modules.pbl.infrastructure.models import PblMessage, PblParticipation
from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository
from app.modules.pbl.wiring import LocalMockGateway
from app.modules.qa.infrastructure.models import Conversation, Message
from app.modules.training.infrastructure.models import CaseAttempt
from app.shared.actor import Actor
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
    return path, first.json(), second.json(), queue.json()["items"][0]


def publish(client, context, diagnostic, **overrides):
    suggestion = diagnostic["recommended_questions"][0]
    payload = {
        "version": suggestion["version"],
        "title": "教师当前编辑内容",
        "prompt": "比较血流和通透性改变的表现。",
        **overrides,
    }
    path = f"/teacher/pbl-question-suggestions/{suggestion['id']}/adopt-and-publish"
    return path, payload, client.post(path, headers=context[0], json=payload)


def test_t11_atomic_edit_publish_learning_and_teacher_verification(client, db, context):
    path, first, second, diagnostic = discussion(client, context)
    teacher, student, outsider, other_teacher, classroom, session, _ = context
    assert diagnostic["student_name"] == "demo_student"
    assert diagnostic["class_name"] == classroom["name"]
    assert diagnostic["session_id"] == session["id"]
    assert diagnostic["knowledge_gaps"][0]["evidence_message_ids"] == [second["messages"][-2]["id"]]
    assert client.get("/teacher/pbl-diagnostics", headers=other_teacher).json()["items"] == []
    assert client.get(f"/teacher/pbl-diagnostics/{diagnostic['id']}", headers=other_teacher).status_code == 404
    assert client.get("/teacher/pbl-diagnostics?limit=21", headers=teacher).status_code == 422
    assert client.get("/teacher/pbl-diagnostics?offset=20", headers=teacher).json()["items"] == []
    assert client.get("/teacher/pbl-diagnostics?class_id=999", headers=teacher).json()["total"] == 0
    adopt_path, payload, adopted = publish(client, context, diagnostic)
    assert adopted.status_code == 200, adopted.text
    assert client.post(adopt_path, headers=teacher, json=payload).json() == adopted.json()
    assert client.post(adopt_path, headers=other_teacher, json=payload).status_code == 404
    db.expire_all()
    assert db.get(Problem, adopted.json()["problem_id"]).title == payload["title"]
    assert db.scalar(select(func.count(ProblemOrigin.id))) == 1
    assert db.scalar(select(func.count(LearningPlan.id))) == 1
    plans = client.get("/student/pbl-learning-plans", headers=student).json()
    assert len(plans) == 1 and plans[0]["verification_status"] == "not_ready"
    assert client.get("/student/pbl-learning-plans", headers=outsider).json() == []
    assert client.get("/learning-plans/current", headers=student).status_code == 404
    assert not any(word in str(plans) for word in ("correct_option", "private_rubric", "criteria", "fixed_facts"))
    plan = plans[0]
    task_path = f"/student/pbl-learning-tasks/{plan['tasks'][0]['id']}/submit"
    assert (
        client.post(
            task_path, headers=outsider, json={"client_submission_id": "x", "answer": {"text": "x"}}
        ).status_code
        == 404
    )
    for task in [item for item in plan["tasks"] if item["status"] == "pending"]:
        stored = db.get(LearningTask, task["id"])
        answer = (
            {"selected_option": stored.private_rubric["correct_option"]}
            if task["task_type"] in {"knowledge_review", "retest"}
            else {"text": "血管扩张增加血流，通透性增加形成渗出，以形态证据区分机制。"}
        )
        task_path = f"/student/pbl-learning-tasks/{task['id']}/submit"
        task_payload = {"client_submission_id": f"task-{task['id']}", "answer": answer}
        result = client.post(task_path, headers=student, json=task_payload)
        assert result.status_code == 200, result.text
        assert client.post(task_path, headers=student, json=task_payload).json() == result.json()
        plan = result.json()
    assert plan["verification_status"] == "improved"
    db.expire_all()
    assert db.scalar(select(func.count(LearningTaskAttempt.id))) == sum(
        task["status"] == "completed" for task in plan["tasks"]
    )
    assert db.scalar(select(func.count(ReviewAttempt.id))) == 2
    verify_path = f"/teacher/pbl-learning-results/{plan['id']}/verify"
    verification = {"version": plan["version"], "decision": "improved", "note": "讨论与两次客观作答能够支持机制区别。"}
    assert client.post(verify_path, headers=other_teacher, json=verification).status_code == 404
    assert client.post(verify_path, headers=teacher, json=verification).status_code == 409
    summary = client.get(f"/classes/{classroom['id']}/pbl-sessions/{session['id']}/summary", headers=teacher).json()
    assert summary["improved"] == 1 and summary["objective_retest_average"] == 100
    assert summary["completed_tasks"] == sum(task["status"] == "completed" for task in plan["tasks"])
    # Retrying the first message after a later diagnostic must return its original result.
    repeated = client.post(path, headers=student, json={"client_message_id": "first", "content": "为什么红肿？"})
    assert repeated.json()["diagnostic"] == first["diagnostic"]


def test_t11_closed_history_scope_phase_and_invalid_targets(client, db, context):
    teacher, student, outsider, other_teacher, classroom, session, _ = context
    path, _, _, diagnostic = discussion(client, context)
    phase_path = f"/classes/{classroom['id']}/pbl-sessions/{session['id']}/phase"
    assert client.patch(phase_path, headers=teacher, json={"phase": "evidence", "version": 1}).status_code == 409
    assert client.patch(phase_path, headers=teacher, json={"phase": "synthesis", "version": 1}).status_code == 409
    assert publish(client, context, diagnostic, target_student_ids=[999999])[2].status_code == 422
    assert publish(client, context, diagnostic, version=100)[2].status_code == 409
    db.expire_all()
    assert db.scalar(select(func.count(ProblemOrigin.id))) == 0
    assert (
        client.post(f"/classes/{classroom['id']}/pbl-sessions/{session['id']}/close", headers=teacher).status_code
        == 200
    )
    assert client.get(f"/student/pbl-sessions/{session['id']}/participation", headers=student).status_code == 200
    assert client.get(f"/student/pbl-sessions/{session['id']}/participation", headers=outsider).status_code == 404
    assert (
        client.post(path, headers=student, json={"client_message_id": "closed-new", "content": "新消息"}).status_code
        == 409
    )
    assert client.get("/student/pbl-sessions", headers=student).json()[0]["status"] == "closed"
    assert publish(client, context, diagnostic)[2].status_code == 200


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


def test_t11_catalog_integrity_and_old_codes(client, context):
    assert len(POINTS) == 30 and len(CARDS) == 120 and len(RECALL_CARDS) == 30
    codes = {p.code for p in POINTS}
    graph = {p.code: p.prerequisite_codes for p in POINTS}

    def visit(code, ancestors):
        assert code not in ancestors
        for dependency in graph[code]:
            assert dependency in codes
            visit(dependency, ancestors | {code})

    for point in POINTS:
        visit(point.code, set())
        assert set(point.related_codes) <= codes
        own = [card for card in CARDS if card.point_code == point.code]
        assert len(own) == 4 and len({card.prompt for card in own}) == 4
        assert all(0 <= card.correct_option < len(card.options) for card in own)
    tree = client.get("/knowledge/tree", headers=context[1]).json()
    assert tree["catalog_version"] == "pathology-general-v3" and len(tree["items"]) == 30
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


def test_t11_full_case_retry_returns_evidence_to_original_plan(client, db, context):
    _, _, _, diagnostic = discussion(client, context)
    assert publish(client, context, diagnostic, include_case_retry=True)[2].status_code == 200
    teacher, student, *_ = context
    plan = client.get("/student/pbl-learning-plans", headers=student).json()[0]
    for task in [
        item for item in plan["tasks"] if item["status"] == "pending" and item["task_type"] != "focused_retry"
    ]:
        stored = db.get(LearningTask, task["id"])
        answer = (
            {"selected_option": stored.private_rubric["correct_option"]}
            if task["task_type"] in {"knowledge_review", "retest"}
            else {"text": "形态与机制证据核对"}
        )
        result = client.post(
            f"/student/pbl-learning-tasks/{task['id']}/submit",
            headers=student,
            json={"client_submission_id": str(task["id"]), "answer": answer},
        )
        assert result.status_code == 200
    retry = next(item for item in plan["tasks"] if item["status"] == "pending" and item["task_type"] == "focused_retry")
    assert retry["task_type"] == "focused_retry"
    user = db.scalar(select(User).where(User.external_id == "demo_student"))
    # Complete a synthetic structured assessment, then connect its evidence to the original intervention task.
    assessment = _seed_assessed_attempt(db, user, db.get(Problem, retry["problem_id"]))
    attempt = db.get(CaseAttempt, assessment.attempt_id)
    attempt.learning_task_id = retry["id"]
    db.commit()
    learning_application(db).ensure_for_case_completion(Actor.from_user(user), attempt.id)
    updated = client.get("/student/pbl-learning-plans", headers=student).json()[0]
    assert updated["verification_status"] in {"improved", "not_ready"}
    completed_retry = next(item for item in updated["tasks"] if item["id"] == retry["id"])
    assert completed_retry["result"]["answer"]["case_attempt_id"] == attempt.id
    assert db.scalar(select(func.count(LearningPlan.id))) == 1
    assert client.get("/learning-plans/current", headers=student).status_code == 404


def test_t14_first_cycle_failure_activates_only_failed_target_and_second_cycle_improves(client, db, context):
    _, _, _, diagnostic = discussion(client, context)
    assert publish(client, context, diagnostic)[2].status_code == 200
    student = context[1]
    plan = client.get("/student/pbl-learning-plans", headers=student).json()[0]
    inactive = next(task for task in plan["tasks"] if task["status"] == "inactive")
    assert (
        client.post(
            f"/student/pbl-learning-tasks/{inactive['id']}/submit",
            headers=student,
            json={"client_submission_id": "early-cycle-2", "answer": {"text": "early"}},
        ).status_code
        == 409
    )
    first_variants = {task["variant_code"] for task in plan["tasks"] if task["cycle_number"] == 1}
    for task in [item for item in plan["tasks"] if item["status"] == "pending"]:
        stored = db.get(LearningTask, task["id"])
        if task["task_type"] == "retest":
            wrong = (stored.private_rubric["correct_option"] + 1) % len(task["public_definition"]["options"])
            answer = {"selected_option": wrong}
        elif task["task_type"] == "knowledge_review":
            answer = {"selected_option": stored.private_rubric["correct_option"]}
        elif task["task_type"] == "micro_drill":
            keywords = [word for criterion in stored.private_rubric["criteria"] for word in criterion["keywords"]]
            answer = {"text": "、".join(keywords)}
        else:
            answer = {"text": "完成正式讨论并提交证据。"}
        response = client.post(
            f"/student/pbl-learning-tasks/{task['id']}/submit",
            headers=student,
            json={"client_submission_id": f"cycle-1-{task['id']}", "answer": answer},
        )
        assert response.status_code == 200, response.text
        plan = response.json()
    assert plan["current_cycle"] == 2 and plan["decision_basis"]["result"] == "next_cycle_activated"
    active_second = [task for task in plan["tasks"] if task["cycle_number"] == 2 and task["status"] == "pending"]
    assert {task["target_type"] for task in active_second} == {"discussion", "knowledge_gap"}
    assert all(task["variant_code"] not in first_variants for task in active_second)
    for task in active_second:
        stored = db.get(LearningTask, task["id"])
        answer = (
            {"selected_option": stored.private_rubric["correct_option"]}
            if task["task_type"] in {"knowledge_review", "retest"}
            else {"text": "根据首轮反馈重新说明证据链与不确定性。"}
        )
        response = client.post(
            f"/student/pbl-learning-tasks/{task['id']}/submit",
            headers=student,
            json={"client_submission_id": f"cycle-2-{task['id']}", "answer": answer},
        )
        assert response.status_code == 200, response.text
        plan = response.json()
    assert plan["verification_status"] == "improved"
    assert plan["automation_exhausted"] is False


def test_t11_conversion_preserves_pbl_mixed_and_original_records(client, db, context):
    _, _, _, diagnostic = discussion(client, context)
    published = publish(client, context, diagnostic)[2].json()
    # An exact legacy seed id with PBL origin is retained, with only its old association removed.
    problem = db.get(Problem, published["problem_id"])
    problem.slug = "demo-question-001"
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
