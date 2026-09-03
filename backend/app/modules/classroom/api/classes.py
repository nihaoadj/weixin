from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_teacher
from app.modules.classroom.api.schemas import ClassCreate, ClassMemberCreate, ClassRead, ClassStudentRead, ClassUpdate
from app.modules.classroom.application.records import ClassCommand, ClassUpdateCommand
from app.modules.classroom.public import class_view, student_view
from app.modules.classroom.wiring import classroom_application
from app.modules.identity.infrastructure.models import User
from app.shared.actor import Actor

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("", response_model=list[ClassRead])
def list_classes(teacher: User = Depends(require_teacher), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [class_view(item) for item in classroom_application(db).list(Actor.from_user(teacher))]


@router.post("", response_model=ClassRead)
def create_class(
    payload: ClassCreate, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> dict[str, object]:
    return class_view(
        classroom_application(db).create(Actor.from_user(teacher), ClassCommand(name=payload.name, code=payload.code))
    )


@router.patch("/{class_id}", response_model=ClassRead)
def update_class(
    class_id: int,
    payload: ClassUpdate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return class_view(
        classroom_application(db).update(
            Actor.from_user(teacher),
            class_id,
            ClassUpdateCommand(name=payload.name, status=payload.status),
        )
    )


@router.get("/{class_id}/students", response_model=list[ClassStudentRead])
def list_students(
    class_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    return [student_view(item) for item in classroom_application(db).students(Actor.from_user(teacher), class_id)]


@router.post("/{class_id}/members/{student_id}", status_code=204)
def add_member(
    class_id: int, student_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> None:
    classroom_application(db).add_member(Actor.from_user(teacher), class_id, student_id)


@router.post("/{class_id}/members", status_code=204)
def add_member_by_external_id(
    class_id: int,
    payload: ClassMemberCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> None:
    classroom_application(db).add_member_by_external_id(Actor.from_user(teacher), class_id, payload.student_external_id)


@router.delete("/{class_id}/members/{student_id}", status_code=204)
def remove_member(
    class_id: int, student_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> None:
    classroom_application(db).remove_member(Actor.from_user(teacher), class_id, student_id)
