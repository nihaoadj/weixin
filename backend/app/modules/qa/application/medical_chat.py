from __future__ import annotations

from app.modules.content.public import KnowledgeCatalogPort
from app.modules.qa.application.ports import MedicalChatAudit, MedicalChatGateway
from app.modules.qa.application.records import MedicalChatRequestRecord, MedicalChatResult
from app.shared.actor import Actor
from app.shared.errors import AppError
from app.shared.uow import UnitOfWork


class MedicalChatApplication:
    def __init__(
        self,
        gateway: MedicalChatGateway,
        audit: MedicalChatAudit,
        uow: UnitOfWork,
        knowledge_catalog: KnowledgeCatalogPort,
    ) -> None:
        self._gateway = gateway
        self._audit = audit
        self._uow = uow
        self._knowledge_catalog = knowledge_catalog

    def reply(self, actor: Actor, request: MedicalChatRequestRecord) -> MedicalChatResult:
        if len(request.topic_codes) > 3 or not self._knowledge_catalog.contains_points(request.topic_codes):
            raise AppError("VALIDATION_ERROR", "学习主题不存在或数量超限", 422)
        result = self._gateway.reply(request)
        if result.failure_reason != "emergency":
            try:
                self._audit.record_ai_call(
                    user_id=actor.id,
                    model_name=result.model_name,
                    prompt_version=result.prompt_version,
                    latency_ms=result.latency_ms,
                    fallback_used=result.fallback_used,
                    failure_reason=result.failure_reason,
                )
                self._uow.commit()
            except Exception as error:
                self._uow.rollback()
                raise AppError("SERVICE_ERROR", "AI audit is temporarily unavailable", 503) from error
        return result
