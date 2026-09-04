"""T05 characterization contracts for the post-T01 isolated test fixture.

This module intentionally consumes the fixture names ``client`` and ``db``
that T01 is expected to provide.  It must not create an engine, import the
application engine, drop tables, or mutate a developer database.  The client
fixture must use the same isolated database as ``db`` and set
``raise_server_exceptions=False`` so the injected 500 response is observable.
The report assertions deliberately do not decide the unresolved teacher
class-scope policy; that policy remains a coordination item for T06/product.
"""

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.models import CaseAssessment, LearningPlan, Problem, Report, StudentNotification
from app.services.case_seed import seed_showcase_case


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, role: str, external_id: str, class_ids: list[str] | None = None) -> tuple[str, dict]:
    response = client.post(
        "/auth/demo-login",
        json={
            "role": role,
            "external_id": external_id,
            "nickname": external_id,
            "avatar_url": "",
            "class_ids": class_ids or [],
        },
    )
    assert response.status_code == 200
    body = response.json()
    return body["access_token"], body["user"]


def _ensure_showcase_case(db) -> Problem:
    problem = db.scalar(select(Problem).where(Problem.slug == "pathology.cell-injury-showcase", Problem.version == 1))
    return problem or seed_showcase_case(db)


def _create_conversation(client, token: str, client_id: str) -> int:
    response = client.post(
        "/conversations",
        headers=_headers(token),
        json={"client_id": client_id, "messages": [{"role": "user", "content": "肺炎如何判断"}]},
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_report(client, token: str, conversation_id: int) -> dict:
    response = client.post(
        "/reports",
        headers=_headers(token),
        json={
            "conversation_id": conversation_id,
            "ai_score": 88,
            "ai_summary": "结构完整",
            "analysis": {
                "errors": [{"content": "缺少鉴别诊断", "suggestion": "补充鉴别依据"}],
                "strengths": ["结构清晰"],
                "general_suggestions": ["继续练习"],
            },
        },
    )
    assert response.status_code == 200
    return response.json()


def test_report_state_visibility_and_reviewer_audit(client, db) -> None:
    student_token, _ = _login(client, "student", "characterization_report_student")
    other_student_token, _ = _login(client, "student", "characterization_report_other")
    teacher_token, _ = _login(client, "teacher", "characterization_report_teacher")
    reviewer_token, reviewer = _login(client, "teacher", "demo_reviewer")

    conversation_id = _create_conversation(client, student_token, "characterization-report")
    report = _create_report(client, student_token, conversation_id)
    report_id = report["id"]
    assert report["status"] == "draft"

    draft_review = client.post(
        f"/reports/{report_id}/review",
        headers=_headers(teacher_token),
        json={"teacher_score": 80, "teacher_feedback": "尚未提交"},
    )
    assert draft_review.status_code == 409
    assert draft_review.json()["detail"]["code"] == "STATE_CONFLICT"

    hidden = client.get(f"/reports/{report_id}", headers=_headers(other_student_token))
    assert hidden.status_code == 404

    submitted = client.post(f"/reports/{report_id}/submit", headers=_headers(student_token))
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "pending_review"
    duplicate_submit = client.post(f"/reports/{report_id}/submit", headers=_headers(student_token))
    assert duplicate_submit.status_code == 409
    assert duplicate_submit.json()["detail"]["code"] == "STATE_CONFLICT"

    reviewed = client.post(
        f"/reports/{report_id}/review",
        headers=_headers(reviewer_token),
        json={"teacher_score": 92, "teacher_feedback": "补充证据后通过"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed"
    assert reviewed.json()["reviewer_id"] == reviewer["id"]

    # Teacher report class-range semantics are intentionally not asserted here;
    # the policy remains unresolved and must be coordinated separately.


@pytest.mark.capture_server_errors
def test_report_commit_failure_rolls_back_the_draft_without_a_partial_row(client, db) -> None:
    student_token, _ = _login(client, "student", "characterization_report_rollback")
    conversation_id = _create_conversation(client, student_token, "characterization-report-rollback")
    armed = True

    def fail_once(_session: Session) -> None:
        nonlocal armed
        if armed:
            armed = False
            raise RuntimeError("injected report commit failure")

    event.listen(Session, "before_commit", fail_once)
    try:
        response = client.post(
            "/reports",
            headers=_headers(student_token),
            json={"conversation_id": conversation_id, "ai_score": 70, "ai_summary": "注入失败"},
        )
    finally:
        event.remove(Session, "before_commit", fail_once)

    assert response.status_code == 500
    db.rollback()
    db.expire_all()
    assert db.scalar(select(Report).where(Report.conversation_id == conversation_id)) is None


def test_publish_rejects_a_stale_review_digest_and_invalidates_approval(client, db) -> None:
    problem = _ensure_showcase_case(db)
    teacher_token, _ = _login(client, "teacher", "demo_teacher")

    db.expire_all()
    persisted = db.get(Problem, problem.id)
    assert persisted is not None
    persisted.title = "审核后发生变更的病例"
    db.commit()

    response = client.post(f"/problems/{problem.id}/publish", headers=_headers(teacher_token))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STATE_CONFLICT"

    db.expire_all()
    changed = db.get(Problem, problem.id)
    assert changed is not None
    assert changed.status == "published"
    assert changed.medical_review_status == "not_submitted"
    assert changed.title == "审核后发生变更的病例"


def _submit_all_case_stages(client, token: str, attempt_id: int) -> None:
    answers = [
        ("history", {"stage_id": "history", "summary": "发热咳嗽", "key_findings": ["发热"]}),
        ("problem_representation", {"stage_id": "problem_representation", "summary": "急性发热咳嗽"}),
        (
            "differential",
            {
                "stage_id": "differential",
                "items": [
                    {"diagnosis": "肺炎", "supporting_evidence": ["发热"], "opposing_evidence": []},
                    {"diagnosis": "病毒性肺炎", "supporting_evidence": [], "opposing_evidence": ["黄痰"]},
                ],
            },
        ),
        (
            "tests",
            {
                "stage_id": "tests",
                "items": [{"test_name": "胸部影像", "rationale": "确认浸润", "priority": "necessary"}],
            },
        ),
        (
            "management",
            {
                "stage_id": "management",
                "items": [{"action": "评估氧合", "rationale": "保障安全"}],
                "safety_considerations": ["复评"],
            },
        ),
    ]
    for stage_id, answer in answers:
        response = client.post(
            f"/attempts/{attempt_id}/stages/{stage_id}/submit",
            headers=_headers(token),
            json={"answer": answer},
        )
        assert response.status_code == 200


def test_repeated_completion_and_learning_plan_creation_are_sequentially_idempotent(client, db) -> None:
    problem = _ensure_showcase_case(db)
    student_token, student = _login(client, "student", "characterization_plan_student")
    started = client.post(f"/problems/{problem.id}/attempts", headers=_headers(student_token), json={})
    assert started.status_code == 200
    attempt_id = started.json()["id"]
    _submit_all_case_stages(client, student_token, attempt_id)

    first_complete = client.post(f"/attempts/{attempt_id}/complete", headers=_headers(student_token))
    second_complete = client.post(f"/attempts/{attempt_id}/complete", headers=_headers(student_token))
    assert first_complete.status_code == 200
    assert second_complete.status_code == 200
    assert second_complete.json()["attempt_id"] == first_complete.json()["attempt_id"] == attempt_id
    assert second_complete.json()["total_score"] == first_complete.json()["total_score"]
    assert second_complete.json()["model_name"] == first_complete.json()["model_name"]

    plan = client.get("/learning-plans/current", headers=_headers(student_token))
    assert plan.status_code == 200
    first_plan = plan.json()
    again = client.post(f"/attempts/{attempt_id}/learning-plan", headers=_headers(student_token))
    again_twice = client.post(f"/attempts/{attempt_id}/learning-plan", headers=_headers(student_token))
    assert again.status_code == 200
    assert again_twice.status_code == 200
    assert again.json()["id"] == first_plan["id"]
    assert again_twice.json()["id"] == first_plan["id"]
    assert [task["id"] for task in again_twice.json()["tasks"]] == [task["id"] for task in first_plan["tasks"]]

    first_task = first_plan["tasks"][0]
    first_start = client.post(f"/learning-tasks/{first_task['id']}/start", headers=_headers(student_token))
    second_start = client.post(f"/learning-tasks/{first_task['id']}/start", headers=_headers(student_token))
    assert first_start.status_code == 200
    assert second_start.status_code == 200
    assert first_start.json()["mode"] == second_start.json()["mode"] == "case_attempt"
    assert first_start.json()["attempt"]["id"] == second_start.json()["attempt"]["id"]

    db.expire_all()
    assessment = db.scalar(select(CaseAssessment).where(CaseAssessment.attempt_id == attempt_id))
    assert assessment is not None
    assert db.scalar(select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == attempt_id)) == 1
    assert db.scalar(select(func.count(LearningPlan.id)).where(LearningPlan.source_assessment_id == assessment.id)) == 1
    assert (
        db.scalar(
            select(func.count(StudentNotification.id)).where(
                StudentNotification.student_id == student["id"],
                StudentNotification.type == "learning_plan_ready",
            )
        )
        == 1
    )
