"""T05 contract tests for publication/review application decisions and retries."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.content.application.records import ProblemCommand, ProblemRecord
from app.modules.content.application.use_cases import ContentApplication
from app.shared.actor import Actor
from app.shared.errors import AppError, PersistenceConflict

NOW = datetime(2026, 8, 31, tzinfo=UTC)
AUTHOR = Actor(1, "author", "teacher", "作者")
REVIEWER = Actor(2, "reviewer", "teacher", "审核者", permissions=frozenset({"medical_review"}))
TEACHER = Actor(3, "teacher", "teacher", "教师")


class Uow:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def problem(**changes) -> ProblemRecord:
    values = dict(
        id=8,
        type="病例分析",
        title="病例",
        description="合成病例",
        target="all",
        target_label="全体学生",
        target_ids=(),
        status="draft",
        created_at=NOW,
        published_at=None,
        content_type="guided_case",
        slug="case-8",
        specialty="内科",
        difficulty="basic",
        estimated_minutes=10,
        version=1,
        parent_problem_id=None,
        author_id=AUTHOR.id,
        medical_review_status="not_submitted",
        capability_tags=(),
        case_definition={"schema_version": 1},
        rubric={"dimensions": []},
    )
    values.update(changes)
    return ProblemRecord(**values)


def command(**changes) -> ProblemCommand:
    values = dict(
        type="病例分析",
        title="更新",
        description="描述",
        target="all",
        target_label="全体学生",
        target_ids=(),
        content_type="guided_case",
        slug="case-8",
        specialty="内科",
        difficulty="basic",
        estimated_minutes=10,
        version=1,
        parent_problem_id=None,
        case_definition={"schema_version": 1},
        rubric={"dimensions": []},
        capability_tags=(),
    )
    values.update(changes)
    return ProblemCommand(**values)


def repository(current: ProblemRecord):
    return SimpleNamespace(
        get=lambda *_: current,
        answer_counts=lambda ids: {item: 4 for item in ids},
        class_codes=lambda *_: set(),
        list_visible_for_student=lambda *_: (current,),
        list_all=lambda: (current,),
        update=lambda *_: current,
        create=lambda *_: current,
        publish=lambda *_: current,
        reject=lambda *_: current,
        submit_review=lambda *_: current,
        add_review=lambda *_: current,
        review_queue=lambda *_: (current,),
        review_history=lambda *_: (),
        review_view=lambda *_: (current, None, ()),
        latest_approved_review_digest=lambda *_: "different",
        invalidate_review=lambda *_: None,
    )


@pytest.mark.parametrize(
    "current,changed",
    [
        (problem(), command(content_type="question")),
        (problem(medical_review_status="pending"), command()),
        (problem(status="published"), command()),
        (problem(medical_review_status="approved"), command()),
    ],
)
def test_content_update_rejects_immutable_type_review_and_published_cases(current, changed) -> None:
    uow = Uow()
    with pytest.raises(AppError, match="immutable|审核中|immutable"):
        ContentApplication(repository(current), uow).update(AUTHOR, current.id, changed)
    assert uow.commits == uow.rollbacks == 0


def test_content_clone_retries_a_unique_version_then_returns_counted_copy() -> None:
    current = problem(status="published", medical_review_status="approved")
    repo = repository(current)
    calls = 0

    def clone(*_args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PersistenceConflict()
        return problem(id=9, version=2, status="draft", medical_review_status="not_submitted")

    repo.clone = clone
    uow = Uow()
    result = ContentApplication(repo, uow).clone(AUTHOR, current.id)
    assert (result.id, result.answer_count, calls, uow.rollbacks, uow.commits) == (9, 4, 2, 1, 1)


def test_content_publish_invalidates_stale_review_and_preserves_published_idempotency() -> None:
    reviewed = problem(status="published", medical_review_status="approved")
    repo = repository(reviewed)
    invalidated = []
    repo.invalidate_review = invalidated.append
    uow = Uow()
    with pytest.raises(AppError, match="摘要已失效"):
        ContentApplication(repo, uow).publish(AUTHOR, reviewed.id)
    assert invalidated == [reviewed.id] and uow.commits == 1

    repo.latest_approved_review_digest = lambda *_: __import__(
        "app.modules.content.domain.digest", fromlist=["case_digest"]
    ).case_digest(reviewed)
    returned = ContentApplication(repo, uow).publish(AUTHOR, reviewed.id)
    assert returned.id == reviewed.id and uow.commits == 1


def test_content_review_permissions_and_generator_availability_fail_closed() -> None:
    current = problem()
    service = ContentApplication(repository(current), Uow())
    with pytest.raises(AppError, match="生成器"):
        service.generate_draft(AUTHOR, "topic", "level", [])
    for operation in (
        lambda: service.review_queue(TEACHER, "pending"),
        lambda: service.decide_review(TEACHER, current.id, "approved", "x"),
        lambda: service.review_view(TEACHER, current.id),
    ):
        with pytest.raises(AppError) as raised:
            operation()
        assert raised.value.code == "FORBIDDEN"


def test_content_review_rejects_self_review_wrong_owner_and_approved_resubmission() -> None:
    current = problem(medical_review_status="approved")
    service = ContentApplication(repository(current), Uow())
    with pytest.raises(AppError, match="已经审核"):
        service.submit_review(AUTHOR, current.id)
    with pytest.raises(AppError, match="Authors cannot"):
        service.decide_review(
            Actor(AUTHOR.id, "same", "teacher", "same", permissions=frozenset({"medical_review"})),
            current.id,
            "approved",
            "x",
        )
    with pytest.raises(AppError, match="没有审核权限"):
        service.review_history(TEACHER, current.id)
