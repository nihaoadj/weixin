import httpx

from app.core.config import get_settings
from app.schemas import MedicalChatRequest
from app.services.medical_ai import create_medical_reply


def test_configured_medical_model_reply_is_server_side(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_base_url", "https://ai.example.com/v1")
    monkeypatch.setattr(settings, "ai_api_key", "server-only-key")
    monkeypatch.setattr(settings, "ai_model", "medical-model")
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return httpx.Response(200, json={"choices": [{"message": {"content": "模型教学回答"}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    response = create_medical_reply(
        MedicalChatRequest(
            prompt="肺炎如何鉴别",
            messages=[{"role": "user", "content": "先说明定义"}],
        )
    )

    assert response == "模型教学回答"
    assert len(calls) == 1
    assert calls[0][0] == "https://ai.example.com/v1/chat/completions"
    assert calls[0][1]["Authorization"] == "Bearer server-only-key"
    assert calls[0][2]["messages"][-1] == {"role": "user", "content": "肺炎如何鉴别"}


def test_medical_model_failure_retries_then_uses_safe_fallback(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_base_url", "https://ai.example.com/v1")
    monkeypatch.setattr(settings, "ai_api_key", "server-only-key")
    monkeypatch.setattr(settings, "ai_model", "medical-model")
    calls = 0

    def fake_post(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": "unavailable"})

    monkeypatch.setattr(httpx, "post", fake_post)
    response = create_medical_reply(MedicalChatRequest(prompt="肺炎有哪些典型症状"))

    assert calls == 2
    assert response.startswith("演示反馈：")
