from __future__ import annotations

from datetime import UTC, datetime

from app.modules.analytics.application.records import ScopeClass, ScopeStudent
from app.modules.analytics.application.use_cases import AnalyticsApplication
from app.modules.learning.public import LearningEvidenceEventRecord, LearningEvidenceMetricRecord
from app.shared.actor import Actor

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


class Reader:
    def __init__(self, students: tuple[ScopeStudent, ...]) -> None:
        self.students = students
        self.classes = (ScopeClass(11, "病理一班", "path-1"),)

    def load_classes(self, _teacher_id: int, _class_id: int | None):
        return self.classes

    def load_students(self, _classes):
        return self.students

    def load_activity(self, *_args):
        return (), ()

    def load_learning(self, _student_id: int):
        return None, ()

    def load_knowledge(self, *_args):
        raise AssertionError("evidence-backed analytics must not read the legacy knowledge aggregate")


class EvidenceReader:
    def __init__(self, events: tuple[LearningEvidenceEventRecord, ...]) -> None:
        self.events = events

    def list_events(self, _student_ids, _start, _end, *, include_student_only=True):
        assert include_student_only is True
        return self.events


class Catalog:
    def point_view(self, code: str):
        return {"title": f"知识点 {code}"}


def event(
    event_id: int,
    *,
    student_id: int,
    source_type: str,
    authority_level: str,
    visibility_scope: str,
    metric_code: str = "kp.inflammation",
    result: str = "correct",
) -> LearningEvidenceEventRecord:
    return LearningEvidenceEventRecord(
        id=event_id,
        student_id=student_id,
        class_id=11 if visibility_scope != "student_only" else None,
        source_type=source_type,
        source_id=f"source-{event_id}",
        source_version=1,
        authority_level=authority_level,
        visibility_scope=visibility_scope,
        event_kind="assessment",
        occurred_at=NOW,
        dedupe_key=f"evidence-{event_id}",
        contract_version=1,
        created_at=NOW,
        metrics=(
            LearningEvidenceMetricRecord(
                id=event_id,
                metric_kind="knowledge",
                metric_code=metric_code,
                normalized_score=80,
                result=result,
                evidence_present=True,
            ),
        ),
    )


def app(events: tuple[LearningEvidenceEventRecord, ...], student_count: int = 5) -> AnalyticsApplication:
    students = tuple(
        ScopeStudent(index, f"s-{index}", f"学生{index}", ("path-1",)) for index in range(1, student_count + 1)
    )
    return AnalyticsApplication(Reader(students), Catalog(), evidence_reader=EvidenceReader(events))


def teacher() -> Actor:
    return Actor(99, "teacher-99", "teacher", "教师")


def test_personal_evidence_is_not_in_teacher_overview_or_knowledge() -> None:
    analytics = app(
        (
            event(
                1,
                student_id=1,
                source_type="ai_personal_practice",
                authority_level="personal_unverified",
                visibility_scope="student_only",
            ),
            event(
                2,
                student_id=1,
                source_type="reviewed_question_attempt",
                authority_level="reviewed_practice",
                visibility_scope="class_aggregate",
            ),
        )
    )

    overview = analytics.overview(teacher(), 11, "2026-09-01", "2026-09-13")
    assert overview["coverage"] == {
        "student_count": 5,
        "participant_count": 1,
        "evidence_count": 1,
        "updated_at": NOW,
    }
    assert overview["current_average_score"] is None
    assert overview["average_improvement"] is None
    assert overview["knowledge"] == []

    knowledge = analytics.knowledge(teacher(), 11)
    assert knowledge["participant_count"] == 1
    assert knowledge["weak_points"] == []
    assert knowledge["rankings_suppressed"] is True


def test_personal_only_evidence_produces_explicit_empty_formal_view() -> None:
    overview = app(
        (
            event(
                1,
                student_id=1,
                source_type="self_pbl_completion",
                authority_level="personal_unverified",
                visibility_scope="student_only",
            ),
        )
    ).overview(teacher(), 11, "2026-09-01", "2026-09-13")

    assert overview["coverage"]["participant_count"] == 0
    assert overview["completion"]["formal_task_rate"] is None
    assert overview["activity_sources"] == []
    assert overview["privacy"]["rankings_suppressed"] is True
