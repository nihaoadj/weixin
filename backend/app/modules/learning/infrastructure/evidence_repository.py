from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.modules.learning.application.evidence_ports import LearningEvidenceCommand, LearningEvidenceRepository
from app.modules.learning.application.evidence_records import LearningEvidenceEventRecord, LearningEvidenceMetricRecord
from app.modules.learning.infrastructure.evidence_models import LearningEvidenceEvent, LearningEvidenceMetric
from app.shared.errors import PersistenceConflict


class SqlAlchemyEvidenceRepository(LearningEvidenceRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _record(row: LearningEvidenceEvent) -> LearningEvidenceEventRecord:
        return LearningEvidenceEventRecord(
            id=row.id,
            student_id=row.student_id,
            class_id=row.class_id,
            source_type=row.source_type,
            source_id=row.source_id,
            source_version=row.source_version,
            authority_level=row.authority_level,
            visibility_scope=row.visibility_scope,
            event_kind=row.event_kind,
            occurred_at=row.occurred_at,
            dedupe_key=row.dedupe_key,
            contract_version=row.contract_version,
            created_at=row.created_at,
            metrics=tuple(
                LearningEvidenceMetricRecord(
                    id=metric.id,
                    metric_kind=metric.metric_kind,
                    metric_code=metric.metric_code,
                    normalized_score=metric.normalized_score,
                    result=metric.result,
                    evidence_present=metric.evidence_present,
                )
                for metric in row.metrics
            ),
        )

    def find_by_dedupe(self, dedupe_key: str) -> LearningEvidenceEventRecord | None:
        row = self._session.scalar(
            select(LearningEvidenceEvent)
            .where(LearningEvidenceEvent.dedupe_key == dedupe_key)
            .options(selectinload(LearningEvidenceEvent.metrics))
        )
        return self._record(row) if row is not None else None

    def append(self, command: LearningEvidenceCommand) -> LearningEvidenceEventRecord:
        row = LearningEvidenceEvent(
            student_id=command.student_id,
            class_id=command.class_id,
            source_type=command.source_type,
            source_id=command.source_id.strip(),
            source_version=command.source_version,
            authority_level=command.authority_level,
            visibility_scope=command.visibility_scope,
            event_kind=command.event_kind,
            occurred_at=command.occurred_at,
            dedupe_key=command.dedupe_key.strip(),
            contract_version=command.contract_version,
            metrics=[
                LearningEvidenceMetric(
                    metric_kind=metric.metric_kind,
                    metric_code=metric.metric_code,
                    normalized_score=metric.normalized_score,
                    result=metric.result,
                    evidence_present=metric.evidence_present,
                )
                for metric in command.metrics
            ],
        )
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        self._session.refresh(row)
        return self._record(row)

    def list_events(
        self,
        student_ids: tuple[int, ...],
        start: datetime,
        end: datetime,
        *,
        include_student_only: bool = True,
    ) -> tuple[LearningEvidenceEventRecord, ...]:
        if not student_ids:
            return ()
        statement = (
            select(LearningEvidenceEvent)
            .where(
                LearningEvidenceEvent.student_id.in_(student_ids),
                LearningEvidenceEvent.occurred_at >= start,
                LearningEvidenceEvent.occurred_at <= end,
            )
            .options(selectinload(LearningEvidenceEvent.metrics))
            .order_by(LearningEvidenceEvent.occurred_at, LearningEvidenceEvent.id)
        )
        if not include_student_only:
            statement = statement.where(LearningEvidenceEvent.visibility_scope != "student_only")
        return tuple(self._record(row) for row in self._session.scalars(statement).all())


__all__ = ["SqlAlchemyEvidenceRepository"]
