from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.learning.public import (
    AuthorityLevel,
    EvidenceEventKind,
    EvidenceMetricKind,
    EvidenceMetricResult,
    EvidenceSourceType,
    LearningEvidenceCommand,
    LearningEvidenceEventRecord,
    LearningEvidenceMetricCommand,
    VisibilityScope,
)


class LearningEvidenceRepository(Protocol):
    def find_by_dedupe(self, dedupe_key: str) -> LearningEvidenceEventRecord | None: ...

    def append(self, command: LearningEvidenceCommand) -> LearningEvidenceEventRecord: ...

    def list_events(
        self,
        student_ids: tuple[int, ...],
        start: datetime,
        end: datetime,
        *,
        include_student_only: bool = True,
    ) -> tuple[LearningEvidenceEventRecord, ...]: ...


__all__ = [
    "AuthorityLevel",
    "EvidenceEventKind",
    "EvidenceMetricKind",
    "EvidenceMetricResult",
    "EvidenceSourceType",
    "LearningEvidenceCommand",
    "LearningEvidenceMetricCommand",
    "LearningEvidenceRepository",
    "VisibilityScope",
]
