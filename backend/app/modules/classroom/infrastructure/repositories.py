from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.classroom.application.ports import ClassroomRepository
from app.modules.classroom.application.records import (
    ClassCommand,
    ClassRecord,
    ClassStudentRecord,
    ClassUpdateCommand,
    TeachingMemberScope,
)
from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.identity.infrastructure.models import User
from app.shared.errors import PersistenceConflict


class SqlAlchemyClassroomRepository(ClassroomRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _record(classroom: ClassRoom) -> ClassRecord:
        return ClassRecord(
            id=classroom.id,
            name=classroom.name,
            code=classroom.code,
            status=classroom.status,
            teacher_id=classroom.teacher_id,
            created_at=classroom.created_at,
        )

    def list_for_teacher(self, teacher_id: int) -> tuple[ClassRecord, ...]:
        return tuple(
            self._record(item)
            for item in self._session.scalars(
                select(ClassRoom).where(ClassRoom.teacher_id == teacher_id).order_by(ClassRoom.id)
            ).all()
        )

    def create(self, teacher_id: int, command: ClassCommand) -> ClassRecord:
        classroom = ClassRoom(name=command.name, code=command.code, teacher_id=teacher_id)
        self._session.add(classroom)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return self._record(classroom)

    def find_owned(self, class_id: int, teacher_id: int) -> ClassRecord | None:
        classroom = self._session.scalar(
            select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id)
        )
        return self._record(classroom) if classroom is not None else None

    def update(self, class_id: int, command: ClassUpdateCommand) -> ClassRecord:
        classroom = self._session.get(ClassRoom, class_id)
        if classroom is None:
            raise LookupError("class disappeared")
        if command.name is not None:
            classroom.name = command.name
        if command.status is not None:
            classroom.status = command.status
        self._session.flush()
        return self._record(classroom)

    def list_students(self, class_id: int) -> tuple[ClassStudentRecord, ...]:
        rows = self._session.execute(
            select(User, ClassMember.joined_at)
            .join(ClassMember, ClassMember.student_id == User.id)
            .where(ClassMember.class_id == class_id)
            .order_by(User.id)
        ).all()
        return tuple(
            ClassStudentRecord(id=user.id, nickname=user.nickname, external_id=user.external_id, joined_at=joined_at)
            for user, joined_at in rows
        )

    def teaching_members(self, teacher_id: int) -> tuple[TeachingMemberScope, ...]:
        rows = self._session.execute(
            select(ClassRoom.id, ClassRoom.name, ClassRoom.status, User.id, User.nickname)
            .join(ClassMember, ClassMember.class_id == ClassRoom.id)
            .join(User, User.id == ClassMember.student_id)
            .where(ClassRoom.teacher_id == teacher_id)
            .order_by(ClassRoom.id, User.id)
        )
        return tuple(TeachingMemberScope(*row) for row in rows)

    def student_exists(self, student_id: int) -> bool:
        return self._session.scalar(select(User.id).where(User.id == student_id, User.role == "student")) is not None

    def student_id_by_external_id(self, external_id: str) -> int | None:
        return self._session.scalar(select(User.id).where(User.external_id == external_id, User.role == "student"))

    def member_exists(self, class_id: int, student_id: int) -> bool:
        return (
            self._session.scalar(
                select(ClassMember.id).where(ClassMember.class_id == class_id, ClassMember.student_id == student_id)
            )
            is not None
        )

    def add_member(self, class_id: int, student_id: int) -> None:
        self._session.add(ClassMember(class_id=class_id, student_id=student_id))
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error

    def remove_member(self, class_id: int, student_id: int) -> None:
        member = self._session.scalar(
            select(ClassMember).where(ClassMember.class_id == class_id, ClassMember.student_id == student_id)
        )
        if member is not None:
            self._session.delete(member)
            self._session.flush()
