from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.modules.analytics.application.ports import AnalyticsReader
from app.modules.analytics.application.records import (
    AssessmentRecord,
    AttemptAnalyticsRecord,
    KnowledgeAnalyticsRecord,
    LearningPlanRecord,
    PracticeMasteryRecord,
    ProblemAnalyticsRecord,
    ScopeClass,
    ScopeStudent,
)
from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.content.infrastructure.models import Problem
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.models import (
    LearningPlan,
    LearningTask,
    LearningTaskAttempt,
    ReviewAttempt,
    ReviewItem,
    ReviewState,
)
from app.modules.training.infrastructure.models import CaseAttempt


class SqlAlchemyAnalyticsReader(AnalyticsReader):
    """Read-only collection queries for the analytics application service."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _class_record(item: ClassRoom) -> ScopeClass:
        return ScopeClass(id=item.id, name=item.name, code=item.code)

    def load_classes(self, teacher_id: int, class_id: int | None) -> tuple[ScopeClass, ...]:
        statement = select(ClassRoom).where(ClassRoom.teacher_id == teacher_id, ClassRoom.status == "active")
        if class_id is not None:
            statement = statement.where(ClassRoom.id == class_id)
        return tuple(self._class_record(item) for item in self._session.scalars(statement).all())

    def load_owned_classes(self, teacher_id: int, class_id: int | None) -> tuple[ScopeClass, ...]:
        statement = select(ClassRoom).where(ClassRoom.teacher_id == teacher_id)
        if class_id is not None:
            statement = statement.where(ClassRoom.id == class_id)
        return tuple(self._class_record(item) for item in self._session.scalars(statement.order_by(ClassRoom.id)).all())

    def load_student_names(self, student_ids: tuple[int, ...]) -> dict[int, str]:
        if not student_ids:
            return {}
        return {
            row.id: row.nickname
            for row in self._session.scalars(select(User).where(User.id.in_(student_ids), User.role == "student")).all()
        }

    def owns_case(self, teacher_id: int, problem_id: int) -> bool:
        return (
            self._session.scalar(
                select(Problem.id).where(
                    Problem.id == problem_id,
                    Problem.author_id == teacher_id,
                    Problem.content_type == "guided_case",
                )
            )
            is not None
        )

    def load_students(self, classes: tuple[ScopeClass, ...]) -> tuple[ScopeStudent, ...]:
        if not classes:
            return ()
        class_ids = {item.id for item in classes}
        class_codes = {item.code for item in classes}
        linked_ids = set(
            self._session.scalars(select(ClassMember.student_id).where(ClassMember.class_id.in_(class_ids))).all()
        )
        candidates = self._session.scalars(select(User).where(User.role == "student")).all()
        students = [
            item
            for item in candidates
            if item.id in linked_ids or bool(set(item.class_ids or []).intersection(class_codes))
        ]
        return tuple(
            ScopeStudent(
                id=item.id,
                external_id=item.external_id,
                nickname=item.nickname,
                class_ids=tuple(item.class_ids or []),
            )
            for item in students
        )

    @staticmethod
    def _problem_record(item: Problem) -> ProblemAnalyticsRecord:
        return ProblemAnalyticsRecord(
            id=item.id,
            title=item.title,
            slug=item.slug,
            version=item.version,
            status=item.status,
            content_type=item.content_type,
            author_id=item.author_id,
            target=item.target,
            target_ids=tuple(value for value in (item.target_ids or "").split(",") if value),
        )

    @staticmethod
    def _attempt_record(item: CaseAttempt) -> AttemptAnalyticsRecord:
        assessment = item.assessment
        assessment_record = (
            AssessmentRecord(
                id=assessment.id,
                attempt_id=assessment.attempt_id,
                total_score=assessment.total_score,
                dimensions=tuple(assessment.dimensions or []),
                focus_stage=assessment.focus_stage,
                created_at=assessment.created_at,
            )
            if assessment is not None
            else None
        )
        return AttemptAnalyticsRecord(
            id=item.id,
            student_id=item.student_id,
            problem_id=item.problem_id,
            status=item.status,
            retry_of_id=item.retry_of_id,
            started_at=item.started_at,
            assessed_at=item.assessed_at,
            assessment=assessment_record,
        )

    def load_activity(
        self,
        student_ids: tuple[int, ...],
        start: datetime,
        end: datetime,
        problem_id: int | None,
    ) -> tuple[tuple[ProblemAnalyticsRecord, ...], tuple[AttemptAnalyticsRecord, ...]]:
        problem_statement = select(Problem).where(Problem.content_type == "guided_case", Problem.status == "published")
        if problem_id is not None:
            problem_statement = problem_statement.where(Problem.id == problem_id)
        problems = tuple(self._problem_record(item) for item in self._session.scalars(problem_statement).all())
        if not student_ids:
            return problems, ()
        attempt_statement = (
            select(CaseAttempt)
            .where(
                CaseAttempt.student_id.in_(student_ids),
                CaseAttempt.started_at >= start,
                CaseAttempt.started_at <= end,
            )
            .options(joinedload(CaseAttempt.assessment))
        )
        if problem_id is not None:
            attempt_statement = attempt_statement.where(CaseAttempt.problem_id == problem_id)
        attempts = tuple(self._attempt_record(item) for item in self._session.scalars(attempt_statement).all())
        return problems, attempts

    def load_learning(self, student_id: int) -> tuple[LearningPlanRecord | None, tuple[PracticeMasteryRecord, ...]]:
        plan = self._session.scalar(
            select(LearningPlan)
            .where(LearningPlan.student_id == student_id, LearningPlan.status == "active")
            .order_by(LearningPlan.id.desc())
            .options(selectinload(LearningPlan.tasks))
        )
        plan_record = (
            LearningPlanRecord(
                id=plan.id,
                status=plan.status,
                target_dimension_ids=tuple(plan.target_dimension_ids or []),
                due_at=plan.due_at,
                tasks=tuple((task.position, task.task_type, task.status) for task in plan.tasks),
            )
            if plan is not None
            else None
        )
        rows = self._session.execute(
            select(LearningTask.dimension_id, func.avg(LearningTaskAttempt.score), func.count(LearningTaskAttempt.id))
            .join(LearningTaskAttempt, LearningTaskAttempt.task_id == LearningTask.id)
            .where(LearningTaskAttempt.student_id == student_id, LearningTaskAttempt.status == "assessed")
            .group_by(LearningTask.dimension_id)
        ).all()
        mastery = tuple(
            PracticeMasteryRecord(dimension_id=dimension, average_score=float(score or 0), attempt_count=count)
            for dimension, score, count in rows
        )
        return plan_record, mastery

    def load_knowledge(self, student_ids: tuple[int, ...], now: datetime) -> KnowledgeAnalyticsRecord:
        if not student_ids:
            return KnowledgeAnalyticsRecord(0, 0, 0, 0, ())
        participant_count = self._session.scalar(
            select(func.count(func.distinct(ReviewItem.student_id))).where(ReviewItem.student_id.in_(student_ids))
        )
        due_backlog = self._session.scalar(
            select(func.count(ReviewState.id)).where(ReviewState.student_id.in_(student_ids), ReviewState.due_at <= now)
        )
        objective_attempt_count, objective_correct_count = self._session.execute(
            select(
                func.count(ReviewAttempt.id),
                func.coalesce(func.sum(case((ReviewAttempt.correct.is_(True), 1), else_=0)), 0),
            ).where(ReviewAttempt.student_id.in_(student_ids), ReviewAttempt.selected_option.is_not(None))
        ).one()
        weak_rows = self._session.execute(
            select(ReviewItem.point_code, func.count(ReviewItem.id))
            .where(ReviewItem.student_id.in_(student_ids), ReviewItem.active.is_(True))
            .group_by(ReviewItem.point_code)
            .order_by(func.count(ReviewItem.id).desc(), ReviewItem.point_code.asc())
            .limit(10)
        ).all()
        return KnowledgeAnalyticsRecord(
            int(participant_count or 0),
            int(due_backlog or 0),
            int(objective_attempt_count or 0),
            int(objective_correct_count or 0),
            tuple((str(code), int(count)) for code, count in weak_rows),
        )
