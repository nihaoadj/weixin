import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CaseAssessment,
    CaseAttempt,
    LearningPlan,
    LearningTask,
    LearningTaskAttempt,
    Problem,
    StudentNotification,
    User,
)
from app.schemas.case_training import DIMENSION_SPECS
from app.services.access_control import is_problem_visible_to_student
from app.services.case_training import create_attempt

PRACTICE_PROMPT_VERSION = "practice-v1"
DIMENSION_ORDER = {item[0]: index for index, item in enumerate(DIMENSION_SPECS)}


def _now() -> datetime:
    return datetime.now(UTC)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _public_task(task: LearningTask) -> dict:
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


def serialize_plan(plan: LearningPlan) -> dict:
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


def _target_dimensions(assessment: CaseAssessment) -> list[str]:
    dimensions = sorted(
        assessment.dimensions,
        key=lambda item: (float(item.get("score", 0)), DIMENSION_ORDER.get(item.get("dimension_id", ""), 99)),
    )
    below = [item for item in dimensions if float(item.get("score", 0)) < 70]
    if len(below) >= 2:
        return [item["dimension_id"] for item in below[:2]]
    if len(below) == 1:
        return [
            below[0]["dimension_id"],
            dimensions[1]["dimension_id"] if len(dimensions) > 1 else below[0]["dimension_id"],
        ]
    return [dimensions[0]["dimension_id"]]


def _stage_for_dimension(dimension_id: str) -> str:
    return next(item[3][0] for item in DIMENSION_SPECS if item[0] == dimension_id)


def _dimension_config(problem: Problem, dimension_id: str) -> dict:
    return next(
        (item for item in (problem.rubric or {}).get("dimensions", []) if item.get("id") == dimension_id),
        {"id": dimension_id, "criteria": []},
    )


def _blueprint(problem: Problem, dimension_id: str) -> dict | None:
    for item in (problem.case_definition or {}).get("practice_blueprints", []):
        if item.get("dimension_id") == dimension_id:
            return item
    return None


def _fallback_blueprint(problem: Problem, dimension_id: str) -> dict:
    config = _dimension_config(problem, dimension_id)
    criteria = [
        {
            "id": item.get("id", f"criterion-{index}"),
            "weight": round(100 / max(1, len(config.get("criteria", []))), 2),
            "keywords": item.get("keywords", []),
            "feedback": item.get("feedback", "补充结构化证据。"),
            "critical": item.get("critical", False),
        }
        for index, item in enumerate(config.get("criteria", []), start=1)
    ]
    if criteria:
        criteria[-1]["weight"] = round(criteria[-1]["weight"] + 100 - sum(item["weight"] for item in criteria), 2)
    else:
        criteria = [
            {"id": "evidence", "weight": 100, "keywords": [], "feedback": "补充可核验的原文证据。", "critical": False}
        ]
    return {
        "id": f"fallback-{problem.id}-{dimension_id}",
        "dimension_id": dimension_id,
        "stage_id": _stage_for_dimension(dimension_id),
        "learner_level": "undergraduate",
        "public_instruction": f"围绕{dimension_id}完成一段结构化推理，并说明依据。",
        "allowed_variants": [],
        "fixed_facts": [],
        "fallback_prompt": "请基于教学情境给出不含处方剂量的结构化回答。",
        "answer_schema": "short_text",
        "criteria": criteria,
    }


def _find_transfer_case(db: Session, source: Problem, dimension_id: str, student_id: int) -> Problem | None:
    problems = db.scalars(
        select(Problem)
        .where(
            Problem.content_type == "guided_case",
            Problem.status == "published",
            Problem.medical_review_status == "approved",
            Problem.id != source.id,
        )
        .order_by(Problem.difficulty.asc(), Problem.id.asc())
    ).all()
    candidates = [
        item for item in problems if dimension_id in (item.capability_tags or []) and _blueprint(item, dimension_id)
    ]
    if not candidates:
        return None
    counts = dict(
        db.execute(
            select(CaseAttempt.problem_id, func.count(CaseAttempt.id))
            .where(CaseAttempt.student_id == student_id, CaseAttempt.status == "assessed")
            .group_by(CaseAttempt.problem_id)
        ).all()
    )
    same_difficulty = [item for item in candidates if item.difficulty == source.difficulty]
    pool = same_difficulty or candidates
    return sorted(pool, key=lambda item: (counts.get(item.id, 0), item.id))[0]


def _add_notification(db: Session, student_id: int, plan_id: int, kind: str, title: str, body: str) -> None:
    key = f"{kind}:learning_plan:{plan_id}"
    if db.scalar(select(StudentNotification).where(StudentNotification.dedupe_key == key)) is None:
        db.add(
            StudentNotification(
                student_id=student_id,
                type=kind,
                entity_type="learning_plan",
                entity_id=plan_id,
                title=title,
                body=body,
                dedupe_key=key,
            )
        )


def ensure_learning_plan(db: Session, assessment: CaseAssessment) -> LearningPlan:
    attempt = assessment.attempt
    existing = db.scalar(
        select(LearningPlan)
        .where(LearningPlan.source_assessment_id == assessment.id)
        .options(selectinload(LearningPlan.tasks))
    )
    if existing:
        return existing
    if attempt.learning_task_id:
        raise HTTPException(status_code=409, detail="Task-linked assessment cannot create a new plan")
    now = _now()
    old = db.scalar(
        select(LearningPlan).where(LearningPlan.student_id == attempt.student_id, LearningPlan.status == "active")
    )
    if old:
        old.status = "superseded"
        old.superseded_at = now
    targets = _target_dimensions(assessment)
    source = attempt.problem
    plan = LearningPlan(
        student_id=attempt.student_id,
        source_assessment_id=assessment.id,
        status="active",
        target_dimension_ids=targets,
        due_at=now + timedelta(days=7),
        generation_mode="deterministic",
        model_name="deterministic-fallback",
        prompt_version=PRACTICE_PROMPT_VERSION,
        fallback_used=True,
    )
    db.add(plan)
    db.flush()
    first = targets[0]
    retry_stage = _stage_for_dimension(first)
    source_config = _dimension_config(source, first)
    db.add(
        LearningTask(
            plan_id=plan.id,
            position=1,
            task_type="focused_retry",
            dimension_id=first,
            stage_id=retry_stage,
            problem_id=source.id,
            source_attempt_id=attempt.id,
            public_definition={
                "title": "同病例强化重练",
                "instruction": f"从{retry_stage}阶段重新组织证据。",
                "reason": "来源病例最低维度",
            },
            private_rubric=source_config,
        )
    )
    drill_dimension = targets[1] if len(targets) > 1 else targets[0]
    blueprint = _blueprint(source, drill_dimension) or _fallback_blueprint(source, drill_dimension)
    db.add(
        LearningTask(
            plan_id=plan.id,
            position=2,
            task_type="micro_drill",
            dimension_id=drill_dimension,
            stage_id=blueprint.get("stage_id"),
            problem_id=source.id,
            source_attempt_id=attempt.id,
            public_definition={
                "title": blueprint.get("title", "证据推理微训练"),
                "context": blueprint.get("context", "合成教学情境"),
                "instruction": blueprint.get("public_instruction", "完成结构化回答"),
                "answer_schema": blueprint.get("answer_schema", "short_text"),
                "display_hints": blueprint.get("display_hints", []),
            },
            private_rubric={"criteria": blueprint.get("criteria", []), "fixed_facts": blueprint.get("fixed_facts", [])},
            blueprint_id=blueprint.get("id"),
            blueprint_digest=_digest(blueprint),
        )
    )
    db.flush()
    drill_task = db.scalar(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.position == 2))
    if drill_task is not None:
        from app.services.case_ai import generate_practice_definition

        generated, fallback_used, failure_reason, model_name, prompt_version = generate_practice_definition(
            db,
            attempt.student_id,
            drill_task.id,
            {**blueprint, "digest": drill_task.blueprint_digest},
            "；".join(
                item.get("feedback", "") for item in assessment.dimensions if item.get("dimension_id") in targets
            ),
        )
        drill_task.public_definition = generated
        plan.fallback_used = fallback_used
        plan.failure_reason = failure_reason
        plan.model_name = model_name
        plan.prompt_version = prompt_version
    transfer = _find_transfer_case(db, source, first, attempt.student_id)
    if transfer:
        transfer_blueprint = _blueprint(transfer, first) or _fallback_blueprint(transfer, first)
        transfer_public = {
            "title": "跨病例迁移",
            "context": transfer_blueprint.get("context", "新的已审核教学病例"),
            "instruction": transfer_blueprint.get("public_instruction", "将目标维度迁移到新病例。"),
            "answer_schema": transfer_blueprint.get("answer_schema", "short_text"),
            "display_hints": transfer_blueprint.get("display_hints", []),
        }
        transfer_private = {
            "criteria": transfer_blueprint.get("criteria", []),
            "fixed_facts": transfer_blueprint.get("fixed_facts", []),
        }
        db.add(
            LearningTask(
                plan_id=plan.id,
                position=3,
                task_type="cross_case_transfer",
                dimension_id=first,
                stage_id=transfer_blueprint.get("stage_id"),
                problem_id=transfer.id,
                source_attempt_id=attempt.id,
                public_definition=transfer_public,
                private_rubric=transfer_private,
                blueprint_id=transfer_blueprint.get("id"),
                blueprint_digest=_digest(transfer_blueprint),
            )
        )
    else:
        db.add(
            LearningTask(
                plan_id=plan.id,
                position=3,
                task_type="micro_drill",
                dimension_id=first,
                stage_id=blueprint.get("stage_id"),
                problem_id=source.id,
                source_attempt_id=attempt.id,
                public_definition={
                    "title": "补充微训练",
                    "context": "当前没有匹配的跨病例审核内容",
                    "instruction": blueprint.get("public_instruction", "完成结构化回答"),
                    "answer_schema": blueprint.get("answer_schema", "short_text"),
                    "display_hints": ["replacement_reason: no_approved_transfer_case"],
                },
                private_rubric={
                    "criteria": blueprint.get("criteria", []),
                    "fixed_facts": blueprint.get("fixed_facts", []),
                },
                blueprint_id=blueprint.get("id"),
                blueprint_digest=_digest(blueprint),
            )
        )
    db.flush()
    _add_notification(
        db, plan.student_id, plan.id, "learning_plan_ready", "个性化训练计划已生成", "请按顺序完成三项训练任务。"
    )
    db.commit()
    return db.scalar(select(LearningPlan).where(LearningPlan.id == plan.id).options(selectinload(LearningPlan.tasks)))


def get_plan(db: Session, plan_id: int, student: User) -> LearningPlan:
    plan = db.scalar(
        select(LearningPlan)
        .where(LearningPlan.id == plan_id, LearningPlan.student_id == student.id)
        .options(selectinload(LearningPlan.tasks))
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return plan


def current_plan(db: Session, student: User) -> LearningPlan | None:
    return db.scalar(
        select(LearningPlan)
        .where(LearningPlan.student_id == student.id, LearningPlan.status == "active")
        .order_by(LearningPlan.id.desc())
        .options(selectinload(LearningPlan.tasks))
    )


def _assert_unlocked(task: LearningTask) -> None:
    if task.position > 1 and task.plan.tasks:
        previous = next(item for item in task.plan.tasks if item.position == task.position - 1)
        if previous.status != "completed":
            raise HTTPException(status_code=409, detail="STATE_CONFLICT")


def start_task(db: Session, task_id: int, student: User) -> tuple[LearningTask, dict]:
    task = db.scalar(
        select(LearningTask)
        .join(LearningPlan)
        .where(LearningTask.id == task_id, LearningPlan.student_id == student.id)
        .options(selectinload(LearningTask.plan))
    )
    if task is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    task.plan.tasks = list(
        db.scalars(
            select(LearningTask).where(LearningTask.plan_id == task.plan_id).order_by(LearningTask.position)
        ).all()
    )
    _assert_unlocked(task)
    if task.status == "completed":
        raise HTTPException(status_code=409, detail="STATE_CONFLICT")
    if task.status == "in_progress":
        if task.task_type == "micro_drill" and task.attempt:
            return task, {
                "id": task.attempt.id,
                "status": task.attempt.status,
                "public_definition": task.public_definition,
            }
        if task.task_type != "micro_drill":
            existing_attempt = db.scalar(
                select(CaseAttempt).where(
                    CaseAttempt.learning_task_id == task.id,
                    CaseAttempt.student_id == student.id,
                )
            )
            if existing_attempt is not None:
                return task, {
                    "id": existing_attempt.id,
                    "current_stage": existing_attempt.current_stage,
                    "status": existing_attempt.status,
                }
    task.status = "in_progress"
    task.started_at = task.started_at or _now()
    if task.task_type in {"focused_retry", "cross_case_transfer"}:
        problem = db.get(Problem, task.problem_id)
        if problem is None or not is_problem_visible_to_student(problem, student, db):
            raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        attempt = create_attempt(
            db, problem, student, task.source_attempt_id if task.task_type == "focused_retry" else None
        )
        attempt.learning_task_id = task.id
        db.commit()
        return task, {"id": attempt.id, "current_stage": attempt.current_stage, "status": attempt.status}
    attempt = task.attempt
    if attempt is None:
        attempt = LearningTaskAttempt(task_id=task.id, student_id=student.id)
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    else:
        db.commit()
    return task, {"id": attempt.id, "status": attempt.status, "public_definition": task.public_definition}


def _answer_text(answer: object) -> str:
    if isinstance(answer, str):
        return answer.strip()
    if isinstance(answer, list):
        return " ".join(_answer_text(item) for item in answer)
    if isinstance(answer, dict):
        return " ".join(_answer_text(value) for key, value in answer.items() if key not in {"id", "stage_id"})
    return ""


def _snippet(text: str, keyword: str) -> str | None:
    for chunk in re.split(r"[。！？；\n]", text):
        if keyword.lower() in chunk.lower() and chunk.strip():
            return chunk.strip()[:160]
    return None


def submit_micro_task(db: Session, task_id: int, student: User, answer: dict) -> LearningTaskAttempt:
    task = db.scalar(
        select(LearningTask)
        .join(LearningPlan)
        .where(LearningTask.id == task_id, LearningPlan.student_id == student.id)
        .options(selectinload(LearningTask.plan), selectinload(LearningTask.attempt))
    )
    if task is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    _assert_unlocked(task)
    if task.task_type != "micro_drill":
        raise HTTPException(status_code=409, detail="STATE_CONFLICT")
    if task.attempt is None:
        task.attempt = LearningTaskAttempt(task_id=task.id, student_id=student.id)
        db.flush()
    attempt = task.attempt
    if attempt.status == "assessed":
        return attempt
    text = _answer_text(answer)
    criteria = (task.private_rubric or {}).get("criteria", [])
    hits = []
    evidence: list[str] = []
    weighted = 0.0
    for criterion in criteria:
        keywords = [str(item) for item in criterion.get("keywords", [])]
        match = not keywords or any(keyword.lower() in text.lower() for keyword in keywords)
        if match:
            hits.append(criterion)
            weighted += float(criterion.get("weight", 0))
            for keyword in keywords:
                snippet = _snippet(text, keyword)
                if snippet and snippet not in evidence:
                    evidence.append(snippet)
    score = min(100.0, round(weighted, 1))
    if any(item.get("critical") and item not in hits for item in criteria):
        score = min(score, 69.0)
    missing = next((item for item in criteria if item not in hits), None)
    attempt.answer = answer
    attempt.score = score
    attempt.evidence = evidence[:3] or [text[:160] or "未提供可核验原文证据"]
    attempt.feedback = "证据较完整。" if missing is None else str(missing.get("feedback", "补充结构化证据。"))
    attempt.next_step = "继续保持结构化推理。" if missing is None else "补充缺失证据后再次练习。"
    attempt.status = "assessed"
    attempt.assessed_at = _now()
    task.status = "completed"
    task.completed_at = _now()
    db.commit()
    return attempt


def complete_plan(db: Session, plan: LearningPlan, student: User) -> LearningPlan:
    if any(task.status != "completed" for task in plan.tasks):
        raise HTTPException(status_code=409, detail="STATE_CONFLICT")
    if plan.status != "completed":
        plan.status = "completed"
        plan.completed_at = _now()
        _add_notification(
            db, student.id, plan.id, "learning_plan_completed", "个性化训练已完成", "你已完成本次三项训练。"
        )
        db.commit()
    return plan


def list_notifications(db: Session, student: User, unread_only: bool, limit: int) -> list[StudentNotification]:
    statement = select(StudentNotification).where(StudentNotification.student_id == student.id)
    if unread_only:
        statement = statement.where(StudentNotification.read_at.is_(None))
    return list(db.scalars(statement.order_by(StudentNotification.created_at.desc()).limit(limit)).all())


def notification_count(db: Session, student_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(StudentNotification.id)).where(
                StudentNotification.student_id == student_id, StudentNotification.read_at.is_(None)
            )
        )
        or 0
    )


def mark_notification_read(db: Session, notification_id: int, student: User) -> None:
    item = db.scalar(
        select(StudentNotification).where(
            StudentNotification.id == notification_id, StudentNotification.student_id == student.id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    item.read_at = item.read_at or _now()
    db.commit()


def mark_all_notifications_read(db: Session, student: User) -> int:
    items = db.scalars(
        select(StudentNotification).where(
            StudentNotification.student_id == student.id, StudentNotification.read_at.is_(None)
        )
    ).all()
    now = _now()
    for item in items:
        item.read_at = now
    db.commit()
    return len(items)


def profile(db: Session, student: User) -> dict:
    assessments = list(
        db.scalars(
            select(CaseAssessment)
            .join(CaseAttempt)
            .where(CaseAttempt.student_id == student.id, CaseAttempt.status == "assessed")
            .order_by(CaseAssessment.created_at.desc())
            .limit(10)
        ).all()
    )
    latest = assessments[0] if assessments else None
    mastery_rows = db.execute(
        select(LearningTask.dimension_id, func.avg(LearningTaskAttempt.score), func.count(LearningTaskAttempt.id))
        .join(LearningTaskAttempt, LearningTaskAttempt.task_id == LearningTask.id)
        .where(LearningTaskAttempt.student_id == student.id, LearningTaskAttempt.status == "assessed")
        .group_by(LearningTask.dimension_id)
    ).all()
    mastery = {
        dimension: {"average_score": round(float(score or 0), 1), "attempt_count": count}
        for dimension, score, count in mastery_rows
    }
    active = current_plan(db, student)
    due_at = (
        active.due_at.replace(tzinfo=UTC)
        if active and active.due_at.tzinfo is None
        else active.due_at
        if active
        else None
    )
    if active and due_at < _now() + timedelta(hours=24):
        _add_notification(db, student.id, active.id, "learning_plan_due", "训练计划即将到期", "请完成剩余训练任务。")
        db.commit()
    return {
        "formal_dimensions": latest.dimensions if latest else [],
        "recent_assessments": [
            {"attempt_id": item.attempt_id, "total_score": item.total_score, "created_at": item.created_at}
            for item in assessments
        ],
        "practice_mastery": mastery,
        "active_plan": serialize_plan(active) if active else None,
        "unread_count": notification_count(db, student.id),
    }
