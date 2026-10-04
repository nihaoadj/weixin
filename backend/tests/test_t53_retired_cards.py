"""Application tests for retired PBL-generated knowledge card writes."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.modules.content.application.records import (
    KnowledgeCardContributionCommand,
    KnowledgeCardContributionRecord,
)
from app.modules.content.application.use_cases import ContentApplication
from app.shared.actor import Actor
from app.shared.errors import AppError

NOW = datetime(2026, 9, 30, tzinfo=UTC)
OWNER = Actor(10, "owner", "teacher", "作者")
OTHER_TEACHER = Actor(11, "other", "teacher", "其他教师")
REVIEWER = Actor(20, "reviewer", "teacher", "审核教师", permissions=frozenset({"medical_review"}))
STUDENT = Actor(99, "student", "student", "学生")


def card(**changes: object) -> KnowledgeCardContributionRecord:
    values: dict[str, object] = {
        "id": 5,
        "point_code": "P-1",
        "owner_id": OWNER.id,
        "class_code": "C-1",
        "version": 1,
        "card_type": "recall",
        "prompt": "描述关键形态",
        "options": (),
        "correct_option": None,
        "explanation": "",
        "reference": "",
        "status": "draft",
        "reviewer_id": None,
        "review_comment": "",
        "reviewed_at": None,
        "created_at": NOW,
        "updated_at": NOW,
        "source_type": None,
    }
    values.update(changes)
    return KnowledgeCardContributionRecord(**values)  # type: ignore[arg-type]


def command(**changes: object) -> KnowledgeCardContributionCommand:
    values: dict[str, object] = {
        "point_code": "P-1",
        "class_code": "C-1",
        "card_type": "recall",
        "prompt": "描述更新后的关键形态",
        "options": (),
        "correct_option": None,
        "explanation": "补充说明",
        "reference": "教材",
        "target_student_ids": (),
    }
    values.update(changes)
    return KnowledgeCardContributionCommand(**values)  # type: ignore[arg-type]


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        raise AssertionError("these application operations must not roll back")


class FakeRepository:
    """Small in-memory repository that records attempted mutations and read scope."""

    def __init__(self, *cards: KnowledgeCardContributionRecord) -> None:
        self.cards = {item.id: item for item in cards}
        self.write_calls: list[str] = []
        self.get_calls = 0
        self.visible_scope: tuple[int, set[str], str | None] | None = None
        self.visible_cards: tuple[KnowledgeCardContributionRecord, ...] = ()

    def get_knowledge_card(self, card_id: int) -> KnowledgeCardContributionRecord | None:
        self.get_calls += 1
        return self.cards.get(card_id)

    def list_knowledge_cards_by_status(self, status: str) -> tuple[KnowledgeCardContributionRecord, ...]:
        return tuple(item for item in self.cards.values() if item.status == status)

    def list_visible_knowledge_cards(
        self, student_id: int, class_codes: set[str], point_code: str | None
    ) -> tuple[KnowledgeCardContributionRecord, ...]:
        self.visible_scope = (student_id, class_codes, point_code)
        return self.visible_cards

    def class_codes(self, student_id: int) -> set[str]:
        assert student_id == STUDENT.id
        return {"C-1"}

    def teacher_owns_class(self, teacher_id: int, class_code: str) -> bool:
        return teacher_id == OWNER.id and class_code == "C-1"

    def class_student_ids(self, _teacher_id: int, _class_code: str) -> set[int]:
        return set()

    def update_knowledge_card(
        self, card_id: int, _owner_id: int, updated: KnowledgeCardContributionCommand
    ) -> KnowledgeCardContributionRecord:
        self.write_calls.append("update")
        result = replace(
            self.cards[card_id],
            point_code=updated.point_code,
            class_code=updated.class_code,
            card_type=updated.card_type,
            prompt=updated.prompt,
            options=updated.options,
            correct_option=updated.correct_option,
            explanation=updated.explanation,
            reference=updated.reference,
            version=self.cards[card_id].version + 1,
            status="draft",
        )
        self.cards[card_id] = result
        return result

    def submit_knowledge_card(self, card_id: int) -> KnowledgeCardContributionRecord:
        self.write_calls.append("submit")
        result = replace(self.cards[card_id], status="pending")
        self.cards[card_id] = result
        return result

    def decide_knowledge_card(
        self, card_id: int, reviewer_id: int, decision: str, comment: str
    ) -> KnowledgeCardContributionRecord:
        self.write_calls.append("decide")
        result = replace(
            self.cards[card_id],
            status=decision,
            reviewer_id=reviewer_id,
            review_comment=comment,
            reviewed_at=NOW,
        )
        self.cards[card_id] = result
        return result

    def disable_knowledge_card(self, card_id: int) -> KnowledgeCardContributionRecord:
        self.write_calls.append("disable")
        result = replace(self.cards[card_id], status="disabled")
        self.cards[card_id] = result
        return result


class FakeCatalog:
    @staticmethod
    def point_view(point_code: str) -> object | None:
        return object() if point_code == "P-1" else None

    @staticmethod
    def contains_points(_point_codes: tuple[str, ...]) -> bool:
        return True


def application(
    repository: FakeRepository, uow: FakeUnitOfWork | None = None
) -> tuple[ContentApplication, FakeUnitOfWork]:
    actual_uow = uow or FakeUnitOfWork()
    return ContentApplication(repository, actual_uow, FakeCatalog()), actual_uow


@pytest.mark.parametrize(
    ("operation", "status", "actor"),
    [
        ("update", "disabled", OWNER),
        ("submit", "draft", OWNER),
        ("decide", "pending", REVIEWER),
        ("disable", "approved", REVIEWER),
    ],
)
def test_retired_card_writes_fail_without_mutation_or_commit(operation: str, status: str, actor: Actor) -> None:
    historical = card(status=status, source_type="pbl_ai")
    repository = FakeRepository(historical)
    service, uow = application(repository)

    with pytest.raises(AppError) as raised:
        if operation == "update":
            service.update_knowledge_card(actor, historical.id, command())
        elif operation == "submit":
            service.submit_knowledge_card(actor, historical.id)
        elif operation == "decide":
            service.decide_knowledge_card(actor, historical.id, "approved", "通过")
        else:
            service.disable_knowledge_card(actor, historical.id)

    assert (raised.value.code, raised.value.status_code) == ("RETIRED_FLOW", 409)
    assert repository.cards[historical.id] == historical
    assert repository.write_calls == []
    assert uow.commits == 0


@pytest.mark.parametrize("operation", ["update", "submit"])
def test_retired_card_owner_check_precedes_retirement_error(operation: str) -> None:
    historical = card(source_type="pbl_ai")
    repository = FakeRepository(historical)
    service, uow = application(repository)

    with pytest.raises(AppError) as raised:
        if operation == "update":
            service.update_knowledge_card(OTHER_TEACHER, historical.id, command())
        else:
            service.submit_knowledge_card(OTHER_TEACHER, historical.id)

    assert (raised.value.code, raised.value.status_code) == ("RESOURCE_NOT_FOUND", 404)
    assert repository.cards[historical.id] == historical
    assert repository.write_calls == []
    assert uow.commits == 0


@pytest.mark.parametrize("operation", ["decide", "disable"])
def test_reviewer_permission_precedes_retired_card_lookup(operation: str) -> None:
    historical = card(status="pending", source_type="pbl_ai")
    repository = FakeRepository(historical)
    service, uow = application(repository)

    with pytest.raises(AppError) as raised:
        if operation == "decide":
            service.decide_knowledge_card(OTHER_TEACHER, historical.id, "approved", "通过")
        else:
            service.disable_knowledge_card(OTHER_TEACHER, historical.id)

    assert (raised.value.code, raised.value.status_code) == ("FORBIDDEN", 403)
    assert repository.get_calls == 0
    assert repository.write_calls == []
    assert uow.commits == 0


def test_review_queue_hides_pending_retired_cards_without_changing_their_state() -> None:
    historical = card(id=6, status="pending", source_type="pbl_ai")
    formal = card(id=7, status="pending", source_type=None)
    repository = FakeRepository(historical, formal)
    service, _uow = application(repository)

    assert service.knowledge_card_review_queue(REVIEWER) == ()
    assert repository.cards[historical.id] == historical
    assert historical.status == "pending"


def test_student_card_read_keeps_existing_repository_scope_for_retired_source() -> None:
    historical = card(
        status="approved",
        source_type="pbl_ai",
        target_student_ids=(STUDENT.id,),
    )
    repository = FakeRepository(historical)
    repository.visible_cards = (historical,)
    service, _uow = application(repository)

    assert service.list_knowledge_cards(STUDENT) == ()
    assert repository.visible_scope is None
    assert repository.cards[historical.id] == historical


def test_independent_formal_card_writes_are_also_retired() -> None:
    formal = card()
    repository = FakeRepository(formal)
    service, uow = application(repository)
    for operation in [
        lambda: service.create_knowledge_card(OWNER, command()),
        lambda: service.update_knowledge_card(OWNER, formal.id, command()),
        lambda: service.submit_knowledge_card(OWNER, formal.id),
        lambda: service.decide_knowledge_card(REVIEWER, formal.id, "approved", "审核通过"),
        lambda: service.disable_knowledge_card(REVIEWER, formal.id),
    ]:
        with pytest.raises(AppError) as raised:
            operation()
        assert (raised.value.code, raised.value.status_code) == ("RETIRED_FLOW", 409)
    assert repository.cards[formal.id] == formal
    assert repository.write_calls == []
    assert uow.commits == 0
