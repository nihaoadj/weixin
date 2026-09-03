from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.security import create_access_token
from app.modules.identity.application.ports import TokenIssuer, WechatGateway
from app.shared.errors import AppError


class WechatHttpGateway(WechatGateway):
    def exchange_code(self, code: str) -> str:
        settings = get_settings()
        if not settings.wechat_app_id or not settings.wechat_app_secret:
            raise AppError("SERVICE_ERROR", "微信登录未配置，请设置 WECHAT_APP_ID 和 WECHAT_APP_SECRET", 503)
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
                    raise AppError("SERVICE_ERROR", "微信登录服务暂时不可用", 502)
                data = response.json()
        except AppError:
            raise
        except (httpx.HTTPError, ValueError) as error:
            raise AppError("SERVICE_ERROR", "微信登录服务暂时不可用", 502) from error
        if (
            not isinstance(data, dict)
            or data.get("errcode")
            or not isinstance(data.get("openid"), str)
            or not data["openid"]
        ):
            raise AppError("AUTH_REQUIRED", "微信登录凭证无效", 401)
        return data["openid"]


class JwtTokenIssuer(TokenIssuer):
    def issue(self, user_id: int) -> str:
        return create_access_token(str(user_id))
