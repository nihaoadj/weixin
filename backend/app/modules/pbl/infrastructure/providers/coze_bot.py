from __future__ import annotations

import hashlib
from typing import Any

from app.modules.pbl.application.records import (
    InferenceRequest,
    InferenceResult,
    PrivateFollowupRequest,
    PrivateFollowupResult,
)
from app.modules.pbl.infrastructure.provider_schema import ProviderTaskEnvelope
from app.modules.pbl.infrastructure.provider_tasks import ProviderTaskFailure, parse_provider_task_json
from app.modules.pbl.infrastructure.providers.coze_events import completed_stream_text
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
                request.interaction_style,
                request.schema_version,
            )
        except TimeoutError:
            return unavailable_result("coze_timeout", request.interaction_style)
        except RuntimeError as error:
            return unavailable_result(str(error), request.interaction_style)
        except Exception:
            return unavailable_result("coze_sdk_error", request.interaction_style)

    def private_follow_up(self, request: PrivateFollowupRequest) -> PrivateFollowupResult:
        try:
            parameters: dict[str, object] = {
                "bot_id": self._bot_id,
                "user_id": request.participation_ref,
                "additional_messages": private_follow_up_messages(request),
            }
            if request.conversation_ref:
                parameters["conversation_id"] = request.conversation_ref
            raw, conversation_ref = completed_stream_text(self._client.chat.stream(**parameters))
            return parse_private_follow_up_json(
                raw,
                {
                    "provider": "coze",
                    "mode": "bot",
                    "resource_id": self._bot_id,
                    "prompt_version": self._prompt_version,
                },
                conversation_ref or request.conversation_ref,
                request.interaction_style,
            )
        except TimeoutError:
            return unavailable_private_follow_up("coze_timeout", request.interaction_style)
        except RuntimeError as error:
            return unavailable_private_follow_up(str(error), request.interaction_style)
        except Exception:
            return unavailable_private_follow_up("coze_sdk_error", request.interaction_style)

    def execute_task(self, envelope: dict[str, object]) -> dict[str, object]:
        """Use the managed bot transport as a fresh, isolated one-shot task call."""
        try:
            task = ProviderTaskEnvelope.model_validate(envelope)
            raw, _ = completed_stream_text(
                self._client.chat.stream(
                    bot_id=self._bot_id,
                    user_id=f"pbl-task-{hashlib.sha256(task.request_id.encode()).hexdigest()[:24]}",
                    additional_messages=provider_task_messages(task),
                )
            )
            return parse_provider_task_json(raw, task)
        except ProviderTaskFailure:
            raise
        except TimeoutError:
            raise ProviderTaskFailure("coze_timeout") from None
        except RuntimeError as error:
            code = (
                error.args[0]
                if error.args and error.args[0] in {"coze_interrupted", "coze_incomplete_stream"}
                else "coze_sdk_error"
            )
            raise ProviderTaskFailure(code) from None
        except Exception:
            raise ProviderTaskFailure("coze_sdk_error") from None
