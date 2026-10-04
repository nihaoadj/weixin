from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.analytics.application.ports import AnalyticsReader
from app.modules.analytics.application.records import (
    AssessmentRecord,
    AttemptAnalyticsRecord,
    ProblemAnalyticsRecord,
    ScopeClass,
    ScopeStudent,
)
from app.modules.analytics.domain.policy import AnalyticsPolicy
from app.modules.content.public import KnowledgeCatalogPort
from app.modules.learning.public import LearningEvidenceEventRecord, LearningEvidenceReadPort
from app.shared.actor import Actor
from app.shared.errors import AppError


class AnalyticsApplication:
    def __init__(
        self,
        reader: AnalyticsReader,
        knowledge_catalog: KnowledgeCatalogPort,
        policy: AnalyticsPolicy | None = None,
        evidence_reader: LearningEvidenceReadPort | None = None,
    ) -> None:
        self._reader = reader
        self._policy = policy or AnalyticsPolicy()
        self._evidence_reader = evidence_reader
        self._knowledge_catalog = knowledge_catalog

    def overview(
        self, actor: Actor, class_id: int | None, date_from: str | None, date_to: str | None
    ) -> dict[str, object]:
        actor.require_role("teacher")
        start, end, start_text, end_text = self._policy.date_range(date_from, date_to)
        classes = self._classes(actor, class_id)
        students = self._reader.load_students(classes)
        if self._evidence_reader is not None:
            current_events = self._qualified_evidence(students, classes, start, end)
            period = end - start
            previous_events = self._qualified_evidence(
                students, classes, start - period - self._epsilon(), start - self._epsilon()
            )
            if self._all_evidence(students, start, end):
                return self._evidence_overview(classes, students, current_events, previous_events, start_text, end_text)
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
        if self._evidence_reader is not None:
            # SQLite cannot reliably bind Python's minimum datetime.  Evidence
            # records are application data, so the Unix epoch is an explicit
            # safe lower bound for the historical read window.
            start = datetime(1970, 1, 1, tzinfo=UTC)
            end = datetime.now(UTC)
            all_events = self._all_evidence(students, start, end)
            if all_events:
                return self._evidence_knowledge(
                    class_id, classes[0].name, self._qualified_evidence(students, classes, start, end)
                )
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
        if self._evidence_reader is not None and self._all_evidence(students, start, end):
            return self._evidence_case_detail(
                problem_id, problems, attempts, students, self._qualified_evidence(students, classes, start, end)
            )
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
        if self._evidence_reader is not None and self._all_evidence((student,), start, end):
            return self._evidence_student_detail(
                student, self._qualified_evidence((student,), classes, start, end), start, end
            )
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

    @staticmethod
    def _epsilon() -> timedelta:
        return timedelta(microseconds=1)

    def _all_evidence(
        self, students: tuple[ScopeStudent, ...], start: datetime, end: datetime
    ) -> tuple[LearningEvidenceEventRecord, ...]:
        if self._evidence_reader is None or not students:
            return ()
        return self._evidence_reader.list_events(
            tuple(item.id for item in students), start, end, include_student_only=True
        )

    def _qualified_evidence(
        self,
        students: tuple[ScopeStudent, ...],
        classes: tuple[ScopeClass, ...],
        start: datetime,
        end: datetime,
    ) -> tuple[LearningEvidenceEventRecord, ...]:
        class_ids = {item.id for item in classes}
        allowed_authority = {"reviewed_practice", "formal_instruction", "pbl_formal"}
        return tuple(
            event
            for event in self._all_evidence(students, start, end)
            if event.class_id in class_ids
            and event.visibility_scope in {"class_aggregate", "class_detail"}
            and event.authority_level in allowed_authority
        )

    def _evidence_overview(
        self,
        classes: tuple[ScopeClass, ...],
        students: tuple[ScopeStudent, ...],
        current: tuple[LearningEvidenceEventRecord, ...],
        previous: tuple[LearningEvidenceEventRecord, ...],
        start_text: str,
        end_text: str,
    ) -> dict[str, object]:
        metric_rows = [(event, metric) for event in current for metric in event.metrics]
        previous_rows = [(event, metric) for event in previous for metric in event.metrics]
        participant_ids = {event.student_id for event in current}
        formal_events_by_student: dict[int, list[LearningEvidenceEventRecord]] = {}
        for event in current:
            formal_events_by_student.setdefault(event.student_id, []).append(event)
        task_events = [event for event in current if event.source_type == "pbl_task_attempt"]
        pbl_events = [event for event in current if event.source_type == "pbl_cycle_evaluation"]
        case_events = [event for event in current if event.source_type == "case_assessment"]

        def passed(event: LearningEvidenceEventRecord) -> bool:
            return bool(event.metrics) and all(item.result in {"correct", "passed"} for item in event.metrics)

        task_passed = sum(passed(event) for event in task_events)
        pbl_completed = sum(passed(event) for event in pbl_events)
        failed_by_student: dict[int, int] = {}
        for event, metric in metric_rows:
            if metric.result == "failed":
                failed_by_student[event.student_id] = failed_by_student.get(event.student_id, 0) + 1
        support_students = {
            event.student_id
            for event in pbl_events
            if event.source_version >= 2 and any(metric.result == "failed" for metric in event.metrics)
        }
        repeated_failure_students = {student_id for student_id, count in failed_by_student.items() if count >= 2}
        inactive_students = {student.id for student in students} - participant_ids
        updated_values = [event.occurred_at for event in current]
        class_name = (
            ", ".join(item.name for item in classes) if len(classes) > 1 else classes[0].name if classes else None
        )

        dimensions = []
        for dimension_id, label, _weight, _stages in self._policy.dimension_specs:
            values = [
                float(metric.normalized_score)
                for event, metric in metric_rows
                if metric.metric_kind == "dimension"
                and metric.metric_code == dimension_id
                and metric.normalized_score is not None
            ]
            baseline_values = [
                float(metric.normalized_score)
                for event, metric in previous_rows
                if metric.metric_kind == "dimension"
                and metric.metric_code == dimension_id
                and metric.normalized_score is not None
            ]
            current_score = self._round(sum(values) / len(values)) if values else None
            baseline_score = self._round(sum(baseline_values) / len(baseline_values)) if baseline_values else None
            dimensions.append(
                {
                    "dimension_id": dimension_id,
                    "label": label,
                    "average_score": current_score,
                    "current_score": current_score,
                    "baseline_score": baseline_score,
                    "delta": self._round(current_score - baseline_score)
                    if current_score is not None and baseline_score is not None
                    else None,
                    "sample_count": len(values),
                }
            )

        knowledge_rows = []
        for code in sorted({metric.metric_code for _event, metric in metric_rows if metric.metric_kind == "knowledge"}):
            rows = [
                (event, metric)
                for event, metric in metric_rows
                if metric.metric_kind == "knowledge" and metric.metric_code == code
            ]
            participants = len({event.student_id for event, _metric in rows})
            correct = sum(metric.result in {"correct", "passed"} for _event, metric in rows)
            knowledge_rows.append(
                {
                    "point_code": code,
                    "label": str((self._knowledge_catalog.point_view(code) or {}).get("title") or code),
                    "participant_count": participants,
                    "evidence_count": len(rows),
                    "correct_count": correct,
                    "rate": self._round(correct * 100 / len(rows)) if rows else None,
                    "trend": None,
                }
            )
        rankings_suppressed = len(participant_ids) < 5
        if rankings_suppressed:
            knowledge_rows = []

        source_summary = []
        for source_type in sorted({event.source_type for event in current}):
            rows = [event for event in current if event.source_type == source_type]
            source_summary.append(
                {
                    "source_type": source_type,
                    "event_count": len(rows),
                    "participant_count": len({event.student_id for event in rows}),
                }
            )

        student_summaries = []
        for student in students:
            rows = formal_events_by_student.get(student.id, [])
            failed_codes = [
                metric.metric_code for event in rows for metric in event.metrics if metric.result == "failed"
            ][:2]
            latest = max(rows, key=lambda event: (event.occurred_at, event.id)) if rows else None
            student_summaries.append(
                {
                    "student_id": student.id,
                    "nickname": student.nickname,
                    "formal_activity_completed": len(rows),
                    "formal_activity_expected": None,
                    "formal_activity_rate": None,
                    "recent_result": next(
                        (
                            metric.result
                            for event in reversed(rows)
                            for metric in reversed(event.metrics)
                            if metric.result in {"correct", "incorrect", "passed", "failed"}
                        ),
                        None,
                    ),
                    "attention_codes": list(dict.fromkeys(failed_codes)),
                    "pbl_status": "support_needed" if student.id in support_students else None,
                    "last_evidence_at": latest.occurred_at if latest else None,
                    # Compatibility fields remain non-scoring counts only.
                    "completed": len(rows),
                    "assigned": None,
                    "average_score": None,
                }
            )
        attention = []
        if support_students:
            attention.append(
                {"kind": "support_needed", "student_count": len(support_students), "route": "pbl-follow-ups"}
            )
        if repeated_failure_students:
            attention.append(
                {
                    "kind": "formal_repeated_failure",
                    "student_count": len(repeated_failure_students),
                    "route": "analytics-students",
                }
            )
        if inactive_students:
            attention.append(
                {"kind": "inactive", "student_count": len(inactive_students), "route": "analytics-students"}
            )
        formal_task_rate = self._round(task_passed * 100 / len(task_events)) if task_events else None
        classroom_pbl_rate = self._round(pbl_completed * 100 / len(pbl_events)) if pbl_events else None
        return {
            "scope": {
                "class_id": classes[0].id if len(classes) == 1 else None,
                "class_name": class_name,
                "date_from": start_text,
                "date_to": end_text,
            },
            "coverage": {
                "student_count": len(students),
                "participant_count": len(participant_ids),
                "evidence_count": len(current),
                "updated_at": max(updated_values) if updated_values else None,
            },
            "completion": {
                "formal_task_rate": formal_task_rate,
                "formal_task_completed": task_passed,
                "formal_task_attempted": len(task_events),
                "classroom_pbl_rate": classroom_pbl_rate,
                "classroom_pbl_completed": pbl_completed,
                "classroom_pbl_started": len(pbl_events),
                "case_rate": 100.0 if case_events else None,
                "case_completed": len(case_events),
            },
            "attention": {
                "support_needed": len(support_students),
                "formal_repeated_failure": len(repeated_failure_students),
                "inactive": len(inactive_students),
                "items": attention,
            },
            "knowledge": knowledge_rows,
            "knowledge_notice": "样本少于 5 名参与学生，已隐藏知识点薄弱排名。" if rankings_suppressed else None,
            "dimensions": dimensions,
            "activity_sources": source_summary,
            "source_summary": source_summary,
            "students": sorted(student_summaries, key=lambda item: self._integer(item["student_id"])),
            "privacy": {"minimum_cohort_size": 5, "rankings_suppressed": rankings_suppressed},
            "updated_at": max(updated_values) if updated_values else None,
            # Legacy fields are retained only as compatibility counts; no
            # composite score is calculated from evidence.
            "student_count": len(students),
            "published_case_count": len(
                {event.source_id for event in current if event.source_type == "case_assessment"}
            ),
            "eligible_pairs": len(students),
            "started_pairs": len(current),
            "completed_pairs": len(current),
            "completion_rate": self._round(len(current) * 100 / len(students)) if students else None,
            "current_average_score": None,
            "average_improvement": None,
            "weak_dimensions": [],
            "cases": [],
        }

    def _evidence_knowledge(self, class_id: int, class_name: str, events: tuple[LearningEvidenceEventRecord, ...]):
        rows = []
        for code in sorted(
            {metric.metric_code for event in events for metric in event.metrics if metric.metric_kind == "knowledge"}
        ):
            metrics = [
                metric
                for event in events
                for metric in event.metrics
                if metric.metric_kind == "knowledge" and metric.metric_code == code
            ]
            participants = len(
                {event.student_id for event in events if any(metric.metric_code == code for metric in event.metrics)}
            )
            correct = sum(metric.result in {"correct", "passed"} for metric in metrics)
            rows.append(
                {
                    "point_code": code,
                    "student_count": participants,
                    "evidence_count": len(metrics),
                    "rate": self._round(correct * 100 / len(metrics)) if metrics else None,
                }
            )
        participant_count = len({event.student_id for event in events})
        suppressed = participant_count < 5
        return {
            "class_id": class_id,
            "class_name": class_name,
            "participant_count": participant_count,
            "due_backlog": None,
            "objective_correct_rate": None,
            "weak_points": [] if suppressed else rows,
            "rankings_suppressed": suppressed,
        }

    def _evidence_case_detail(self, problem_id, problems, attempts, students, events):
        problem = next((item for item in problems if item.id == problem_id), None)
        if problem is None or problem.content_type != "guided_case" or problem.status != "published":
            raise AppError("RESOURCE_NOT_FOUND", "病例不存在", 404)
        assessment_ids = {str(attempt.assessment.id) for attempt in attempts if attempt.assessment is not None}
        rows = tuple(
            event for event in events if event.source_type == "case_assessment" and event.source_id in assessment_ids
        )
        dimensions = self._aggregate_dimensions(rows, ())
        return {
            "problem": {"id": problem.id, "title": problem.title, "version": problem.version, "slug": problem.slug},
            "eligible_pairs": None,
            "started_pairs": len({event.student_id for event in rows}),
            "completed_pairs": len({event.student_id for event in rows}),
            "completion_rate": None,
            "current_average_score": None,
            "average_improvement": None,
            "average_duration_minutes": None,
            "dimensions": dimensions,
            "distribution": {},
            "students": [
                {
                    "student_id": student.id,
                    "nickname": student.nickname,
                    "status": "assessed" if any(event.student_id == student.id for event in rows) else "not_started",
                    "baseline": None,
                    "current": None,
                    "delta": None,
                    "focus_stage": None,
                    "last_assessed_at": max(
                        (event.occurred_at for event in rows if event.student_id == student.id), default=None
                    ),
                }
                for student in students
            ],
        }

    def _evidence_student_detail(self, student, events, start, end):
        dimensions = self._aggregate_dimensions(events, ())
        formal = [
            event
            for event in events
            if event.authority_level in {"reviewed_practice", "formal_instruction", "pbl_formal"}
        ]
        failed = [metric.metric_code for event in formal for metric in event.metrics if metric.result == "failed"]
        pbl_support = any(
            event.source_type == "pbl_cycle_evaluation"
            and event.source_version >= 2
            and any(metric.result == "failed" for metric in event.metrics)
            for event in formal
        )
        latest = max((event.occurred_at for event in formal), default=None)
        return {
            "student": {"id": student.id, "nickname": student.nickname},
            "assigned": None,
            "started": len(formal),
            "completed": len(formal),
            "completion_rate": None,
            "current_average_score": None,
            "average_improvement": None,
            "dimensions": dimensions,
            "cases": [],
            "timeline": [
                {"source_type": event.source_type, "event_kind": event.event_kind, "occurred_at": event.occurred_at}
                for event in formal[-12:]
            ],
            "learning_plan": None,
            "practice_mastery": {},
            "formal_evidence": {"event_count": len(formal), "last_evidence_at": latest},
            "attention_codes": list(dict.fromkeys(failed))[:2],
            "pbl_status": "support_needed" if pbl_support else None,
        }

    def _aggregate_dimensions(self, events, previous):
        rows = [(event, metric) for event in events for metric in event.metrics]
        result = []
        for dimension_id, label, _weight, _stages in self._policy.dimension_specs:
            values = [
                float(metric.normalized_score)
                for _event, metric in rows
                if metric.metric_kind == "dimension"
                and metric.metric_code == dimension_id
                and metric.normalized_score is not None
            ]
            result.append(
                {
                    "dimension_id": dimension_id,
                    "label": label,
                    "average_score": self._round(sum(values) / len(values)) if values else None,
                    "baseline_score": None,
                    "current_score": self._round(sum(values) / len(values)) if values else None,
                    "delta": None,
                    "sample_count": len(values),
                }
            )
        return result

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
