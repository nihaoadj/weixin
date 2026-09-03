from __future__ import annotations

from app.modules.classroom.application.ports import ClassroomRepository
from app.modules.classroom.application.records import ClassCommand, ClassRecord, ClassStudentRecord, ClassUpdateCommand
from app.modules.classroom.domain.policy import ClassroomPolicy
from app.shared.actor import Actor
from app.shared.errors import AppError, PersistenceConflict
from app.shared.uow import UnitOfWork


class ClassroomApplication:
    def __init__(self, repository: ClassroomRepository, uow: UnitOfWork) -> None:
        self._repository = repository
        self._uow = uow
        self._policy = ClassroomPolicy()

    def list(self, actor: Actor) -> tuple[ClassRecord, ...]:
        self._policy.require_teacher(actor)
        return self._repository.list_for_teacher(actor.id)

    def create(self, actor: Actor, command: ClassCommand) -> ClassRecord:
        self._policy.require_teacher(actor)
        try:
            result = self._repository.create(actor.id, command)
            self._uow.commit()
            return result
        except PersistenceConflict as error:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "班级编码已存在", 409) from error

    def update(self, actor: Actor, class_id: int, command: ClassUpdateCommand) -> ClassRecord:
        self._policy.require_teacher(actor)
        current = self._owned(actor, class_id)
        result = self._repository.update(current.id, command)
        self._uow.commit()
        return result

    def students(self, actor: Actor, class_id: int) -> tuple[ClassStudentRecord, ...]:
        self._policy.require_teacher(actor)
        self._owned(actor, class_id)
        return self._repository.list_students(class_id)

    def add_member(self, actor: Actor, class_id: int, student_id: int) -> None:
        self._policy.require_teacher(actor)
        classroom = self._owned(actor, class_id)
        self._policy.require_active(classroom.status)
        if not self._repository.student_exists(student_id):
            raise AppError("RESOURCE_NOT_FOUND", "学生不存在", 404)
        if self._repository.member_exists(class_id, student_id):
            return
        try:
            self._repository.add_member(class_id, student_id)
            self._uow.commit()
        except PersistenceConflict as error:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "成员已存在", 409) from error

    def add_member_by_external_id(self, actor: Actor, class_id: int, external_id: str) -> None:
        student_id = self._repository.student_id_by_external_id(external_id)
        if student_id is None:
            raise AppError("RESOURCE_NOT_FOUND", "学生不存在", 404)
        self.add_member(actor, class_id, student_id)

    def remove_member(self, actor: Actor, class_id: int, student_id: int) -> None:
        self._policy.require_teacher(actor)
        self._owned(actor, class_id)
        self._repository.remove_member(class_id, student_id)
        self._uow.commit()

    def _owned(self, actor: Actor, class_id: int) -> ClassRecord:
        record = self._repository.find_owned(class_id, actor.id)
        if record is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        return record
