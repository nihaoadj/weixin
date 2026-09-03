"""Compatibility facade for the QA medical-chat application boundary."""

from __future__ import annotations

from app.modules.identity.infrastructure.models import User
from app.modules.qa.application.records import ChatHistoryMessage, MedicalChatRequestRecord
from app.modules.qa.domain.safety import fallback_reply, is_emergency
from app.modules.qa.infrastructure.medical_chat_gateway import MedicalChatHttpGateway
from app.modules.qa.wiring import medical_chat_application
from app.shared.actor import Actor


def create_medical_reply(request, user_id: int | None = None, db=None) -> str:
    record = MedicalChatRequestRecord(
        prompt=request.prompt,
        mode=request.mode,
        messages=tuple(ChatHistoryMessage(role=item.role, content=item.content) for item in request.messages),
    )
    if db is not None and user_id is not None:
        user = db.get(User, user_id)
        if user is None:
            raise ValueError("user not found")
        result = medical_chat_application(db).reply(Actor.from_user(user), record)
    else:
        result = MedicalChatHttpGateway().reply(record)
    return result.content


__all__ = ["create_medical_reply", "fallback_reply", "is_emergency"]
