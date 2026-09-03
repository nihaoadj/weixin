from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from app.shared.errors import AppError


class AnalyticsPolicy:
    dimension_specs = (
        ("information_gathering", "信息采集", 20, ("history",)),
        ("problem_representation", "问题表征", 15, ("problem_representation",)),
        ("differential_diagnosis", "鉴别诊断", 20, ("differential",)),
        ("evidence_reasoning", "证据推理", 15, ("differential",)),
        ("test_selection", "检查合理性", 15, ("tests",)),
        ("management_safety", "处置与安全意识", 15, ("management",)),
    )

    @staticmethod
    def date_range(date_from: str | None, date_to: str | None) -> tuple[datetime, datetime, str, str]:
        try:
            end = date.fromisoformat(date_to) if date_to else datetime.now(UTC).date()
            start = date.fromisoformat(date_from) if date_from else end - timedelta(days=29)
        except ValueError as error:
            raise AppError("INVALID_DATE_RANGE", "日期范围无效", 400) from error
        if start > end or (end - start).days > 366:
            raise AppError("INVALID_DATE_RANGE", "日期范围无效", 400)
        return (
            datetime.combine(start, time.min, UTC),
            datetime.combine(end, time.max, UTC),
            start.isoformat(),
            end.isoformat(),
        )

    @staticmethod
    def visible(
        *,
        status: str,
        target: str,
        target_ids: tuple[str, ...],
        student_external_id: str,
        class_codes: set[str],
    ) -> bool:
        if status != "published":
            return False
        if target == "all":
            return True
        if target == "individual":
            return student_external_id in target_ids
        return target == "class" and bool(set(target_ids).intersection(class_codes))
