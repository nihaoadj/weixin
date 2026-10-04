from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.classroom.infrastructure.repositories import SqlAlchemyClassroomRepository
from app.modules.classroom.public import ClassroomScope, TeachingMemberScope


class SqlAlchemyClassroomScope:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _record(item: ClassRoom) -> ClassroomScope:
        return ClassroomScope(
            id=item.id, code=item.code, teacher_id=item.teacher_id, status=item.status, name=item.name
        )

    def owned(self, teacher_id: int, class_id: int) -> ClassroomScope | None:
        # Ownership includes archived classes so historical teaching records
        # stay readable for the owning teacher.
        item = self._session.scalar(
            select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id)
        )
        return self._record(item) if item else None

    def owned_class_ids(self, teacher_id: int) -> tuple[int, ...]:
        return tuple(
            self._session.scalars(
                select(ClassRoom.id).where(ClassRoom.teacher_id == teacher_id).order_by(ClassRoom.id)
            ).all()
        )

    def owned_active(self, teacher_id: int, class_id: int) -> ClassroomScope | None:
        item = self._session.scalar(
            select(ClassRoom).where(
                ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id, ClassRoom.status == "active"
            )
        )
        return self._record(item) if item else None

    def active_class_ids_for_student(self, student_id: int) -> tuple[int, ...]:
        return tuple(
            self._session.scalars(
                select(ClassRoom.id)
                .join(ClassMember, ClassMember.class_id == ClassRoom.id)
                .where(ClassMember.student_id == student_id, ClassRoom.status == "active")
            ).all()
        )

    def active_classes_for_student(self, student_id: int) -> tuple[ClassroomScope, ...]:
        return tuple(
            self._record(item)
            for item in self._session.scalars(
                select(ClassRoom)
                .join(ClassMember, ClassMember.class_id == ClassRoom.id)
                .where(ClassMember.student_id == student_id, ClassRoom.status == "active")
                .order_by(ClassRoom.id)
            ).all()
        )

    def active_member(self, student_id: int, class_id: int) -> bool:
        return (
            self._session.scalar(
                select(ClassMember.id)
                .join(ClassRoom, ClassRoom.id == ClassMember.class_id)
                .where(
                    ClassMember.student_id == student_id, ClassMember.class_id == class_id, ClassRoom.status == "active"
                )
            )
            is not None
        )

    def students(self, teacher_id: int, class_id: int):
        repository = SqlAlchemyClassroomRepository(self._session)
        if repository.find_owned(class_id, teacher_id) is None:
            return ()
        return repository.list_students(class_id)

    def teaching_members(self, teacher_id: int) -> tuple[TeachingMemberScope, ...]:
        return SqlAlchemyClassroomRepository(self._session).teaching_members(teacher_id)
