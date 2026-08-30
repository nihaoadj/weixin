import httpx

from app.core.config import get_settings
from app.schemas.case_training import PatientReplyModel
from app.services.case_ai import call_structured


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "mock error", request=httpx.Request("POST", "http://mock"), response=httpx.Response(self.status_code)
            )

    def json(self) -> dict:
        return self.payload


def _enable_ai(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_base_url", "http://mock")
    monkeypatch.setattr(settings, "ai_api_key", "test-key")
    monkeypatch.setattr(settings, "ai_model", "test-model")
    monkeypatch.setattr(settings, "ai_timeout_seconds", 1)


def test_structured_call_success_and_request_contract(monkeypatch) -> None:
    _enable_ai(monkeypatch)
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({"choices": [{"message": {"content": '{"reply":"已了解。"}'}}]})

    monkeypatch.setattr("app.services.case_ai.httpx.post", fake_post)
    result = call_structured("patient_reply", [{"role": "user", "content": "hello"}], PatientReplyModel, 0.2)
    assert result.value is not None
    assert result.value.reply == "已了解。"
    assert calls[0][0] == "http://mock/chat/completions"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0][1]["json"]["temperature"] == 0.2


def test_structured_call_retries_invalid_json(monkeypatch) -> None:
    _enable_ai(monkeypatch)
    calls = iter(
        [
            FakeResponse({"choices": [{"message": {"content": "not-json"}}]}),
            FakeResponse({"choices": [{"message": {"content": "still-not-json"}}]}),
        ]
    )
    monkeypatch.setattr("app.services.case_ai.httpx.post", lambda *args, **kwargs: next(calls))
    result = call_structured("patient_reply", [], PatientReplyModel, 0.2)
    assert result.value is None
    assert result.failure_reason in {"invalid_json", "schema_error"}


def test_structured_call_disabled_and_http_error(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_enabled", False)
    disabled = call_structured("patient_reply", [], PatientReplyModel, 0.2)
    assert disabled.failure_reason == "disabled"
    _enable_ai(monkeypatch)
    monkeypatch.setattr("app.services.case_ai.httpx.post", lambda *args, **kwargs: FakeResponse({}, 500))
    failed = call_structured("patient_reply", [], PatientReplyModel, 0.2)
    assert failed.failure_reason == "http_error"
