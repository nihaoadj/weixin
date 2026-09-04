from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.content.public import (
    knowledge_card_for_code,
    knowledge_cards_for_topics,
    knowledge_point_view,
    knowledge_tree_view,
)
from app.modules.learning.application.review_ports import ReviewRepository
from app.modules.learning.application.review_records import (
    KnowledgeMapPoint,
    ReviewCardPrompt,
    ReviewDashboard,
    ReviewItemRecord,
    ReviewResult,
    ReviewStateRecord,
    SupplementalChoiceCard,
)
from app.shared.actor import Actor
from app.shared.errors import AppError
from app.shared.uow import UnitOfWork


class KnowledgeReviewApplication:
    def __init__(self, repository: ReviewRepository, uow: UnitOfWork) -> None:
        self._repository = repository
        self._uow = uow

    def exit_quiz(
        self, actor: Actor, topic_codes: tuple[str, ...], supplemental: tuple[SupplementalChoiceCard, ...] = ()
    ) -> tuple[ReviewCardPrompt, ...]:
        actor.require_role("student")
        self._validate_topics(topic_codes)
        cards = knowledge_cards_for_topics(topic_codes)
        supplement = tuple(item for item in supplemental if item.point_code in topic_codes)
        return tuple(
            [ReviewCardPrompt(item.card_code, item.point_code, item.prompt, item.options, None) for item in supplement]
            + [self._prompt(actor.id, card.code) for card in cards]
        )[:3]

    def due(
        self, actor: Actor, limit: int, supplemental: tuple[SupplementalChoiceCard, ...] = ()
    ) -> tuple[ReviewCardPrompt, ...]:
        actor.require_role("student")
        states = self._repository.due_states(actor.id, self._now(), limit)
        prompts: list[ReviewCardPrompt] = []
        supplemental_by_code = {item.card_code: item for item in supplemental}
        for state in states:
            extra = supplemental_by_code.get(state.card_code)
            if extra is not None:
                prompts.append(
                    ReviewCardPrompt(extra.card_code, extra.point_code, extra.prompt, extra.options, state.due_at)
                )
                continue
            if knowledge_card_for_code(state.card_code) is not None:
                prompts.append(self._prompt(actor.id, state.card_code, state))
        return tuple(prompts)

    def grade(self, actor: Actor, card_code: str, selected_option: int, confidence: str) -> ReviewResult:
        actor.require_role("student")
        card = knowledge_card_for_code(card_code)
        if card is None:
            raise AppError("RESOURCE_NOT_FOUND", "复习卡不存在", 404)
        if selected_option < 0 or selected_option >= len(card.options):
            raise AppError("VALIDATION_ERROR", "答案选项无效", 422)
        if confidence not in {"low", "medium", "high"}:
            raise AppError("VALIDATION_ERROR", "置信度无效", 422)
        correct = selected_option == card.correct_option
        rating = "again" if not correct else {"low": "hard", "medium": "good", "high": "easy"}[confidence]
        state = self._repository.get_state(actor.id, card.code)
        next_state = self._schedule(state, actor.id, card.code, card.point_code, rating)
        saved = self._repository.save_state(next_state)
        self._repository.add_attempt(actor.id, saved.id, selected_option, correct, rating)
        if not correct:
            self._repository.upsert_item(actor.id, card.point_code, card.code, "objective_card", card.code, "")
        self._uow.commit()
        return ReviewResult(card.code, correct, rating, card.explanation, saved.due_at)

    def grade_supplemental(
        self, actor: Actor, card: SupplementalChoiceCard, selected_option: int, confidence: str, *, commit: bool = True
    ) -> ReviewResult:
        actor.require_role("student")
        if selected_option < 0 or selected_option >= len(card.options) or confidence not in {"low", "medium", "high"}:
            raise AppError("VALIDATION_ERROR", "补充卡答案无效", 422)
        correct = selected_option == card.correct_option
        rating = "again" if not correct else {"low": "hard", "medium": "good", "high": "easy"}[confidence]
        saved = self._repository.save_state(
            self._schedule(
                self._repository.get_state(actor.id, card.card_code), actor.id, card.card_code, card.point_code, rating
            )
        )
        self._repository.add_attempt(actor.id, saved.id, selected_option, correct, rating)
        if not correct:
            self._repository.upsert_item(
                actor.id, card.point_code, card.card_code, "teacher_choice_card", card.card_code, ""
            )
        if commit:
            self._uow.commit()
        return ReviewResult(card.card_code, correct, rating, card.explanation, saved.due_at)

    def capture(self, actor: Actor, point_code: str, source_type: str, source_id: str, note: str) -> ReviewItemRecord:
        actor.require_role("student")
        if knowledge_point_view(point_code) is None:
            raise AppError("VALIDATION_ERROR", "知识点不存在", 422)
        if not source_type or not source_id or len(source_type) > 40 or len(source_id) > 160 or len(note) > 300:
            raise AppError("VALIDATION_ERROR", "复习记录无效", 422)
        item = self._repository.upsert_item(actor.id, point_code, None, source_type, source_id, note.strip())
        self._uow.commit()
        return item

    def rate_recall(self, actor: Actor, card_code: str, point_code: str, rating: str) -> ReviewResult:
        """Schedule a revealed teacher recall card without fabricating objective correctness."""
        actor.require_role("student")
        if not card_code.startswith("teacher-recall:") or knowledge_point_view(point_code) is None:
            raise AppError("VALIDATION_ERROR", "回忆卡无效", 422)
        if rating not in {"again", "hard", "good", "easy"}:
            raise AppError("VALIDATION_ERROR", "复习评分无效", 422)
        saved = self._repository.save_state(
            self._schedule(self._repository.get_state(actor.id, card_code), actor.id, card_code, point_code, rating)
        )
        # Null option keeps self-rating out of objective-correctness aggregation.
        self._repository.add_attempt(actor.id, saved.id, None, True, rating)
        self._uow.commit()
        return ReviewResult(card_code, True, rating, "已记录你的回忆自评。", saved.due_at)

    def dashboard(self, actor: Actor) -> ReviewDashboard:
        actor.require_role("student")
        items = self._repository.list_items(actor.id)
        due_count = len(self._repository.due_states(actor.id, self._now(), 1000))
        return ReviewDashboard(due_count, tuple(dict.fromkeys(item.point_code for item in items)), items)

    def knowledge_map(self, actor: Actor) -> tuple[KnowledgeMapPoint, ...]:
        """Classify catalog nodes from learner evidence, never from AI suggestions."""

        actor.require_role("student")
        now = self._now()
        states_by_point: dict[str, list[ReviewStateRecord]] = {}
        for state in self._repository.list_states(actor.id):
            states_by_point.setdefault(state.point_code, []).append(state)
        weak_points = {item.point_code for item in self._repository.list_items(actor.id) if item.active}
        result: list[KnowledgeMapPoint] = []
        for point in knowledge_tree_view():
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

    def dismiss(self, actor: Actor, item_id: int) -> None:
        actor.require_role("student")
        if not self._repository.dismiss_item(actor.id, item_id):
            raise AppError("RESOURCE_NOT_FOUND", "复习记录不存在", 404)
        self._uow.commit()

    def _prompt(self, student_id: int, card_code: str, state: ReviewStateRecord | None = None) -> ReviewCardPrompt:
        card = knowledge_card_for_code(card_code)
        if card is None:
            raise AppError("RESOURCE_NOT_FOUND", "复习卡不存在", 404)
        current = state or self._repository.get_state(student_id, card_code)
        return ReviewCardPrompt(
            card.code,
            card.point_code,
            card.prompt,
            card.options,
            current.due_at if current else None,
        )

    @staticmethod
    def _validate_topics(topic_codes: tuple[str, ...]) -> None:
        if not topic_codes or len(topic_codes) > 3 or any(knowledge_point_view(code) is None for code in topic_codes):
            raise AppError("VALIDATION_ERROR", "请先选择有效的学习主题", 422)

    def _schedule(
        self,
        existing: ReviewStateRecord | None,
        student_id: int,
        card_code: str,
        point_code: str,
        rating: str,
    ) -> ReviewStateRecord:
        now = self._now()
        state = existing or ReviewStateRecord(0, student_id, card_code, point_code, now, 0, 2.5, 0, 0, None, None)
        ease = state.ease
        lapses = state.lapses
        repetitions = state.repetitions
        if rating == "again":
            interval, ease, repetitions, lapses = 1, max(1.3, ease - 0.2), 0, lapses + 1
        elif rating == "hard":
            interval = max(1, round(max(1, state.interval_days) * 1.2))
            ease = max(1.3, ease - 0.15)
            repetitions += 1
        elif rating == "easy":
            interval = 4 if repetitions == 0 else round(max(1, state.interval_days) * ease * 1.3)
            ease, repetitions = ease + 0.15, repetitions + 1
        else:
            interval = 1 if repetitions == 0 else 3 if repetitions == 1 else round(max(1, state.interval_days) * ease)
            repetitions += 1
        interval = min(180, max(1, interval))
        return ReviewStateRecord(
            state.id,
            student_id,
            card_code,
            point_code,
            now + timedelta(days=interval),
            interval,
            ease,
            repetitions,
            lapses,
            rating,
            now,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
