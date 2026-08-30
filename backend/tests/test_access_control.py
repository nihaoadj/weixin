from types import SimpleNamespace

import pytest

from app.services.access_control import ensure_report_transition, is_problem_visible_to_student


def problem(target: str, target_ids: str = "", status: str = "published") -> SimpleNamespace:
    return SimpleNamespace(target=target, target_ids=target_ids, status=status)


def student(external_id: str = "s1", class_ids: list[str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(role="student", external_id=external_id, class_ids=class_ids or [])


def test_problem_visibility_rules() -> None:
    assert is_problem_visible_to_student(problem("all"), student())
    assert is_problem_visible_to_student(problem("class", "a,b"), student(class_ids=["b"]))
    assert is_problem_visible_to_student(problem("individual", "s1"), student())
    assert not is_problem_visible_to_student(problem("all", status="draft"), student())
    assert not is_problem_visible_to_student(problem("class", "a"), student(class_ids=["b"]))
    assert not is_problem_visible_to_student(problem("unknown"), student())


def test_report_transition_rules() -> None:
    ensure_report_transition("draft", "pending_review")
    ensure_report_transition("pending_review", "reviewed")
    ensure_report_transition("reviewed", "reviewed")
    with pytest.raises(ValueError):
        ensure_report_transition("draft", "reviewed")
