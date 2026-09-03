from __future__ import annotations

from app.shared.actor import Actor
from app.shared.errors import AppError


class ClassroomPolicy:
    @staticmethod
    def require_teacher(actor: Actor) -> None:
        actor.require_role("teacher")

    @staticmethod
    def require_owner(actor: Actor, teacher_id: int) -> None:
        if actor.id != teacher_id:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)

    @staticmethod
    def require_active(status: str) -> None:
        if status != "active":
            raise AppError("STATE_CONFLICT", "班级已归档", 409)
