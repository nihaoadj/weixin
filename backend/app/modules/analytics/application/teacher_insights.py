"""Read-only teacher projections with explicit, independent metric windows."""

from collections import defaultdict
from datetime import UTC, datetime
from math import isfinite

from app.modules.analytics.application.classroom_reports import EPOCH, _utc, _window
from app.modules.analytics.application.ports import AnalyticsReader
from app.modules.learning.public import LearningRouteResultReadPort
from app.modules.pbl.public import PblTeacherDiagnosisReadPort
from app.shared.actor import Actor
from app.shared.errors import AppError


def _number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and isfinite(value)


def _options(value, *, reference=False) -> bool:
    return (
        isinstance(value, list)
        and (bool(value) or not reference)
        and all(type(item) is int and 0 <= item <= 3 for item in value)
        and len(value) == len(set(value))
    )


def point_statistics(results: tuple[dict, ...]) -> list[dict]:
    points = {}
    for result in results:
        payload = result.get("payload")
        questions = payload.get("questions") if isinstance(payload, dict) else None
        for question in questions if isinstance(questions, list) else []:
            if not isinstance(question, dict) or not isinstance(question.get("point_code"), str):
                continue
            code = question["point_code"].strip()
            if not code:
                continue
            item = points.setdefault(
                code,
                {
                    "point_code": code,
                    "correct_count": 0,
                    "objective_count": 0,
                    "invalid_objective_count": 0,
                    "short_answer_count": 0,
                    "invalid_short_answer_count": 0,
                    "points_awarded": 0.0,
                    "points_possible": 0.0,
                },
            )
            kind = question.get("question_type", "single_choice")
            if kind == "short_answer":
                earned, possible = question.get("points_awarded"), question.get("points_possible")
                if _number(earned) and _number(possible) and 0 <= earned <= possible and possible > 0:
                    item["short_answer_count"] += 1
                    item["points_awarded"] += earned
                    item["points_possible"] += possible
                else:
                    item["invalid_short_answer_count"] += 1
            elif kind == "single_choice":
                selected, correct = question.get("selected_option"), question.get("correct_option")
                if type(selected) is int and type(correct) is int and 0 <= selected <= 3 and 0 <= correct <= 3:
                    item["objective_count"] += 1
                    item["correct_count"] += selected == correct
                else:
                    item["invalid_objective_count"] += 1
            elif kind == "multiple_choice":
                selected, correct = question.get("selected_options"), question.get("correct_options")
                if _options(selected) and _options(correct, reference=True):
                    item["objective_count"] += 1
                    item["correct_count"] += set(selected) == set(correct)
                else:
                    item["invalid_objective_count"] += 1
    return [
        {
            **item,
            "accuracy_rate": round(item["correct_count"] * 100 / item["objective_count"], 1)
            if item["objective_count"]
            else None,
            "short_answer_score_rate": round(item["points_awarded"] * 100 / item["points_possible"], 1)
            if item["points_possible"]
            else None,
        }
        for _code, item in sorted(points.items())
    ]


def _result_summary(result: dict) -> dict:
    payload = result.get("payload")
    return {
        "result_id": result["result_id"],
        "route_id": result["route_id"],
        "class_id": result["class_id"],
        "session_id": result["session_id"],
        "student_id": result["student_id"],
        "score": result["score"],
        "completed_at": result["completed_at"],
        "format_version": payload.get("format_version", "single_choice_v1")
        if isinstance(payload, dict)
        else "single_choice_v1",
    }


class TeacherInsights:
    def __init__(
        self, reader: AnalyticsReader, results: LearningRouteResultReadPort, diagnoses: PblTeacherDiagnosisReadPort
    ):
        self.reader, self.results, self.diagnoses = reader, results, diagnoses

    def _facts(self, actor: Actor, class_id, session_id, date_from, date_to):
        actor.require_role("teacher")
        classes = self.reader.load_owned_classes(actor.id, class_id)
        if class_id is not None and not classes:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        class_ids = tuple(item.id for item in classes)
        start, end, first, last = _window(date_from, date_to)
        timestamp = datetime.now(UTC)
        visible_end = min(end, timestamp)
        published = self.results.published_for_teacher(actor.id, class_ids, start, visible_end, session_id)
        results = tuple(
            item
            for item in self.results.completed_for_teacher(actor.id, class_ids, start, visible_end)
            if session_id is None or item["session_id"] == session_id
        )
        diagnoses = self.diagnoses.teacher_diagnoses(actor.id, class_ids, start, visible_end, session_id)
        discussions = self.diagnoses.teacher_discussions(actor.id, class_ids, start, visible_end, session_id)
        roster = self.reader.load_students(classes)
        identities = {item.id for item in roster} | {item["student_id"] for item in published + results}
        identities |= {item.student_id for item in diagnoses + discussions}
        names = self.reader.load_student_names(tuple(sorted(identities)))
        scope = {
            "class_id": class_id,
            "class_name": classes[0].name if class_id is not None else None,
            "class_ids": list(class_ids),
            "session_id": session_id,
            "date_from": first,
            "date_to": last,
            "timezone": "Asia/Shanghai",
            "as_of": timestamp,
            "metric_basis": {
                "progress": "published_route_cohort",
                "results": "completed_test_window",
                "diagnoses": "completed_diagnosis_window",
            },
        }
        return scope, classes, roster, published, results, diagnoses, names, discussions

    @staticmethod
    def _cohort(published, timestamp):
        completed = sum(
            bool(item.get("result_id"))
            and item.get("completed_at") is not None
            and _utc(item["completed_at"]) <= timestamp
            for item in published
        )
        return {
            "published_routes": len(published),
            "completed_tests": completed,
            "completion_rate": round(completed * 100 / len(published), 1) if published else None,
            "grading_tests": sum(
                item.get("attempt_status") == "grading" and not item.get("result_id") for item in published
            ),
        }

    @staticmethod
    def _scores(results):
        formats = defaultdict(int)
        for result in results:
            formats[_result_summary(result)["format_version"]] += 1
        return {
            "completed_tests": len(results),
            "average_score": round(sum(item["score"] for item in results) / len(results), 1) if results else None,
            "format_counts": dict(formats),
        }

    def overview(self, actor, class_id=None, session_id=None, date_from=None, date_to=None):
        scope, _classes, _roster, published, results, diagnoses, _names, discussions = self._facts(
            actor, class_id, session_id, date_from, date_to
        )
        return {
            "scope": scope,
            "cohort": self._cohort(published, scope["as_of"]),
            "period_results": self._scores(results),
            "diagnosis_count": len(diagnoses),
            "student_count": len(
                {item["student_id"] for item in published + results}
                | {item.student_id for item in diagnoses + discussions}
            ),
        }

    @staticmethod
    def _student_rows(classes, roster, published, results, diagnoses, names, timestamp, discussions=()):
        codes = {item.code: item.id for item in classes}
        identities = {item.id for item in roster} | {item["student_id"] for item in published + results}
        identities |= {item.student_id for item in diagnoses + discussions}
        rows = []
        for student_id in sorted(identities):
            own_routes = tuple(item for item in published if item["student_id"] == student_id)
            own_results = tuple(item for item in results if item["student_id"] == student_id)
            own_diagnoses = tuple(item for item in diagnoses if item.student_id == student_id)
            class_ids = {
                codes[code] for item in roster if item.id == student_id for code in item.class_ids if code in codes
            }
            class_ids |= {item["class_id"] for item in own_routes + own_results}
            own_discussions = tuple(item for item in discussions if item.student_id == student_id)
            class_ids |= {item.class_id for item in own_diagnoses + own_discussions}
            rows.append(
                {
                    "student_id": student_id,
                    "student_name": names.get(student_id, "历史学生"),
                    "class_ids": sorted(class_ids),
                    "cohort": TeacherInsights._cohort(own_routes, timestamp),
                    "period_results": TeacherInsights._scores(own_results),
                    "diagnosis_count": len(own_diagnoses),
                    "discussion_progress": {
                        "participated": len(own_discussions),
                        "active": sum(item.status == "active" for item in own_discussions),
                        "completed": sum(item.status == "completed" for item in own_discussions),
                    },
                    "last_completed_at": max((_utc(item["completed_at"]) for item in own_results), default=None),
                }
            )
        return rows

    def students(self, actor, class_id=None, session_id=None, date_from=None, date_to=None, limit=20, offset=0):
        scope, classes, roster, published, results, diagnoses, names, discussions = self._facts(
            actor, class_id, session_id, date_from, date_to
        )
        items = self._student_rows(classes, roster, published, results, diagnoses, names, scope["as_of"], discussions)
        return {
            "scope": scope,
            "items": items[offset : offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        }

    def knowledge(self, actor, class_id=None, session_id=None, date_from=None, date_to=None):
        scope, _classes, _roster, _published, results, _diagnoses, _names, discussions = self._facts(
            actor, class_id, session_id, date_from, date_to
        )
        return {"scope": scope, "items": point_statistics(results), "result_count": len(results)}

    @staticmethod
    def _diagnosis_rows(records, names, class_names):
        return [
            {
                "participation_id": item.participation_id,
                "session_id": item.session_id,
                "class_id": item.class_id,
                "class_name": class_names[item.class_id],
                "student_id": item.student_id,
                "student_name": names.get(item.student_id, "历史学生"),
                "completed_at": _utc(item.completed_at),
                "knowledge_gap_codes": list(item.knowledge_gap_codes),
                "reasoning_issue_codes": list(item.reasoning_issue_codes),
                "knowledge_gaps": [
                    {"code": finding.code, "summary": finding.summary} for finding in item.knowledge_gaps
                ],
                "reasoning_issues": [
                    {"code": finding.code, "summary": finding.summary} for finding in item.reasoning_issues
                ],
            }
            for item in records
        ]

    @staticmethod
    def _finding_groups(records, field):
        groups = {}
        for item in records:
            for code in getattr(item, field):
                group = groups.setdefault(
                    code,
                    {
                        "code": code,
                        "students": set(),
                        "diagnosis_count": 0,
                        "last_completed_at": _utc(item.completed_at),
                    },
                )
                group["students"].add(item.student_id)
                group["diagnosis_count"] += 1
                group["last_completed_at"] = max(group["last_completed_at"], _utc(item.completed_at))
        return [
            {
                "code": code,
                "student_count": len(item["students"]),
                "diagnosis_count": item["diagnosis_count"],
                "last_completed_at": item["last_completed_at"],
            }
            for code, item in sorted(groups.items())
        ]

    def diagnostics(self, actor, class_id=None, session_id=None, date_from=None, date_to=None, limit=20, offset=0):
        scope, classes, _roster, _published, _results, records, names, discussions = self._facts(
            actor, class_id, session_id, date_from, date_to
        )
        rows = self._diagnosis_rows(records, names, {item.id: item.name for item in classes})
        return {
            "scope": scope,
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "limit": limit,
            "offset": offset,
            "knowledge_gaps": self._finding_groups(records, "knowledge_gap_codes"),
            "reasoning_issues": self._finding_groups(records, "reasoning_issue_codes"),
        }

    def student(self, actor, student_id, class_id, session_id=None, date_from=None, date_to=None):
        scope, classes, roster, published, results, records, names, discussions = self._facts(
            actor, class_id, session_id, date_from, date_to
        )
        allowed = any(item.id == student_id for item in roster)
        if not allowed:
            history = self.results.published_for_teacher(actor.id, (class_id,), EPOCH, scope["as_of"])
            diagnoses = self.diagnoses.teacher_diagnoses(actor.id, (class_id,), EPOCH, scope["as_of"])
            history_discussions = self.diagnoses.teacher_discussions(actor.id, (class_id,), EPOCH, scope["as_of"])
            allowed = (
                any(item.student_id == student_id for item in history_discussions)
                or any(item["student_id"] == student_id for item in history)
                or any(item.student_id == student_id for item in diagnoses)
            )
        if not allowed:
            raise AppError("RESOURCE_NOT_FOUND", "学生不存在", 404)
        names.update(self.reader.load_student_names((student_id,)))
        own_routes = tuple(item for item in published if item["student_id"] == student_id)
        own_results = tuple(
            sorted(
                (item for item in results if item["student_id"] == student_id),
                key=lambda item: (_utc(item["completed_at"]), item["result_id"]),
                reverse=True,
            )
        )
        own_records = tuple(item for item in records if item.student_id == student_id)
        summaries = self._student_rows(
            classes, roster, own_routes, own_results, own_records, names, scope["as_of"], discussions
        )
        summary = next((item for item in summaries if item["student_id"] == student_id), None)
        if summary is None:
            summary = {
                "student_id": student_id,
                "student_name": names.get(student_id, "历史学生"),
                "class_ids": [class_id],
                "cohort": self._cohort((), scope["as_of"]),
                "period_results": self._scores(()),
                "diagnosis_count": 0,
                "discussion_progress": {"participated": 0, "active": 0, "completed": 0},
                "last_completed_at": None,
            }
        route_fields = (
            "route_id",
            "student_id",
            "class_id",
            "session_id",
            "published_at",
            "result_id",
            "test_generation_state",
            "test_review_state",
            "attempt_status",
            "completed_steps",
            "total_steps",
            "reading_seconds",
        )
        return {
            "scope": scope,
            "summary": summary,
            "discussions": [
                {
                    "participation_id": item.participation_id,
                    "session_id": item.session_id,
                    "class_id": item.class_id,
                    "student_id": item.student_id,
                    "phase": item.phase,
                    "status": item.status,
                    "started_at": _utc(item.started_at),
                    "completed_at": _utc(item.completed_at) if item.completed_at else None,
                }
                for item in discussions
                if item.student_id == student_id
            ],
            "routes": [{field: item.get(field) for field in route_fields} for item in own_routes],
            "results": [_result_summary(item) for item in own_results],
            "diagnoses": self._diagnosis_rows(own_records, names, {item.id: item.name for item in classes}),
            "knowledge": point_statistics(own_results),
        }
