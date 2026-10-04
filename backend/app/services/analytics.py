"""Compatibility facade for the analytics read application."""

from __future__ import annotations

from app.modules.analytics.domain.policy import AnalyticsPolicy
from app.modules.analytics.wiring import analytics_application
from app.shared.actor import Actor


def date_range(date_from: str | None, date_to: str | None):
    return AnalyticsPolicy.date_range(date_from, date_to)


def overview(teacher, class_id: int | None, date_from: str | None, date_to: str | None, db):
    return analytics_application(db).overview(Actor.from_user(teacher), class_id, date_from, date_to)


def case_detail(teacher, problem_id: int, class_id: int | None, date_from: str | None, date_to: str | None, db):
    return analytics_application(db).case_detail(Actor.from_user(teacher), problem_id, class_id, date_from, date_to)


def student_detail(teacher, student_id: int, class_id: int | None, date_from: str | None, date_to: str | None, db):
    return analytics_application(db).student_detail(Actor.from_user(teacher), student_id, class_id, date_from, date_to)
