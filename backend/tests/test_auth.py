import httpx
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db import Base, engine
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_wechat_login_exchanges_code_on_server_and_returns_token(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "wechat_app_id", "wx-test-app")
    monkeypatch.setattr(settings, "wechat_app_secret", "server-only-secret")

    def fake_get(_client, url, *, params):
        assert url == "https://api.weixin.qq.com/sns/jscode2session"
        assert params["appid"] == "wx-test-app"
        assert params["secret"] == "server-only-secret"
        assert params["js_code"] == "one-time-code"
        return httpx.Response(200, json={"openid": "wx-student-1", "session_key": "not-returned"})

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    response = client.post(
        "/auth/wechat-login",
        json={
            "code": "one-time-code",
            "nickname": "微信学生",
            "avatar_url": "https://example.com/avatar.png",
            "requested_role": "student",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "student"
    assert body["user"]["nickname"] == "微信学生"
    assert "session_key" not in body
    assert body["access_token"]


def test_wechat_login_does_not_allow_client_role_escalation(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "wechat_app_id", "wx-test-app")
    monkeypatch.setattr(settings, "wechat_app_secret", "server-only-secret")
    monkeypatch.setattr(httpx.Client, "get", lambda *_args, **_kwargs: httpx.Response(200, json={"openid": "wx-2"}))

    first = client.post(
        "/auth/wechat-login",
        json={"code": "first", "nickname": "学生", "requested_role": "student"},
    )
    second = client.post(
        "/auth/wechat-login",
        json={"code": "second", "nickname": "冒充教师", "requested_role": "teacher"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["user"]["role"] == "student"


def test_wechat_login_fails_closed_when_not_configured(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "wechat_app_id", "")
    monkeypatch.setattr(settings, "wechat_app_secret", "")

    response = client.post("/auth/wechat-login", json={"code": "one-time-code"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_ERROR"
    assert "WECHAT_APP_ID" in response.json()["detail"]["message"]
