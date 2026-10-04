"""T05 characterization contracts for the post-T01 isolated test fixture.

This module intentionally consumes the fixture names ``client`` and ``db``
that T01 is expected to provide.  It must not create an engine, import the
application engine, drop tables, or mutate a developer database.  The client
fixture must use the same isolated database as ``db`` and set
``raise_server_exceptions=False`` so error-boundary responses are observable.
T30 keeps reports as student-owned history and retires their write workflow.
"""

import pytest
from sqlalchemy import func, select

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


def test_report_state_visibility_and_reviewer_audit(client, db) -> None:
    student_token, student = _login(client, "student", "characterization_report_student")
    other_student_token, _ = _login(client, "student", "characterization_report_other")
    teacher_token, _ = _login(client, "teacher", "characterization_report_teacher")
    conversation_id = _create_conversation(client, student_token, "characterization-report")
    report = Report(
        conversation_id=conversation_id,
        student_id=student["id"],
        status="reviewed",
        ai_score=88,
        ai_summary="保留的历史总结",
        teacher_score=92,
        teacher_feedback="保留的历史反馈",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    report_id = report.id

    hidden = client.get(f"/reports/{report_id}", headers=_headers(other_student_token))
    assert hidden.status_code == 404

    submitted = client.post(f"/reports/{report_id}/submit", headers=_headers(student_token), json={"class_id": 1})
    assert submitted.status_code == 409
    assert submitted.json()["detail"]["code"] == "STATE_CONFLICT"

    reviewed = client.post(
        f"/reports/{report_id}/review",
        headers=_headers(teacher_token),
        json={"teacher_score": 92, "teacher_feedback": "补充证据后通过"},
    )
    assert reviewed.status_code == 409
    assert reviewed.json()["detail"]["code"] == "STATE_CONFLICT"

    assert client.get(f"/reports/{report_id}", headers=_headers(student_token)).status_code == 200
    outsider = client.get(f"/reports/{report_id}", headers=_headers(teacher_token))
    assert outsider.status_code == 404


@pytest.mark.capture_server_errors
def test_retired_report_write_does_not_create_a_partial_row(client, db) -> None:
    student_token, _ = _login(client, "student", "characterization_report_rollback")
    conversation_id = _create_conversation(client, student_token, "characterization-report-rollback")
    response = client.post(
        "/reports",
        headers=_headers(student_token),
        json={"conversation_id": conversation_id, "ai_score": 70, "ai_summary": "不应写入"},
    )

    assert response.status_code == 409
    db.rollback()
    db.expire_all()
    assert db.scalar(select(Report).where(Report.conversation_id == conversation_id)) is None


def test_retired_publish_keeps_historical_review_state_unchanged(client, db) -> None:
    problem = _ensure_showcase_case(db)
    teacher_token, _ = _login(client, "teacher", "demo_teacher")

    db.expire_all()
    persisted = db.get(Problem, problem.id)
    assert persisted is not None
    persisted.title = "审核后发生变更的病例"
    db.commit()
    status_before = persisted.status
    review_status_before = persisted.medical_review_status

    response = client.post(f"/problems/{problem.id}/publish", headers=_headers(teacher_token))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "RETIRED_FLOW"

    db.expire_all()
    changed = db.get(Problem, problem.id)
    assert changed is not None
    assert changed.status == status_before
    assert changed.medical_review_status == review_status_before
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


def test_repeated_independent_case_completion_keeps_analysis_without_formal_plan(client, db) -> None:
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
    assert plan.status_code == 404
    again = client.post(f"/attempts/{attempt_id}/learning-plan", headers=_headers(student_token))
    again_twice = client.post(f"/attempts/{attempt_id}/learning-plan", headers=_headers(student_token))
    assert again.status_code == again_twice.status_code == 409

    db.expire_all()
    assessment = db.scalar(select(CaseAssessment).where(CaseAssessment.attempt_id == attempt_id))
    assert assessment is not None
    assert db.scalar(select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == attempt_id)) == 1
    assert db.scalar(select(func.count(LearningPlan.id)).where(LearningPlan.source_assessment_id == assessment.id)) == 0
    assert (
        db.scalar(
            select(func.count(StudentNotification.id)).where(
                StudentNotification.student_id == student["id"],
                StudentNotification.type == "learning_plan_ready",
            )
        )
        == 0
    )
