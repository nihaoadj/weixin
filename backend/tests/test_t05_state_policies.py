"""T05 unit contracts for deterministic learning, training, and content state rules."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.content.domain.policy import ContentPolicy
from app.modules.learning.domain.policy import (
    answer_text,
    blueprint,
    blueprint_digest,
    dimension_config,
    fallback_blueprint,
    require_unlocked,
    target_dimensions,
)
from app.modules.training.application.use_cases import TrainingApplication
from app.modules.training.domain.state import TrainingPolicy
from app.shared.actor import Actor
from app.shared.errors import AppError


def test_learning_policy_selects_weak_dimensions_and_preserves_fallback_blueprint_contract() -> None:
    assert target_dimensions(({"dimension_id": "tests", "score": 30}, {"dimension_id": "history", "score": 40})) == [
        "tests",
        "history",
    ]
    assert target_dimensions(({"dimension_id": "tests", "score": 30}, {"dimension_id": "history", "score": 90})) == [
        "tests",
        "history",
    ]
    assert target_dimensions(({"dimension_id": "tests", "score": 90},)) == ["tests"]
    problem = SimpleNamespace(
        id=4,
        rubric={"dimensions": [{"id": "test_selection", "criteria": [{"id": "a", "keywords": ["影像"]}, {"id": "b"}]}]},
        case_definition={"practice_blueprints": [{"dimension_id": "test_selection", "id": "approved"}]},
    )
    assert dimension_config(problem, "test_selection")["id"] == "test_selection"
    assert dimension_config(problem, "unknown") == {"id": "unknown", "criteria": []}
    assert blueprint(problem, "test_selection") == {"dimension_id": "test_selection", "id": "approved"}
    assert blueprint(problem, "unknown") is None
    fallback = fallback_blueprint(problem, "test_selection")
    assert fallback["id"] == "fallback-4-test_selection"
    assert sum(item["weight"] for item in fallback["criteria"]) == 100
    assert blueprint_digest(fallback) == blueprint_digest(dict(fallback))


def test_learning_policy_rejects_locked_tasks_and_only_uses_student_answer_text() -> None:
    with pytest.raises(AppError, match="STATE_CONFLICT"):
        require_unlocked(2, "pending")
    require_unlocked(1, None)
    require_unlocked(3, "completed")
    assert answer_text({"id": "secret", "stage_id": "tests", "text": ["影像", 42], "none": None}).strip() == "影像"


def test_training_and_content_policies_reject_invalid_transitions_and_cross_scope_visibility() -> None:
    with pytest.raises(AppError, match="答案阶段"):
        TrainingPolicy.require_stage_answer("history", {"stage_id": "tests"})
    with pytest.raises(AppError, match="全部阶段"):
        TrainingPolicy.require_complete("in_progress")
    with pytest.raises(AppError, match="病例阶段无效"):
        TrainingPolicy.next_stage("unknown")

    student = Actor(1, "student-1", "student", "学生")
    teacher = Actor(2, "teacher-2", "teacher", "教师")
    assert not ContentPolicy.is_visible_to_student(
        status="published",
        target="individual",
        target_ids=("other",),
        student_external_id="student-1",
        class_codes=set(),
    )
    assert ContentPolicy.is_visible_to_student(
        status="published",
        target="class",
        target_ids=("class-a",),
        student_external_id="student-1",
        class_codes={"class-a"},
    )
    ContentPolicy.require_owner(teacher, None)
    with pytest.raises(AppError, match="内容不存在"):
        ContentPolicy.require_owner(teacher, 99)
    with pytest.raises(AppError, match="Medical review"):
        ContentPolicy.require_review_approved("pending")
    with pytest.raises(AppError):
        ContentPolicy.require_teacher(student)


def test_training_application_rejects_missing_retry_source_and_unavailable_assessment_without_writes() -> None:
    repository = SimpleNamespace(
        class_codes=lambda *_: set(),
        find_visible_problem=lambda *_: SimpleNamespace(content_type="guided_case"),
        find_attempt=lambda *_: None,
        find_assessment=lambda *_: None,
    )
    uow = SimpleNamespace(commit=lambda: pytest.fail("no commit"), rollback=lambda: pytest.fail("no rollback"))
    application = TrainingApplication(
        repository,
        uow,
        SimpleNamespace(),
        SimpleNamespace(),
    )
    actor = Actor(7, "student-7", "student", "学生")

    with pytest.raises(AppError, match="Retry requires"):
        application.start(actor, 1, retry_of_id=42)
    with pytest.raises(AppError, match="Assessment is not available"):
        application.assessment(actor, 42)


def test_training_application_rejects_blank_and_locked_patient_messages_before_gateway_or_persistence() -> None:
    repository = SimpleNamespace(
        find_attempt=lambda *_: SimpleNamespace(status="completed", current_stage="tests", messages=()),
    )
    uow = SimpleNamespace(commit=lambda: pytest.fail("no commit"), rollback=lambda: pytest.fail("no rollback"))
    application = TrainingApplication(repository, uow, SimpleNamespace(), SimpleNamespace())
    actor = Actor(7, "student-7", "student", "学生")
    with pytest.raises(AppError, match="不能为空"):
        application.send_patient_message(actor, 1, "  ")
    with pytest.raises(AppError, match="locked"):
        application.send_patient_message(actor, 1, "问题")
