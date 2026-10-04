from __future__ import annotations

from typing import Protocol

from app.modules.learning.application.review_records import ReviewItemRecord, ReviewStateRecord


class ReviewRepository(Protocol):
    def list_states(self, student_id: int) -> tuple[ReviewStateRecord, ...]: ...

    def list_items(self, student_id: int) -> tuple[ReviewItemRecord, ...]: ...
