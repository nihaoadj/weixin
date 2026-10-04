"""T44 classroom analytics counts published routes and completed final-test results only."""

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.analytics.api.analytics import (
    ClassroomProgress,
    ClassroomProgressItemPage,
    ReportAnalyticsOverview,
    ReportAnalyticsStudent,
    ReportAnalyticsStudents,
)
from app.modules.analytics.application.classroom_reports import ClassroomReportAnalytics
from app.modules.analytics.application.records import ScopeClass, ScopeStudent
from app.shared.actor import Actor
from app.shared.errors import AppError

TEACHER = Actor(id=5, external_id="analytics-teacher", role="teacher", nickname="教师")
NOW = datetime.now(UTC).replace(microsecond=0)
ROUTE_A = "11111111-1111-4111-8111-111111111111"
ROUTE_B = "22222222-2222-4222-8222-222222222222"
ROUTE_OUTSIDE = "33333333-3333-4333-8333-333333333333"
RESULT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RESULT_OUTSIDE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _published(route_id: str, student_id: int, *, result_id: str | None = None) -> dict:
    return {
        "route_id": route_id,
        "student_id": student_id,
        "class_id": 7,
        "session_id": 70,
        "published_at": NOW - timedelta(hours=4),
        "published": True,
        "result_id": result_id,
        "score": 66.7 if result_id else None,
        "completed_at": NOW - timedelta(hours=2) if result_id else None,
        "question_count": 3 if result_id else None,
        "correct_count": 2 if result_id else None,
    }


def _result(route_id: str, result_id: str, student_id: int = 11) -> dict:
    return {
        "id": result_id,
        "result_id": result_id,
        "route_id": route_id,
        "student_id": student_id,
        "class_id": 7,
        "session_id": 70,
        "score": 66.7,
        "completed_at": NOW - timedelta(hours=2),
        "question_count": 3,
        "correct_count": 2,
        "payload": {
            "source_kind": "classroom",
            "questions": [
                {"point_code": "pathology.inflammation", "selected_option": 1, "correct_option": 1},
                {"point_code": "pathology.inflammation", "selected_option": 0, "correct_option": 1},
                {"point_code": "pathology.neoplasia", "selected_option": 2, "correct_option": 2},
            ],
        },
    }


class FakeReader:
    def __init__(self, owned: bool = True) -> None:
        self.owned = owned

    def load_owned_classes(self, teacher_id: int, class_id: int | None) -> tuple[ScopeClass, ...]:
        if not self.owned or teacher_id != TEACHER.id or class_id not in (None, 7):
            return ()
        return (ScopeClass(7, "炎症班", "inflammation"),)

    def load_students(self, classes: tuple[ScopeClass, ...]) -> tuple[ScopeStudent, ...]:
        return (ScopeStudent(11, "student-11", "甲同学", ("inflammation",)),)

    def load_student_names(self, student_ids: tuple[int, ...]) -> dict[int, str]:
        return {student_id: f"学生{student_id}" for student_id in student_ids}


class FakeRouteResults:
    def __init__(self) -> None:
        self.published = (_published(ROUTE_A, 11, result_id=RESULT_A), _published(ROUTE_B, 12))
        self.completed = (_result(ROUTE_A, RESULT_A), _result(ROUTE_OUTSIDE, RESULT_OUTSIDE))
        self.calls: list[tuple] = []

    @staticmethod
    def _within(rows: tuple[dict, ...], key: str, start: datetime, end: datetime) -> tuple[dict, ...]:
        return tuple(row for row in rows if start <= row[key] < end)

    def completed_for_teacher(self, teacher_id: int, class_ids: tuple[int, ...], start, end) -> tuple[dict, ...]:
        self.calls.append(("completed", teacher_id, class_ids, start, end))
        rows = tuple(row for row in self.completed if row["class_id"] in class_ids)
        return self._within(rows, "completed_at", start, end)

    def published_for_teacher(self, teacher_id: int, class_ids: tuple[int, ...], start, end, session_id=None):
        self.calls.append(("published", teacher_id, class_ids, start, end, session_id))
        rows = tuple(
            row
            for row in self.published
            if row["class_id"] in class_ids and (session_id is None or row["session_id"] == session_id)
        )
        return self._within(rows, "published_at", start, end)

    def classroom_progress_for_teacher(self, teacher_id: int, class_id: int, session_id: int) -> tuple[dict, ...]:
        self.calls.append(("progress", teacher_id, class_id, session_id))
        return tuple(
            row for row in self.published if row["class_id"] == class_id and row["session_id"] == session_id
        )


class FakeParticipations:
    def classroom_participants(self, class_id: int, session_id: int) -> tuple[int, ...] | None:
        return (11, 12, 13) if (class_id, session_id) == (7, 70) else None


def _analytics(*, owned: bool = True) -> tuple[ClassroomReportAnalytics, FakeRouteResults]:
    results = FakeRouteResults()
    return ClassroomReportAnalytics(FakeReader(owned), results, FakeParticipations()), results


def test_overview_uses_published_route_cohort_and_final_test_point_accuracy() -> None:
    analytics, port = _analytics()
    overview = analytics.overview(TEACHER, 7, None, None)

    assert overview["data_basis"] == "learning_routes"
    assert overview["published_routes"] == 2
    assert overview["completed_tests"] == 1
    assert overview["completion_rate"] == 50
    assert overview["student_count"] == 2
    assert overview["knowledge"] == [
        {
            "point_code": "pathology.inflammation",
            "correct_count": 1,
            "question_count": 2,
            "accuracy_rate": 50,
        },
        {
            "point_code": "pathology.neoplasia",
            "correct_count": 1,
            "question_count": 1,
            "accuracy_rate": 100,
        },
    ]
    assert "dimensions" not in overview and "rankings_suppressed" not in overview
    assert {call[0] for call in port.calls} == {"completed", "published"}
    schema = ReportAnalyticsOverview.model_validate(overview)
    assert schema.completed_tests == 1


def test_student_and_class_progress_views_expose_only_route_result_facts() -> None:
    analytics, _port = _analytics()
    students = analytics.students(TEACHER, 7, None, None, 20, 0)
    ReportAnalyticsStudents.model_validate(students)
    assert students["items"] == [
        {
            "student_id": 11,
            "nickname": "甲同学",
            "published_routes": 1,
            "completed_tests": 1,
            "completion_rate": 100,
            "last_completed_at": NOW - timedelta(hours=2),
        },
        {
            "student_id": 12,
            "nickname": "学生12",
            "published_routes": 1,
            "completed_tests": 0,
            "completion_rate": 0,
            "last_completed_at": None,
        },
    ]

    detail = analytics.student_detail(TEACHER, 7, 11, None, None, 20, 0)
    ReportAnalyticsStudent.model_validate(detail)
    assert detail["completed_tests"] == 1
    assert detail["result_page"]["items"] == [
        {
            "result_id": RESULT_A,
            "route_id": ROUTE_A,
            "session_id": 70,
            "score": 66.7,
            "correct_count": 2,
            "question_count": 3,
            "completed_at": NOW - timedelta(hours=2),
        }
    ]
    assert "report_page" not in detail and "dimensions" not in detail

    progress = analytics.progress(TEACHER, 7, None, None, 70)
    ClassroomProgress.model_validate(progress)
    assert progress["published_routes"] == 2
    assert progress["completed_tests"] == 1
    assert progress["in_progress"] == 1
    assert progress["completion_rate"] == 50
    items = analytics.progress_items(TEACHER, 7, 70, None, 20, 0)
    ClassroomProgressItemPage.model_validate(items)
    assert [row["execution_status"] for row in items["items"]] == ["completed", "in_progress", "unpublished"]
    assert items["items"][0]["result_id"] == RESULT_A
    assert items["items"][2]["route_id"] is None
    assert all("current_cycle" not in row and "due_at" not in row for row in items["items"])


def test_teacher_scope_and_empty_denominator_are_enforced() -> None:
    analytics, _port = _analytics(owned=False)
    with pytest.raises(AppError) as error:
        analytics.overview(TEACHER, 7, None, None)
    assert error.value.code == "RESOURCE_NOT_FOUND"

    no_results = FakeRouteResults()
    no_results.published = ()
    no_results.completed = ()
    empty = ClassroomReportAnalytics(FakeReader(), no_results, FakeParticipations()).overview(TEACHER, 7, None, None)
    assert empty["completion_rate"] is None
    assert empty["completed_tests"] == empty["published_routes"] == 0
    assert empty["knowledge"] == []
