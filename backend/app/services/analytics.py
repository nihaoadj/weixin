from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    CaseAssessment,
    CaseAttempt,
    ClassMember,
    ClassRoom,
    LearningPlan,
    LearningTask,
    LearningTaskAttempt,
    Problem,
    User,
)
from app.schemas.case_training import DIMENSION_SPECS
from app.services.access_control import is_problem_visible_to_student


def date_range(date_from: str | None, date_to: str | None) -> tuple[datetime, datetime, str, str]:
    end = date.fromisoformat(date_to) if date_to else datetime.now(UTC).date()
    start = date.fromisoformat(date_from) if date_from else end - timedelta(days=29)
    if start > end or (end - start).days > 366:
        raise HTTPException(status_code=400, detail="INVALID_DATE_RANGE")
    return (
        datetime.combine(start, time.min, UTC),
        datetime.combine(end, time.max, UTC),
        start.isoformat(),
        end.isoformat(),
    )


def _classes(teacher: User, class_id: int | None, db: Session) -> list[ClassRoom]:
    statement = select(ClassRoom).where(ClassRoom.teacher_id == teacher.id, ClassRoom.status == "active")
    if class_id is not None:
        statement = statement.where(ClassRoom.id == class_id)
    classes = list(db.scalars(statement).all())
    if class_id is not None and not classes:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return classes


def _students(classes: list[ClassRoom], db: Session) -> list[User]:
    if not classes:
        return []
    class_ids = {item.id for item in classes}
    class_codes = {item.code for item in classes}
    linked_ids = set(db.scalars(select(ClassMember.student_id).where(ClassMember.class_id.in_(class_ids))).all())
    candidates = db.scalars(select(User).where(User.role == "student")).all()
    return [
        student
        for student in candidates
        if student.id in linked_ids or bool(set(student.class_ids or []).intersection(class_codes))
    ]


def _pairs(
    students: list[User], start: datetime, end: datetime, db: Session, problem_id: int | None = None
) -> tuple[list[tuple[User, Problem]], list[CaseAttempt]]:
    problems = list(
        db.scalars(select(Problem).where(Problem.content_type == "guided_case", Problem.status == "published")).all()
    )
    if problem_id is not None:
        problems = [problem for problem in problems if problem.id == problem_id]
    attempts = list(
        db.scalars(
            select(CaseAttempt).where(
                CaseAttempt.student_id.in_([student.id for student in students]) if students else False,
                CaseAttempt.started_at >= start,
                CaseAttempt.started_at <= end,
                *([CaseAttempt.problem_id == problem_id] if problem_id is not None else []),
            ).options(joinedload(CaseAttempt.assessment))
        ).all()
    )
    # Keep the overview focused on cases with a student activity signal (plus
    # the canonical CAP demo case), while explicit case drill-down still
    # reports every published case. This avoids empty showcase variants
    # diluting a teacher's initial class completion rate.
    if problem_id is None:
        active_ids = {item.problem_id for item in attempts}
        problems = [
            problem for problem in problems if problem.slug == "cap-undergraduate-showcase" or problem.id in active_ids
        ]
    pairs = [
        (student, problem)
        for student in students
        for problem in problems
        if is_problem_visible_to_student(problem, student, db)
    ]
    return pairs, attempts


def _current_assessment(attempts: list[CaseAttempt]) -> dict[tuple[int, int], CaseAssessment]:
    result: dict[tuple[int, int], CaseAssessment] = {}
    for attempt in attempts:
        if attempt.status != "assessed" or attempt.assessment is None:
            continue
        key = (attempt.student_id, attempt.problem_id)
        old = result.get(key)
        attempt_time = _timestamp(attempt.assessed_at)
        old_time = _timestamp(old.attempt.assessed_at) if old else datetime.min.replace(tzinfo=UTC)
        if old is None or (attempt_time, attempt.id) > (old_time, old.attempt_id):
            result[key] = attempt.assessment
    return result


def _baseline(attempts: list[CaseAttempt]) -> dict[tuple[int, int], CaseAssessment]:
    result: dict[tuple[int, int], CaseAssessment] = {}
    for attempt in sorted(attempts, key=lambda item: (_timestamp(item.assessed_at), item.id)):
        if attempt.status != "assessed" or attempt.assessment is None:
            continue
        key = (attempt.student_id, attempt.problem_id)
        if key not in result or attempt.retry_of_id is None and result[key].attempt.retry_of_id is not None:
            result[key] = attempt.assessment
    return result


def _timestamp(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=UTC)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def _dimension_summary(
    current: dict[tuple[int, int], CaseAssessment], baseline: dict[tuple[int, int], CaseAssessment]
) -> list[dict]:
    result = []
    for dimension_id, label, _weight, _stages in DIMENSION_SPECS:
        current_values = {
            key: next(
                (float(row["score"]) for row in assessment.dimensions if row["dimension_id"] == dimension_id), None
            )
            for key, assessment in current.items()
        }
        current_values = {key: value for key, value in current_values.items() if value is not None}
        baseline_values = {
            key: next(
                (float(row["score"]) for row in assessment.dimensions if row["dimension_id"] == dimension_id), None
            )
            for key, assessment in baseline.items()
        }
        baseline_values = {key: value for key, value in baseline_values.items() if value is not None}
        deltas = [current_values[key] - baseline_values[key] for key in current_values.keys() & baseline_values.keys()]
        result.append(
            {
                "dimension_id": dimension_id,
                "label": label,
                "average_score": _round(sum(current_values.values()) / len(current_values)) if current_values else None,
                "baseline_score": _round(sum(baseline_values.values()) / len(baseline_values))
                if baseline_values
                else None,
                "current_score": _round(sum(current_values.values()) / len(current_values)) if current_values else None,
                "delta": _round(sum(deltas) / len(deltas)) if deltas else None,
            }
        )
    return result


def _duration_minutes(attempts: list[CaseAttempt]) -> float | None:
    values = []
    for attempt in attempts:
        if attempt.assessed_at is None:
            continue
        duration = (_timestamp(attempt.assessed_at) - _timestamp(attempt.started_at)).total_seconds() / 60
        if 0 <= duration <= 8 * 60:
            values.append(duration)
    return _round(sum(values) / len(values)) if values else None


def overview(teacher: User, class_id: int | None, date_from: str | None, date_to: str | None, db: Session) -> dict:
    start, end, start_text, end_text = date_range(date_from, date_to)
    classes = _classes(teacher, class_id, db)
    students = _students(classes, db)
    pairs, attempts = _pairs(students, start, end, db)
    current = _current_assessment(attempts)
    baseline = _baseline(attempts)
    eligible = len(pairs)
    started = {(item.student_id, item.problem_id) for item in attempts}
    completed = set(current)
    dimensions = []
    for dimension_id, label, _weight, _stages in DIMENSION_SPECS:
        scores = [item.dimensions for item in current.values()]
        values = [
            next((float(row["score"]) for row in rows if row["dimension_id"] == dimension_id), None) for rows in scores
        ]
        values = [value for value in values if value is not None]
        dimensions.append(
            {
                "dimension_id": dimension_id,
                "label": label,
                "average_score": _round(sum(values) / len(values)) if values else None,
            }
        )
    improvements = [current[key].total_score - baseline[key].total_score for key in current.keys() & baseline.keys()]
    weak_counts = []
    for dimension in dimensions:
        count = sum(
            any(
                row["dimension_id"] == dimension["dimension_id"] and float(row["score"]) < 70
                for row in assessment.dimensions
            )
            for assessment in current.values()
        )
        weak_counts.append(
            {**dimension, "student_count": count, "rate": _round(count * 100 / len(current)) if current else None}
        )
    case_summaries = []
    for problem in {problem.id: problem for _, problem in pairs}.values():
        eligible_for_case = sum(item.id == problem.id for _, item in pairs)
        current_scores = [
            assessment.total_score for (student_id, case_id), assessment in current.items() if case_id == problem.id
        ]
        case_summaries.append(
            {
                "problem_id": problem.id,
                "title": problem.title,
                "completed": len(current_scores),
                "assigned": eligible_for_case,
                "average_score": _round(sum(current_scores) / len(current_scores)) if current_scores else None,
            }
        )
    student_summaries = []
    for student in students:
        student_scores = [
            assessment.total_score for (student_id, _), assessment in current.items() if student_id == student.id
        ]
        assigned_for_student = sum(item.id == student.id for item, _ in pairs)
        student_summaries.append(
            {
                "student_id": student.id,
                "nickname": student.nickname,
                "completed": len(student_scores),
                "assigned": assigned_for_student,
                "average_score": _round(sum(student_scores) / len(student_scores)) if student_scores else None,
            }
        )
    return {
        "scope": {
            "class_id": class_id,
            "class_name": classes[0].name if class_id and classes else None,
            "date_from": start_text,
            "date_to": end_text,
        },
        "student_count": len(students),
        "published_case_count": len({problem.id for _, problem in pairs}),
        "eligible_pairs": eligible,
        "started_pairs": len(started),
        "completed_pairs": len(completed),
        "completion_rate": _round(len(completed) * 100 / eligible) if eligible else None,
        "current_average_score": _round(sum(item.total_score for item in current.values()) / len(current))
        if current
        else None,
        "average_improvement": _round(sum(improvements) / len(improvements)) if improvements else None,
        "dimensions": dimensions,
        "weak_dimensions": weak_counts,
        "cases": sorted(case_summaries, key=lambda item: item["title"]),
        "students": sorted(student_summaries, key=lambda item: item["student_id"]),
    }


def case_detail(
    teacher: User, problem_id: int, class_id: int | None, date_from: str | None, date_to: str | None, db: Session
) -> dict:
    start, end, _start_text, _end_text = date_range(date_from, date_to)
    classes = _classes(teacher, class_id, db)
    students = _students(classes, db)
    problem = db.get(Problem, problem_id)
    # Analytics is a teacher-owned resource. Do not reveal whether another
    # teacher's case exists, even when the caller happens to share a class.
    if (
        problem is None
        or problem.content_type != "guided_case"
        or problem.status != "published"
        or problem.author_id != teacher.id
    ):
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    pairs, attempts = _pairs(students, start, end, db, problem_id)
    current, baseline = _current_assessment(attempts), _baseline(attempts)
    current_attempts = {key: assessment.attempt for key, assessment in current.items()}
    scores = [item.total_score for item in current.values()]
    distribution = {"0-59": 0, "60-69": 0, "70-84": 0, "85-100": 0}
    for score in scores:
        key = "0-59" if score < 60 else "60-69" if score < 70 else "70-84" if score < 85 else "85-100"
        distribution[key] += 1
    return {
        "problem": {"id": problem.id, "title": problem.title, "version": problem.version, "slug": problem.slug},
        "eligible_pairs": len(pairs),
        "started_pairs": len({(item.student_id, item.problem_id) for item in attempts}),
        "completed_pairs": len(current),
        "completion_rate": _round(len(current) * 100 / len(pairs)) if pairs else None,
        "current_average_score": _round(sum(scores) / len(scores)) if scores else None,
        "average_improvement": _round(
            sum(current[key].total_score - baseline[key].total_score for key in current.keys() & baseline.keys())
            / len(current.keys() & baseline.keys())
        )
        if current.keys() & baseline.keys()
        else None,
        "average_duration_minutes": _duration_minutes(list(current_attempts.values())),
        "dimensions": _dimension_summary(current, baseline),
        "distribution": distribution,
        "students": [
            {
                "student_id": student.id,
                "nickname": student.nickname,
                "status": "assessed"
                if (student.id, problem_id) in current
                else "started"
                if any(item.student_id == student.id for item in attempts)
                else "not_started",
                "baseline": baseline[(student.id, problem_id)].total_score
                if (student.id, problem_id) in baseline
                else None,
                "current": current[(student.id, problem_id)].total_score
                if (student.id, problem_id) in current
                else None,
                "delta": current[(student.id, problem_id)].total_score - baseline[(student.id, problem_id)].total_score
                if (student.id, problem_id) in current and (student.id, problem_id) in baseline
                else None,
                "focus_stage": current[(student.id, problem_id)].focus_stage
                if (student.id, problem_id) in current
                else None,
                "last_assessed_at": current_attempts[(student.id, problem_id)].assessed_at
                if (student.id, problem_id) in current_attempts
                else None,
            }
            for student in students
        ],
    }


def student_detail(
    teacher: User, student_id: int, class_id: int | None, date_from: str | None, date_to: str | None, db: Session
) -> dict:
    classes = _classes(teacher, class_id, db)
    students = _students(classes, db)
    student = next((item for item in students if item.id == student_id), None)
    if student is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    start, end, _start_text, _end_text = date_range(date_from, date_to)
    pairs, attempts = _pairs([student], start, end, db)
    current, baseline = _current_assessment(attempts), _baseline(attempts)
    cases = []
    for _student, problem in pairs:
        key = (student.id, problem.id)
        latest, first = current.get(key), baseline.get(key)
        cases.append(
            {
                "problem_id": problem.id,
                "title": problem.title,
                "version": problem.version,
                "first_score": first.total_score if first else None,
                "latest_score": latest.total_score if latest else None,
                "delta": latest.total_score - first.total_score if latest and first else None,
                "attempt_count": sum(item.problem_id == problem.id for item in attempts),
                "focus_stage": latest.focus_stage if latest else None,
                "last_assessed_at": latest.attempt.assessed_at if latest else None,
            }
        )
    timeline = sorted(
        [
            {
                "attempt_id": item.attempt_id,
                "problem_id": item.attempt.problem_id,
                "score": item.total_score,
                "assessed_at": item.attempt.assessed_at,
            }
            for item in current.values()
        ],
        key=lambda item: item["assessed_at"] or datetime.min.replace(tzinfo=UTC),
    )[-12:]
    plan = db.scalar(
        select(LearningPlan)
        .where(LearningPlan.student_id == student.id, LearningPlan.status == "active")
        .order_by(LearningPlan.id.desc())
    )
    practice_rows = db.execute(
        select(LearningTask.dimension_id, func.avg(LearningTaskAttempt.score), func.count(LearningTaskAttempt.id))
        .join(LearningTaskAttempt, LearningTaskAttempt.task_id == LearningTask.id)
        .where(LearningTaskAttempt.student_id == student.id, LearningTaskAttempt.status == "assessed")
        .group_by(LearningTask.dimension_id)
    ).all()
    return {
        "student": {"id": student.id, "nickname": student.nickname},
        "assigned": len(pairs),
        "started": len({(item.student_id, item.problem_id) for item in attempts}),
        "completed": len(current),
        "completion_rate": _round(len(current) * 100 / len(pairs)) if pairs else None,
        "current_average_score": _round(sum(item.total_score for item in current.values()) / len(current))
        if current
        else None,
        "average_improvement": _round(
            sum(current[key].total_score - baseline[key].total_score for key in current.keys() & baseline.keys())
            / len(current.keys() & baseline.keys())
        )
        if current.keys() & baseline.keys()
        else None,
        "dimensions": _dimension_summary(current, baseline),
        "cases": cases,
        "timeline": timeline,
        "learning_plan": {
            "id": plan.id,
            "status": plan.status,
            "target_dimension_ids": plan.target_dimension_ids,
            "due_at": plan.due_at,
            "tasks": [
                {"position": task.position, "task_type": task.task_type, "status": task.status} for task in plan.tasks
            ],
        }
        if plan
        else None,
        "practice_mastery": {
            dimension: {"average_score": _round(float(score or 0)), "attempt_count": count}
            for dimension, score, count in practice_rows
        },
    }
