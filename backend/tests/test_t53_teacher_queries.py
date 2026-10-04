"""Actionable queue boundaries and authorized, unchanged question copies."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.classroom.public import TeachingMemberScope
from app.modules.learning.api.route_schemas import TeacherReviewQueuePage
from app.modules.learning.application.learning_routes import LearningRouteApplication
from app.modules.pbl.infrastructure.models import PblDiagnosticSnapshot, PblParticipation, PblSession
from app.shared.errors import AppError
from tests.t44_route_support import complete_bank_route, configure_bank_route
from tests.test_pbl_api import _classroom, _headers, _login, _session_payload


def _candidate(generation="ready", review="pending_review", student=1, **values):
    return {
        "id": str(uuid4()),
        "route_id": str(uuid4()),
        "title": "最终测试",
        "class_id": 7,
        "session_id": 70,
        "student_id": student,
        "generation_state": generation,
        "review_state": review,
        "updated_at": datetime.now(UTC),
        "claim_expires_at": None,
        **values,
    }


def test_queue_counts_only_current_actionable_scope_and_separates_failed_generation():
    member = TeachingMemberScope(7, "炎症班", "active", 1, "甲同学")
    scope = SimpleNamespace(
        owned=lambda teacher, class_id: object() if class_id == 7 else None,
        teaching_members=lambda teacher: (member, replace(member, class_id=8, class_status="archived")),
    )
    rows = [
        _candidate(),
        _candidate(review="needs_changes"),
        _candidate("generation_failed"),
        _candidate(student=2),
        _candidate(class_id=8),
        _candidate("generation_failed", claim_expires_at=datetime.now(UTC) + timedelta(hours=1)),
    ]
    app = LearningRouteApplication(
        SimpleNamespace(teacher_review_candidates=lambda teacher, filters: rows), None, None, scope, None, None
    )
    page = app.teacher_review_queue(10, {"limit": 2, "offset": 0})
    assert page["counts"] == {"pending_review": 1, "needs_changes": 1, "generation_failed": 1}
    assert page["total"] == 3 and len(page["items"]) == 2
    assert all(item["can_review"] and not item["can_retry"] for item in page["items"])
    TeacherReviewQueuePage.model_validate(page)
    failures = app.teacher_review_queue(10, {"kind": "generation_failed"})
    assert failures["total"] == 1 and failures["items"][0]["can_retry"]
    assert failures["counts"] == page["counts"]
    assert "questions" not in str(page) and "diagnosis" not in str(page)
    with pytest.raises(AppError) as denied:
        app.teacher_review_queue(10, {"class_id": 9})
    assert denied.value.status_code == 404


def test_review_queue_and_content_source_api_keep_unreleased_sources_authorized(client, db, monkeypatch):
    configure_bank_route(monkeypatch)
    teacher = _login(client, "teacher", "t53-owner")
    student = _login(client, "student", "t53-member")
    other = _login(client, "teacher", "t53-other")
    class_id = _classroom(client, teacher, "t53-member")
    created = client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db))
    assert created.status_code == 201
    _route_id, detail = complete_bank_route(client, student, session_id=created.json()["id"])
    test_id = detail["test_summary"]["id"]
    test = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).json()
    queue = client.get("/learning/teacher/final-test-review-queue", headers=_headers(teacher))
    assert queue.status_code == 200
    assert queue.json()["counts"]["pending_review"] == 1
    item = queue.json()["items"][0]
    assert item["id"] == test_id and item["can_review"]
    assert not {"questions", "diagnosis_summary", "answers"}.intersection(item)
    path = f"/teacher/question-bank/sources/route-test-questions/{test['questions'][0]['id']}"
    source = client.get(path, headers=_headers(teacher))
    assert source.status_code == 200 and source.json()["source_digest"]
    assert set(source.json()) == {
        "source_type",
        "source_id",
        "source_digest",
        "task_type",
        "title",
        "prompt",
        "options",
        "answer",
        "explanation",
        "point_codes",
        "dimension_ids",
    }
    assert client.get(path, headers=_headers(other)).status_code == 404
    assert client.get(path, headers=_headers(student)).status_code == 403
    assert client.get("/learning/teacher/final-test-review-queue", headers=_headers(other)).json()["total"] == 0
    assert (
        client.get(
            "/learning/teacher/final-test-review-queue", params={"class_id": class_id}, headers=_headers(other)
        ).status_code
        == 404
    )
    change_payload = {"client_request_id": "t53-changes", "expected_version": test["version"], "note": "补充形态依据"}
    changes_path = f"/learning/teacher/final-tests/{test_id}/request-changes"
    changed = client.post(changes_path, headers=_headers(teacher), json=change_payload)
    assert changed.status_code == 200
    updated = changed.json()
    assert updated["review_state"] == "needs_changes"
    assert updated["feedback_draft"] == "补充形态依据"
    assert updated["draft_digest"] == test["draft_digest"] and updated["questions"] == test["questions"]
    replay = client.post(changes_path, headers=_headers(teacher), json=change_payload)
    assert replay.status_code == 200 and replay.json()["version"] == updated["version"]
    assert client.get(path, headers=_headers(teacher)).json() == source.json()
    queue_after_changes = client.get("/learning/teacher/final-test-review-queue", headers=_headers(teacher)).json()
    assert queue_after_changes["counts"] == {"pending_review": 0, "needs_changes": 1, "generation_failed": 0}
    released = client.post(
        f"/learning/teacher/final-tests/{test_id}/release",
        headers=_headers(teacher),
        json={
            "client_request_id": "t53-release",
            "expected_version": updated["version"],
            "draft_digest": test["draft_digest"],
        },
    )
    assert released.status_code == 200
    assert client.get("/learning/teacher/final-test-review-queue", headers=_headers(teacher)).json()["total"] == 0
    assert client.get(path, headers=_headers(teacher)).json() == source.json()


def test_teacher_test_scope_projection_tracks_class_and_membership_not_closed_pbl_session(client, db, monkeypatch):
    configure_bank_route(monkeypatch)
    teacher = _login(client, "teacher", "t53-scope-owner")
    student = _login(client, "student", "t53-scope-member")
    class_id = _classroom(client, teacher, "t53-scope-member")
    created = client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db))
    assert created.status_code == 201
    session_id = created.json()["id"]
    _route_id, detail = complete_bank_route(client, student, session_id=session_id)
    test_id = detail["test_summary"]["id"]

    closed = client.post(f"/classes/{class_id}/pbl-sessions/{session_id}/close", headers=_headers(teacher))
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    current = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).json()
    assert current["current_scope_active"] is True
    page = client.get(
        "/learning/teacher/final-tests",
        params={"class_id": class_id, "session_id": session_id},
        headers=_headers(teacher),
    )
    assert page.status_code == 200, page.text
    assert page.json()["items"][0]["current_scope_active"] is True

    questions = [
        {key: value for key, value in question.items() if key != "source_digest"} for question in current["questions"]
    ]
    questions[0]["prompt"] = "活动范围内仍可保存的题目"
    saved = client.put(
        f"/learning/teacher/final-tests/{test_id}",
        headers=_headers(teacher),
        json={
            "client_request_id": "t53-scope-save",
            "expected_version": current["version"],
            "questions": questions,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["current_scope_active"] is True
    changed = client.post(
        f"/learning/teacher/final-tests/{test_id}/request-changes",
        headers=_headers(teacher),
        json={
            "client_request_id": "t53-scope-changes",
            "expected_version": saved.json()["version"],
            "note": "补充证据",
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["current_scope_active"] is True

    classroom = db.get(ClassRoom, class_id)
    classroom.status = "archived"
    db.commit()
    archived = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher))
    assert archived.status_code == 200, archived.text
    assert archived.json()["current_scope_active"] is False
    archived_page = client.get(
        "/learning/teacher/final-tests", params={"class_id": class_id}, headers=_headers(teacher)
    )
    assert archived_page.status_code == 200, archived_page.text
    assert archived_page.json()["items"][0]["current_scope_active"] is False
    inactive_save = client.put(
        f"/learning/teacher/final-tests/{test_id}",
        headers=_headers(teacher),
        json={
            "client_request_id": "t53-inactive-save",
            "expected_version": changed.json()["version"],
            "questions": questions,
        },
    )
    assert inactive_save.status_code == 409
    assert inactive_save.json()["detail"]["reason"] == "CLASSROOM_SCOPE_INACTIVE"
    inactive_changes = client.post(
        f"/learning/teacher/final-tests/{test_id}/request-changes",
        headers=_headers(teacher),
        json={
            "client_request_id": "t53-inactive-changes",
            "expected_version": changed.json()["version"],
            "note": "不应写入",
        },
    )
    assert inactive_changes.status_code == 409
    assert inactive_changes.json()["detail"]["reason"] == "CLASSROOM_SCOPE_INACTIVE"

    classroom.status = "active"
    db.commit()
    reactivated = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher))
    assert reactivated.status_code == 200
    assert reactivated.json()["current_scope_active"] is True
    member = db.scalar(
        select(ClassMember).where(ClassMember.class_id == class_id, ClassMember.student_id == current["student_id"])
    )
    assert member is not None
    db.delete(member)
    db.commit()
    left = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher))
    assert left.status_code == 200, left.text
    assert left.json()["current_scope_active"] is False
    left_page = client.get("/learning/teacher/final-tests", params={"class_id": class_id}, headers=_headers(teacher))
    assert left_page.status_code == 200, left_page.text
    assert left_page.json()["items"][0]["current_scope_active"] is False
    assert db.get(PblSession, session_id).status == "closed"
    assert client.get("/learning/teacher/final-test-review-queue", headers=_headers(teacher)).json()["total"] == 0


def test_insights_sql_scope_uses_frozen_revision_and_excludes_autonomous_diagnoses(client, db, monkeypatch):
    configure_bank_route(monkeypatch)
    teacher = _login(client, "teacher", "t53-insights-owner")
    student = _login(client, "student", "t53-insights-member")
    other = _login(client, "teacher", "t53-insights-other")
    class_id = _classroom(client, teacher, "t53-insights-member")
    created = client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db))
    session_id = created.json()["id"]
    route_id, _ = complete_bank_route(client, student, session_id=session_id)
    complete_bank_route(client, student)  # autonomous facts must remain private
    participation = db.scalar(select(PblParticipation).where(PblParticipation.session_id == session_id))
    snapshot = db.get(PblDiagnosticSnapshot, participation.completion_snapshot_id)
    snapshot.knowledge_gaps = [
        {"point_code": "inflammation", "summary": "机制解释不完整", "evidence_summary": "PRIVATE_EVIDENCE"}
    ]
    snapshot.reasoning_issues = [
        {"dimension_id": "causal", "summary": "因果依据不足", "evidence_message_ids": ["PRIVATE_MESSAGE"]}
    ]
    db.commit()
    base = "/analytics/teacher-insights"
    overview = client.get(f"{base}/overview", headers=_headers(teacher))
    assert overview.status_code == 200
    assert overview.json()["cohort"]["published_routes"] == 1
    assert overview.json()["period_results"]["average_score"] is None
    diagnosis = client.get(f"{base}/diagnostics", headers=_headers(teacher)).json()
    assert diagnosis["total"] == 1
    assert diagnosis["items"][0]["knowledge_gaps"] == [{"code": "inflammation", "summary": "机制解释不完整"}]
    assert "PRIVATE" not in str(diagnosis)
    student_id = participation.student_id
    detail = client.get(f"{base}/students/{student_id}", params={"class_id": class_id}, headers=_headers(teacher))
    assert detail.status_code == 200
    assert [item["route_id"] for item in detail.json()["routes"]] == [route_id]
    assert "questions" not in str(detail.json())
    assert detail.json()["summary"]["discussion_progress"] == {"participated": 1, "active": 0, "completed": 1}
    assert len(detail.json()["discussions"]) == 1  # excludes the autonomous participation
    assert set(detail.json()["discussions"][0]) == {
        "participation_id",
        "session_id",
        "class_id",
        "student_id",
        "phase",
        "status",
        "started_at",
        "completed_at",
    }
    _login(client, "student", "t53-left-unfinished")
    from app.modules.identity.infrastructure.models import User

    left_id = db.scalar(select(User.id).where(User.external_id == "t53-left-unfinished"))
    unfinished = PblParticipation(
        session_id=session_id, student_id=left_id, current_phase="hypothesis", phase_status="active"
    )
    db.add(unfinished)
    db.commit()
    progress = client.get(f"{base}/students", headers=_headers(teacher)).json()
    left_summary = next(item for item in progress["items"] if item["student_id"] == left_id)
    assert left_summary["discussion_progress"] == {"participated": 1, "active": 1, "completed": 0}
    left_detail = client.get(f"{base}/students/{left_id}", params={"class_id": class_id}, headers=_headers(teacher))
    assert left_detail.status_code == 200
    assert left_detail.json()["routes"] == [] and len(left_detail.json()["discussions"]) == 1
    assert (
        client.get(f"{base}/students/{left_id}", params={"class_id": class_id}, headers=_headers(other)).status_code
        == 404
    )

    assert client.get(f"{base}/overview", headers=_headers(other)).json()["cohort"]["published_routes"] == 0
    assert client.get(f"{base}/overview", params={"class_id": class_id}, headers=_headers(other)).status_code == 404
    assert client.get(f"{base}/diagnostics", headers=_headers(student)).status_code == 403
    snapshot.revision += 1
    db.commit()
    assert client.get(f"{base}/diagnostics", headers=_headers(teacher)).json()["total"] == 0
