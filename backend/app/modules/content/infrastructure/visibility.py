from __future__ import annotations

from sqlalchemy import and_, false, or_, select
from sqlalchemy.orm import Session

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.content.infrastructure.models import Problem
from app.modules.identity.infrastructure.models import User


class SqlAlchemyContentVisibility:
    """SQL predicates for content visibility; publication policy remains domain-owned."""

    @staticmethod
    def student_class_codes(db: Session, student: User) -> set[str]:
        legacy = {item for item in (student.class_ids or []) if item}
        linked = set(
            db.scalars(
                select(ClassRoom.code)
                .join(ClassMember, ClassMember.class_id == ClassRoom.id)
                .where(ClassMember.student_id == student.id, ClassRoom.status == "active")
            ).all()
        )
        return legacy | linked

    @staticmethod
    def student_problem_filter(student: User, class_codes: set[str]):
        targets = "," + Problem.target_ids + ","
        class_matches = (
            or_(*[targets.contains(f",{code},", autoescape=True) for code in class_codes]) if class_codes else false()
        )
        return and_(
            Problem.status == "published",
            or_(
                Problem.target == "all",
                and_(Problem.target == "individual", targets.contains(f",{student.external_id},", autoescape=True)),
                and_(Problem.target == "class", class_matches),
            ),
        )
