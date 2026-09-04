"""Learning-owned intervention persistence, sharing the caller's transaction."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.learning.application.knowledge_review import KnowledgeReviewApplication
from app.modules.learning.application.review_records import SupplementalChoiceCard
from app.modules.learning.domain.policy import assess_micro
from app.modules.learning.infrastructure.knowledge_review_repository import SqlAlchemyReviewRepository
from app.modules.learning.infrastructure.models import (
    LearningPlan,
    LearningTask,
    LearningTaskAttempt,
    StudentNotification,
)
from app.platform.transactions import SqlAlchemyUnitOfWork
from app.shared.actor import Actor
from app.shared.errors import AppError


def _utc(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


class PblLearningStore:
    def __init__(self, session: Session):
        self._session = session

    def create(self, student_ids: tuple[int, ...], source_id: int, context: dict, resources: tuple[dict, ...]):
        plan_ids = []
        for student_id in student_ids:
            existing = self._session.scalar(
                select(LearningPlan).where(
                    LearningPlan.student_id == student_id,
                    LearningPlan.source_type == "pbl_suggestion",
                    LearningPlan.source_id == source_id,
                )
            )
            if existing:
                plan_ids.append(existing.id)
                continue
            plan = LearningPlan(
                student_id=student_id,
                source_type="pbl_suggestion",
                source_id=source_id,
                source_context=context,
                status="active",
                due_at=datetime.now(UTC) + timedelta(days=7),
                generation_mode="teacher_adopted",
                model_name="teacher_review",
                prompt_version="pbl-learning-v2",
                fallback_used=False,
                target_dimension_ids=list(context.get("dimension_ids", [])),
            )
            for position, resource in enumerate(resources, 1):
                public = {key: value for key, value in resource.items() if key != "private_rubric"}
                public["source"] = {key: context[key] for key in ("session_id", "snapshot_id", "suggestion_id")}
                plan.tasks.append(
                    LearningTask(
                        position=position,
                        task_type=resource["task_type"],
                        dimension_id=resource.get("dimension_id", "discussion"),
                        stage_id=resource.get("stage_id"),
                        problem_id=resource.get("problem_id"),
                        public_definition=public,
                        private_rubric=resource.get("private_rubric", {}),
                        status="pending",
                    )
                )
            self._session.add(plan)
            self._session.flush()
            self._session.add(
                StudentNotification(
                    student_id=student_id,
                    type="learning_plan_ready",
                    entity_id=plan.id,
                    title="PBL 课后任务已发布",
                    body="完成讨论与针对性练习后，交由教师核验。",
                    dedupe_key=f"pbl:{source_id}:{student_id}",
                )
            )
            plan_ids.append(plan.id)
        self._session.flush()
        return tuple(plan_ids)

    @staticmethod
    def _view(plan: LearningPlan):
        tasks = []
        for task in plan.tasks:
            attempt = task.attempt
            tasks.append(
                {
                    "id": task.id,
                    "task_type": task.task_type,
                    "position": task.position,
                    "status": task.status,
                    "problem_id": task.problem_id,
                    "public_definition": task.public_definition,
                    "result": {
                        "score": attempt.score,
                        "feedback": attempt.feedback,
                        "evidence": attempt.evidence,
                        "answer": attempt.answer,
                        "submitted_at": _utc(attempt.assessed_at),
                    }
                    if attempt
                    else None,
                }
            )
        return {
            "id": plan.id,
            "student_id": plan.student_id,
            "source_type": plan.source_type,
            "source_id": plan.source_id,
            "source_context": plan.source_context,
            "status": plan.status,
            "verification_status": plan.verification_status,
            "verification_note": plan.verification_note,
            "verified_at": _utc(plan.verified_at),
            "version": plan.version,
            "due_at": _utc(plan.due_at),
            "tasks": tasks,
        }

    def list(self, *, student_id: int | None = None, teacher_id: int | None = None, session_id: int | None = None):
        statement = select(LearningPlan).where(LearningPlan.source_type == "pbl_suggestion")
        if student_id is not None:
            statement = statement.where(LearningPlan.student_id == student_id)
        if teacher_id is not None:
            statement = statement.where(LearningPlan.source_context["teacher_id"].as_integer() == teacher_id)
        if session_id is not None:
            statement = statement.where(LearningPlan.source_context["session_id"].as_integer() == session_id)
        return tuple(
            self._view(plan) for plan in self._session.scalars(statement.order_by(LearningPlan.id.desc())).all()
        )

    def submit(self, student_id: int, task_id: int, submission_id: str, answer: dict):
        task = self._session.scalar(
            select(LearningTask)
            .join(LearningPlan)
            .where(
                LearningTask.id == task_id,
                LearningPlan.student_id == student_id,
                LearningPlan.source_type == "pbl_suggestion",
            )
        )
        if task is None:
            raise AppError("RESOURCE_NOT_FOUND", "任务不存在", 404)
        if task.attempt:
            if task.attempt.client_submission_id != submission_id or task.attempt.answer != answer:
                raise AppError("STATE_CONFLICT", "任务已经提交", 409)
            return self._view(task.plan)
        if task.task_type == "focused_retry":
            raise AppError("VALIDATION_ERROR", "请通过病例训练完成重练", 422)
        if task.plan.status != "active":
            raise AppError("STATE_CONFLICT", "学习计划当前不能提交", 409)
        previous = [t for t in task.plan.tasks if t.position < task.position]
        if any(t.status != "completed" for t in previous):
            raise AppError("STATE_CONFLICT", "请先完成前面的任务", 409)
        score, evidence, feedback = None, [], "已保存学习证据，待教师核验。"
        if task.task_type in {"knowledge_review", "retest"}:
            option = answer.get("selected_option")
            if type(option) is not int or not 0 <= option < len(task.public_definition["options"]):
                raise AppError("VALIDATION_ERROR", "请选择有效答案", 422)
            score = 100.0 if option == task.private_rubric["correct_option"] else 0.0
            feedback = task.private_rubric["explanation"]
            evidence = [f"客观作答：{'正确' if score else '错误'}"]
        else:
            text = answer.get("text", "")
            if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
                raise AppError("VALIDATION_ERROR", "请输入学习回答（1～4000 字）", 422)
            if task.task_type == "micro_drill":
                score, evidence, feedback, _ = assess_micro(answer, task.private_rubric)
        if task.task_type in {"knowledge_review", "retest"}:
            public = task.public_definition
            review = KnowledgeReviewApplication(
                SqlAlchemyReviewRepository(self._session), SqlAlchemyUnitOfWork(self._session)
            )
            review.grade_supplemental(
                Actor(student_id, "", "student", ""),
                SupplementalChoiceCard(
                    public["card_code"],
                    public["point_code"],
                    public["prompt"],
                    tuple(public["options"]),
                    task.private_rubric["correct_option"],
                    task.private_rubric["explanation"],
                ),
                answer["selected_option"],
                "medium",
                commit=False,
            )
        now = datetime.now(UTC)
        changed = self._session.execute(
            update(LearningTask)
            .where(LearningTask.id == task.id, LearningTask.status.in_(("pending", "in_progress")))
            .values(status="completed", completed_at=now)
        )
        if changed.rowcount != 1:
            raise AppError("STATE_CONFLICT", "任务状态已更新", 409)
        attempt = LearningTaskAttempt(
            task_id=task.id,
            student_id=student_id,
            client_submission_id=submission_id,
            status="assessed",
            answer=answer,
            score=score,
            evidence=evidence,
            feedback=feedback,
            assessed_at=now,
            model_name="objective" if task.task_type in {"knowledge_review", "retest"} else "teacher_pending",
            prompt_version="pbl-learning-v2",
            fallback_used=False,
        )
        self._session.add(attempt)
        self._session.flush()
        self._session.refresh(task)
        self._finish_if_ready(task.plan)
        self._session.flush()
        return self._view(task.plan)

    @staticmethod
    def _finish_if_ready(plan):
        if plan.status != "completed" and all(task.status == "completed" for task in plan.tasks):
            plan.status = "completed"
            plan.completed_at = datetime.now(UTC)
            plan.verification_status = "pending_teacher"
            plan.version += 1

    def verify(self, teacher_id: int, plan_id: int, version: int, decision: str, note: str):
        plan = self._session.scalar(
            select(LearningPlan).where(
                LearningPlan.id == plan_id,
                LearningPlan.source_type == "pbl_suggestion",
                LearningPlan.source_context["teacher_id"].as_integer() == teacher_id,
            )
        )
        if not plan:
            raise AppError("RESOURCE_NOT_FOUND", "学习结果不存在", 404)
        self._finish_if_ready(plan)
        if plan.verification_status != "pending_teacher" or plan.version != version:
            raise AppError("STATE_CONFLICT", "结果尚未完成或版本已更新", 409)
        changed = self._session.execute(
            update(LearningPlan)
            .where(
                LearningPlan.id == plan.id,
                LearningPlan.version == version,
                LearningPlan.verification_status == "pending_teacher",
            )
            .values(
                verification_status=decision,
                verification_note=note,
                verified_by=teacher_id,
                verified_at=datetime.now(UTC),
                version=version + 1,
            )
        )
        if changed.rowcount != 1:
            raise AppError("STATE_CONFLICT", "结果已被核验", 409)
        self._session.flush()
        self._session.refresh(plan)
        return self._view(plan)
