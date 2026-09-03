from __future__ import annotations

from app.modules.identity.application.ports import TokenIssuer, UserRepository, WechatGateway
from app.modules.identity.application.records import DemoLoginCommand, LoginResult, WechatLoginCommand
from app.modules.identity.domain.policy import AuthPolicy
from app.shared.errors import AppError
from app.shared.uow import UnitOfWork


class AuthApplication:
    def __init__(
        self,
        users: UserRepository,
        wechat: WechatGateway,
        tokens: TokenIssuer,
        uow: UnitOfWork,
        *,
        demo_enabled: bool,
        teacher_openids: set[str],
        policy: AuthPolicy | None = None,
    ) -> None:
        self._users = users
        self._wechat = wechat
        self._tokens = tokens
        self._uow = uow
        self._demo_enabled = demo_enabled
        self._teacher_openids = teacher_openids
        self._policy = policy or AuthPolicy()

    def demo_login(self, command: DemoLoginCommand) -> LoginResult:
        if not self._demo_enabled:
            raise AppError("RESOURCE_NOT_FOUND", "Demo login is disabled", 404)
        user = self._users.find_by_external_id(command.external_id)
        if user is not None and not self._policy.can_demo_login(user.auth_provider):
            raise AppError("STATE_CONFLICT", "该账号不属于演示登录，请使用正式登录方式", 409)
        permissions = self._policy.demo_permissions(command.external_id)
        if user is None:
            user = self._users.create_demo(command, permissions)
        else:
            if user.role != command.role:
                raise AppError("STATE_CONFLICT", "Existing account role cannot be changed", 409)
            user = self._users.update_demo(user.id, command, permissions)
        self._uow.commit()
        return LoginResult(self._tokens.issue(user.id), user)

    def wechat_login(self, command: WechatLoginCommand) -> LoginResult:
        openid = self._wechat.exchange_code(command.code)
        role = self._policy.wechat_role(openid, command.requested_role, self._teacher_openids)
        user = self._users.find_by_external_id(openid, "wechat")
        if user is None:
            # A pre-0009/demo legacy row is deliberately adopted and stripped of
            # client-controlled role/permissions by the repository adapter.
            user = self._users.find_by_external_id(openid)
        user = self._users.adopt_wechat(openid, command.nickname, command.avatar_url, role)
        self._uow.commit()
        return LoginResult(self._tokens.issue(user.id), user)
