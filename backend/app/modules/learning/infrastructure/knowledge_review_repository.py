from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.learning.application.review_records import ReviewItemRecord, ReviewStateRecord
from app.modules.learning.infrastructure.models import ReviewAttempt, ReviewItem, ReviewState
from app.shared.errors import PersistenceConflict


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

    def get_state(self, student_id: int, card_code: str) -> ReviewStateRecord | None:
        item = self._session.scalar(
            select(ReviewState).where(ReviewState.student_id == student_id, ReviewState.card_code == card_code)
        )
        return self._state(item) if item else None

    def due_states(self, student_id: int, now: datetime, limit: int) -> tuple[ReviewStateRecord, ...]:
        rows = self._session.scalars(
            select(ReviewState)
            .where(ReviewState.student_id == student_id, ReviewState.due_at <= now)
            .order_by(ReviewState.due_at.asc(), ReviewState.id.asc())
            .limit(limit)
        ).all()
        return tuple(self._state(item) for item in rows)

    def list_states(self, student_id: int) -> tuple[ReviewStateRecord, ...]:
        rows = self._session.scalars(
            select(ReviewState)
            .where(ReviewState.student_id == student_id)
            .order_by(ReviewState.last_reviewed_at.desc(), ReviewState.id.desc())
        ).all()
        return tuple(self._state(item) for item in rows)

    def save_state(self, state: ReviewStateRecord) -> ReviewStateRecord:
        item = self._session.get(ReviewState, state.id) if state.id else None
        if item is None:
            item = ReviewState(
                student_id=state.student_id,
                card_code=state.card_code,
                point_code=state.point_code,
                due_at=state.due_at,
            )
            self._session.add(item)
        item.point_code = state.point_code
        item.due_at = state.due_at
        item.interval_days = state.interval_days
        item.ease = state.ease
        item.repetitions = state.repetitions
        item.lapses = state.lapses
        item.last_rating = state.last_rating
        item.last_reviewed_at = state.last_reviewed_at
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return self._state(item)

    def add_attempt(
        self, student_id: int, state_id: int, selected_option: int | None, correct: bool, rating: str
    ) -> None:
        self._session.add(
            ReviewAttempt(
                state_id=state_id,
                student_id=student_id,
                selected_option=selected_option,
                correct=correct,
                rating=rating,
            )
        )

    def upsert_item(
        self,
        student_id: int,
        point_code: str,
        card_code: str | None,
        source_type: str,
        source_id: str,
        note: str,
    ) -> ReviewItemRecord:
        item = self._session.scalar(
            select(ReviewItem).where(
                ReviewItem.student_id == student_id,
                ReviewItem.point_code == point_code,
                ReviewItem.source_type == source_type,
                ReviewItem.source_id == source_id,
            )
        )
        if item is None:
            item = ReviewItem(
                student_id=student_id,
                point_code=point_code,
                card_code=card_code,
                source_type=source_type,
                source_id=source_id,
                note=note,
                active=True,
            )
            self._session.add(item)
        else:
            item.card_code = card_code or item.card_code
            item.note = note or item.note
            item.active = True
            item.updated_at = datetime.now(UTC)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return self._item(item)

    def list_items(self, student_id: int, active_only: bool = True) -> tuple[ReviewItemRecord, ...]:
        statement = select(ReviewItem).where(ReviewItem.student_id == student_id)
        if active_only:
            statement = statement.where(ReviewItem.active.is_(True))
        rows = self._session.scalars(statement.order_by(ReviewItem.updated_at.desc(), ReviewItem.id.desc())).all()
        return tuple(self._item(item) for item in rows)

    def dismiss_item(self, student_id: int, item_id: int) -> bool:
        item = self._session.scalar(
            select(ReviewItem).where(ReviewItem.id == item_id, ReviewItem.student_id == student_id)
        )
        if item is None:
            return False
        item.active = False
        item.updated_at = datetime.now(UTC)
        return True
