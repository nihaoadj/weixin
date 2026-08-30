import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse, WechatLoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _wechat_openid(code: str) -> str:
    settings = get_settings()
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="微信登录未配置，请设置 WECHAT_APP_ID 和 WECHAT_APP_SECRET",
        )
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{settings.wechat_api_base_url.rstrip('/')}/sns/jscode2session",
                params={
                    "appid": settings.wechat_app_id,
                    "secret": settings.wechat_app_secret,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
            if not 200 <= response.status_code < 300:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="微信登录服务暂时不可用")
            data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="微信登录服务暂时不可用") from error
    if (
        not isinstance(data, dict)
        or data.get("errcode")
        or not isinstance(data.get("openid"), str)
        or not data["openid"]
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="微信登录凭证无效")
    return data["openid"]


def _wechat_user(payload: WechatLoginRequest, db: Session) -> User:
    settings = get_settings()
    openid = _wechat_openid(payload.code)
    user = db.scalar(select(User).where(User.external_id == openid))
    if user is None:
        role = (
            "teacher"
            if payload.requested_role == "teacher" and openid in settings.wechat_teacher_openid_list
            else "student"
        )
        user = User(
            external_id=openid,
            role=role,
            nickname=payload.nickname,
            avatar_url=payload.avatar_url,
            class_ids=[],
            permissions=[],
        )
        db.add(user)
    else:
        # The role is owned by the server. A client-side role button cannot
        # change an existing account's privileges.
        user.nickname = payload.nickname
        user.avatar_url = payload.avatar_url
    db.commit()
    db.refresh(user)
    return user


@router.post("/demo-login", response_model=LoginResponse)
def demo_login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    if not get_settings().demo_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo login is disabled")
    user = db.scalar(select(User).where(User.external_id == payload.external_id))
    if user is None:
        permissions = ["medical_review"] if payload.external_id == "demo_reviewer" else []
        user = User(
            external_id=payload.external_id,
            role=payload.role,
            nickname=payload.nickname,
            avatar_url=payload.avatar_url,
            class_ids=payload.class_ids,
            permissions=permissions,
        )
        db.add(user)
    else:
        if user.role != payload.role:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Existing account role cannot be changed")
        user.nickname = payload.nickname
        user.avatar_url = payload.avatar_url
        user.class_ids = payload.class_ids
        if user.external_id == "demo_reviewer":
            user.permissions = ["medical_review"]
    db.commit()
    db.refresh(user)
    return LoginResponse(access_token=create_access_token(str(user.id)), user=user)


@router.post("/wechat-login", response_model=LoginResponse)
def wechat_login(payload: WechatLoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = _wechat_user(payload, db)
    return LoginResponse(access_token=create_access_token(str(user.id)), user=user)
