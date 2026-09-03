from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.application.use_cases import AuthApplication
from app.modules.identity.domain.policy import AuthPolicy
from app.modules.identity.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.identity.infrastructure.transport import JwtTokenIssuer, WechatHttpGateway
from app.platform.transactions import SqlAlchemyUnitOfWork


def auth_application(session: Session) -> AuthApplication:
    settings = get_settings()
    return AuthApplication(
        users=SqlAlchemyUserRepository(session),
        wechat=WechatHttpGateway(),
        tokens=JwtTokenIssuer(),
        uow=SqlAlchemyUnitOfWork(session),
        demo_enabled=settings.demo_auth_enabled,
        teacher_openids=settings.wechat_teacher_openid_list,
        policy=AuthPolicy(),
    )
