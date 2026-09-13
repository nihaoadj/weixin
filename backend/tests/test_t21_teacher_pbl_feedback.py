"""T21 feedback loop: the API tests are deliberately actor-scoped."""

import pytest
from sqlalchemy import select

from app.modules.learning.infrastructure.models import LearningPlan
from app.modules.learning.infrastructure.pbl_interventions import PblLearningStore
from app.modules.pbl.infrastructure.models import PblTeacherFeedback
from tests.test_pbl_api import _classroom, _configure_gateway, _headers, _login, _session_payload
from tests.test_t17_unified_dialogues import _create_dialogue


def _completed_submission(client, student, class_id, prefix="t21"):
    session = _create_dialogue(client, student, class_id, client_id=f"{prefix}-dialogue").json()["session"]["id"]
    for index in range(4):
        response = client.post(
            f"/student/learning-dialogues/{session}/messages",
            headers=_headers(student),
            json={"client_message_id": f"{prefix}-{index}", "content": f"第 {index + 1} 阶段证据"},
        )
        assert response.status_code == 200
    preview = client.get(f"/student/learning-dialogues/{session}/submission", headers=_headers(student)).json()
    response = client.post(
        f"/student/learning-dialogues/{session}/submission",
        headers=_headers(student),
        json={"snapshot_id": preview["snapshot_id"], "class_id": class_id, "client_submission_id": f"{prefix}-share"},
    )
    assert response.status_code == 200
    return session, preview["snapshot_id"]


def test_t21_feedback_is_idempotent_and_hidden_from_other_teachers(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t21-owner")
    other = _login(client, "teacher", "t21-other")
    student = _login(client, "student", "t21-student")
    class_id = _classroom(client, teacher, "t21-student")
    _, snapshot_id = _completed_submission(client, student, class_id)
    assert client.get(f"/teacher/pbl-work-items/{snapshot_id}", headers=_headers(other)).status_code == 404
    payload = {
        "client_feedback_id": "t21-feedback-once",
        "body": "请先重新核对血管反应与证据之间的关系。",
        "action_type": "feedback_only",
    }
    first = client.post(f"/teacher/pbl-work-items/{snapshot_id}/feedback", headers=_headers(teacher), json=payload)
    second = client.post(f"/teacher/pbl-work-items/{snapshot_id}/feedback", headers=_headers(teacher), json=payload)
    assert first.status_code == second.status_code == 200
    assert db.scalars(select(PblTeacherFeedback)).all().__len__() == 1
    changed = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={**payload, "body": "不同正文"},
    )
    assert changed.status_code == 409


def test_t21_feedback_and_publish_creates_a_plan_in_the_same_request(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t21-publish-owner")
    student = _login(client, "student", "t21-publish-student")
    class_id = _classroom(client, teacher, "t21-publish-student")
    _, snapshot_id = _completed_submission(client, student, class_id, "t21-publish")
    item = client.get(f"/teacher/pbl-work-items/{snapshot_id}", headers=_headers(teacher))
    assert item.status_code == 200
    suggestion = item.json()["diagnostic"]["recommended_questions"][0]
    response = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={
            "client_feedback_id": "t21-publish-once",
            "body": "请完成这组正式任务，再回看证据链。",
            "action_type": "task_published",
            "suggestion_id": suggestion["id"],
            "suggestion_version": suggestion["version"],
            "title": suggestion["title"],
            "prompt": suggestion["prompt"],
        },
    )
    assert response.status_code == 200, response.text
    work = client.get("/teacher/pbl-work-items", headers=_headers(teacher)).json()
    assert any(row["snapshot_id"] == snapshot_id and row["status"] == "task_published" for row in work["items"])
    plans = client.get("/student/pbl-learning-plans", headers=_headers(student))
    assert plans.status_code == 200 and plans.json()
    assert (
        client.post(
            f"/teacher/pbl-work-items/{snapshot_id}/feedback",
            headers=_headers(teacher),
            json={
                "client_feedback_id": "t21-after-publish",
                "body": "不应继续在待处理区发送。",
                "action_type": "feedback_only",
            },
        ).status_code
        == 409
    )


def test_t21_student_feedback_is_visible_only_to_the_submitting_student(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t21-feedback-owner")
    student = _login(client, "student", "t21-feedback-student")
    classmate = _login(client, "student", "t21-feedback-classmate")
    class_id = _classroom(client, teacher, "t21-feedback-student")
    session_id, snapshot_id = _completed_submission(client, student, class_id, "t21-feedback-visible")
    response = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={
            "client_feedback_id": "t21-feedback-visible",
            "body": "请把核改变和可逆性损伤的证据分别列出来。",
            "action_type": "feedback_only",
        },
    )
    assert response.status_code == 200
    preview = client.get(f"/student/learning-dialogues/{session_id}/submission", headers=_headers(student))
    assert preview.status_code == 200
    assert preview.json()["teacher_status"] == "responded"
    assert preview.json()["feedbacks"][0]["body"] == "请把核改变和可逆性损伤的证据分别列出来。"
    classmate_preview = client.get(
        f"/student/learning-dialogues/{session_id}/submission", headers=_headers(classmate)
    )
    assert classmate_preview.status_code == 404
    report = client.get(f"/student/pbl-learning-reports/{session_id}", headers=_headers(student))
    assert report.status_code == 200
    assert {item["type"] for item in report.json()["timeline"]} >= {"submitted_to_teacher", "teacher_feedback"}


def test_t21_closed_work_item_blocks_feedback_and_legacy_adoption(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t21-closed-owner")
    student = _login(client, "student", "t21-closed-student")
    class_id = _classroom(client, teacher, "t21-closed-student")
    _, snapshot_id = _completed_submission(client, student, class_id, "t21-closed")
    item = client.get(f"/teacher/pbl-work-items/{snapshot_id}", headers=_headers(teacher)).json()
    suggestion = item["diagnostic"]["recommended_questions"][0]
    close = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={"client_feedback_id": "t21-close", "body": "本轮先到这里，请按建议开启新研讨。", "action_type": "closed"},
    )
    assert close.status_code == 200
    repeat = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={"client_feedback_id": "t21-after-close", "body": "不应保存", "action_type": "feedback_only"},
    )
    assert repeat.status_code == 409
    legacy = client.post(
        f"/teacher/pbl-question-suggestions/{suggestion['id']}/adopt-and-publish",
        headers=_headers(teacher),
        json={"version": suggestion["version"], "title": suggestion["title"], "prompt": suggestion["prompt"]},
    )
    assert legacy.status_code == 409


def test_t21_classroom_dashboard_tracks_work_item_status_and_follow_up_isolated(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t21-dashboard-owner")
    student = _login(client, "student", "t21-dashboard-student")
    class_id = _classroom(client, teacher, "t21-dashboard-student")
    created = client.post(
        f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db)
    )
    assert created.status_code == 201
    session_id = created.json()["id"]
    for index in range(4):
        response = client.post(
            f"/student/pbl-sessions/{session_id}/messages",
            headers=_headers(student),
            json={"client_message_id": f"t21-dashboard-{index}", "content": f"第 {index + 1} 阶段课堂证据"},
        )
        assert response.status_code == 200
    items = client.get(
        "/teacher/pbl-work-items?source=classroom_diagnostic", headers=_headers(teacher)
    ).json()["items"]
    snapshot_id = next(item["snapshot_id"] for item in items if item["session_id"] == session_id)
    dashboard = client.get(
        f"/classes/{class_id}/pbl-sessions/{session_id}/dashboard", headers=_headers(teacher)
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["students"][0]["work_item_status"] == "pending"
    assert (
        client.post(
            f"/teacher/pbl-work-items/{snapshot_id}/feedback",
            headers=_headers(teacher),
            json={
                "client_feedback_id": "t21-dashboard-feedback",
                "body": "请把观察到的形态与推理依据逐项对应。",
                "action_type": "feedback_only",
            },
        ).status_code
        == 200
    )
    dashboard = client.get(
        f"/classes/{class_id}/pbl-sessions/{session_id}/dashboard", headers=_headers(teacher)
    )
    assert dashboard.json()["students"][0]["work_item_status"] == "responded"


def test_t21_publish_failure_rolls_back_feedback_and_formal_plan(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t21-rollback-owner")
    student = _login(client, "student", "t21-rollback-student")
    class_id = _classroom(client, teacher, "t21-rollback-student")
    _, snapshot_id = _completed_submission(client, student, class_id, "t21-rollback")
    item = client.get(f"/teacher/pbl-work-items/{snapshot_id}", headers=_headers(teacher)).json()
    suggestion = item["diagnostic"]["recommended_questions"][0]

    def fail_notify(*_args, **_kwargs):
        raise RuntimeError("simulated notification failure")

    monkeypatch.setattr(PblLearningStore, "notify", fail_notify)
    with pytest.raises(RuntimeError, match="simulated notification failure"):
        client.post(
            f"/teacher/pbl-work-items/{snapshot_id}/feedback",
            headers=_headers(teacher),
            json={
                "client_feedback_id": "t21-rollback-publish",
                "body": "这个动作必须整体回滚。",
                "action_type": "task_published",
                "suggestion_id": suggestion["id"],
                "suggestion_version": suggestion["version"],
                "title": suggestion["title"],
                "prompt": suggestion["prompt"],
            },
        )
    db.expire_all()
    assert not db.scalars(select(PblTeacherFeedback).where(PblTeacherFeedback.snapshot_id == snapshot_id)).all()
    assert not db.scalars(select(LearningPlan)).all()
    refreshed = client.get(f"/teacher/pbl-work-items/{snapshot_id}", headers=_headers(teacher)).json()
    assert refreshed["diagnostic"]["recommended_questions"][0]["status"] == "proposed"


def test_t21_follow_up_is_scoped_idempotent_and_does_not_change_mastery(client, db, monkeypatch):
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t21-follow-up-owner")
    other_teacher = _login(client, "teacher", "t21-follow-up-other")
    student = _login(client, "student", "t21-follow-up-student")
    class_id = _classroom(client, teacher, "t21-follow-up-student")
    session_id, snapshot_id = _completed_submission(client, student, class_id, "t21-follow-up")
    item = client.get(f"/teacher/pbl-work-items/{snapshot_id}", headers=_headers(teacher)).json()
    suggestion = item["diagnostic"]["recommended_questions"][0]
    published = client.post(
        f"/teacher/pbl-work-items/{snapshot_id}/feedback",
        headers=_headers(teacher),
        json={
            "client_feedback_id": "t21-follow-up-publish",
            "body": "请先完成正式任务，再针对未达标部分复盘。",
            "action_type": "task_published",
            "suggestion_id": suggestion["id"],
            "suggestion_version": suggestion["version"],
            "title": suggestion["title"],
            "prompt": suggestion["prompt"],
        },
    )
    assert published.status_code == 200
    plan = db.scalar(select(LearningPlan))
    assert plan is not None
    plan.verification_status = "needs_reinforcement"
    plan.automation_exhausted = True
    plan.decision_basis = {
        "failed_targets": [{"target_type": "knowledge", "target_code": "pathology.inflammation.vascular"}]
    }
    db.commit()
    follow_ups = client.get("/teacher/pbl-follow-ups?status=support_needed", headers=_headers(teacher))
    assert follow_ups.status_code == 200
    assert follow_ups.json()["items"][0]["plan_id"] == plan.id
    assert client.get(f"/teacher/pbl-follow-ups/{plan.id}", headers=_headers(other_teacher)).status_code == 404
    payload = {"client_feedback_id": "t21-follow-up-once", "body": "请预约一次针对证据链的补充讨论。"}
    first = client.post(f"/teacher/pbl-follow-ups/{plan.id}/feedback", headers=_headers(teacher), json=payload)
    second = client.post(f"/teacher/pbl-follow-ups/{plan.id}/feedback", headers=_headers(teacher), json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    db.expire_all()
    unchanged = db.get(LearningPlan, plan.id)
    assert unchanged is not None
    assert unchanged.verification_status == "needs_reinforcement"
    assert unchanged.automation_exhausted is True
    report = client.get(f"/student/pbl-learning-reports/{session_id}", headers=_headers(student))
    assert report.status_code == 200
    assert "follow_up_feedback" in {item["type"] for item in report.json()["timeline"]}
