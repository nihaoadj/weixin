from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.analytics.application.records import (
    AttemptAnalyticsRecord,
    KnowledgeAnalyticsRecord,
    LearningPlanRecord,
    PracticeMasteryRecord,
    ProblemAnalyticsRecord,
    ScopeClass,
    ScopeStudent,
)


class AnalyticsReader(Protocol):
    def load_classes(self, teacher_id: int, class_id: int | None) -> tuple[ScopeClass, ...]: ...

    def load_students(self, classes: tuple[ScopeClass, ...]) -> tuple[ScopeStudent, ...]: ...

    def load_activity(
        self,
        student_ids: tuple[int, ...],
        start: datetime,
        end: datetime,
        problem_id: int | None,
    ) -> tuple[tuple[ProblemAnalyticsRecord, ...], tuple[AttemptAnalyticsRecord, ...]]: ...

    def load_learning(self, student_id: int) -> tuple[LearningPlanRecord | None, tuple[PracticeMasteryRecord, ...]]: ...

    def load_knowledge(self, student_ids: tuple[int, ...], now: datetime) -> KnowledgeAnalyticsRecord: ...
