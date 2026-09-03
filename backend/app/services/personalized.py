"""Legacy compatibility facade for the ``learning`` bounded context.

The API and application code use ``app.modules.learning`` directly.  These
ORM-shaped helpers remain only for seed scripts and older integrations.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bootstrap.composition import learning_application
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.models import (
    LearningPlan,
    LearningTask,
    LearningTaskAttempt,
    StudentNotification,
)
from app.modules.learning.public import task_attempt_view
from app.modules.training.application.records import AttemptRecord
from app.modules.training.public import attempt_view
from app.shared.actor import Actor
from app.shared.errors import AppError


def _actor(student: User) -> Actor:
    return Actor.from_user(student)


def _now() -> datetime:
    return datetime.now(UTC)


def _public_task(task: LearningTask) -> dict[str, object]:
    return {
        "id": task.id,
        "position": task.position,
        "task_type": task.task_type,
        "dimension_id": task.dimension_id,
        "stage_id": task.stage_id,
        "problem_id": task.problem_id,
        "status": task.status,
        "public_definition": task.public_definition or {},
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }


def serialize_plan(plan: LearningPlan) -> dict[str, object]:
    return {
        "id": plan.id,
        "status": plan.status,
        "source_assessment_id": plan.source_assessment_id,
        "target_dimension_ids": plan.target_dimension_ids or [],
        "due_at": plan.due_at,
        "generation_mode": plan.generation_mode,
        "model_name": plan.model_name,
        "prompt_version": plan.prompt_version,
        "fallback_used": plan.fallback_used,
        "failure_reason": plan.failure_reason,
        "created_at": plan.created_at,
        "completed_at": plan.completed_at,
        "superseded_at": plan.superseded_at,
        "tasks": [_public_task(task) for task in sorted(plan.tasks, key=lambda item: item.position)],
    }


def ensure_learning_plan(db: Session, assessment) -> LearningPlan:
    student = assessment.attempt.student
    result = learning_application(db).ensure_for_assessment(_actor(student), assessment.attempt_id)
    plan = db.get(LearningPlan, result.id)
    if plan is None:
        raise HTTPException(status_code=500, detail="Learning plan was not persisted")
    return plan


def get_plan(db: Session, plan_id: int, student: User) -> LearningPlan:
    result = learning_application(db).get_plan(_actor(student), plan_id)
    plan = db.get(LearningPlan, result.id)
    if plan is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return plan


def current_plan(db: Session, student: User) -> LearningPlan | None:
    try:
        result = learning_application(db).current_plan(_actor(student))
    except AppError as error:
        if error.status_code != 404:
            raise
        return None
    return db.get(LearningPlan, result.id)


def start_task(db: Session, task_id: int, student: User) -> tuple[LearningTask, dict[str, object]]:
    task_record, attempt = learning_application(db).start_task(_actor(student), task_id)
    task = db.get(LearningTask, task_record.id)
    if task is None:
        raise HTTPException(status_code=500, detail="Learning task was not persisted")
    return task, attempt_view(attempt) if isinstance(attempt, AttemptRecord) else task_attempt_view(attempt)


def submit_micro_task(db: Session, task_id: int, student: User, answer: dict) -> LearningTaskAttempt:
    task = db.scalar(
        select(LearningTaskAttempt)
        .join(LearningTask, LearningTask.id == LearningTaskAttempt.task_id)
        .where(LearningTaskAttempt.student_id == student.id, LearningTask.id == task_id)
    )
    if task is None:
        task_record, attempt = learning_application(db).start_task(_actor(student), task_id)
        del task_record
        task = db.get(LearningTaskAttempt, attempt.id)
    if task is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    result = learning_application(db).submit_micro_task(_actor(student), task.id, answer)
    persisted = db.get(LearningTaskAttempt, result.id)
    if persisted is None:
        raise HTTPException(status_code=500, detail="Learning task attempt was not persisted")
    return persisted


def complete_plan(db: Session, plan: LearningPlan, student: User) -> LearningPlan:
    result = learning_application(db).complete_plan(_actor(student), plan.id)
    persisted = db.get(LearningPlan, result.id)
    if persisted is None:
        raise HTTPException(status_code=500, detail="Learning plan was not persisted")
    return persisted


def mark_task_completed(db: Session, task_id: int) -> None:
    task = db.get(LearningTask, task_id)
    if task is None:
        return
    student_id = db.scalar(select(LearningPlan.student_id).where(LearningPlan.id == task.plan_id))
    student = db.get(User, student_id) if student_id else None
    if student is not None:
        learning_application(db).mark_task_completed(_actor(student), task_id)


def list_notifications(db: Session, student: User, unread_only: bool, limit: int) -> list[StudentNotification]:
    # Read-only compatibility path; mutation is owned by LearningApplication.
    statement = select(StudentNotification).where(StudentNotification.student_id == student.id)
    if unread_only:
        statement = statement.where(StudentNotification.read_at.is_(None))
    return list(db.scalars(statement.order_by(StudentNotification.created_at.desc()).limit(limit)).all())


def notification_count(db: Session, student_id: int) -> int:
    student = db.get(User, student_id)
    return learning_application(db).unread_count(_actor(student)) if student is not None else 0


def mark_notification_read(db: Session, notification_id: int, student: User) -> None:
    learning_application(db).mark_notification_read(_actor(student), notification_id)


def mark_all_notifications_read(db: Session, student: User) -> int:
    return learning_application(db).mark_all_notifications_read(_actor(student))


def profile(db: Session, student: User) -> dict[str, object]:
    from app.modules.learning.public import profile_view

    return profile_view(learning_application(db).profile(_actor(student)))
