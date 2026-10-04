from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.content.infrastructure.models import Problem
from app.modules.learning.application.ports import LearningRepository
from app.modules.learning.application.records import (
    LearningPlanDraft,
    LearningPlanRecord,
    LearningProfileRecord,
    LearningSourceRecord,
    LearningTaskAttemptRecord,
    LearningTaskRecord,
    NotificationRecord,
    PracticeMasteryRecord,
    RecentAssessmentRecord,
    TransferCaseRecord,
)
from app.modules.learning.infrastructure.models import (
    LearningPlan,
    LearningTask,
    LearningTaskAttempt,
    StudentNotification,
)
from app.modules.training.infrastructure.models import AICallLog, CaseAssessment, CaseAttempt
from app.modules.training.public import AssessmentSourceContract, CaseProblemContract, CaseSourceContract
from app.shared.actor import Actor
from app.shared.errors import PersistenceConflict


class SqlAlchemyLearningRepository(LearningRepository):
    """Learning persistence adapter; transaction control stays in the application layer."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _problem_record(problem: Problem) -> CaseProblemContract:
        return CaseProblemContract(
            id=problem.id,
            slug=problem.slug,
            difficulty=problem.difficulty,
            version=problem.version,
            case_definition=deepcopy(problem.case_definition or {}),
            rubric=deepcopy(problem.rubric or {}),
        )

    @staticmethod
    def _assessment_record(assessment: CaseAssessment) -> AssessmentSourceContract:
        return AssessmentSourceContract(
            id=assessment.id,
            dimensions=tuple(deepcopy(assessment.dimensions or [])),
        )

    @staticmethod
    def _attempt_record(attempt: CaseAttempt) -> CaseSourceContract:
        return CaseSourceContract(
            id=attempt.id,
            learning_task_id=attempt.learning_task_id,
            problem=SqlAlchemyLearningRepository._problem_record(attempt.problem),
        )

    @staticmethod
    def _task_attempt_record(
        attempt: LearningTaskAttempt, public_definition: dict[str, object]
    ) -> LearningTaskAttemptRecord:
        return LearningTaskAttemptRecord(
            id=attempt.id,
            task_id=attempt.task_id,
            student_id=attempt.student_id,
            status=attempt.status,
            answer=deepcopy(attempt.answer or {}),
            score=attempt.score,
            evidence=tuple(attempt.evidence or []),
            feedback=attempt.feedback,
            next_step=attempt.next_step,
            model_name=attempt.model_name,
            prompt_version=attempt.prompt_version,
            fallback_used=attempt.fallback_used,
            failure_reason=attempt.failure_reason,
            created_at=attempt.created_at,
            assessed_at=attempt.assessed_at,
            public_definition=deepcopy(public_definition or {}),
        )

    @classmethod
    def _task_record(cls, task: LearningTask, previous_status: str | None = None) -> LearningTaskRecord:
        return LearningTaskRecord(
            id=task.id,
            plan_id=task.plan_id,
            position=task.position,
            task_type=task.task_type,
            dimension_id=task.dimension_id,
            stage_id=task.stage_id,
            problem_id=task.problem_id,
            source_attempt_id=task.source_attempt_id,
            status=task.status,
            public_definition=deepcopy(task.public_definition or {}),
            private_rubric=deepcopy(task.private_rubric or {}),
            blueprint_id=task.blueprint_id,
            blueprint_digest=task.blueprint_digest,
            started_at=task.started_at,
            completed_at=task.completed_at,
            previous_status=previous_status,
            attempt=cls._task_attempt_record(task.attempt, task.public_definition) if task.attempt else None,
            cycle_number=task.cycle_number,
            target_type=task.target_type,
            target_code=task.target_code,
            variant_code=task.variant_code,
            plan_source_type=task.plan.source_type if task.plan else "",
            plan_source_id=task.plan.source_id if task.plan else None,
            plan_source_context=deepcopy(task.plan.source_context or {}) if task.plan else None,
        )

    @classmethod
    def _plan_record(cls, plan: LearningPlan) -> LearningPlanRecord:
        return LearningPlanRecord(
            id=plan.id,
            student_id=plan.student_id,
            status=plan.status,
            source_assessment_id=plan.source_assessment_id,
            source_type=plan.source_type,
            source_id=plan.source_id,
            target_dimension_ids=tuple(plan.target_dimension_ids or []),
            due_at=plan.due_at,
            generation_mode=plan.generation_mode,
            model_name=plan.model_name,
            prompt_version=plan.prompt_version,
            fallback_used=plan.fallback_used,
            failure_reason=plan.failure_reason,
            created_at=plan.created_at,
            completed_at=plan.completed_at,
            superseded_at=plan.superseded_at,
            tasks=tuple(cls._task_record(task) for task in sorted(plan.tasks, key=lambda item: item.position)),
            source_context=deepcopy(plan.source_context or {}),
            current_cycle=plan.current_cycle,
            verification_status=plan.verification_status,
            automation_exhausted=plan.automation_exhausted,
            decision_policy_version=plan.decision_policy_version,
            decision_basis=deepcopy(plan.decision_basis or {}),
            evaluated_at=plan.evaluated_at,
        )

    @staticmethod
    def _notification_record(item: StudentNotification) -> NotificationRecord:
        return NotificationRecord(
            id=item.id,
            type=item.type,
            entity_type=item.entity_type,
            entity_id=item.entity_public_id or item.entity_id,
            title=item.title,
            body=item.body,
            read_at=item.read_at,
            created_at=item.created_at,
        )

    def find_source(self, student_id: int, attempt_id: int) -> LearningSourceRecord | None:
        attempt = self._session.scalar(
            select(CaseAttempt)
            .where(CaseAttempt.id == attempt_id, CaseAttempt.student_id == student_id)
            .options(
                selectinload(CaseAttempt.problem),
                selectinload(CaseAttempt.messages),
                selectinload(CaseAttempt.submissions),
                selectinload(CaseAttempt.assessment),
            )
        )
        if attempt is None or attempt.assessment is None or attempt.status != "assessed":
            return None
        return LearningSourceRecord(self._attempt_record(attempt), self._assessment_record(attempt.assessment))

    def find_plan_by_assessment(self, student_id: int, assessment_id: int) -> LearningPlanRecord | None:
        plan = self._session.scalar(
            select(LearningPlan)
            .where(LearningPlan.student_id == student_id, LearningPlan.source_assessment_id == assessment_id)
            .options(selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt))
        )
        return self._plan_record(plan) if plan else None

    def find_active_plan(self, student_id: int) -> LearningPlanRecord | None:
        plan = self._session.scalar(
            select(LearningPlan)
            .where(
                LearningPlan.student_id == student_id,
                LearningPlan.status == "active",
                LearningPlan.source_type == "case_assessment",
            )
            .order_by(LearningPlan.id.desc())
            .options(selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt))
        )
        return self._plan_record(plan) if plan else None

    def find_plan(self, student_id: int, plan_id: int) -> LearningPlanRecord | None:
        plan = self._session.scalar(
            select(LearningPlan)
            .where(LearningPlan.id == plan_id, LearningPlan.student_id == student_id)
            .options(selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt))
        )
        return self._plan_record(plan) if plan else None

    def find_task(self, student_id: int, task_id: int) -> LearningTaskRecord | None:
        task = self._session.scalar(
            select(LearningTask)
            .join(LearningPlan)
            .where(LearningTask.id == task_id, LearningPlan.student_id == student_id)
            .options(
                selectinload(LearningTask.plan).selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt),
                selectinload(LearningTask.attempt),
            )
        )
        if task is None:
            return None
        previous = next((item for item in task.plan.tasks if item.position == task.position - 1), None)
        return self._task_record(task, previous.status if previous else None)

    def find_task_attempt(self, student_id: int, attempt_id: int) -> LearningTaskAttemptRecord | None:
        attempt = self._session.scalar(
            select(LearningTaskAttempt)
            .join(LearningTask, LearningTask.id == LearningTaskAttempt.task_id)
            .join(LearningPlan, LearningPlan.id == LearningTask.plan_id)
            .where(LearningTaskAttempt.id == attempt_id, LearningTaskAttempt.student_id == student_id)
            .options(selectinload(LearningTaskAttempt.task))
        )
        if attempt is None:
            return None
        return self._task_attempt_record(attempt, attempt.task.public_definition)

    def find_case_attempt_for_task(self, student_id: int, task_id: int) -> int | None:
        return self._session.scalar(
            select(CaseAttempt.id).where(CaseAttempt.learning_task_id == task_id, CaseAttempt.student_id == student_id)
        )

    def find_transfer_case(
        self, source_problem_id: int, source_difficulty: str, dimension_id: str, student: Actor
    ) -> TransferCaseRecord | None:
        class_codes = set(student.class_ids)
        class_codes.update(
            self._session.scalars(
                select(ClassRoom.code)
                .join(ClassMember, ClassMember.class_id == ClassRoom.id)
                .where(ClassMember.student_id == student.id, ClassRoom.status == "active")
            ).all()
        )
        problems = self._session.scalars(
            select(Problem)
            .where(
                Problem.content_type == "guided_case",
                Problem.status == "published",
                Problem.medical_review_status == "approved",
                Problem.id != source_problem_id,
            )
            .order_by(Problem.difficulty.asc(), Problem.id.asc())
        ).all()

        def visible(problem: Problem) -> bool:
            target_ids = set(item for item in (problem.target_ids or "").split(",") if item)
            return (
                problem.target == "all"
                or (problem.target == "individual" and student.external_id in target_ids)
                or (problem.target == "class" and bool(target_ids.intersection(class_codes)))
            )

        candidates = [
            item
            for item in problems
            if visible(item)
            and dimension_id in (item.capability_tags or [])
            and any(
                blueprint.get("dimension_id") == dimension_id
                for blueprint in (item.case_definition or {}).get("practice_blueprints", [])
            )
        ]
        if not candidates:
            return None
        counts = dict(
            self._session.execute(
                select(CaseAttempt.problem_id, func.count(CaseAttempt.id))
                .where(CaseAttempt.student_id == student.id, CaseAttempt.status == "assessed")
                .group_by(CaseAttempt.problem_id)
            ).all()
        )
        same = [item for item in candidates if item.difficulty == source_difficulty]
        chosen = sorted(same or candidates, key=lambda item: (counts.get(item.id, 0), item.id))[0]
        selected = next(
            item
            for item in (chosen.case_definition or {}).get("practice_blueprints", [])
            if item.get("dimension_id") == dimension_id
        )
        return TransferCaseRecord(chosen.id, chosen.difficulty, deepcopy(selected))

    def create_plan(self, draft: LearningPlanDraft) -> LearningPlanRecord:
        now = datetime.now(UTC)
        old = self._session.scalar(
            select(LearningPlan).where(
                LearningPlan.student_id == draft.student_id,
                LearningPlan.status == "active",
                LearningPlan.source_type == "case_assessment",
            )
        )
        if old is not None:
            old.status = "superseded"
            old.superseded_at = now
        plan = LearningPlan(
            student_id=draft.student_id,
            source_assessment_id=draft.source_assessment_id,
            source_type="case_assessment",
            source_id=draft.source_assessment_id,
            status="active",
            target_dimension_ids=list(draft.target_dimension_ids),
            due_at=draft.due_at,
            generation_mode=draft.generation_mode,
            model_name=draft.model_name,
            prompt_version=draft.prompt_version,
            fallback_used=draft.fallback_used,
            failure_reason=draft.failure_reason,
        )
        self._session.add(plan)
        try:
            self._session.flush()
            for item in draft.tasks:
                self._session.add(
                    LearningTask(
                        plan_id=plan.id,
                        position=item.position,
                        task_type=item.task_type,
                        dimension_id=item.dimension_id,
                        stage_id=item.stage_id,
                        problem_id=item.problem_id,
                        source_attempt_id=item.source_attempt_id,
                        status="pending",
                        public_definition=deepcopy(item.public_definition),
                        private_rubric=deepcopy(item.private_rubric),
                        blueprint_id=item.blueprint_id,
                        blueprint_digest=item.blueprint_digest,
                    )
                )
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        saved = self._session.scalar(
            select(LearningPlan)
            .where(LearningPlan.id == plan.id)
            .options(selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt))
        )
        if saved is None:
            raise PersistenceConflict
        return self._plan_record(saved)

    def mark_task_started(self, student_id: int, task_id: int, started_at: datetime) -> LearningTaskRecord:
        task = self._session.scalar(
            select(LearningTask)
            .join(LearningPlan)
            .where(LearningTask.id == task_id, LearningPlan.student_id == student_id)
            .options(
                selectinload(LearningTask.plan).selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt),
                selectinload(LearningTask.attempt),
            )
        )
        if task is None:
            raise PersistenceConflict
        task.status = "in_progress"
        task.started_at = task.started_at or started_at
        self._session.flush()
        previous = next((item for item in task.plan.tasks if item.position == task.position - 1), None)
        return self._task_record(task, previous.status if previous else None)

    def create_micro_attempt(self, student_id: int, task_id: int) -> LearningTaskAttemptRecord:
        task = self._session.scalar(
            select(LearningTask)
            .join(LearningPlan)
            .where(LearningTask.id == task_id, LearningPlan.student_id == student_id)
            .options(selectinload(LearningTask.attempt))
        )
        if task is None:
            raise PersistenceConflict
        if task.attempt is None:
            attempt = LearningTaskAttempt(task_id=task.id, student_id=student_id)
            self._session.add(attempt)
            try:
                self._session.flush()
            except IntegrityError as error:
                raise PersistenceConflict from error
        else:
            attempt = task.attempt
        self._session.refresh(attempt)
        return self._task_attempt_record(attempt, task.public_definition)

    def assess_micro_task(
        self,
        student_id: int,
        task_id: int,
        attempt_id: int,
        answer: dict[str, object],
        score: float,
        evidence: list[str],
        feedback: str,
        next_step: str,
    ) -> LearningTaskAttemptRecord:
        task = self._session.scalar(
            select(LearningTask)
            .join(LearningPlan)
            .where(LearningTask.id == task_id, LearningPlan.student_id == student_id)
            .options(selectinload(LearningTask.attempt))
        )
        if task is None or task.attempt is None or task.attempt.id != attempt_id:
            raise PersistenceConflict
        attempt = task.attempt
        if attempt.status == "assessed":
            return self._task_attempt_record(attempt, task.public_definition)
        now = datetime.now(UTC)
        attempt.answer = deepcopy(answer)
        attempt.score = score
        attempt.evidence = list(evidence)
        attempt.feedback = feedback
        attempt.next_step = next_step
        attempt.status = "assessed"
        attempt.assessed_at = now
        task.status = "completed"
        task.completed_at = now
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return self._task_attempt_record(attempt, task.public_definition)

    def mark_task_completed(self, student_id: int, task_id: int, completed_at: datetime) -> None:
        task = self._session.scalar(
            select(LearningTask)
            .join(LearningPlan)
            .where(LearningTask.id == task_id, LearningPlan.student_id == student_id)
        )
        if task is not None and task.plan.source_type in {"pbl_suggestion", "classroom_package"}:
            raise PersistenceConflict
        if task is not None and task.status != "completed":
            task.status = "completed"
            task.completed_at = completed_at
            self._session.flush()

    def complete_plan(self, student_id: int, plan_id: int, completed_at: datetime) -> LearningPlanRecord:
        plan = self._session.scalar(
            select(LearningPlan)
            .where(LearningPlan.id == plan_id, LearningPlan.student_id == student_id)
            .options(selectinload(LearningPlan.tasks).selectinload(LearningTask.attempt))
        )
        if plan is None:
            raise PersistenceConflict
        if plan.source_type in {"pbl_suggestion", "classroom_package"}:
            raise PersistenceConflict
        if plan.status != "completed":
            plan.status = "completed"
            plan.completed_at = completed_at
        self._session.flush()
        return self._plan_record(plan)

    def add_notification(
        self, student_id: int, plan_id: int, kind: str, title: str, body: str
    ) -> NotificationRecord | None:
        key = f"{kind}:learning_plan:{plan_id}"
        item = self._session.scalar(select(StudentNotification).where(StudentNotification.dedupe_key == key))
        if item is not None:
            return self._notification_record(item)
        item = StudentNotification(
            student_id=student_id,
            type=kind,
            entity_type="learning_plan",
            entity_id=plan_id,
            title=title,
            body=body,
            dedupe_key=key,
        )
        self._session.add(item)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return self._notification_record(item)

    def list_notifications(self, student_id: int, unread_only: bool, limit: int) -> tuple[NotificationRecord, ...]:
        statement = select(StudentNotification).where(StudentNotification.student_id == student_id)
        if unread_only:
            statement = statement.where(StudentNotification.read_at.is_(None))
        statement = statement.order_by(StudentNotification.created_at.desc()).limit(limit)
        return tuple(self._notification_record(item) for item in self._session.scalars(statement).all())

    def unread_count(self, student_id: int) -> int:
        return int(
            self._session.scalar(
                select(func.count(StudentNotification.id)).where(
                    StudentNotification.student_id == student_id,
                    StudentNotification.read_at.is_(None),
                )
            )
            or 0
        )

    def mark_notification_read(self, student_id: int, notification_id: int, read_at: datetime) -> None:
        item = self._session.scalar(
            select(StudentNotification).where(
                StudentNotification.id == notification_id, StudentNotification.student_id == student_id
            )
        )
        if item is None:
            raise PersistenceConflict
        item.read_at = item.read_at or read_at

    def mark_all_notifications_read(self, student_id: int, read_at: datetime) -> int:
        items = self._session.scalars(
            select(StudentNotification).where(
                StudentNotification.student_id == student_id, StudentNotification.read_at.is_(None)
            )
        ).all()
        for item in items:
            item.read_at = read_at
        return len(items)

    def profile(self, student_id: int) -> LearningProfileRecord:
        assessments = self._session.scalars(
            select(CaseAssessment)
            .join(CaseAttempt)
            .where(CaseAttempt.student_id == student_id, CaseAttempt.status == "assessed")
            .order_by(CaseAssessment.created_at.desc())
            .limit(10)
        ).all()
        recent = tuple(
            RecentAssessmentRecord(
                attempt_id=item.attempt_id,
                total_score=item.total_score,
                dimensions=tuple(deepcopy(item.dimensions or [])),
                created_at=item.created_at,
            )
            for item in assessments
        )
        mastery_rows = self._session.execute(
            select(LearningTask.dimension_id, func.avg(LearningTaskAttempt.score), func.count(LearningTaskAttempt.id))
            .join(LearningTaskAttempt, LearningTaskAttempt.task_id == LearningTask.id)
            .where(LearningTaskAttempt.student_id == student_id, LearningTaskAttempt.status == "assessed")
            .group_by(LearningTask.dimension_id)
        ).all()
        mastery = tuple(
            PracticeMasteryRecord(str(dimension), float(score or 0), int(count))
            for dimension, score, count in mastery_rows
        )
        active = self.find_active_plan(student_id)
        return LearningProfileRecord(
            formal_dimensions=recent[0].dimensions if recent else (),
            recent_assessments=recent,
            practice_mastery=mastery,
            active_plan=active,
            unread_count=self.unread_count(student_id),
        )

    def record_ai_call(
        self,
        *,
        student_id: int,
        task: str,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
        learning_task_id: int | None,
        blueprint_id: str | None,
        blueprint_digest: str | None,
    ) -> None:
        self._session.add(
            AICallLog(
                user_id=student_id,
                task=task,
                model_name=model_name,
                prompt_version=prompt_version,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                failure_reason=failure_reason,
                learning_task_id=learning_task_id,
                blueprint_id=blueprint_id,
                blueprint_digest=blueprint_digest,
            )
        )
