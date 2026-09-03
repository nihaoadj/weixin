from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.application.ports import UserRepository
from app.modules.identity.application.records import DemoLoginCommand, UserRecord
from app.modules.identity.infrastructure.models import User


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _record(user: User) -> UserRecord:
        return UserRecord(
            id=user.id,
            external_id=user.external_id,
            role=user.role,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            class_ids=tuple(user.class_ids or []),
            permissions=tuple(user.permissions or []),
            auth_provider=user.auth_provider,
            created_at=user.created_at,
        )

    def _user(self, external_id: str, auth_provider: str | None = None) -> User | None:
        statement = select(User).where(User.external_id == external_id)
        if auth_provider is not None:
            statement = statement.where(User.auth_provider == auth_provider)
        return self._session.scalar(statement)

    def find_by_external_id(self, external_id: str, auth_provider: str | None = None) -> UserRecord | None:
        user = self._user(external_id, auth_provider)
        return self._record(user) if user is not None else None

    def create_demo(self, command: DemoLoginCommand, permissions: tuple[str, ...]) -> UserRecord:
        user = User(
            external_id=command.external_id,
            role=command.role,
            nickname=command.nickname,
            avatar_url=command.avatar_url,
            class_ids=list(command.class_ids),
            permissions=list(permissions),
            auth_provider="demo",
        )
        self._session.add(user)
        self._session.flush()
        return self._record(user)

    def update_demo(self, user_id: int, command: DemoLoginCommand, permissions: tuple[str, ...]) -> UserRecord:
        user = self._session.get(User, user_id)
        if user is None:
            raise LookupError("demo account disappeared")
        user.nickname = command.nickname
        user.avatar_url = command.avatar_url
        user.class_ids = list(command.class_ids)
        user.permissions = list(permissions)
        self._session.flush()
        return self._record(user)

    def adopt_wechat(self, external_id: str, nickname: str, avatar_url: str, role: str) -> UserRecord:
        user = self._user(external_id)
        if user is None:
            user = User(
                external_id=external_id,
                role=role,
                nickname=nickname,
                avatar_url=avatar_url,
                class_ids=[],
                permissions=[],
                auth_provider="wechat",
            )
            self._session.add(user)
        else:
            user.auth_provider = "wechat"
            user.role = role
            user.permissions = []
            user.nickname = nickname
            user.avatar_url = avatar_url
        self._session.flush()
        return self._record(user)
