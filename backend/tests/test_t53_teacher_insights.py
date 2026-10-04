"""Teacher insights keep metric windows, frozen result statistics and privacy separate."""

import json
from datetime import timedelta

import pytest

from app.modules.analytics.api.teacher_insights import (
    InsightDiagnosisPage,
    InsightOverview,
    InsightStudentDetail,
    InsightStudentPage,
)
from app.modules.analytics.application.teacher_insights import TeacherInsights, point_statistics
from app.modules.pbl.public import PblTeacherDiagnosisRecord, PblTeacherDiscussionRecord
from app.shared.errors import AppError
from tests.test_t44_analytics import (
    NOW,
    RESULT_A,
    ROUTE_A,
    TEACHER,
    FakeReader,
    FakeRouteResults,
    _published,
    _result,
)


class Diagnoses:
    def __init__(self):
        self.rows = (PblTeacherDiagnosisRecord(1, 70, 7, 11, NOW - timedelta(hours=1), ("inflammation",), ("causal",)),)

    def teacher_discussions(self, teacher_id, class_ids, start, end, session_id=None):
        return ()

    def teacher_diagnoses(self, teacher_id, class_ids, start, end, session_id=None):
        return tuple(
            row
            for row in self.rows
            if row.class_id in class_ids
            and start <= row.completed_at < end
            and (session_id is None or row.session_id == session_id)
        )


def test_mixed_and_legacy_statistics_use_exact_objective_sets_and_separate_short_points():
    questions = [
        {"point_code": "p", "selected_option": 0, "correct_option": 0},
        {"point_code": "p", "question_type": "multiple_choice", "selected_options": [2, 0], "correct_options": [0, 2]},
        {"point_code": "p", "question_type": "multiple_choice", "selected_options": [0], "correct_options": [0, 2]},
        {"point_code": "p", "question_type": "multiple_choice", "selected_options": [0, 0], "correct_options": [0]},
        {"point_code": "p", "question_type": "short_answer", "points_awarded": 0, "points_possible": 30},
        {"point_code": "p", "question_type": "short_answer", "points_awarded": 15, "points_possible": 30},
        {"point_code": "p", "question_type": "short_answer", "points_awarded": True, "points_possible": 30},
        {"point_code": "q", "selected_option": None, "correct_option": 1},
    ]
    points = point_statistics(({"payload": {"questions": questions}},))
    assert points[0] == {
        "point_code": "p",
        "correct_count": 2,
        "objective_count": 3,
        "invalid_objective_count": 1,
        "short_answer_count": 2,
        "invalid_short_answer_count": 1,
        "points_awarded": 15,
        "points_possible": 60,
        "accuracy_rate": 66.7,
        "short_answer_score_rate": 25,
    }
    assert points[1]["accuracy_rate"] is None
    assert points[1]["short_answer_score_rate"] is None


def test_progress_cohort_and_completed_results_use_different_dates_without_fake_zero():
    port = FakeRouteResults()
    old_route = _published(ROUTE_A, 11, result_id=RESULT_A)
    old_route["published_at"] = NOW - timedelta(days=60)
    grading_route = _published("grading-route", 12)
    grading_route["attempt_status"] = "grading"
    port.published = (old_route, grading_route)
    result = _result(ROUTE_A, RESULT_A)
    result["score"] = 0
    result["payload"]["selected_text"] = "PRIVATE STUDENT ANSWER"
    port.completed = (result,)
    service = TeacherInsights(FakeReader(), port, Diagnoses())

    overview = service.overview(TEACHER, 7)
    InsightOverview.model_validate(overview)
    assert overview["cohort"] == {
        "published_routes": 1,
        "completed_tests": 0,
        "completion_rate": 0,
        "grading_tests": 1,
    }
    assert overview["period_results"]["completed_tests"] == 1
    assert overview["period_results"]["average_score"] == 0
    students = service.students(TEACHER, 7)
    InsightStudentPage.model_validate(students)
    empty = next(item for item in students["items"] if item["student_id"] == 12)
    assert empty["period_results"]["average_score"] is None
    detail = service.student(TEACHER, 11, 7)
    InsightStudentDetail.model_validate(detail)
    assert len(detail["results"]) == 1 and not detail["routes"]
    serialized = json.dumps(detail, default=str)
    assert "PRIVATE STUDENT ANSWER" not in serialized
    assert '"questions"' not in serialized and '"selected_text"' not in serialized


def test_diagnostics_are_classroom_scoped_paginated_and_no_private_payload_is_exposed():
    service = TeacherInsights(FakeReader(), FakeRouteResults(), Diagnoses())
    data = service.diagnostics(TEACHER, 7, limit=1)
    InsightDiagnosisPage.model_validate(data)
    assert data["total"] == 1
    assert data["knowledge_gaps"][0]["student_count"] == 1
    assert data["reasoning_issues"][0]["code"] == "causal"
    assert "messages" not in data["items"][0]
    assert service.diagnostics(TEACHER, 7, session_id=71)["total"] == 0
    with pytest.raises(AppError) as wrong_class:
        service.overview(TEACHER, 8)
    assert wrong_class.value.status_code == 404
    with pytest.raises(AppError) as unknown_student:
        service.student(TEACHER, 999, 7)
    assert unknown_student.value.status_code == 404


def test_unfinished_discussions_without_routes_are_visible_with_their_own_date_basis():
    class Discussions(Diagnoses):
        def teacher_discussions(self, teacher_id, class_ids, start, end, session_id=None):
            rows = (
                PblTeacherDiscussionRecord(
                    91, 70, 7, 99, "hypothesis", "active", NOW - timedelta(hours=1), None
                ),
                PblTeacherDiscussionRecord(
                    92, 70, 7, 99, "completed", "completed", NOW - timedelta(days=60), NOW - timedelta(hours=1)
                ),
            )
            return tuple(
                row
                for row in rows
                if row.class_id in class_ids
                and start <= row.started_at < end
                and (session_id is None or row.session_id == session_id)
            )

    routes = FakeRouteResults()
    routes.published = ()
    routes.completed = ()
    service = TeacherInsights(FakeReader(), routes, Discussions())
    page = service.students(TEACHER, 7)
    InsightStudentPage.model_validate(page)
    summary = next(item for item in page["items"] if item["student_id"] == 99)
    assert summary["discussion_progress"] == {"participated": 1, "active": 1, "completed": 0}
    assert summary["cohort"]["published_routes"] == 0
    detail = service.student(TEACHER, 99, 7)
    InsightStudentDetail.model_validate(detail)
    assert len(detail["discussions"]) == 1 and detail["routes"] == []
    assert detail["discussions"][0]["phase"] == "hypothesis"
    assert "messages" not in json.dumps(detail, default=str)
    assert service.student(TEACHER, 99, 7, session_id=71)["discussions"] == []
