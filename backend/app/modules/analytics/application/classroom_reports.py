"""Teacher analytics backed only by published classroom learning routes and results."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.modules.analytics.application.ports import AnalyticsReader
from app.modules.analytics.application.records import ScopeClass
from app.modules.learning.public import LearningRouteResultReadPort
from app.modules.pbl.public import PblClassroomParticipationPort
from app.shared.actor import Actor
from app.shared.errors import AppError

SHANGHAI = ZoneInfo("Asia/Shanghai")
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _window(date_from: str | None, date_to: str | None) -> tuple[datetime, datetime, str, str]:
    try:
        end_day = date.fromisoformat(date_to) if date_to else datetime.now(SHANGHAI).date()
        start_day = date.fromisoformat(date_from) if date_from else end_day - timedelta(days=29)
    except ValueError as error:
        raise AppError("INVALID_DATE_RANGE", "日期范围无效", 400) from error
    if start_day > end_day or (end_day - start_day).days > 366:
        raise AppError("INVALID_DATE_RANGE", "日期范围无效", 400)
    start = datetime.combine(start_day, time.min, SHANGHAI).astimezone(UTC)
    end = datetime.combine(end_day + timedelta(days=1), time.min, SHANGHAI).astimezone(UTC)
    return start, end, start_day.isoformat(), end_day.isoformat()


def _point_accuracy(results: tuple[dict[str, object], ...]) -> list[dict[str, object]]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for result in results:
        payload = result.get("payload")
        questions = payload.get("questions") if isinstance(payload, dict) else None
        if not isinstance(questions, list):
            continue
        for question in questions:
            if not isinstance(question, dict):
                continue
            point_code = question.get("point_code")
            selected = question.get("selected_option")
            correct = question.get("correct_option")
            if (
                not isinstance(point_code, str)
                or not point_code
                or not isinstance(selected, int)
                or isinstance(selected, bool)
                or not isinstance(correct, int)
                or isinstance(correct, bool)
            ):
                continue
            counts[point_code][1] += 1
            counts[point_code][0] += selected == correct
    return [
        {
            "point_code": point_code,
            "correct_count": values[0],
            "question_count": values[1],
            "accuracy_rate": round(values[0] * 100 / values[1], 1),
        }
        for point_code, values in sorted(counts.items())
        if values[1]
    ]


def _result_by_route(results: tuple[dict[str, object], ...]) -> dict[str, dict[str, object]]:
    return {str(result["route_id"]): result for result in results}


def _result_summary(result: dict[str, object]) -> dict[str, object]:
    return {
        "result_id": result["result_id"],
        "route_id": result["route_id"],
        "session_id": result["session_id"],
        "score": result["score"],
        "correct_count": result["correct_count"],
        "question_count": result["question_count"],
        "completed_at": result["completed_at"],
    }


class ClassroomReportAnalytics:
    def __init__(
        self,
        reader: AnalyticsReader,
        results: LearningRouteResultReadPort,
        participations: PblClassroomParticipationPort,
    ) -> None:
        self._reader = reader
        self._results = results
        self._participations = participations

    def _classes(self, actor: Actor, class_id: int | None) -> tuple[ScopeClass, ...]:
        actor.require_role("teacher")
        classes = self._reader.load_owned_classes(actor.id, class_id)
        if class_id is not None and not classes:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        return classes

    def _completed(
        self, actor: Actor, classes: tuple[ScopeClass, ...], start: datetime, end: datetime
    ) -> tuple[dict[str, object], ...]:
        return self._results.completed_for_teacher(actor.id, tuple(item.id for item in classes), start, end)

    def _published(
        self,
        actor: Actor,
        classes: tuple[ScopeClass, ...],
        start: datetime,
        end: datetime,
        session_id: int | None = None,
    ) -> tuple[dict[str, object], ...]:
        return self._results.published_for_teacher(
            actor.id, tuple(item.id for item in classes), start, end, session_id
        )

    @staticmethod
    def _completion_rate(completed: int, published: int) -> float | None:
        return round(completed * 100 / published, 1) if published else None

    def overview(
        self, actor: Actor, class_id: int | None, date_from: str | None, date_to: str | None
    ) -> dict[str, object]:
        classes = self._classes(actor, class_id)
        start, end, from_text, to_text = _window(date_from, date_to)
        published = self._published(actor, classes, start, end)
        results = _result_by_route(self._completed(actor, classes, EPOCH, datetime.now(UTC)))
        published_route_ids = {str(item["route_id"]) for item in published}
        cohort_results = tuple(results[route_id] for route_id in sorted(published_route_ids & results.keys()))
        roster = self._reader.load_students(classes)
        student_ids = {item.id for item in roster} | {int(item["student_id"]) for item in published}
        student_ids.update(int(item["student_id"]) for item in cohort_results)
        completed = len(cohort_results)
        return {
            "schema_version": 3,
            "data_basis": "learning_routes",
            "scope": {
                "class_id": class_id,
                "class_name": classes[0].name if len(classes) == 1 else None,
                "date_from": from_text,
                "date_to": to_text,
            },
            "student_count": len(student_ids),
            "published_routes": len(published),
            "completed_tests": completed,
            "completion_rate": self._completion_rate(completed, len(published)),
            "knowledge": _point_accuracy(cohort_results),
        }

    def students(
        self,
        actor: Actor,
        class_id: int,
        date_from: str | None,
        date_to: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, object]:
        classes = self._classes(actor, class_id)
        start, end, _from, _to = _window(date_from, date_to)
        published = self._published(actor, classes, start, end)
        route_ids = {str(item["route_id"]) for item in published}
        results = _result_by_route(self._completed(actor, classes, EPOCH, datetime.now(UTC)))
        cohort_results = {route_id: result for route_id, result in results.items() if route_id in route_ids}
        roster = self._reader.load_students(classes)
        names = {item.id: item.nickname for item in roster}
        historical_student_ids = {
            int(item["student_id"]) for item in published
        } | {int(item["student_id"]) for item in cohort_results.values()}
        names.update(self._reader.load_student_names(tuple(historical_student_ids - names.keys())))
        by_student: dict[int, list[dict[str, object]]] = defaultdict(list)
        for item in published:
            by_student[int(item["student_id"])].append(item)
        results_by_student: dict[int, list[dict[str, object]]] = defaultdict(list)
        for result in cohort_results.values():
            results_by_student[int(result["student_id"])].append(result)

        items: list[dict[str, object]] = []
        for student_id in sorted(names):
            own_published = by_student[student_id]
            own_results = results_by_student[student_id]
            items.append(
                {
                    "student_id": student_id,
                    "nickname": names[student_id],
                    "published_routes": len(own_published),
                    "completed_tests": len(own_results),
                    "completion_rate": self._completion_rate(len(own_results), len(own_published)),
                    "last_completed_at": max((_utc(item["completed_at"]) for item in own_results), default=None),
                }
            )
        items.sort(key=lambda item: (-item["completed_tests"], -item["published_routes"], item["student_id"]))
        return {
            "schema_version": 3,
            "data_basis": "learning_routes",
            "items": items[offset : offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        }

    def student_detail(
        self,
        actor: Actor,
        class_id: int,
        student_id: int,
        date_from: str | None,
        date_to: str | None,
        result_limit: int,
        result_offset: int,
    ) -> dict[str, object]:
        classes = self._classes(actor, class_id)
        start, end, from_text, to_text = _window(date_from, date_to)
        published = tuple(
            item for item in self._published(actor, classes, start, end) if int(item["student_id"]) == student_id
        )
        route_ids = {str(item["route_id"]) for item in published}
        all_results = _result_by_route(self._completed(actor, classes, EPOCH, datetime.now(UTC)))
        selected_results = tuple(
            all_results[route_id] for route_id in sorted(route_ids & all_results.keys())
        )
        history = self._published(actor, classes, EPOCH, datetime.now(UTC))
        owns_history = any(int(item["student_id"]) == student_id for item in history)
        roster = {item.id: item.nickname for item in self._reader.load_students(classes)}
        if student_id not in roster and not owns_history:
            raise AppError("RESOURCE_NOT_FOUND", "学生不存在", 404)
        name = roster.get(student_id) or self._reader.load_student_names((student_id,)).get(student_id, "历史学生")
        selected_results = tuple(sorted(selected_results, key=lambda item: _utc(item["completed_at"]), reverse=True))
        page = selected_results[result_offset : result_offset + result_limit]
        return {
            "schema_version": 3,
            "data_basis": "learning_routes",
            "student": {"id": student_id, "nickname": name},
            "class_id": class_id,
            "period": {"date_from": from_text, "date_to": to_text},
            "published_routes": len(published),
            "completed_tests": len(selected_results),
            "completion_rate": self._completion_rate(len(selected_results), len(published)),
            "knowledge": _point_accuracy(selected_results),
            "result_page": {
                "items": [_result_summary(result) for result in page],
                "total": len(selected_results),
                "limit": result_limit,
                "offset": result_offset,
            },
        }

    def progress(
        self,
        actor: Actor,
        class_id: int,
        date_from: str | None,
        date_to: str | None,
        session_id: int | None,
    ) -> dict[str, object]:
        classes = self._classes(actor, class_id)
        start, end, from_text, to_text = _window(date_from, date_to)
        published = self._published(actor, classes, start, end, session_id)
        completed = sum(item["result_id"] is not None for item in published)
        return {
            "schema_version": 3,
            "data_basis": "published_classroom_routes",
            "class_id": class_id,
            "session_id": session_id,
            "period": {"date_from": from_text, "date_to": to_text},
            "published_routes": len(published),
            "completed_tests": completed,
            "in_progress": len(published) - completed,
            "completion_rate": self._completion_rate(completed, len(published)),
        }

    def progress_items(
        self,
        actor: Actor,
        class_id: int,
        session_id: int,
        status: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, object]:
        self._classes(actor, class_id)
        participants = self._participations.classroom_participants(class_id, session_id)
        if participants is None:
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        published = self._results.classroom_progress_for_teacher(actor.id, class_id, session_id)
        by_student = {int(item["student_id"]): item for item in published}
        student_ids = tuple(sorted(set(participants) | set(by_student)))
        names = self._reader.load_student_names(student_ids)
        rows: list[dict[str, object]] = []
        for student_id in student_ids:
            item = by_student.get(student_id)
            state = "unpublished" if item is None else ("completed" if item["result_id"] else "in_progress")
            if status is not None and status != state:
                continue
            rows.append(
                {
                    "student_id": student_id,
                    "nickname": names.get(student_id, "历史学生"),
                    "route_id": item["route_id"] if item else None,
                    "result_id": item["result_id"] if item else None,
                    "execution_status": state,
                    "score": item["score"] if item else None,
                    "correct_count": item["correct_count"] if item else None,
                    "question_count": item["question_count"] if item else None,
                    "completed_at": item["completed_at"] if item else None,
                }
            )
        return {"items": rows[offset : offset + limit], "total": len(rows), "limit": limit, "offset": offset}

    def knowledge(self, actor: Actor, class_id: int) -> dict[str, object]:
        classes = self._classes(actor, class_id)
        published = self._published(actor, classes, EPOCH, datetime.now(UTC))
        published_route_ids = {str(item["route_id"]) for item in published}
        results = _result_by_route(self._completed(actor, classes, EPOCH, datetime.now(UTC)))
        cohort_results = tuple(results[route_id] for route_id in sorted(published_route_ids & results.keys()))
        participants = self._reader.load_students(classes)
        participant_ids = {item.id for item in participants} | {int(item["student_id"]) for item in published}
        return {
            "schema_version": 3,
            "data_basis": "learning_routes",
            "class_id": class_id,
            "class_name": classes[0].name,
            "participant_count": len(participant_ids),
            "published_routes": len(published),
            "completed_tests": len(cohort_results),
            "knowledge": _point_accuracy(cohort_results),
        }

    def retired_case_detail(self, actor: Actor, problem_id: int, class_id: int | None) -> None:
        self._classes(actor, class_id)
        if not self._reader.owns_case(actor.id, problem_id):
            raise AppError("RESOURCE_NOT_FOUND", "病例不存在", 404)
        raise AppError("STATE_CONFLICT", "单项病例表现已退出教师结果统计，请查看课堂最终结果", 409)


__all__ = ["ClassroomReportAnalytics"]
