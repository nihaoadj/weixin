import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


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


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503, json={"errcode": 1}),
        httpx.Response(200, json={"errcode": 40029}),
        httpx.Response(200, json={"openid": ""}),
        httpx.Response(200, json=[]),
    ],
)
def test_wechat_login_rejects_provider_status_and_invalid_identity_payloads(monkeypatch, response) -> None:
    _enable_wechat(monkeypatch, "unused")
    monkeypatch.setattr(httpx.Client, "get", lambda *_args, **_kwargs: response)

    result = client.post("/auth/wechat-login", json={"code": "bad-provider-response"})

    assert result.status_code in {401, 502}
    assert result.json()["detail"]["code"] in {"AUTH_REQUIRED", "SERVICE_ERROR"}


def test_wechat_login_maps_provider_transport_failure_without_exposing_provider_detail(monkeypatch) -> None:
    _enable_wechat(monkeypatch, "unused")
    monkeypatch.setattr(
        httpx.Client, "get", lambda *_args, **_kwargs: (_ for _ in ()).throw(httpx.ConnectError("secret"))
    )

    result = client.post("/auth/wechat-login", json={"code": "network-failure"})

    assert (result.status_code, result.json()["detail"]["code"]) == (502, "SERVICE_ERROR")
    assert "secret" not in result.json()["detail"]["message"]


def _enable_wechat(monkeypatch, openid: str) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "wechat_app_id", "wx-test-app")
    monkeypatch.setattr(settings, "wechat_app_secret", "server-only-secret")
    monkeypatch.setattr(httpx.Client, "get", lambda *_args, **_kwargs: httpx.Response(200, json={"openid": openid}))


def test_demo_login_cannot_impersonate_wechat_account(monkeypatch) -> None:
    _enable_wechat(monkeypatch, "wx-real-student")
    created = client.post(
        "/auth/wechat-login",
        json={"code": "one-time-code", "nickname": "微信学生", "requested_role": "student"},
    )
    assert created.status_code == 200

    response = client.post(
        "/auth/demo-login",
        json={"role": "student", "external_id": "wx-real-student", "nickname": "冒充者", "avatar_url": ""},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STATE_CONFLICT"


def test_wechat_login_adopts_legacy_account_without_inheriting_demo_privileges(monkeypatch) -> None:
    # 攻击者先用 demo-login 抢注受害者 openid（教师角色）。
    hijack = client.post(
        "/auth/demo-login",
        json={"role": "teacher", "external_id": "wx-victim-openid", "nickname": "抢注", "avatar_url": ""},
    )
    assert hijack.status_code == 200

    # 受害者通过微信登录：账号被收编，角色由服务端白名单重新裁定为 student。
    _enable_wechat(monkeypatch, "wx-victim-openid")
    adopted = client.post(
        "/auth/wechat-login",
        json={"code": "one-time-code", "nickname": "受害者", "requested_role": "teacher"},
    )
    assert adopted.status_code == 200
    assert adopted.json()["user"]["role"] == "student"

    # 收编后 demo 通道失效，攻击者无法再用 demo-login 进入该账号。
    again = client.post(
        "/auth/demo-login",
        json={"role": "teacher", "external_id": "wx-victim-openid", "nickname": "抢注", "avatar_url": ""},
    )
    assert again.status_code == 409
