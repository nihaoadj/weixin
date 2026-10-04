from __future__ import annotations

from app.shared.actor import Actor
from app.shared.errors import AppError


class ReportPolicy:
    """Report state and visibility policy.

    T29 replaced the undecided ``submitted_global`` scope: teachers read and
    review only reports attributed to classes they own; drafts and legacy
    unattributed records stay student-only.
    """

    teacher_scope = "owned_class"

    def can_read(self, actor: Actor, student_id: int, status: str) -> bool:
        if actor.role == "student":
            return actor.id == student_id
        return actor.role == "teacher" and status in {"pending_review", "reviewed"}

    def require_student_owner(self, actor: Actor, student_id: int) -> None:
        actor.require_role("student")
        if actor.id != student_id:
            raise AppError("RESOURCE_NOT_FOUND", "报告不存在", 404)

    def require_transition(self, current: str, next_status: str) -> None:
        allowed = {
            "draft": {"pending_review"},
            "pending_review": {"reviewed"},
            "reviewed": {"reviewed"},
        }
        if next_status not in allowed.get(current, set()):
            raise AppError("STATE_CONFLICT", "报告状态不允许此操作", 409)
