from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import MedicalChatRequest, MedicalChatResponse
from app.services.medical_ai import create_medical_reply

router = APIRouter(prefix="/v1", tags=["ai"])


@router.post("/medical-chat", response_model=MedicalChatResponse)
def medical_chat(
    payload: MedicalChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicalChatResponse:
    return MedicalChatResponse(content=create_medical_reply(payload, user_id=user.id, db=db))
