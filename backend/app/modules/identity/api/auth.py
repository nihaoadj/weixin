from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.identity.api.schemas import LoginRequest, LoginResponse, WechatLoginRequest
from app.modules.identity.application.records import DemoLoginCommand, WechatLoginCommand
from app.modules.identity.public import login_view
from app.modules.identity.wiring import auth_application

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/demo-login", response_model=LoginResponse)
def demo_login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    result = auth_application(db).demo_login(
        DemoLoginCommand(
            role=payload.role,
            nickname=payload.nickname,
            external_id=payload.external_id,
            avatar_url=payload.avatar_url,
            class_ids=tuple(payload.class_ids),
        )
    )
    return login_view(result)


@router.post("/wechat-login", response_model=LoginResponse)
def wechat_login(payload: WechatLoginRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    result = auth_application(db).wechat_login(
        WechatLoginCommand(
            code=payload.code,
            nickname=payload.nickname,
            avatar_url=payload.avatar_url,
            requested_role=payload.requested_role,
        )
    )
    return login_view(result)
