"""T05 contract tests for publication/review application decisions and retries."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.content.application.records import ProblemCommand, ProblemRecord
from app.modules.content.application.use_cases import ContentApplication
from app.shared.actor import Actor
from app.shared.errors import AppError

NOW = datetime(2026, 8, 31, tzinfo=UTC)
AUTHOR = Actor(1, "author", "teacher", "作者")
REVIEWER = Actor(2, "reviewer", "teacher", "审核者", permissions=frozenset({"medical_review"}))
TEACHER = Actor(3, "teacher", "teacher", "教师")
CATALOG = SimpleNamespace(contains_points=lambda _codes: True)


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


@pytest.mark.parametrize("medical,status", [("pending", "draft"), ("approved", "published"), ("rejected", "draft")])
def test_content_update_is_direct_for_owner_regardless_of_old_lifecycle(medical, status) -> None:
    current = problem(medical_review_status=medical, status=status)
    uow = Uow()
    result = ContentApplication(repository(current), uow, CATALOG).update(AUTHOR, current.id, command())
    assert result.id == current.id and uow.commits == 1


def test_content_type_conversion_is_still_retired() -> None:
    current = problem()
    with pytest.raises(AppError) as raised:
        ContentApplication(repository(current), Uow(), CATALOG).update(
            AUTHOR, current.id, command(content_type="question")
        )
    assert (raised.value.code, raised.value.status_code) == ("RETIRED_FLOW", 409)


@pytest.mark.parametrize("operation", ["clone", "publish", "reject", "submit_review"])
def test_content_old_lifecycle_writes_are_retired_without_repository_mutation(operation) -> None:
    current = problem(status="published", medical_review_status="approved")
    uow = Uow()
    with pytest.raises(AppError) as raised:
        getattr(ContentApplication(repository(current), uow, CATALOG), operation)(AUTHOR, current.id)
    assert (raised.value.code, raised.value.status_code) == ("RETIRED_FLOW", 409)
    assert uow.commits == uow.rollbacks == 0


def test_content_review_permissions_and_generator_availability_fail_closed() -> None:
    current = problem()
    service = ContentApplication(repository(current), Uow(), CATALOG)
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
    service = ContentApplication(repository(current), Uow(), CATALOG)
    with pytest.raises(AppError, match="无需审核或发布"):
        service.submit_review(AUTHOR, current.id)
    with pytest.raises(AppError, match="无需审核或发布"):
        service.decide_review(
            Actor(AUTHOR.id, "same", "teacher", "same", permissions=frozenset({"medical_review"})),
            current.id,
            "approved",
            "x",
        )
    with pytest.raises(AppError, match="没有审核权限"):
        service.review_history(TEACHER, current.id)
