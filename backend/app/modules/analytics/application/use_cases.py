from __future__ import annotations

from datetime import UTC, datetime

from app.modules.analytics.application.ports import AnalyticsReader
from app.modules.analytics.application.records import (
    AssessmentRecord,
    AttemptAnalyticsRecord,
    ProblemAnalyticsRecord,
    ScopeClass,
    ScopeStudent,
)
from app.modules.analytics.domain.policy import AnalyticsPolicy
from app.shared.actor import Actor
from app.shared.errors import AppError


class AnalyticsApplication:
    def __init__(self, reader: AnalyticsReader, policy: AnalyticsPolicy | None = None) -> None:
        self._reader = reader
        self._policy = policy or AnalyticsPolicy()

    def overview(
        self, actor: Actor, class_id: int | None, date_from: str | None, date_to: str | None
    ) -> dict[str, object]:
        actor.require_role("teacher")
        start, end, start_text, end_text = self._policy.date_range(date_from, date_to)
        classes = self._classes(actor, class_id)
        students = self._reader.load_students(classes)
        problems, attempts = self._activity(students, start, end, None)
        pairs, active_attempts = self._pairs(students, classes, problems, attempts)
        current = self._current_assessment(active_attempts)
        baseline = self._baseline(active_attempts)
        eligible = len(pairs)
        started = {(item.student_id, item.problem_id) for item in active_attempts}
        dimensions = self._dimensions(current)
        improvements = [
            current[key].total_score - baseline[key].total_score for key in current.keys() & baseline.keys()
        ]
        weak_dimensions: list[dict[str, object]] = []
        for dimension in dimensions:
            count = sum(
                any(
                    row.get("dimension_id") == dimension["dimension_id"] and self._number(row.get("score", 0)) < 70
                    for row in assessment.dimensions
                )
                for assessment in current.values()
            )
            weak_dimensions.append(
                {
                    **dimension,
                    "student_count": count,
                    "rate": self._round(count * 100 / len(current)) if current else None,
                }
            )
        case_summaries: list[dict[str, object]] = []
        for problem in {item.id: item for _, item in pairs}.values():
            scores = [
                assessment.total_score for (student_id, case_id), assessment in current.items() if case_id == problem.id
            ]
            case_summaries.append(
                {
                    "problem_id": problem.id,
                    "title": problem.title,
                    "completed": len(scores),
                    "assigned": sum(item.id == problem.id for _, item in pairs),
                    "average_score": self._round(sum(scores) / len(scores)) if scores else None,
                }
            )
        student_summaries: list[dict[str, object]] = []
        for student in students:
            scores = [
                assessment.total_score for (student_id, _), assessment in current.items() if student_id == student.id
            ]
            student_summaries.append(
                {
                    "student_id": student.id,
                    "nickname": student.nickname,
                    "completed": len(scores),
                    "assigned": sum(item.id == student.id for item, _ in pairs),
                    "average_score": self._round(sum(scores) / len(scores)) if scores else None,
                }
            )
        completed = set(current)
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
            "completion_rate": self._round(len(completed) * 100 / eligible) if eligible else None,
            "current_average_score": self._round(sum(item.total_score for item in current.values()) / len(current))
            if current
            else None,
            "average_improvement": self._round(sum(improvements) / len(improvements)) if improvements else None,
            "dimensions": dimensions,
            "weak_dimensions": weak_dimensions,
            "cases": sorted(case_summaries, key=lambda item: str(item["title"])),
            "students": sorted(student_summaries, key=lambda item: self._integer(item["student_id"])),
        }

    def knowledge(self, actor: Actor, class_id: int) -> dict[str, object]:
        actor.require_role("teacher")
        classes = self._classes(actor, class_id)
        students = self._reader.load_students(classes)
        summary = self._reader.load_knowledge(tuple(item.id for item in students), datetime.now(UTC))
        return {
            "class_id": class_id,
            "class_name": classes[0].name,
            "participant_count": summary.participant_count,
            "due_backlog": summary.due_backlog,
            "objective_correct_rate": self._round(
                summary.objective_correct_count * 100 / summary.objective_attempt_count
            )
            if summary.objective_attempt_count
            else None,
            "weak_points": [{"point_code": code, "student_count": count} for code, count in summary.weak_points]
            if summary.participant_count >= 5
            else [],
            "rankings_suppressed": summary.participant_count < 5,
        }

    def case_detail(
        self, actor: Actor, problem_id: int, class_id: int | None, date_from: str | None, date_to: str | None
    ) -> dict[str, object]:
        actor.require_role("teacher")
        start, end, _start_text, _end_text = self._policy.date_range(date_from, date_to)
        classes = self._classes(actor, class_id)
        students = self._reader.load_students(classes)
        problems, attempts = self._activity(students, start, end, problem_id)
        problem = next((item for item in problems if item.id == problem_id), None)
        if (
            problem is None
            or problem.content_type != "guided_case"
            or problem.status != "published"
            or problem.author_id != actor.id
        ):
            raise AppError("RESOURCE_NOT_FOUND", "病例不存在", 404)
        pairs, active_attempts = self._pairs(students, classes, problems, attempts, problem_id)
        current = self._current_assessment(active_attempts)
        baseline = self._baseline(active_attempts)
        current_attempts = self._current_attempts(active_attempts)
        scores = [item.total_score for item in current.values()]
        distribution = {"0-59": 0, "60-69": 0, "70-84": 0, "85-100": 0}
        for score in scores:
            key = "0-59" if score < 60 else "60-69" if score < 70 else "70-84" if score < 85 else "85-100"
            distribution[key] += 1
        overlap = current.keys() & baseline.keys()
        return {
            "problem": {"id": problem.id, "title": problem.title, "version": problem.version, "slug": problem.slug},
            "eligible_pairs": len(pairs),
            "started_pairs": len({(item.student_id, item.problem_id) for item in active_attempts}),
            "completed_pairs": len(current),
            "completion_rate": self._round(len(current) * 100 / len(pairs)) if pairs else None,
            "current_average_score": self._round(sum(scores) / len(scores)) if scores else None,
            "average_improvement": self._round(
                sum(current[key].total_score - baseline[key].total_score for key in overlap) / len(overlap)
            )
            if overlap
            else None,
            "average_duration_minutes": self._duration(tuple(current_attempts.values())),
            "dimensions": self._dimension_summary(current, baseline),
            "distribution": distribution,
            "students": [
                self._case_student_row(student, problem_id, current, baseline, active_attempts) for student in students
            ],
        }

    def student_detail(
        self, actor: Actor, student_id: int, class_id: int | None, date_from: str | None, date_to: str | None
    ) -> dict[str, object]:
        actor.require_role("teacher")
        classes = self._classes(actor, class_id)
        students = self._reader.load_students(classes)
        student = next((item for item in students if item.id == student_id), None)
        if student is None:
            raise AppError("RESOURCE_NOT_FOUND", "学生不存在", 404)
        start, end, _start_text, _end_text = self._policy.date_range(date_from, date_to)
        problems, attempts = self._activity((student,), start, end, None)
        pairs, active_attempts = self._pairs((student,), classes, problems, attempts)
        current = self._current_assessment(active_attempts)
        baseline = self._baseline(active_attempts)
        current_attempts = self._current_attempts(active_attempts)
        cases: list[dict[str, object]] = []
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
                    "attempt_count": sum(item.problem_id == problem.id for item in active_attempts),
                    "focus_stage": latest.focus_stage if latest else None,
                    "last_assessed_at": current_attempts[key].assessed_at if latest else None,
                }
            )
        timeline = sorted(
            [
                {
                    "attempt_id": attempt.id,
                    "problem_id": attempt.problem_id,
                    "score": attempt.assessment.total_score,
                    "assessed_at": attempt.assessed_at,
                }
                for attempt in current_attempts.values()
                if attempt.assessment is not None
            ],
            key=lambda item: item["assessed_at"] or datetime.min.replace(tzinfo=UTC),
        )[-12:]
        plan, mastery = self._reader.load_learning(student.id)
        return {
            "student": {"id": student.id, "nickname": student.nickname},
            "assigned": len(pairs),
            "started": len({(item.student_id, item.problem_id) for item in active_attempts}),
            "completed": len(current),
            "completion_rate": self._round(len(current) * 100 / len(pairs)) if pairs else None,
            "current_average_score": self._round(sum(item.total_score for item in current.values()) / len(current))
            if current
            else None,
            "average_improvement": self._average_improvement(current, baseline),
            "dimensions": self._dimension_summary(current, baseline),
            "cases": cases,
            "timeline": timeline,
            "learning_plan": {
                "id": plan.id,
                "status": plan.status,
                "target_dimension_ids": list(plan.target_dimension_ids),
                "due_at": plan.due_at,
                "tasks": [
                    {"position": position, "task_type": task_type, "status": status}
                    for position, task_type, status in plan.tasks
                ],
            }
            if plan
            else None,
            "practice_mastery": {
                item.dimension_id: {
                    "average_score": self._round(item.average_score),
                    "attempt_count": item.attempt_count,
                }
                for item in mastery
            },
        }

    def _classes(self, actor: Actor, class_id: int | None) -> tuple[ScopeClass, ...]:
        classes = self._reader.load_classes(actor.id, class_id)
        if class_id is not None and not classes:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        return classes

    def _activity(
        self, students: tuple[ScopeStudent, ...], start: datetime, end: datetime, problem_id: int | None
    ) -> tuple[tuple[ProblemAnalyticsRecord, ...], tuple[AttemptAnalyticsRecord, ...]]:
        return self._reader.load_activity(tuple(item.id for item in students), start, end, problem_id)

    def _pairs(
        self,
        students: tuple[ScopeStudent, ...],
        classes: tuple[ScopeClass, ...],
        problems: tuple[ProblemAnalyticsRecord, ...],
        attempts: tuple[AttemptAnalyticsRecord, ...],
        problem_id: int | None = None,
    ) -> tuple[list[tuple[ScopeStudent, ProblemAnalyticsRecord]], tuple[AttemptAnalyticsRecord, ...]]:
        if problem_id is None:
            active_ids = {item.problem_id for item in attempts}
            problems = tuple(
                item for item in problems if item.slug == "cap-undergraduate-showcase" or item.id in active_ids
            )
        class_codes = {item.code for item in classes}
        pairs = [
            (student, problem)
            for student in students
            for problem in problems
            if self._policy.visible(
                status=problem.status,
                target=problem.target,
                target_ids=problem.target_ids,
                student_external_id=student.external_id,
                class_codes=class_codes | set(student.class_ids),
            )
        ]
        return pairs, attempts

    @staticmethod
    def _timestamp(value: datetime | None) -> datetime:
        if value is None:
            return datetime.min.replace(tzinfo=UTC)
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value

    def _current_assessment(
        self, attempts: tuple[AttemptAnalyticsRecord, ...]
    ) -> dict[tuple[int, int], AssessmentRecord]:
        return {
            key: attempt.assessment
            for key, attempt in self._current_attempts(attempts).items()
            if attempt.assessment is not None
        }

    def _current_attempts(
        self, attempts: tuple[AttemptAnalyticsRecord, ...]
    ) -> dict[tuple[int, int], AttemptAnalyticsRecord]:
        result: dict[tuple[int, int], AttemptAnalyticsRecord] = {}
        for attempt in attempts:
            if attempt.status != "assessed" or attempt.assessment is None:
                continue
            key = (attempt.student_id, attempt.problem_id)
            old = result.get(key)
            if old is None or (self._timestamp(attempt.assessed_at), attempt.id) > (
                self._timestamp(old.assessed_at),
                old.id,
            ):
                result[key] = attempt
        return result

    def _baseline(self, attempts: tuple[AttemptAnalyticsRecord, ...]) -> dict[tuple[int, int], AssessmentRecord]:
        result: dict[tuple[int, int], AssessmentRecord] = {}
        selected_is_retry: dict[tuple[int, int], bool] = {}
        for attempt in sorted(attempts, key=lambda item: (self._timestamp(item.assessed_at), item.id)):
            if attempt.status != "assessed" or attempt.assessment is None:
                continue
            key = (attempt.student_id, attempt.problem_id)
            old = result.get(key)
            is_retry = attempt.retry_of_id is not None
            if old is None or (selected_is_retry[key] and not is_retry):
                result[key] = attempt.assessment
                selected_is_retry[key] = is_retry
        return result

    def _dimensions(self, current: dict[tuple[int, int], AssessmentRecord]) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for dimension_id, label, _weight, _stages in self._policy.dimension_specs:
            values = [
                self._number(row.get("score", 0))
                for assessment in current.values()
                for row in assessment.dimensions
                if row.get("dimension_id") == dimension_id
            ]
            result.append(
                {
                    "dimension_id": dimension_id,
                    "label": label,
                    "average_score": self._round(sum(values) / len(values)) if values else None,
                }
            )
        return result

    def _dimension_summary(
        self, current: dict[tuple[int, int], AssessmentRecord], baseline: dict[tuple[int, int], AssessmentRecord]
    ) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for dimension_id, label, _weight, _stages in self._policy.dimension_specs:
            current_values_with_missing = {
                key: self._dimension_score(assessment, dimension_id) for key, assessment in current.items()
            }
            baseline_values_with_missing = {
                key: self._dimension_score(assessment, dimension_id) for key, assessment in baseline.items()
            }
            current_values: dict[tuple[int, int], float] = {
                key: value for key, value in current_values_with_missing.items() if value is not None
            }
            baseline_values: dict[tuple[int, int], float] = {
                key: value for key, value in baseline_values_with_missing.items() if value is not None
            }
            deltas = [
                current_values[key] - baseline_values[key] for key in current_values.keys() & baseline_values.keys()
            ]
            result.append(
                {
                    "dimension_id": dimension_id,
                    "label": label,
                    "average_score": self._round(sum(current_values.values()) / len(current_values))
                    if current_values
                    else None,
                    "baseline_score": self._round(sum(baseline_values.values()) / len(baseline_values))
                    if baseline_values
                    else None,
                    "current_score": self._round(sum(current_values.values()) / len(current_values))
                    if current_values
                    else None,
                    "delta": self._round(sum(deltas) / len(deltas)) if deltas else None,
                }
            )
        return result

    @staticmethod
    def _dimension_score(assessment: AssessmentRecord, dimension_id: str) -> float | None:
        return next(
            (
                AnalyticsApplication._number(row.get("score", 0))
                for row in assessment.dimensions
                if row.get("dimension_id") == dimension_id
            ),
            None,
        )

    def _case_student_row(
        self,
        student: ScopeStudent,
        problem_id: int,
        current: dict[tuple[int, int], AssessmentRecord],
        baseline: dict[tuple[int, int], AssessmentRecord],
        attempts: tuple[AttemptAnalyticsRecord, ...],
    ) -> dict[str, object]:
        key = (student.id, problem_id)
        latest, first = current.get(key), baseline.get(key)
        latest_attempt = self._current_attempts(tuple(attempts)).get(key)
        return {
            "student_id": student.id,
            "nickname": student.nickname,
            "status": "assessed"
            if latest
            else "started"
            if any(item.student_id == student.id for item in attempts)
            else "not_started",
            "baseline": first.total_score if first else None,
            "current": latest.total_score if latest else None,
            "delta": latest.total_score - first.total_score if latest and first else None,
            "focus_stage": latest.focus_stage if latest else None,
            "last_assessed_at": latest_attempt.assessed_at if latest_attempt else None,
        }

    def _duration(self, attempts: tuple[AttemptAnalyticsRecord, ...]) -> float | None:
        values = []
        for attempt in attempts:
            if attempt.assessed_at is None:
                continue
            duration = (self._timestamp(attempt.assessed_at) - self._timestamp(attempt.started_at)).total_seconds() / 60
            if 0 <= duration <= 8 * 60:
                values.append(duration)
        return self._round(sum(values) / len(values)) if values else None

    def _average_improvement(
        self,
        current: dict[tuple[int, int], AssessmentRecord],
        baseline: dict[tuple[int, int], AssessmentRecord],
    ) -> float | None:
        overlap = current.keys() & baseline.keys()
        return (
            self._round(sum(current[key].total_score - baseline[key].total_score for key in overlap) / len(overlap))
            if overlap
            else None
        )

    @staticmethod
    def _round(value: float | None) -> float | None:
        return None if value is None else round(value, 1)

    @staticmethod
    def _number(value: object) -> float:
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def _integer(value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return 0
