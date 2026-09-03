from __future__ import annotations

from app.modules.classroom.application.records import ClassRecord, ClassStudentRecord


def class_view(item: ClassRecord) -> dict[str, object]:
    return {
        "id": item.id,
        "name": item.name,
        "code": item.code,
        "status": item.status,
        "teacher_id": item.teacher_id,
        "created_at": item.created_at,
    }


def student_view(item: ClassStudentRecord) -> dict[str, object]:
    return {
        "id": item.id,
        "nickname": item.nickname,
        "external_id": item.external_id,
        "joined_at": item.joined_at,
    }
