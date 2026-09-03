from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.content.application.ports import CaseDraftAudit
from app.modules.training.infrastructure.models import AICallLog


class SqlAlchemyCaseDraftAudit(CaseDraftAudit):
    """Persist metadata only; the content application owns commit and rollback."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record_ai_call(
        self,
        *,
        user_id: int,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
    ) -> None:
        self._session.add(
            AICallLog(
                user_id=user_id,
                attempt_id=None,
                task="case_draft",
                model_name=model_name,
                prompt_version=prompt_version,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                failure_reason=failure_reason,
            )
        )


__all__ = ["SqlAlchemyCaseDraftAudit"]
