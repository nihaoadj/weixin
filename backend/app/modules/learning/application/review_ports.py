from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.learning.application.review_records import ReviewItemRecord, ReviewStateRecord


class ReviewRepository(Protocol):
    def get_state(self, student_id: int, card_code: str) -> ReviewStateRecord | None: ...

    def due_states(self, student_id: int, now: datetime, limit: int) -> tuple[ReviewStateRecord, ...]: ...

    def list_states(self, student_id: int) -> tuple[ReviewStateRecord, ...]: ...

    def save_state(self, state: ReviewStateRecord) -> ReviewStateRecord: ...

    def add_attempt(
        self, student_id: int, state_id: int, selected_option: int | None, correct: bool, rating: str
    ) -> None: ...

    def upsert_item(
        self,
        student_id: int,
        point_code: str,
        card_code: str | None,
        source_type: str,
        source_id: str,
        note: str,
    ) -> ReviewItemRecord: ...

    def list_items(self, student_id: int, active_only: bool = True) -> tuple[ReviewItemRecord, ...]: ...

    def dismiss_item(self, student_id: int, item_id: int) -> bool: ...
