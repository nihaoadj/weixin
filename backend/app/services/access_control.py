from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClassMember, ClassRoom, Problem, User


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


def is_problem_visible_to_student(problem: Problem, student: User, db: Session | None = None) -> bool:
    if student.role != "student" or problem.status != "published":
        return False
    if problem.target == "all":
        return True
    target_ids = {item for item in problem.target_ids.split(",") if item}
    if problem.target == "individual":
        return student.external_id in target_ids
    if problem.target == "class":
        class_codes = student_class_codes(db, student) if db is not None else set(student.class_ids or [])
        return bool(target_ids.intersection(class_codes))
    return False


def ensure_report_transition(current_status: str, next_status: str) -> None:
    allowed = {
        "draft": {"pending_review"},
        "pending_review": {"reviewed"},
        "reviewed": {"reviewed"},
    }
    if next_status not in allowed.get(current_status, set()):
        raise ValueError(f"Report cannot transition from {current_status} to {next_status}")
