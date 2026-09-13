"""PBL stable contracts are exposed through API and wiring only."""

from app.modules.pbl.application.ports import PblInferenceGateway

__all__ = ["PblInferenceGateway"]

from typing import Protocol


class StudyDialoguePort(Protocol):
    def start(self, student_id: int, point_code: str, client_id: str, style: str) -> int: ...
    def state(self, student_id: int, session_id: int) -> dict: ...


class PracticeJsonPort(Protocol):
    def practice_json(self, context: dict, schema: dict) -> str: ...
