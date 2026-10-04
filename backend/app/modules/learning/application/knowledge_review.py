from __future__ import annotations

from datetime import UTC, datetime

from app.modules.content.public import KnowledgeCatalogPort
from app.modules.learning.application.review_ports import ReviewRepository
from app.modules.learning.application.review_records import KnowledgeMapPoint, ReviewStateRecord
from app.shared.actor import Actor


class KnowledgeReviewApplication:
    def __init__(
        self,
        repository: ReviewRepository,
        knowledge_catalog: KnowledgeCatalogPort,
    ) -> None:
        self._repository = repository
        self._knowledge_catalog = knowledge_catalog

    def knowledge_map(self, actor: Actor) -> tuple[KnowledgeMapPoint, ...]:
        """Classify catalog nodes from learner evidence, never from AI suggestions."""

        actor.require_role("student")
        now = self._now()
        states_by_point: dict[str, list[ReviewStateRecord]] = {}
        for state in self._repository.list_states(actor.id):
            states_by_point.setdefault(state.point_code, []).append(state)
        weak_points = {item.point_code for item in self._repository.list_items(actor.id) if item.active}
        result: list[KnowledgeMapPoint] = []
        for point in self._knowledge_catalog.tree_view():
            code = str(point["code"])
            states = states_by_point.get(code, [])
            if code in weak_points:
                status = "weak"
            elif any(state.due_at <= now for state in states):
                status = "due"
            elif any(state.repetitions >= 3 and state.interval_days >= 7 for state in states):
                status = "stable"
            elif states:
                status = "learning"
            else:
                status = "not_started"
            result.append(KnowledgeMapPoint(code, status))
        return tuple(result)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
