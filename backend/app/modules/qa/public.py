from __future__ import annotations

from app.modules.qa.application.records import (
    ConversationRecord,
    ConversationSummaryPage,
    MessageRecord,
    QuestionThreadRecord,
    StudentQuestionRecord,
)


def message_view(message: MessageRecord) -> dict[str, object]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }


def conversation_view(conversation: ConversationRecord) -> dict[str, object]:
    return {
        "id": conversation.id,
        "client_id": conversation.client_id,
        "student_id": conversation.student_id,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": [message_view(item) for item in conversation.messages],
        "topic_codes": list(conversation.topic_codes),
    }


def conversation_summary_page_view(page: ConversationSummaryPage) -> dict[str, object]:
    return {
        "items": [
            {
                "id": item.id,
                "client_id": item.client_id,
                "message_preview": item.message_preview,
                "message_count": item.message_count,
                "report_id": item.report_id,
                "report_status": item.report_status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "topic_codes": list(item.topic_codes),
            }
            for item in page.items
        ],
        "total": page.total,
        "limit": page.limit,
        "offset": page.offset,
    }


def student_question_view(question: StudentQuestionRecord) -> dict[str, object]:
    return {
        "id": question.id,
        "type": question.type,
        "title": question.title,
        "description": question.description,
        "published_at": question.published_at,
        "status": "answered" if question.answered else "unanswered",
        "topic_codes": list(question.topic_codes),
    }


def question_thread_view(thread: QuestionThreadRecord) -> dict[str, object]:
    return {
        "question_id": thread.question_id,
        "messages": [message_view(item) for item in thread.messages],
        "updated_at": thread.updated_at,
    }
