from __future__ import annotations

from app.modules.identity.application.records import LoginResult, UserRecord


def user_view(user: UserRecord) -> dict[str, object]:
    return {
        "id": user.id,
        "role": user.role,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "class_ids": list(user.class_ids),
        "permissions": list(user.permissions),
        "created_at": user.created_at,
    }


def login_view(result: LoginResult) -> dict[str, object]:
    return {"access_token": result.access_token, "token_type": "bearer", "user": user_view(result.user)}
