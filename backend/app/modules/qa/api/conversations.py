from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.dependencies import require_student
from app.modules.identity.infrastructure.models import User
from app.modules.qa.api.schemas import (
    ConversationLearningContextRead,
    ConversationLearningContextWrite,
    ConversationRead,
    ConversationSummaryPage,
    ConversationUpsert,
)
from app.modules.qa.application.ports import ConversationCommand
from app.modules.qa.application.records import MessageInput
from app.modules.qa.public import conversation_summary_page_view, conversation_view
from app.modules.qa.wiring import conversations_application
from app.shared.actor import Actor
from app.shared.errors import AppError

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/summaries", response_model=ConversationSummaryPage)
def list_conversation_summaries(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    knowledge_point_code: str | None = Query(default=None, min_length=1, max_length=120),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    page = conversations_application(db).list_summaries(Actor.from_user(user), limit, offset, knowledge_point_code)
    return conversation_summary_page_view(page)


@router.get("/by-client/{client_id:path}", response_model=ConversationRead)
def get_conversation_by_client_id(
    client_id: str,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return conversation_view(conversations_application(db).get_by_client(Actor.from_user(user), client_id))


@router.get("/{conversation_id}/learning-context", response_model=ConversationLearningContextRead)
def get_conversation_learning_context(
    conversation_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    conversation = conversations_application(db).get(Actor.from_user(user), conversation_id)
    return {"conversation_id": conversation.id, "topic_codes": list(conversation.topic_codes)}


@router.put("/{conversation_id}/learning-context", response_model=ConversationLearningContextRead)
def set_conversation_learning_context(
    conversation_id: int,
    payload: ConversationLearningContextWrite,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if payload.topic_codes and not get_settings().t08_learning_context_enabled:
        raise AppError("FEATURE_DISABLED", "问答学习主题当前未开放", 409)
    conversation = conversations_application(db).set_topics(
        Actor.from_user(user), conversation_id, tuple(dict.fromkeys(payload.topic_codes))
    )
    return {"conversation_id": conversation.id, "topic_codes": list(conversation.topic_codes)}


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    knowledge_point_code: str | None = Query(default=None, min_length=1, max_length=120),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return [
        conversation_view(item)
        for item in conversations_application(db).list_full(Actor.from_user(user), knowledge_point_code)
    ]


@router.post("", response_model=ConversationRead)
def upsert_conversation(
    payload: ConversationUpsert,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if payload.topic_codes and not get_settings().t08_learning_context_enabled:
        raise AppError("FEATURE_DISABLED", "问答学习主题当前未开放", 409)
    command = ConversationCommand(
        client_id=payload.client_id,
        messages=tuple(MessageInput(role=item.role, content=item.content) for item in payload.messages),
        topic_codes=tuple(dict.fromkeys(payload.topic_codes)),
    )
    return conversation_view(conversations_application(db).upsert(Actor.from_user(user), command))


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(
    conversation_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return conversation_view(conversations_application(db).get(Actor.from_user(user), conversation_id))
