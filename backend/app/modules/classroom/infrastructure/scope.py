from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.classroom.infrastructure.repositories import SqlAlchemyClassroomRepository
from app.modules.classroom.public import ClassroomScope


class SqlAlchemyClassroomScope:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _record(item: ClassRoom) -> ClassroomScope:
        return ClassroomScope(
            id=item.id, code=item.code, teacher_id=item.teacher_id, status=item.status, name=item.name
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
