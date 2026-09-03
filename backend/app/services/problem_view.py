"""Compatibility facade for content response mappers and answer counts."""

from __future__ import annotations

from app.modules.content.infrastructure.repositories import SqlAlchemyProblemRepository
from app.modules.content.public import authoring_problem_view, problem_view


def serialize_problem(problem, answer_count: int = 0, public_for_student: bool = False) -> dict[str, object]:
    return problem_view(
        SqlAlchemyProblemRepository._record(problem, answer_count), public_for_student=public_for_student
    )


def serialize_authoring_problem(problem, answer_count: int = 0) -> dict[str, object]:
    return authoring_problem_view(SqlAlchemyProblemRepository._record(problem, answer_count))


def answer_counts(db, problem_ids: list[int] | None = None) -> dict[int, int]:
    if problem_ids == []:
        return {}
    if problem_ids is None:
        from sqlalchemy import select

        from app.modules.content.infrastructure.models import Problem

        problem_ids = list(db.scalars(select(Problem.id)).all())
    return SqlAlchemyProblemRepository(db).answer_counts(problem_ids)
