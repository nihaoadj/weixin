from __future__ import annotations

from app.shared.actor import Actor
from app.shared.errors import AppError


class ContentPolicy:
    """Pure ownership, visibility and publication decisions for content."""

    @staticmethod
    def require_teacher(actor: Actor) -> None:
        actor.require_role("teacher")

    @staticmethod
    def require_owner(actor: Actor, author_id: int | None) -> None:
        if author_id != actor.id:
            raise AppError("RESOURCE_NOT_FOUND", "内容不存在", 404)

    @staticmethod
    def is_visible_to_student(
        *,
        status: str,
        target: str,
        target_ids: tuple[str, ...],
        student_external_id: str,
        class_codes: set[str],
    ) -> bool:
        if status != "published":
            return False
        if target == "all":
            return True
        if target == "individual":
            return student_external_id in target_ids
        if target == "class":
            return bool(set(target_ids).intersection(class_codes))
        return False

    @staticmethod
    def require_publishable_case(case_definition: dict[str, object] | None, rubric: dict[str, object] | None) -> None:
        if not case_definition or not rubric:
            raise AppError("VALIDATION_ERROR", "Guided case requires definition and rubric", 422)

    @staticmethod
    def require_review_approved(review_status: str) -> None:
        if review_status != "approved":
            raise AppError("STATE_CONFLICT", "Medical review approval required", 409)
