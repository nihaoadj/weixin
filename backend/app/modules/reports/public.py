from __future__ import annotations

from app.modules.reports.application.records import MessageRecord, ReportRecord, ReportSummaryPage


def message_view(message: MessageRecord) -> dict[str, object]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }


def report_view(report: ReportRecord) -> dict[str, object]:
    return {
        "id": report.id,
        "conversation_id": report.conversation_id,
        "conversation_client_id": report.conversation_client_id,
        "student_id": report.student_id,
        "student_name": report.student_name,
        "status": report.status,
        "report_kind": "qa_learning_report",
        "ai_score": report.ai_score,
        "ai_summary": report.ai_summary,
        "analysis": report.analysis,
        "messages": [message_view(message) for message in report.messages],
        "teacher_score": report.teacher_score,
        "teacher_feedback": report.teacher_feedback,
        "reviewer_id": report.reviewer_id,
        "review_topic_codes": list(report.review_topic_codes),
        "class_id": report.class_id,
        "class_name": report.class_name,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def report_summary_page_view(page: ReportSummaryPage) -> dict[str, object]:
    return {
        "items": [
            {
                "id": item.id,
                "conversation_id": item.conversation_id,
                "conversation_client_id": item.conversation_client_id,
                "student_id": item.student_id,
                "student_name": item.student_name,
                "status": item.status,
                "report_kind": "qa_learning_report",
                "ai_score": item.ai_score,
                "teacher_score": item.teacher_score,
                "message_preview": item.message_preview,
                "message_count": item.message_count,
                "class_id": item.class_id,
                "class_name": item.class_name,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in page.items
        ],
        "total": page.total,
        "pending_count": page.pending_count,
        "reviewed_count": page.reviewed_count,
        "limit": page.limit,
        "offset": page.offset,
    }
