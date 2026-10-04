from __future__ import annotations

import httpx

from app.modules.pbl.application.records import (
    InferenceRequest,
    InferenceResult,
    PrivateFollowupRequest,
    PrivateFollowupResult,
)
from app.modules.pbl.infrastructure.provider_schema import ProviderTaskEnvelope
from app.modules.pbl.infrastructure.provider_tasks import ProviderTaskFailure, parse_provider_task_json
from app.modules.pbl.infrastructure.providers.coze_parser import (
    parse_private_follow_up_json,
    parse_provider_json,
    unavailable_private_follow_up,
    unavailable_result,
)
from app.modules.pbl.infrastructure.providers.request_builder import (
    private_follow_up_messages,
    provider_messages,
    provider_task_messages,
)


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
                return unavailable_result("openai_compatible_invalid_choices", request.interaction_style)
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            raw = message.get("content") if isinstance(message, dict) else None
            if not isinstance(raw, str):
                return unavailable_result("openai_compatible_invalid_choices", request.interaction_style)
            return parse_provider_json(
                raw,
                {"provider": "openai_compatible", "prompt_version": self._prompt_version},
                interaction_style=request.interaction_style,
                schema_version=request.schema_version,
            )
        except httpx.TimeoutException:
            return unavailable_result("openai_compatible_timeout", request.interaction_style)
        except httpx.HTTPStatusError as error:
            return unavailable_result(f"openai_compatible_http_{error.response.status_code}", request.interaction_style)
        except httpx.HTTPError:
            return unavailable_result("openai_compatible_http_error", request.interaction_style)
        except Exception:
            return unavailable_result("openai_compatible_error", request.interaction_style)

    def private_follow_up(self, request: PrivateFollowupRequest) -> PrivateFollowupResult:
        try:
            response = httpx.post(
                f"{self._base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": private_follow_up_messages(request),
                    "response_format": {"type": "json_object"},
                    "thinking": {"type": "disabled"},
                    "max_tokens": 4096,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            choices = response.json().get("choices")
            if not isinstance(choices, list) or not choices:
                return unavailable_private_follow_up("openai_compatible_invalid_choices", request.interaction_style)
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            raw = message.get("content") if isinstance(message, dict) else None
            if not isinstance(raw, str):
                return unavailable_private_follow_up("openai_compatible_invalid_choices", request.interaction_style)
            return parse_private_follow_up_json(
                raw,
                {"provider": "openai_compatible", "prompt_version": self._prompt_version},
                interaction_style=request.interaction_style,
            )
        except httpx.TimeoutException:
            return unavailable_private_follow_up("openai_compatible_timeout", request.interaction_style)
        except httpx.HTTPStatusError as error:
            return unavailable_private_follow_up(
                f"openai_compatible_http_{error.response.status_code}", request.interaction_style
            )
        except httpx.HTTPError:
            return unavailable_private_follow_up("openai_compatible_http_error", request.interaction_style)
        except Exception:
            return unavailable_private_follow_up("openai_compatible_error", request.interaction_style)

    def execute_task(self, envelope: dict[str, object]) -> dict[str, object]:
        """Development-only one-shot structured task call; never carries a chat conversation."""
        try:
            task = ProviderTaskEnvelope.model_validate(envelope)
            response = httpx.post(
                f"{self._base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": provider_task_messages(task),
                    "response_format": {"type": "json_object"},
                    "thinking": {"type": "disabled"},
                    "max_tokens": 8192,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            choices = response.json().get("choices")
            message = choices[0].get("message") if isinstance(choices, list) and choices else None
            raw = message.get("content") if isinstance(message, dict) else None
            if not isinstance(raw, str):
                raise ProviderTaskFailure("openai_compatible_invalid_response")
            return parse_provider_task_json(raw, task)
        except ProviderTaskFailure:
            raise
        except httpx.TimeoutException:
            raise ProviderTaskFailure("openai_compatible_timeout") from None
        except httpx.HTTPStatusError as error:
            raise ProviderTaskFailure(f"openai_compatible_http_{error.response.status_code}") from None
        except httpx.HTTPError:
            raise ProviderTaskFailure("openai_compatible_http_error") from None
        except Exception:
            raise ProviderTaskFailure("openai_compatible_error") from None
