from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: int
    external_id: str
    role: str
    nickname: str
    avatar_url: str
    class_ids: tuple[str, ...]
    permissions: tuple[str, ...]
    auth_provider: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DemoLoginCommand:
    role: str
    nickname: str
    external_id: str
    avatar_url: str
    class_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WechatLoginCommand:
    code: str
    nickname: str
    avatar_url: str
    requested_role: str


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    user: UserRecord
