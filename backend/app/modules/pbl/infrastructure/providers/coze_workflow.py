from __future__ import annotations

from typing import Any, Literal

from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.infrastructure.providers.coze_events import completed_stream_text
from app.modules.pbl.infrastructure.providers.coze_parser import parse_provider_json, unavailable_result
from app.modules.pbl.infrastructure.providers.request_builder import provider_messages


class CozeWorkflowGateway:
    def __init__(
        self,
        client: Any,
        workflow_id: str,
        resource_id: str,
        resource_kind: Literal["app", "bot"],
        prompt_version: str,
    ) -> None:
        self._client = client
        self._workflow_id = workflow_id
        self._resource_id = resource_id
        self._resource_kind = resource_kind
        self._prompt_version = prompt_version

    def infer(self, request: InferenceRequest) -> InferenceResult:
        try:
            parameters: dict[str, object] = {
                "workflow_id": self._workflow_id,
                "additional_messages": provider_messages(request),
                f"{self._resource_kind}_id": self._resource_id,
            }
            if request.conversation_ref:
                parameters["conversation_id"] = request.conversation_ref
            raw, conversation_ref = completed_stream_text(self._client.workflows.chat.stream(**parameters))
            return parse_provider_json(
                raw,
                {
                    "provider": "coze",
                    "mode": "workflow",
                    "resource_id": self._workflow_id,
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
