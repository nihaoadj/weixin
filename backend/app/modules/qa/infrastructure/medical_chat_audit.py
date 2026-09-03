from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.qa.application.ports import MedicalChatAudit
from app.modules.training.infrastructure.models import AICallLog


class SqlAlchemyMedicalChatAudit(MedicalChatAudit):
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_ai_call(
        self,
        *,
        user_id: int | None,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
    ) -> None:
        self._session.add(
            AICallLog(
                user_id=user_id,
                task="medical_chat",
                model_name=model_name,
                prompt_version=prompt_version,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                failure_reason=failure_reason,
            )
        )
