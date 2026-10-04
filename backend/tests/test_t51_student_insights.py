"""Student learning-insight projections stay scoped, safe, and evidence-based."""

from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select

from app.modules.learning.application.student_insights import StudentLearningInsightsApplication
from app.modules.learning.infrastructure.route_models import LearningRoute, RouteFinalTest
from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore
from app.modules.learning.public import (
    StudentInsightQuestionScore,
    StudentInsightRouteRecord,
    StudentInsightTestResult,
)
from app.modules.pbl.infrastructure.models import PblDiagnosticSnapshot, PblParticipation, PblSession
from app.modules.pbl.public import PblStudentInsightRecord
from tests.test_pbl_api import _headers, _login
from tests.test_t44_learning_routes import POINT, completed_route, configure
from tests.test_t48_mixed_final_test import _submitted_mixed_test, configure_mixed


class _RouteReader:
    def __init__(self, records):
        self.records = records

    def student_insight_routes(self, student_id):
        self.student_id = student_id
        return tuple(self.records)


class _PblReader:
    def __init__(self, records):
        self.records = records

    def student_insight_records(self, student_id):
        self.student_id = student_id
        return tuple(self.records)


class _Catalog:
    def tree_view(self):
        return [
            {"code": "point-a", "title": "目标 A"},
            {"code": "point-b", "title": "目标 B"},
            {"code": "point-c", "title": "目标 C"},
        ]

    def module_labels(self):
        return {"pathology.inflammation": "炎症"}


def _insight_record(
    *,
    route_id="route",
    session_id=1,
    goals=(),
    reading_seconds=0,
    result=None,
    status="learning",
    updated_at=datetime(2026, 9, 30, tzinfo=UTC),
):
    return StudentInsightRouteRecord(
        route_id=route_id,
        session_id=session_id,
        source_kind="autonomous",
        goal_point_codes=tuple(goals),
        created_at=updated_at,
        updated_at=updated_at,
        route_generation_state="published",
        status=status,
        completed_steps=1,
        total_steps=2,
        reading_seconds=reading_seconds,
        current_step_kind="reading",
        current_case_phase=None,
        result=result,
    )


def _test_result(score, completed_at, question_scores=(), result_id="result"):
    return StudentInsightTestResult(
        result_id=result_id,
        score=score,
        correct_count=0,
        question_count=len(question_scores),
        completed_at=completed_at,
        question_scores=tuple(question_scores),
    )


def _diagnosis(*, session_id, diagnosed_at, gaps=(), reasoning=(), outcome="identified_gaps"):
    return PblStudentInsightRecord(
        participation_id=session_id,
        session_id=session_id,
        topic_code="pathology.inflammation",
        case_title="研讨记录",
        session_kind="student_initiated",
        goal_point_codes=tuple(gaps),
        current_phase="completed",
        phase_status="completed",
        participation_created_at=diagnosed_at,
        updated_at=diagnosed_at,
        phase_completed_at=diagnosed_at,
        diagnosis_created_at=diagnosed_at,
        diagnosis_outcome=outcome,
        knowledge_gap_codes=tuple(gaps),
        reasoning_issue_codes=tuple(reasoning),
    )


def _application(routes, pbl=(), now=datetime(2026, 9, 30, 8, tzinfo=UTC)):
    return StudentLearningInsightsApplication(
        _RouteReader(routes), _PblReader(pbl), _Catalog(), clock=lambda: now
    )


def test_dashboard_distinguishes_zero_from_no_sample_and_counts_persisted_shells():
    previous = _test_result(80, datetime(2026, 9, 23, 8, tzinfo=UTC), result_id="previous")
    zero = _test_result(
        0,
        datetime(2026, 9, 29, 8, tzinfo=UTC),
        [StudentInsightQuestionScore("point-b", 0, 1)],
        "zero",
    )
    routes = [
        _insight_record(route_id="previous", session_id=1, goals=("point-a",), result=previous),
        _insight_record(route_id="zero", session_id=2, goals=("point-b",), result=zero),
        _insight_record(route_id="failed", session_id=3, reading_seconds=119, status="generation_failed"),
    ]
    page = _application(routes).read(student_id=41, limit=20, offset=0)
    dashboard = page["summary"]["dashboard"]
    assert dashboard["mastery_score"] == 0
    assert dashboard["mastery_delta"] == -80
    assert dashboard["mastery_sample_count"] == 1
    assert dashboard["trend"][-1]["score"] == 0
    assert dashboard["study_minutes"] == 1
    assert dashboard["plan_completion_rate"] == 66.7
    assert dashboard["tested_knowledge_count"] == 2

    no_current_sample = _application([routes[0], routes[2]]).read(41, 20, 0)["summary"]["dashboard"]
    assert no_current_sample["mastery_score"] is None
    assert no_current_sample["mastery_delta"] is None
    assert no_current_sample["mastery_sample_count"] == 0


def test_weaknesses_use_latest_weighted_target_evidence_and_reasoning_stays_unscored():
    diagnosed_at = datetime(2026, 9, 28, 8, tzinfo=UTC)
    result = _test_result(
        57.9,
        datetime(2026, 9, 29, 8, tzinfo=UTC),
        [
            StudentInsightQuestionScore("point-a", 1, 1),
            StudentInsightQuestionScore("point-a", 9, 9),
            StudentInsightQuestionScore("point-b", 1, 4),
            StudentInsightQuestionScore("point-b", 0, 4),
            StudentInsightQuestionScore("point-c", 0, 1),
        ],
    )
    route = _insight_record(route_id="mixed", session_id=8, goals=("point-a", "point-b", "point-c"), result=result)
    pbl = _diagnosis(
        session_id=8,
        diagnosed_at=diagnosed_at,
        gaps=("point-a", "point-b"),
        reasoning=("evidence_reasoning",),
    )
    dashboard = _application([route], [pbl]).read(41, 20, 0)["summary"]["dashboard"]
    weaknesses = {item["target_code"]: item for item in dashboard["weaknesses"]}
    assert "point-a" not in weaknesses
    assert weaknesses["point-b"]["target_type"] == "knowledge"
    assert weaknesses["point-b"]["mastery_percentage"] == 12.5
    assert weaknesses["point-c"]["mastery_percentage"] == 0
    assert weaknesses["point-c"]["occurrences"] == 1
    assert weaknesses["evidence_reasoning"]["target_type"] == "reasoning"
    assert weaknesses["evidence_reasoning"]["mastery_percentage"] is None


def test_legacy_single_choice_snapshot_projects_only_per_item_scores():
    scores = SqlLearningRouteStore._insight_question_scores(
        {
            "questions": [
                {"point_code": "point-a", "selected_option": 1, "correct_option": 1},
                {"point_code": "point-b", "selected_option": 0, "correct_option": 2},
                {"point_code": "point-secret", "selected_option": True, "correct_option": 1},
            ]
        }
    )
    assert [(item.target_code, item.earned_points, item.possible_points) for item in scores] == [
        ("point-a", 1, 1),
        ("point-b", 0, 1),
    ]


def test_new_diagnosis_for_another_target_does_not_hide_existing_test_weakness():
    result = _test_result(
        0, datetime(2026, 9, 28, tzinfo=UTC), [StudentInsightQuestionScore("point-a", 0, 1)]
    )
    route = _insight_record(goals=("point-a",), result=result)
    diagnosis = _diagnosis(session_id=2, diagnosed_at=datetime(2026, 9, 29, tzinfo=UTC), gaps=("point-b",))
    weaknesses = _application([route], [diagnosis]).read(41, 20, 0)["summary"]["dashboard"]["weaknesses"]
    assert {item["target_code"] for item in weaknesses} == {"point-a", "point-b"}
    assert next(item for item in weaknesses if item["target_code"] == "point-a")["mastery_percentage"] == 0


def test_summary_without_diagnosis_still_reports_persisted_routes_and_results():
    result = _test_result(75, datetime(2026, 9, 28, tzinfo=UTC))
    page = _application([_insight_record(goals=("point-a",), result=result)]).read(41, 20, 0)
    dashboard = page["summary"]["dashboard"]
    assert dashboard["ai_diagnostic_count"] == 0
    assert "1 条学习路线" in dashboard["ai_summary"]
    assert "75 分" in dashboard["ai_summary"]
    assert "尚无可确认的研讨完成诊断" in dashboard["ai_summary"]


def test_unlinked_route_gets_a_safe_card_and_linked_route_is_not_duplicated():
    completed = _test_result(93, datetime(2026, 9, 29, 8, tzinfo=UTC), result_id="finished")
    routes = [
        _insight_record(
            route_id="unfinished-route",
            session_id=31,
            goals=("point-a",),
            status="ready_for_test",
        ),
        _insight_record(
            route_id="finished-route",
            session_id=32,
            goals=("point-b",),
            result=completed,
        ),
        _insight_record(route_id="linked-route", session_id=33, goals=("point-c",)),
    ]
    routes[0] = replace(routes[0], title="未关联计划")
    routes[1] = replace(routes[1], title="已完成计划")
    routes[2] = replace(routes[2], title="已关联计划")
    diagnosis = _diagnosis(
        session_id=33,
        diagnosed_at=datetime(2026, 9, 28, tzinfo=UTC),
        gaps=("point-c",),
    )

    page = _application(routes, [diagnosis]).read(41, 20, 0)
    items = {item["id"]: item for item in page["items"]}
    assert page["total"] == 3
    assert items["route:unfinished-route"]["session"] == {
        "id": "31",
        "topic_label": "目标 A",
        "case_title": "未关联计划",
    }
    assert items["route:unfinished-route"]["action"]["kind"] == "route"
    assert items["route:unfinished-route"]["action"]["route_id"] == "unfinished-route"
    assert items["route:finished-route"]["action"]["kind"] == "result"
    assert "route:linked-route" not in items
    assert page["summary"]["dashboard"]["ai_diagnostic_count"] == 1


def test_student_insights_scope_and_validate_completion_snapshot_without_leaking_private_fields(
    client, db, monkeypatch
):
    configure(monkeypatch)
    student = _login(client, "student", "t51-insight-owner")
    outsider = _login(client, "student", "t51-insight-outsider")
    _, detail = completed_route(client, student)
    session_id = int(detail["summary"]["session_locator"])
    route = db.scalar(select(LearningRoute).where(LearningRoute.session_id == session_id))
    final_test = db.scalar(select(RouteFinalTest).where(RouteFinalTest.route_id == route.id))
    participation = db.scalar(select(PblParticipation).where(PblParticipation.session_id == session_id))
    snapshot = db.get(PblDiagnosticSnapshot, participation.completion_snapshot_id)
    session = db.get(PblSession, session_id)

    route.generation_state = "generation_failed"
    final_test.generation_state = "generation_failed"
    snapshot.assistant_reply = "PRIVATE_ASSISTANT_REPLY"
    snapshot.knowledge_gaps = [{"point_code": POINT, "summary": "PRIVATE_EVIDENCE"}]
    snapshot.reasoning_issues = [{"dimension_id": "evidence_reasoning", "evidence": "PRIVATE_REASONING"}]
    session.case_context = {"title": "安全标题", "hidden_case": "PRIVATE_HIDDEN_CASE"}
    db.commit()

    owner_response = client.get(
        f"/learning/student-insights?student_id={outsider}", headers=_headers(student)
    )
    assert owner_response.status_code == 200, owner_response.text
    owner_page = owner_response.json()
    dashboard = owner_page["summary"]["dashboard"]
    assert owner_page["total"] == 1
    assert dashboard["ai_diagnostic_count"] == 1
    assert dashboard["mastery_score"] is None
    assert dashboard["mastery_sample_count"] == 0
    assert dashboard["plan_completion_rate"] == 0
    assert dashboard["weaknesses"][0]["target_code"] == POINT
    assert owner_page["items"][0]["session"]["case_title"] == "安全标题"
    assert "生成未成功" in owner_page["items"][0]["summary_text"]
    serialized = str(owner_page)
    for private_value in ("PRIVATE_ASSISTANT_REPLY", "PRIVATE_EVIDENCE", "PRIVATE_REASONING", "PRIVATE_HIDDEN_CASE"):
        assert private_value not in serialized

    participation.evidence_completed_revision = 0
    db.commit()
    invalidated = client.get("/learning/student-insights", headers=_headers(student)).json()
    assert invalidated["summary"]["dashboard"]["ai_diagnostic_count"] == 0
    assert invalidated["summary"]["dashboard"]["weaknesses"] == []

    outsider_page = client.get("/learning/student-insights", headers=_headers(outsider)).json()
    assert outsider_page["total"] == 0
    assert outsider_page["summary"]["dashboard"]["ai_diagnostic_count"] == 0


def test_mixed_result_insights_wait_for_grading_then_support_paging_and_authorization(client, monkeypatch):
    gateway = configure_mixed(monkeypatch)
    gateway.fail = "short_answer_grading"
    student = _login(client, "student", "t51-mixed-owner")
    outsider = _login(client, "student", "t51-mixed-outsider")
    teacher = _login(client, "teacher", "t51-mixed-teacher")
    _, test_id, _, payload = _submitted_mixed_test(client, student)

    submitted = client.post(
        f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload
    )
    assert submitted.status_code == 200, submitted.text
    pending = client.get(f"/learning/final-tests/{test_id}/grading", headers=_headers(student))
    assert pending.json()["status"] == "grading"
    pending_insights = client.get("/learning/student-insights", headers=_headers(student)).json()
    assert pending_insights["summary"]["dashboard"]["mastery_score"] is None
    assert pending_insights["summary"]["dashboard"]["mastery_sample_count"] == 0
    assert pending_insights["summary"]["dashboard"]["plan_completion_rate"] == 0

    gateway.fail = None
    retried = client.post(
        f"/learning/final-tests/{test_id}/retry-grading",
        headers=_headers(student),
        json={"client_request_id": "t51-retry-grading"},
    )
    assert retried.status_code == 202, retried.text
    graded = client.get(f"/learning/final-tests/{test_id}/grading", headers=_headers(student))
    assert graded.json()["status"] == "completed"

    first_page = client.get("/learning/student-insights?limit=1&offset=0", headers=_headers(student))
    assert first_page.status_code == 200, first_page.text
    page = first_page.json()
    dashboard = page["summary"]["dashboard"]
    assert page["total"] == 1 and len(page["items"]) == 1
    assert page["items"][0]["action"]["kind"] == "result"
    assert page["summary"]["next_action"]["kind"] == "result"
    assert dashboard["mastery_score"] == 93
    assert dashboard["mastery_sample_count"] == 1
    assert dashboard["plan_completion_rate"] == 100
    assert dashboard["tested_knowledge_count"] == 1
    assert len(dashboard["weaknesses"]) == 1
    assert dashboard["weaknesses"][0]["target_type"] == "knowledge"
    assert dashboard["weaknesses"][0]["target_code"] == POINT
    assert dashboard["weaknesses"][0]["occurrences"] == 1
    assert dashboard["weaknesses"][0]["mastery_percentage"] == 93

    next_page = client.get("/learning/student-insights?limit=1&offset=1", headers=_headers(student)).json()
    assert next_page["items"] == []
    assert next_page["total"] == 1
    assert next_page["summary"] == page["summary"]
    assert client.get("/learning/student-insights", headers=_headers(teacher)).status_code == 403
    assert client.get("/learning/student-insights", headers=_headers(outsider)).json()["total"] == 0
