from __future__ import annotations

from typing import Any, Literal

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
                "workflow_id": self._workflow_id,
                "additional_messages": private_follow_up_messages(request),
                f"{self._resource_kind}_id": self._resource_id,
            }
            if request.conversation_ref:
                parameters["conversation_id"] = request.conversation_ref
            raw, conversation_ref = completed_stream_text(self._client.workflows.chat.stream(**parameters))
            return parse_private_follow_up_json(
                raw,
                {
                    "provider": "coze",
                    "mode": "workflow",
                    "resource_id": self._workflow_id,
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
        """Use the managed workflow transport as a fresh, isolated one-shot task call."""
        try:
            task = ProviderTaskEnvelope.model_validate(envelope)
            parameters: dict[str, object] = {
                "workflow_id": self._workflow_id,
                "additional_messages": provider_task_messages(task),
            }
            parameters[f"{self._resource_kind}_id"] = self._resource_id
            raw, _ = completed_stream_text(self._client.workflows.chat.stream(**parameters))
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
