from __future__ import annotations

import httpx

from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.infrastructure.providers.coze_parser import parse_provider_json, unavailable_result
from app.modules.pbl.infrastructure.providers.request_builder import provider_messages


class OpenAICompatibleGateway:
    """Development/test adapter. It is never selected in production wiring."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int, prompt_version: str) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._prompt_version = prompt_version

    def infer(self, request: InferenceRequest) -> InferenceResult:
        try:
            response = httpx.post(
                f"{self._base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": provider_messages(request),
                    "response_format": {"type": "json_object"},
                    "thinking": {"type": "disabled"},
                    "max_tokens": 4096,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            choices = response.json().get("choices")
            if not isinstance(choices, list) or not choices:
                return unavailable_result("openai_compatible_invalid_choices")
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            raw = message.get("content") if isinstance(message, dict) else None
            if not isinstance(raw, str):
                return unavailable_result("openai_compatible_invalid_choices")
            return parse_provider_json(
                raw,
                {"provider": "openai_compatible", "prompt_version": self._prompt_version},
            )
        except httpx.TimeoutException:
            return unavailable_result("openai_compatible_timeout")
        except httpx.HTTPStatusError as error:
            return unavailable_result(f"openai_compatible_http_{error.response.status_code}")
        except httpx.HTTPError:
            return unavailable_result("openai_compatible_http_error")
        except Exception:
            return unavailable_result("openai_compatible_error")
