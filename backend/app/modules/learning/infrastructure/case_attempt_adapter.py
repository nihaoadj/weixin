from __future__ import annotations

from app.modules.learning.application.ports import CaseAttemptPort
from app.modules.training.public import CaseAttemptContract, TrainingCasePort
from app.shared.actor import Actor


class TrainingCaseAttemptAdapter(CaseAttemptPort):
    """Cross-module port used by learning tasks to start or resume case training."""

    def __init__(self, training: TrainingCasePort) -> None:
        self._training = training

    def start(
        self, actor: Actor, problem_id: int, retry_of_id: int | None, learning_task_id: int
    ) -> CaseAttemptContract:
        return self._training.start(actor, problem_id, retry_of_id, learning_task_id)

    def get(self, actor: Actor, attempt_id: int) -> CaseAttemptContract:
        return self._training.get(actor, attempt_id)
