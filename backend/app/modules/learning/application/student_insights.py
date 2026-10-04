from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.modules.content.public import KnowledgeCatalogPort
from app.modules.learning.public import (
    StudentInsightRouteReadPort,
)
from app.modules.pbl.public import PblStudentInsightReadPort, PblStudentInsightRecord

SHANGHAI = ZoneInfo("Asia/Shanghai")
_PHASE_LABELS = {
    "problem_framing": "问题表征",
    "hypothesis": "提出假设",
    "evidence": "搜集证据",
    "synthesis": "综合总结",
    "completed": "研讨完成",
}
_REASONING_LABELS = {
    "information_gathering": "信息搜集",
    "problem_representation": "问题表征",
    "differential_diagnosis": "鉴别诊断",
    "evidence_reasoning": "证据推理",
    "test_selection": "检查选择",
    "management_safety": "处置安全",
}
_CASE_PHASE_LABELS = {
    "pathology_recognition": "病理识别",
    "mechanism_explanation": "机制解释",
    "evidence_judgment": "证据判断",
    "summary_reflection": "总结反思",
    "completed": "病例完成",
}


class StudentLearningInsightsApplication:
    def __init__(
        self,
        routes: StudentInsightRouteReadPort,
        pbl: PblStudentInsightReadPort,
        knowledge_catalog: KnowledgeCatalogPort,
        clock=None,
    ) -> None:
        self._routes = routes
        self._pbl = pbl
        self._knowledge_catalog = knowledge_catalog
        self._clock = clock or (lambda: datetime.now(UTC))

    def read(self, student_id: int, limit: int, offset: int) -> dict[str, object]:
        route_records = self._routes.student_insight_routes(student_id)
        pbl_records = self._pbl.student_insight_records(student_id)
        catalog_points = {str(item["code"]): str(item["title"]) for item in self._knowledge_catalog.tree_view()}
        module_labels = self._knowledge_catalog.module_labels()
        routes_by_session = {item.session_id: item for item in route_records}
        results = tuple((route, route.result) for route in route_records if route.result is not None)
        now_local = _aware(self._clock()).astimezone(SHANGHAI)
        week_start = now_local.date() - timedelta(days=now_local.weekday())
        dashboard = self._dashboard(route_records, pbl_records, results, week_start, catalog_points)
        rows = [
            self._item(record, routes_by_session.get(record.session_id), module_labels)
            for record in pbl_records
        ]
        pbl_session_ids = {record.session_id for record in pbl_records}
        rows.extend(
            self._route_item(route, catalog_points, module_labels)
            for route in route_records
            if route.session_id not in pbl_session_ids
        )
        rows.sort(key=lambda item: (_aware(item["updated_at"]), item["id"]), reverse=True)
        next_action = self._next_action(rows)
        latest_diagnosis = max(
            (item for item in pbl_records if item.diagnosis_created_at is not None),
            key=lambda item: _aware(item.diagnosis_created_at),
            default=None,
        )
        dashboard["ai_summary"] = self._summary(latest_diagnosis, routes_by_session, catalog_points)
        return {
            "summary": {"dashboard": dashboard, "next_action": next_action},
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "limit": limit,
            "offset": offset,
        }

    def _dashboard(self, routes, pbl_records, results, week_start, point_labels):
        trend = []
        weekly_scores: list[float | None] = []
        local_results = [(_aware(result.completed_at).astimezone(SHANGHAI), result) for _, result in results]
        for index in range(3, -1, -1):
            start = week_start - timedelta(weeks=index)
            end = start + timedelta(days=7)
            scores = [
                float(result.score)
                for completed_at, result in local_results
                if start <= completed_at.date() < end
            ]
            average = _average(scores)
            weekly_scores.append(average)
            trend.append(
                {
                    "period_start": start.isoformat(),
                    "period_end": (end - timedelta(days=1)).isoformat(),
                    "score": _round(average),
                    "sample_count": len(scores),
                }
            )
        current_samples = [
            result
            for completed_at, result in local_results
            if week_start <= completed_at.date() < week_start + timedelta(days=7)
        ]
        current_score, previous_score = weekly_scores[-1], weekly_scores[-2]
        delta = current_score - previous_score if current_score is not None and previous_score is not None else None
        if current_score is None:
            status_label = "待积累"
        elif delta is None:
            status_label = "本周已有测试"
        elif delta > 0:
            status_label = "较上周提升"
        elif delta < 0:
            status_label = "较上周回落"
        else:
            status_label = "与上周持平"

        tested_codes = {
            score.target_code
            for route, result in results
            for score in result.question_scores
            if score.target_code
        }
        for route, _result in results:
            tested_codes.update(route.goal_point_codes)
        total_reading_seconds = sum(route.reading_seconds for route in routes)
        completion_rate = len(results) * 100 / len(routes) if routes else None
        return {
            "data_basis": "learning_route_results",
            "period_start": week_start.isoformat(),
            "period_end": (week_start + timedelta(days=6)).isoformat(),
            "mastery_score": _round(current_score),
            "mastery_delta": _round(delta),
            "mastery_sample_count": len(current_samples),
            "study_minutes": total_reading_seconds // 60,
            "study_duration_basis": "recorded_reading",
            "plan_completion_rate": _round(completion_rate),
            "tested_knowledge_count": len(tested_codes),
            "ai_diagnostic_count": sum(item.diagnosis_created_at is not None for item in pbl_records),
            "status_label": status_label,
            "trend": trend,
            "weaknesses": self._weaknesses(pbl_records, results, point_labels),
            "ai_summary": "",
        }

    def _weaknesses(self, pbl_records, results, point_labels):
        knowledge_sessions: dict[str, set[int]] = defaultdict(set)
        reasoning_sessions: dict[str, set[int]] = defaultdict(set)
        latest_diagnosis: dict[tuple[str, str], datetime] = {}
        for item in pbl_records:
            if item.diagnosis_created_at is None:
                continue
            diagnosed_at = _aware(item.diagnosis_created_at)
            for code in item.knowledge_gap_codes:
                knowledge_sessions[code].add(item.session_id)
                key = ("knowledge", code)
                latest_diagnosis[key] = max(latest_diagnosis.get(key, diagnosed_at), diagnosed_at)
            for code in item.reasoning_issue_codes:
                reasoning_sessions[code].add(item.session_id)
                key = ("reasoning", code)
                latest_diagnosis[key] = max(latest_diagnosis.get(key, diagnosed_at), diagnosed_at)

        latest_test_score = self._latest_test_scores(results)
        values = []
        knowledge_codes = set(knowledge_sessions) | set(latest_test_score)
        for code in knowledge_codes:
            sessions = knowledge_sessions.get(code, set())
            if sessions:
                tested_at, percentage = self._latest_target_score(
                    code, latest_diagnosis[("knowledge", code)], results
                )
                if tested_at is not None and percentage >= 100 - 1e-9:
                    continue
            else:
                tested_at, percentage = latest_test_score[code]
                if percentage >= 100 - 1e-9:
                    continue
            values.append(
                {
                    "target_type": "knowledge",
                    "target_code": code,
                    "label": point_labels.get(code, code),
                    "occurrences": len(sessions) or 1,
                    "mastery_percentage": _round(percentage),
                }
            )
        for code, sessions in reasoning_sessions.items():
            values.append(
                {
                    "target_type": "reasoning",
                    "target_code": code,
                    "label": _REASONING_LABELS.get(code, code),
                    "occurrences": len(sessions),
                    "mastery_percentage": None,
                }
            )
        return sorted(
            values,
            key=lambda item: (-int(item["occurrences"]), str(item["target_type"]), str(item["target_code"])),
        )

    @staticmethod
    def _latest_target_score(code, diagnosed_at, results):
        latest_at = None
        latest_percentage = None
        for route, result in results:
            completed_at = _aware(result.completed_at)
            if completed_at <= diagnosed_at:
                continue
            percentage = StudentLearningInsightsApplication._target_score(code, route, result)
            if percentage is None:
                continue
            if latest_at is None or completed_at > latest_at:
                latest_at, latest_percentage = completed_at, percentage
        return latest_at, latest_percentage

    @staticmethod
    def _target_score(code, route, result):
        scores = [item for item in result.question_scores if item.target_code == code and item.possible_points > 0]
        if scores:
            earned = sum(item.earned_points for item in scores)
            possible = sum(item.possible_points for item in scores)
            return 100 * earned / possible if possible > 0 else None
        if len(route.goal_point_codes) == 1 and code in route.goal_point_codes:
            return result.score
        return None

    @classmethod
    def _latest_test_scores(cls, results):
        latest = {}
        for route, result in results:
            codes = set(route.goal_point_codes) | {
                item.target_code for item in result.question_scores if item.target_code
            }
            for code in codes:
                score = cls._target_score(code, route, result)
                completed_at = _aware(result.completed_at)
                if score is not None and (code not in latest or completed_at > latest[code][0]):
                    latest[code] = (completed_at, score)
        return latest

    def _item(self, record, route, module_labels):
        result = route.result if route else None
        if result is not None:
            action = {
                "kind": "result",
                "session_id": str(record.session_id),
                "route_id": route.route_id,
                "label": "查看结果",
            }
            summary = f"学习路线与最终测试已完成，得分 {_format_score(result.score)} 分。"
            updated_at = max(_aware(record.updated_at), _aware(route.updated_at), _aware(result.completed_at))
        elif route is not None:
            action = {
                "kind": "route",
                "session_id": str(record.session_id),
                "route_id": route.route_id,
                "label": "继续学习",
            }
            summary = self._route_summary(route)
            updated_at = max(_aware(record.updated_at), _aware(route.updated_at))
        else:
            action = {"kind": "discussion", "session_id": str(record.session_id), "label": "查看研讨"}
            if record.phase_status == "completed":
                summary = "研讨已完成，学习路线暂未生成。"
            else:
                summary = f"研讨进行中 · {_PHASE_LABELS.get(record.current_phase, '继续讨论')}。"
            updated_at = _aware(record.updated_at)
        return {
            "id": str(record.session_id),
            "session": {
                "id": str(record.session_id),
                "topic_label": module_labels.get(record.topic_code, record.topic_code),
                "case_title": record.case_title,
            },
            "summary_text": summary,
            "updated_at": updated_at,
            "action": action,
        }

    def _route_item(self, route, point_labels, module_labels):
        result = route.result
        action = {
            "kind": "result" if result is not None else "route",
            "session_id": str(route.session_id),
            "route_id": route.route_id,
            "label": "查看结果" if result is not None else "继续学习",
        }
        updated_at = max(_aware(route.updated_at), _aware(result.completed_at)) if result else _aware(route.updated_at)
        point_code = route.goal_point_codes[0] if route.goal_point_codes else ""
        return {
            "id": f"route:{route.route_id}",
            "session": {
                "id": str(route.session_id),
                "topic_label": point_labels.get(point_code, module_labels.get(point_code, point_code or "自主学习")),
                "case_title": route.title or "学习路线",
            },
            "summary_text": (
                f"最终测试得分 {_format_score(result.score)} 分。" if result else self._route_summary(route)
            ),
            "updated_at": updated_at,
            "action": action,
        }

    @staticmethod
    def _route_summary(route):
        progress = f"已完成 {route.completed_steps}/{route.total_steps} 步。"
        if route.status == "generation_failed":
            return "学习路线生成未成功，尚未完成。"
        if route.status == "generating":
            return "学习路线正在生成。"
        if route.status == "grading":
            return "最终测试已提交，等待评分。"
        if route.status == "waiting_test_generation":
            return "路线学习已完成，最终测试待生成。"
        if route.status == "waiting_teacher":
            return "路线学习已完成，最终测试待审核。"
        if route.status == "ready_for_test":
            return "路线学习已完成，可以开始最终测试。"
        if route.status == "testing":
            return "最终测试正在进行。"
        if route.current_step_kind == "reading":
            return f"正在阅读学习 · {progress}"
        if route.current_step_kind == "case":
            phase = _CASE_PHASE_LABELS.get(route.current_case_phase or "", "病例推理")
            return f"正在病例学习（{phase}）· {progress}"
        return f"学习路线进行中 · {progress}"

    def _next_action(self, rows):
        for item in rows:
            if item["action"]["kind"] == "route":
                return item["action"]
        for item in rows:
            if item["action"]["kind"] == "result":
                return item["action"]
        return rows[0]["action"] if rows else None

    def _summary(self, diagnosis: PblStudentInsightRecord | None, routes_by_session, point_labels):
        if diagnosis is None:
            if not routes_by_session:
                return "完成研讨后，这里会结合结构化诊断、路线进度和测试结果汇总学习记录。"
            completed = [route for route in routes_by_session.values() if route.result is not None]
            summary = f"当前共有 {len(routes_by_session)} 条学习路线，{len(completed)} 条已完成最终测试。"
            if completed:
                latest = max(completed, key=lambda route: _aware(route.result.completed_at))
                summary += f"最近最终测试得分 {_format_score(latest.result.score)} 分。"
            return summary + "尚无可确认的研讨完成诊断，以上为学习记录汇总。"
        route = routes_by_session.get(diagnosis.session_id)
        parts = []
        knowledge = [point_labels.get(code, code) for code in diagnosis.knowledge_gap_codes]
        reasoning = [_REASONING_LABELS.get(code, code) for code in diagnosis.reasoning_issue_codes]
        if diagnosis.diagnosis_outcome == "no_clear_gaps" and not knowledge and not reasoning:
            parts.append("最近一次研讨未识别出明确薄弱点。")
        elif knowledge or reasoning:
            targets = knowledge + reasoning
            parts.append(f"最近一次研讨记录了学习重点：{'、'.join(targets[:3])}。")
        else:
            parts.append("最近一次研讨已完成结构化诊断。")
        if route is None:
            parts.append("学习路线尚未生成。")
        elif route.result is not None:
            parts.append(f"后续最终测试得分 {_format_score(route.result.score)} 分。")
        else:
            parts.append(f"当前路线完成 {route.completed_steps}/{route.total_steps} 步。")
        return "".join(parts)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def _format_score(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"
