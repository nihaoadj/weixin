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
from app.modules.learning.public import LearningEvidenceReadPort


class AnalyticsReader(Protocol):
    def load_classes(self, teacher_id: int, class_id: int | None) -> tuple[ScopeClass, ...]: ...

    def load_owned_classes(self, teacher_id: int, class_id: int | None) -> tuple[ScopeClass, ...]: ...

    def load_student_names(self, student_ids: tuple[int, ...]) -> dict[int, str]: ...

    def owns_case(self, teacher_id: int, problem_id: int) -> bool: ...

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


__all__ = ["AnalyticsReader", "LearningEvidenceReadPort"]
