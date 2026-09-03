from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class UserLike(Protocol):
    id: int
    external_id: str
    role: str
    nickname: str
    class_ids: list[str] | None
    permissions: list[str] | None


@dataclass(frozen=True, slots=True)
class Actor:
    """The only identity value that application code receives from HTTP."""

    id: int
    external_id: str
    role: str
    nickname: str
    class_ids: tuple[str, ...] = ()
    permissions: frozenset[str] = frozenset()

    @classmethod
    def from_user(cls, user: UserLike) -> Actor:
        return cls(
            id=user.id,
            external_id=user.external_id,
            role=user.role,
            nickname=user.nickname,
            class_ids=tuple(item for item in (user.class_ids or []) if item),
            permissions=frozenset(item for item in (user.permissions or []) if item),
        )

    def require_role(self, role: str) -> None:
        if self.role != role:
            from app.shared.errors import AppError

            raise AppError("ROLE_REQUIRED", f"需要 {role} 角色", 403)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions
