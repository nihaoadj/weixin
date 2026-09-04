from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.classroom.application.records import ClassRecord, ClassStudentRecord


@dataclass(frozen=True, slots=True)
class ClassroomScope:
    id: int
    code: str
    teacher_id: int
    status: str
    name: str = ""


class ClassroomScopePort(Protocol):
    def students(self, teacher_id: int, class_id: int) -> tuple[ClassStudentRecord, ...]: ...

    def owned_active(self, teacher_id: int, class_id: int) -> ClassroomScope | None: ...

    def active_class_ids_for_student(self, student_id: int) -> tuple[int, ...]: ...

    def active_member(self, student_id: int, class_id: int) -> bool: ...


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
