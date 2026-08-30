from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_teacher
from app.models import ClassMember, ClassRoom, User
from app.schemas.classroom import ClassCreate, ClassMemberCreate, ClassRead, ClassStudentRead, ClassUpdate

router = APIRouter(prefix="/classes", tags=["classes"])


def _owned(class_id: int, teacher: User, db: Session) -> ClassRoom:
    classroom = db.scalar(select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher.id))
    if classroom is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return classroom


@router.get("", response_model=list[ClassRead])
def list_classes(teacher: User = Depends(require_teacher), db: Session = Depends(get_db)) -> list[ClassRoom]:
    return list(db.scalars(select(ClassRoom).where(ClassRoom.teacher_id == teacher.id).order_by(ClassRoom.id)).all())


@router.post("", response_model=ClassRead)
def create_class(
    payload: ClassCreate, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> ClassRoom:
    classroom = ClassRoom(name=payload.name, code=payload.code, teacher_id=teacher.id)
    db.add(classroom)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="STATE_CONFLICT") from None
    db.refresh(classroom)
    return classroom


@router.patch("/{class_id}", response_model=ClassRead)
def update_class(
    class_id: int,
    payload: ClassUpdate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> ClassRoom:
    classroom = _owned(class_id, teacher, db)
    if payload.name is not None:
        classroom.name = payload.name
    if payload.status is not None:
        classroom.status = payload.status
    db.commit()
    db.refresh(classroom)
    return classroom


@router.get("/{class_id}/students", response_model=list[ClassStudentRead])
def list_students(class_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)) -> list[dict]:
    _owned(class_id, teacher, db)
    rows = db.execute(
        select(User, ClassMember.joined_at)
        .join(ClassMember, ClassMember.student_id == User.id)
        .where(ClassMember.class_id == class_id)
        .order_by(User.id)
    ).all()
    return [
        {"id": user.id, "nickname": user.nickname, "external_id": user.external_id, "joined_at": joined}
        for user, joined in rows
    ]


@router.post("/{class_id}/members/{student_id}", status_code=204)
def add_member(
    class_id: int, student_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> None:
    classroom = _owned(class_id, teacher, db)
    if classroom.status != "active":
        raise HTTPException(status_code=409, detail="STATE_CONFLICT")
    student = db.get(User, student_id)
    if student is None or student.role != "student":
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    if (
        db.scalar(select(ClassMember).where(ClassMember.class_id == class_id, ClassMember.student_id == student_id))
        is None
    ):
        db.add(ClassMember(class_id=class_id, student_id=student_id))
        db.commit()


@router.post("/{class_id}/members", status_code=204)
def add_member_by_external_id(
    class_id: int,
    payload: ClassMemberCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> None:
    classroom = _owned(class_id, teacher, db)
    if classroom.status != "active":
        raise HTTPException(status_code=409, detail="STATE_CONFLICT")
    student = db.scalar(select(User).where(User.external_id == payload.student_external_id))
    if student is None or student.role != "student":
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    member_exists = db.scalar(
        select(ClassMember).where(ClassMember.class_id == class_id, ClassMember.student_id == student.id)
    )
    if member_exists is None:
        db.add(ClassMember(class_id=class_id, student_id=student.id))
        db.commit()


@router.delete("/{class_id}/members/{student_id}", status_code=204)
def remove_member(
    class_id: int, student_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> None:
    _owned(class_id, teacher, db)
    member = db.scalar(
        select(ClassMember).where(ClassMember.class_id == class_id, ClassMember.student_id == student_id)
    )
    if member is not None:
        db.delete(member)
        db.commit()
