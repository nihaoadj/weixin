from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.learning.application.review_records import ReviewItemRecord, ReviewStateRecord
from app.modules.learning.infrastructure.models import ReviewItem, ReviewState


class SqlAlchemyReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _state(item: ReviewState) -> ReviewStateRecord:
        return ReviewStateRecord(
            item.id,
            item.student_id,
            item.card_code,
            item.point_code,
            item.due_at,
            item.interval_days,
            item.ease,
            item.repetitions,
            item.lapses,
            item.last_rating,
            item.last_reviewed_at,
        )

    @staticmethod
    def _item(item: ReviewItem) -> ReviewItemRecord:
        return ReviewItemRecord(
            item.id,
            item.point_code,
            item.card_code,
            item.source_type,
            item.source_id,
            item.note,
            item.active,
            item.created_at,
            item.updated_at,
        )

    def list_states(self, student_id: int) -> tuple[ReviewStateRecord, ...]:
        rows = self._session.scalars(
            select(ReviewState)
            .where(ReviewState.student_id == student_id)
            .order_by(ReviewState.last_reviewed_at.desc(), ReviewState.id.desc())
        ).all()
        return tuple(self._state(item) for item in rows)

    def list_items(self, student_id: int) -> tuple[ReviewItemRecord, ...]:
        statement = select(ReviewItem).where(ReviewItem.student_id == student_id, ReviewItem.active.is_(True))
        rows = self._session.scalars(statement.order_by(ReviewItem.updated_at.desc(), ReviewItem.id.desc())).all()
        return tuple(self._item(item) for item in rows)
