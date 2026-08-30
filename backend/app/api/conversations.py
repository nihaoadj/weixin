from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.dependencies import require_student
from app.models import Conversation, Message, Report, User
from app.schemas import ConversationRead, ConversationSummaryPage, ConversationUpsert

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/summaries", response_model=ConversationSummaryPage)
def list_conversation_summaries(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    message_count = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    message_preview = (
        select(func.substr(Message.content, 1, 160))
        .where(Message.conversation_id == Conversation.id)
        .order_by(Message.id.asc())
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    total = db.scalar(select(func.count(Conversation.id)).where(Conversation.student_id == user.id)) or 0
    rows = db.execute(
        select(Conversation, message_preview, message_count, Report.id, Report.status)
        .outerjoin(Report, Report.conversation_id == Conversation.id)
        .where(Conversation.student_id == user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [
            {
                "id": conversation.id,
                "client_id": conversation.client_id,
                "message_preview": preview or "",
                "message_count": count or 0,
                "report_id": report_id,
                "report_status": report_status,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
            }
            for conversation, preview, count, report_id, report_status in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/by-client/{client_id:path}", response_model=ConversationRead)
def get_conversation_by_client_id(
    client_id: str,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.client_id == client_id, Conversation.student_id == user.id)
        .options(selectinload(Conversation.messages))
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


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
    conversation.updated_at = datetime.now(UTC)
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
