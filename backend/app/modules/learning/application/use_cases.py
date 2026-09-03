from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.learning.application.ports import CaseAttemptPort, LearningRepository, PracticeGenerator
from app.modules.learning.application.records import (
    LearningPlanDraft,
    LearningPlanRecord,
    LearningProfileRecord,
    LearningSourceRecord,
    LearningTaskAttemptRecord,
    LearningTaskDraft,
    LearningTaskRecord,
    NotificationRecord,
    PracticeGenerationResult,
)
from app.modules.learning.domain.policy import (
    PRACTICE_PROMPT_VERSION,
    assess_micro,
    blueprint,
    blueprint_digest,
    dimension_config,
    fallback_blueprint,
    require_unlocked,
    stage_for_dimension,
    target_dimensions,
)
from app.modules.training.public import CaseAttemptContract
from app.shared.actor import Actor
from app.shared.errors import AppError, PersistenceConflict
from app.shared.uow import UnitOfWork


class LearningApplication:
    """Owns plan/task transitions and delegates persistence to learning ports."""

    def __init__(
        self,
        repository: LearningRepository,
        uow: UnitOfWork,
        practice_generator: PracticeGenerator,
        case_attempts: CaseAttemptPort,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._practice_generator = practice_generator
        self._case_attempts = case_attempts

    def ensure_for_case_completion(self, actor: Actor, attempt_id: int) -> LearningPlanRecord | None:
        actor.require_role("student")
        source = self._source(actor, attempt_id)
        if source.attempt.learning_task_id is not None:
            self._repository.mark_task_completed(actor.id, source.attempt.learning_task_id, self._now())
            self._uow.commit()
            return self._repository.find_active_plan(actor.id)
        return self._ensure_plan(actor, source)

    def ensure_for_assessment(self, actor: Actor, attempt_id: int) -> LearningPlanRecord:
        actor.require_role("student")
        source = self._source(actor, attempt_id)
        if source.attempt.learning_task_id is not None:
            raise AppError("STATE_CONFLICT", "Task-linked assessment cannot create a new plan", 409)
        return self._ensure_plan(actor, source)

    def current_plan(self, actor: Actor) -> LearningPlanRecord:
        actor.require_role("student")
        plan = self._repository.find_active_plan(actor.id)
        if plan is None:
            raise AppError("RESOURCE_NOT_FOUND", "RESOURCE_NOT_FOUND", 404)
        return plan

    def get_plan(self, actor: Actor, plan_id: int) -> LearningPlanRecord:
        actor.require_role("student")
        plan = self._repository.find_plan(actor.id, plan_id)
        if plan is None:
            raise AppError("RESOURCE_NOT_FOUND", "RESOURCE_NOT_FOUND", 404)
        return plan

    def start_task(
        self, actor: Actor, task_id: int
    ) -> tuple[LearningTaskRecord, CaseAttemptContract | LearningTaskAttemptRecord]:
        actor.require_role("student")
        task = self._task(actor, task_id)
        require_unlocked(task.position, task.previous_status)
        if task.status == "completed":
            raise AppError("STATE_CONFLICT", "STATE_CONFLICT", 409)

        if task.task_type == "micro_drill":
            if task.status == "in_progress" and task.attempt is not None:
                return task, task.attempt
            try:
                started = self._repository.mark_task_started(actor.id, task.id, self._now())
                attempt = self._repository.create_micro_attempt(actor.id, task.id)
                self._uow.commit()
                return started, attempt
            except PersistenceConflict as error:
                self._uow.rollback()
                current = self._task(actor, task.id)
                if current.status == "in_progress" and current.attempt is not None:
                    return current, current.attempt
                raise AppError("STATE_CONFLICT", "Learning task is already being started", 409) from error

        if task.problem_id is None:
            raise AppError("RESOURCE_NOT_FOUND", "RESOURCE_NOT_FOUND", 404)
        existing_case_attempt = self._repository.find_case_attempt_for_task(actor.id, task.id)
        try:
            if existing_case_attempt is not None:
                case_attempt = self._case_attempts.get(actor, existing_case_attempt)
            else:
                case_attempt = self._case_attempts.start(
                    actor,
                    task.problem_id,
                    task.source_attempt_id if task.task_type == "focused_retry" else None,
                    task.id,
                )
            started = self._repository.mark_task_started(actor.id, task.id, self._now())
            self._uow.commit()
            return started, case_attempt
        except (PersistenceConflict, AppError) as error:
            self._uow.rollback()
            current = self._task(actor, task.id)
            existing_case_attempt = self._repository.find_case_attempt_for_task(actor.id, task.id)
            if existing_case_attempt is not None:
                current_attempt = self._case_attempts.get(actor, existing_case_attempt)
                if current.status != "completed":
                    return current, current_attempt
            if isinstance(error, AppError):
                raise error
            raise AppError("STATE_CONFLICT", "Learning task is already being started", 409) from error

    def get_task_attempt(self, actor: Actor, attempt_id: int) -> LearningTaskAttemptRecord:
        actor.require_role("student")
        attempt = self._repository.find_task_attempt(actor.id, attempt_id)
        if attempt is None:
            raise AppError("RESOURCE_NOT_FOUND", "RESOURCE_NOT_FOUND", 404)
        return attempt

    def submit_micro_task(self, actor: Actor, attempt_id: int, answer: dict[str, object]) -> LearningTaskAttemptRecord:
        actor.require_role("student")
        existing = self.get_task_attempt(actor, attempt_id)
        task = self._task(actor, existing.task_id)
        require_unlocked(task.position, task.previous_status)
        if task.task_type != "micro_drill":
            raise AppError("STATE_CONFLICT", "STATE_CONFLICT", 409)
        if existing.status == "assessed":
            return existing
        score, evidence, feedback, next_step = assess_micro(answer, task.private_rubric)
        try:
            result = self._repository.assess_micro_task(
                actor.id, task.id, existing.id, answer, score, evidence, feedback, next_step
            )
            self._uow.commit()
            return result
        except PersistenceConflict as error:
            self._uow.rollback()
            current = self._repository.find_task_attempt(actor.id, attempt_id)
            if current is not None and current.status == "assessed":
                return current
            raise AppError("STATE_CONFLICT", "Task attempt already assessed", 409) from error

    def complete_plan(self, actor: Actor, plan_id: int) -> LearningPlanRecord:
        actor.require_role("student")
        plan = self.get_plan(actor, plan_id)
        if any(task.status != "completed" for task in plan.tasks):
            raise AppError("STATE_CONFLICT", "STATE_CONFLICT", 409)
        if plan.status == "completed":
            return plan
        try:
            result = self._repository.complete_plan(actor.id, plan.id, self._now())
            self._repository.add_notification(
                actor.id,
                plan.id,
                "learning_plan_completed",
                "个性化训练已完成",
                "你已完成本次三项训练。",
            )
            self._uow.commit()
            return result
        except PersistenceConflict as error:
            self._uow.rollback()
            current = self._repository.find_plan(actor.id, plan.id)
            if current is not None and current.status == "completed":
                return current
            raise AppError("STATE_CONFLICT", "Learning plan is already being completed", 409) from error
        except Exception as error:
            self._uow.rollback()
            raise AppError("SERVICE_ERROR", "Learning plan completion is temporarily unavailable", 503) from error

    def notifications(self, actor: Actor, unread_only: bool, limit: int) -> tuple[NotificationRecord, ...]:
        actor.require_role("student")
        return self._repository.list_notifications(actor.id, unread_only, limit)

    def unread_count(self, actor: Actor) -> int:
        actor.require_role("student")
        return self._repository.unread_count(actor.id)

    def mark_notification_read(self, actor: Actor, notification_id: int) -> None:
        actor.require_role("student")
        try:
            self._repository.mark_notification_read(actor.id, notification_id, self._now())
            self._uow.commit()
        except PersistenceConflict as error:
            self._uow.rollback()
            raise AppError("RESOURCE_NOT_FOUND", "RESOURCE_NOT_FOUND", 404) from error

    def mark_all_notifications_read(self, actor: Actor) -> int:
        actor.require_role("student")
        marked = self._repository.mark_all_notifications_read(actor.id, self._now())
        self._uow.commit()
        return marked

    def profile(self, actor: Actor) -> LearningProfileRecord:
        actor.require_role("student")
        profile = self._repository.profile(actor.id)
        if profile.active_plan is not None and self._as_utc(profile.active_plan.due_at) < self._now() + timedelta(
            hours=24
        ):
            self._repository.add_notification(
                actor.id,
                profile.active_plan.id,
                "learning_plan_due",
                "训练计划即将到期",
                "请完成剩余训练任务。",
            )
            self._uow.commit()
            profile = self._repository.profile(actor.id)
        return profile

    def mark_task_completed(self, actor: Actor, task_id: int) -> None:
        actor.require_role("student")
        self._repository.mark_task_completed(actor.id, task_id, self._now())
        self._uow.commit()

    def _ensure_plan(self, actor: Actor, source: LearningSourceRecord) -> LearningPlanRecord:
        existing = self._repository.find_plan_by_assessment(actor.id, source.assessment.id)
        if existing is not None:
            return existing
        targets = target_dimensions(source.assessment.dimensions)
        first = targets[0]
        source_problem = source.attempt.problem
        source_config = dimension_config(source_problem, first)
        retry_stage = stage_for_dimension(first)
        drill_dimension = targets[1] if len(targets) > 1 else targets[0]
        drill_blueprint = blueprint(source_problem, drill_dimension) or fallback_blueprint(
            source_problem, drill_dimension
        )
        generated = self._practice_generator.generate(
            drill_blueprint,
            "；".join(
                str(item.get("feedback", ""))
                for item in source.assessment.dimensions
                if item.get("dimension_id") in targets
            ),
        )
        transfer = self._repository.find_transfer_case(source_problem.id, source_problem.difficulty, first, actor)
        tasks = [
            LearningTaskDraft(
                position=1,
                task_type="focused_retry",
                dimension_id=first,
                stage_id=retry_stage,
                problem_id=source_problem.id,
                source_attempt_id=source.attempt.id,
                public_definition={
                    "title": "同病例强化重练",
                    "instruction": f"从{retry_stage}阶段重新组织证据。",
                    "reason": "来源病例最低维度",
                },
                private_rubric=source_config,
            ),
            self._micro_task(2, drill_dimension, source_problem.id, source.attempt.id, drill_blueprint, generated),
        ]
        if transfer is not None:
            transfer_public = self._public_blueprint(transfer.blueprint, "跨病例迁移")
            tasks.append(
                LearningTaskDraft(
                    position=3,
                    task_type="cross_case_transfer",
                    dimension_id=first,
                    stage_id=str(transfer.blueprint.get("stage_id")),
                    problem_id=transfer.problem_id,
                    source_attempt_id=source.attempt.id,
                    public_definition=transfer_public,
                    private_rubric=self._private_blueprint(transfer.blueprint),
                    blueprint_id=str(transfer.blueprint.get("id")) if transfer.blueprint.get("id") else None,
                    blueprint_digest=blueprint_digest(transfer.blueprint),
                )
            )
        else:
            tasks.append(
                LearningTaskDraft(
                    position=3,
                    task_type="micro_drill",
                    dimension_id=first,
                    stage_id=str(drill_blueprint.get("stage_id")),
                    problem_id=source_problem.id,
                    source_attempt_id=source.attempt.id,
                    public_definition={
                        **self._public_blueprint(drill_blueprint, "补充微训练"),
                        "display_hints": ["replacement_reason: no_approved_transfer_case"],
                    },
                    private_rubric=self._private_blueprint(drill_blueprint),
                    blueprint_id=str(drill_blueprint.get("id")) if drill_blueprint.get("id") else None,
                    blueprint_digest=blueprint_digest(drill_blueprint),
                )
            )
        draft = LearningPlanDraft(
            student_id=actor.id,
            source_assessment_id=source.assessment.id,
            target_dimension_ids=tuple(targets),
            due_at=self._now() + timedelta(days=7),
            generation_mode="deterministic" if generated.fallback_used else "model",
            model_name=generated.model_name,
            prompt_version=generated.prompt_version or PRACTICE_PROMPT_VERSION,
            fallback_used=generated.fallback_used,
            failure_reason=generated.failure_reason,
            tasks=tuple(
                tasks[:1]
                + [
                    LearningTaskDraft(
                        position=tasks[1].position,
                        task_type=tasks[1].task_type,
                        dimension_id=tasks[1].dimension_id,
                        stage_id=tasks[1].stage_id,
                        problem_id=tasks[1].problem_id,
                        source_attempt_id=tasks[1].source_attempt_id,
                        public_definition=generated.public_definition,
                        private_rubric=tasks[1].private_rubric,
                        blueprint_id=tasks[1].blueprint_id,
                        blueprint_digest=tasks[1].blueprint_digest,
                    ),
                    *tasks[2:],
                ]
            ),
        )
        try:
            plan = self._repository.create_plan(draft)
            drill_task = next(item for item in plan.tasks if item.position == 2)
            self._repository.record_ai_call(
                student_id=actor.id,
                task="practice_generation",
                model_name=generated.model_name,
                prompt_version=generated.prompt_version or PRACTICE_PROMPT_VERSION,
                latency_ms=generated.latency_ms,
                fallback_used=generated.fallback_used,
                failure_reason=generated.failure_reason,
                learning_task_id=drill_task.id,
                blueprint_id=drill_task.blueprint_id,
                blueprint_digest=drill_task.blueprint_digest,
            )
            self._repository.add_notification(
                actor.id,
                plan.id,
                "learning_plan_ready",
                "个性化训练计划已生成",
                "请按顺序完成三项训练任务。",
            )
            self._uow.commit()
            return self._repository.find_plan(actor.id, plan.id) or plan
        except PersistenceConflict as error:
            self._uow.rollback()
            existing = self._repository.find_plan_by_assessment(actor.id, source.assessment.id)
            if existing is not None:
                return existing
            raise AppError("STATE_CONFLICT", "Learning plan already exists", 409) from error
        except Exception as error:
            self._uow.rollback()
            raise AppError("SERVICE_ERROR", "AI audit is temporarily unavailable", 503) from error

    def _micro_task(
        self,
        position: int,
        dimension_id: str,
        problem_id: int,
        source_attempt_id: int,
        value: dict[str, object],
        generated: PracticeGenerationResult,
    ) -> LearningTaskDraft:
        return LearningTaskDraft(
            position=position,
            task_type="micro_drill",
            dimension_id=dimension_id,
            stage_id=str(value.get("stage_id")),
            problem_id=problem_id,
            source_attempt_id=source_attempt_id,
            public_definition=generated.public_definition,
            private_rubric=self._private_blueprint(value),
            blueprint_id=str(value.get("id")) if value.get("id") else None,
            blueprint_digest=blueprint_digest(value),
        )

    @staticmethod
    def _public_blueprint(value: dict[str, object], title: str | None = None) -> dict[str, object]:
        return {
            "title": title or value.get("title", "证据推理微训练"),
            "context": value.get("context", "合成教学情境"),
            "instruction": value.get("public_instruction", "完成结构化回答"),
            "answer_schema": value.get("answer_schema", "short_text"),
            "display_hints": value.get("display_hints", []),
        }

    @staticmethod
    def _private_blueprint(value: dict[str, object]) -> dict[str, object]:
        return {"criteria": value.get("criteria", []), "fixed_facts": value.get("fixed_facts", [])}

    def _task(self, actor: Actor, task_id: int) -> LearningTaskRecord:
        task = self._repository.find_task(actor.id, task_id)
        if task is None:
            raise AppError("RESOURCE_NOT_FOUND", "RESOURCE_NOT_FOUND", 404)
        return task

    def _source(self, actor: Actor, attempt_id: int) -> LearningSourceRecord:
        source = self._repository.find_source(actor.id, attempt_id)
        if source is None:
            raise AppError("RESOURCE_NOT_FOUND", "RESOURCE_NOT_FOUND", 404)
        return source

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value
