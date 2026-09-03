from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.modules.identity.infrastructure.models import User
from app.modules.qa.api.medical_schemas import MedicalChatRequest, MedicalChatResponse
from app.modules.qa.application.records import ChatHistoryMessage, MedicalChatRequestRecord
from app.modules.qa.wiring import medical_chat_application
from app.shared.actor import Actor

router = APIRouter(prefix="/v1", tags=["ai"])


@router.post("/medical-chat", response_model=MedicalChatResponse)
def medical_chat(
    payload: MedicalChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicalChatResponse:
    result = medical_chat_application(db).reply(
        Actor.from_user(user),
        MedicalChatRequestRecord(
            prompt=payload.prompt,
            mode=payload.mode,
            messages=tuple(ChatHistoryMessage(role=item.role, content=item.content) for item in payload.messages),
            topic_codes=tuple(dict.fromkeys(payload.topic_codes)),
        ),
    )
    return MedicalChatResponse(content=result.content)
