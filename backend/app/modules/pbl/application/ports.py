from typing import Protocol

from app.modules.pbl.application.records import InferenceRequest, InferenceResult


class PblInferenceGateway(Protocol):
    def infer(self, request: InferenceRequest) -> InferenceResult: ...
