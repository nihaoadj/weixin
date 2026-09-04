from __future__ import annotations

from typing import Any

from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.infrastructure.providers.coze_events import completed_stream_text
from app.modules.pbl.infrastructure.providers.coze_parser import parse_provider_json, unavailable_result
from app.modules.pbl.infrastructure.providers.request_builder import provider_messages


class CozeBotGateway:
    def __init__(self, client: Any, bot_id: str, prompt_version: str) -> None:
        self._client = client
        self._bot_id = bot_id
        self._prompt_version = prompt_version

    def infer(self, request: InferenceRequest) -> InferenceResult:
        try:
            parameters: dict[str, object] = {
                "bot_id": self._bot_id,
                "user_id": request.anonymous_user_ref or f"pbl-{request.session_id}",
                "additional_messages": provider_messages(request),
            }
            if request.conversation_ref:
                parameters["conversation_id"] = request.conversation_ref
            raw, conversation_ref = completed_stream_text(self._client.chat.stream(**parameters))
            return parse_provider_json(
                raw,
                {
                    "provider": "coze",
                    "mode": "bot",
                    "resource_id": self._bot_id,
                    "prompt_version": self._prompt_version,
                },
                conversation_ref or request.conversation_ref,
            )
        except TimeoutError:
            return unavailable_result("coze_timeout")
        except RuntimeError as error:
            return unavailable_result(str(error))
        except Exception:
            return unavailable_result("coze_sdk_error")
