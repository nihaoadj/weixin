from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.dependencies import require_student
from app.models import Conversation, Message, User
from app.schemas import ConversationRead, ConversationUpsert

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
def list_conversations(user: User = Depends(require_student), db: Session = Depends(get_db)) -> list[Conversation]:
    statement = (
        select(Conversation)
        .where(Conversation.student_id == user.id)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post("", response_model=ConversationRead)
def upsert_conversation(
    payload: ConversationUpsert,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.client_id == payload.client_id, Conversation.student_id == user.id)
        .options(selectinload(Conversation.messages))
    )
    if conversation is None:
        conversation = Conversation(client_id=payload.client_id, student_id=user.id)
        db.add(conversation)
        db.flush()
    conversation.messages.clear()
    db.flush()
    for message in payload.messages:
        conversation.messages.append(Message(role=message.role, content=message.content))
    db.commit()
    return db.scalar(
        select(Conversation).where(Conversation.id == conversation.id).options(selectinload(Conversation.messages))
    )


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(
    conversation_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(Conversation.id == conversation_id).options(selectinload(Conversation.messages))
    )
    if conversation is None or conversation.student_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation
