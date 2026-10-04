from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.route_models import LearningRoute, RouteFinalTest
from app.modules.pbl.infrastructure.models import PblDiagnosticSnapshot, PblParticipation, PblSession
from tests.test_pbl_api import _headers, _login


def test_retired_learning_reports_are_empty_and_mutations_fail_closed(client, db) -> None:
    student_token = _login(client, "student", "t15-student")
    other_token = _login(client, "student", "t15-outsider")
    teacher_token = _login(client, "teacher", "t15-teacher")

    page = client.get("/student/pbl-learning-reports", headers=_headers(student_token))
    assert page.status_code == 200, page.text
    assert page.json()["items"] == []
    assert page.json()["total"] == 0
    assert client.get("/student/pbl-learning-plans", headers=_headers(student_token)).json() == []

    missing = "/student/pbl-learning-reports/999999"
    assert client.get(missing, headers=_headers(student_token)).status_code == 404
    assert client.get(missing, headers=_headers(other_token)).status_code == 404

    student_mutation = client.post(
        "/student/pbl-learning-tasks/999999/submit",
        headers=_headers(student_token),
        json={"client_submission_id": "retired-submit", "answer": {"text": "不会被保存"}},
    )
    assert student_mutation.status_code == 409
    assert student_mutation.json()["detail"]["reason"] == "RETIRED_FLOW"

    teacher_mutation = client.post(
        "/teacher/pbl-learning-results/999999/verify",
        headers=_headers(teacher_token),
        json={"version": 1, "decision": "improved", "note": "旧流程已退役"},
    )
    assert teacher_mutation.status_code == 409
    assert teacher_mutation.json()["detail"]["reason"] == "RETIRED_FLOW"


def test_autonomous_route_is_visible_only_to_its_student(client, db) -> None:
    student_token = _login(client, "student", "t15-route-owner")
    other_token = _login(client, "student", "t15-route-outsider")
    owner = db.scalar(select(User).where(User.external_id == "t15-route-owner"))
    assert owner is not None

    session = PblSession(
        session_kind="student_initiated",
        created_by_student_id=owner.id,
        client_session_id="t15-autonomous-route",
        topic_code="pathology.inflammation",
        provider="coze",
        status="closed",
        goal_point_codes=["pathology.inflammation.vascular"],
    )
    db.add(session)
    db.flush()

    participation = PblParticipation(
        session_id=session.id,
        student_id=owner.id,
        revision=1,
        current_phase="completed",
        phase_status="completed",
        phase_completed_at=datetime.now(UTC),
        evidence_completed_revision=1,
    )
    db.add(participation)
    db.flush()

    snapshot = PblDiagnosticSnapshot(
        participation_id=participation.id,
        revision=1,
        status="ready",
        schema_version=8,
        phase="synthesis",
        phase_decision="complete",
        phase_evidence_message_ids=["t15-evidence"],
        phase_evidence_summary="自主研讨完成综合解释。",
        assistant_reply="已完成当前学习讨论。",
        knowledge_gaps=[],
        reasoning_issues=[],
        diagnosis_outcome="no_clear_gaps",
        provider_metadata={},
    )
    db.add(snapshot)
    db.flush()
    participation.completion_snapshot_id = snapshot.id

    route_id = str(uuid4())
    route = LearningRoute(
        public_id=route_id,
        student_id=owner.id,
        source_participation_id=participation.id,
        session_id=session.id,
        completion_snapshot_id=snapshot.id,
        source_kind="autonomous",
        title="自主学习路线",
        goal_point_codes=["pathology.inflammation.vascular"],
        diagnosis_summary={"private_marker": "owner-only-diagnosis"},
        generation_context={},
        generation_state="pending",
    )
    db.add(route)
    db.flush()
    db.add(
        RouteFinalTest(
            public_id=str(uuid4()),
            route_id=route.id,
            generation_state="pending",
            review_state="pending_review",
            review_kind="teacher",
        )
    )
    db.commit()

    own_page = client.get("/learning/routes", headers=_headers(student_token))
    assert own_page.status_code == 200, own_page.text
    assert own_page.json()["total"] == 1
    assert own_page.json()["items"][0]["id"] == route_id

    other_page = client.get("/learning/routes", headers=_headers(other_token))
    assert other_page.status_code == 200, other_page.text
    assert other_page.json()["items"] == []
    assert other_page.json()["total"] == 0
    forbidden = client.get(f"/learning/routes/{route_id}", headers=_headers(other_token))
    assert forbidden.status_code == 404
    assert "owner-only-diagnosis" not in forbidden.text

    own_detail = client.get(f"/learning/routes/{route_id}", headers=_headers(student_token))
    assert own_detail.status_code == 200, own_detail.text
    assert own_detail.json()["diagnosis_summary"]["private_marker"] == "owner-only-diagnosis"
