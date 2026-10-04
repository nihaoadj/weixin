from __future__ import annotations

from typing import Protocol

from app.modules.identity.application.records import (
    DemoLoginCommand,
    UserRecord,
)


class UserRepository(Protocol):
    def find_by_external_id(self, external_id: str, auth_provider: str | None = None) -> UserRecord | None: ...

    def create_demo(self, command: DemoLoginCommand, permissions: tuple[str, ...]) -> UserRecord: ...

    def update_demo(self, user_id: int, command: DemoLoginCommand, permissions: tuple[str, ...]) -> UserRecord: ...

    def adopt_wechat(self, external_id: str, nickname: str, avatar_url: str, role: str) -> UserRecord: ...


class WechatGateway(Protocol):
    def exchange_code(self, code: str) -> str: ...


class TokenIssuer(Protocol):
    def issue(self, user_id: int) -> str: ...
