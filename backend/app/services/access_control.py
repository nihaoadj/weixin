"""Compatibility facade for content visibility and report transition policies."""

from __future__ import annotations

from app.modules.content.domain.policy import ContentPolicy
from app.modules.content.infrastructure.visibility import SqlAlchemyContentVisibility
from app.modules.reports.domain.policy import ReportPolicy
from app.shared.errors import AppError


def student_class_codes(db, student):
    return SqlAlchemyContentVisibility.student_class_codes(db, student)


def student_problem_filter(student, class_codes):
    return SqlAlchemyContentVisibility.student_problem_filter(student, class_codes)


def is_problem_visible_to_student(problem, student, db=None) -> bool:
    if student.role != "student":
        return False
    class_codes = set(student.class_ids or [])
    if db is not None:
        class_codes = student_class_codes(db, student)
    return ContentPolicy.is_visible_to_student(
        status=problem.status,
        target=problem.target,
        target_ids=tuple(item for item in (problem.target_ids or "").split(",") if item),
        student_external_id=student.external_id,
        class_codes=class_codes,
    )


def ensure_report_transition(current_status: str, next_status: str) -> None:
    try:
        ReportPolicy().require_transition(current_status, next_status)
    except AppError as error:
        raise ValueError(error.message) from error
