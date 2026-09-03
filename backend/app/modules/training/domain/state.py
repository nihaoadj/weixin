from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.shared.errors import AppError

CASE_STAGES = ("history", "problem_representation", "differential", "tests", "management")
DIMENSION_SPECS = (
    ("information_gathering", "信息采集", 20, ("history",)),
    ("problem_representation", "问题表征", 15, ("problem_representation",)),
    ("differential_diagnosis", "鉴别诊断", 20, ("differential",)),
    ("evidence_reasoning", "证据推理", 15, ("differential",)),
    ("test_selection", "检查合理性", 15, ("tests",)),
    ("management_safety", "处置与安全意识", 15, ("management",)),
)
SAFETY_NOTICE = "合成教学病例仅用于训练，不代表真实患者或医疗建议。"


class _MessageLike(Protocol):
    @property
    def role(self) -> str: ...

    @property
    def content(self) -> str: ...


class _SubmissionLike(Protocol):
    @property
    def stage_id(self) -> str: ...

    @property
    def answer(self) -> dict[str, object]: ...


class _ProblemLike(Protocol):
    @property
    def rubric(self) -> dict[str, object]: ...


class TrainingAttemptLike(Protocol):
    @property
    def problem(self) -> _ProblemLike: ...

    @property
    def messages(self) -> tuple[_MessageLike, ...]: ...

    @property
    def submissions(self) -> tuple[_SubmissionLike, ...]: ...


@dataclass(frozen=True, slots=True)
class AssessmentCandidate:
    dimension_id: str
    score: float
    evidence: tuple[str, ...]
    feedback: str
    next_step: str


class TrainingPolicy:
    @staticmethod
    def require_in_progress(stage: str, current_stage: str) -> None:
        if current_stage != stage:
            raise AppError("STATE_CONFLICT", "当前阶段不可提交", 409)

    @staticmethod
    def require_stage_answer(stage: str, answer: dict[str, object]) -> None:
        if answer.get("stage_id") != stage:
            raise AppError("VALIDATION_ERROR", "答案阶段与路径不一致", 422)

    @staticmethod
    def require_complete(status: str) -> None:
        if status != "completed":
            raise AppError("STATE_CONFLICT", "全部阶段完成后才能评估", 409)

    @staticmethod
    def next_stage(stage: str) -> str | None:
        try:
            index = CASE_STAGES.index(stage) + 1
        except ValueError as error:
            raise AppError("STATE_CONFLICT", "病例阶段无效", 409) from error
        return CASE_STAGES[index] if index < len(CASE_STAGES) else None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _number(value: object, default: float = 0.0) -> float:
    return float(value) if isinstance(value, int | float) else default


def _collect(value: object, output: list[str]) -> None:
    if isinstance(value, str) and value.strip() and value not in {"history", *CASE_STAGES[1:]}:
        output.append(value.strip())
    elif isinstance(value, list):
        for item in value:
            _collect(item, output)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in {"stage_id", "priority"}:
                _collect(item, output)


def answer_sources(attempt: TrainingAttemptLike, stage_ids: tuple[str, ...]) -> list[str]:
    """Collect only student-authored text; attempt is a narrow structural port."""
    sources: list[str] = []
    if "history" in stage_ids:
        sources.extend(message.content for message in attempt.messages if message.role == "user")
    for submission in attempt.submissions:
        if submission.stage_id in stage_ids:
            _collect(submission.answer, sources)
    return sources


def _evidence_for_keyword(sources: list[str], keyword: str) -> str | None:
    needle = _normalize(keyword)
    candidates = [
        part.strip()
        for source in sources
        for part in re.split(r"[。！？；\n]", source)
        if part.strip() and needle in _normalize(part)
    ]
    return min(candidates, key=len)[:160] if candidates else None


def deterministic_assessment(
    attempt: TrainingAttemptLike,
) -> tuple[list[dict[str, object]], str, list[str], list[str], list[str], int, str]:
    rubric = attempt.problem.rubric or {}
    dimensions: list[dict[str, object]] = []
    for dimension in _dict_list(rubric.get("dimensions", [])):
        stage_ids = tuple(_string_list(dimension.get("stage_ids", [])))
        sources = answer_sources(attempt, stage_ids)
        text = "|".join(_normalize(source) for source in sources)
        criteria = _dict_list(dimension.get("criteria", []))
        hits = [
            criterion
            for criterion in criteria
            if any(_normalize(str(keyword)) in text for keyword in _string_list(criterion.get("keywords", [])))
        ]
        raw = round(100 * len(hits) / len(criteria), 1) if criteria else 0
        if any(item.get("critical") for item in criteria) and any(
            item.get("critical") and item not in hits for item in criteria
        ):
            raw = min(raw, 69)
        evidence: list[str] = []
        for criterion in hits:
            for keyword in _string_list(criterion.get("keywords", [])):
                snippet = _evidence_for_keyword(sources, str(keyword))
                if snippet and snippet not in evidence:
                    evidence.append(snippet)
        evidence = evidence[:3] or ["尚未发现对应的学生原文证据"]
        missed = next((item for item in criteria if item not in hits), None)
        dimensions.append(
            {
                "dimension_id": dimension.get("id"),
                "label": dimension.get("label"),
                "score": raw,
                "weighted_score": round(raw * _number(dimension.get("weight", 0)) / 100, 1),
                "evidence": evidence,
                "feedback": "证据较完整。" if missed is None else missed.get("feedback", "补充结构化证据。"),
                "next_step": "继续保持结构化推理。" if missed is None else missed.get("feedback", "补充结构化证据。"),
            }
        )
    expected = {item[0] for item in DIMENSION_SPECS}
    if {item.get("dimension_id") for item in dimensions} != expected:
        raise AppError("VALIDATION_ERROR", "病例评分规则无效", 422)
    focus_stage, strengths, weaknesses, next_steps, total = summarize_dimensions(dimensions)
    return dimensions, focus_stage, strengths, weaknesses, next_steps, total, SAFETY_NOTICE


def summarize_dimensions(
    dimensions: list[dict[str, object]],
) -> tuple[str, list[str], list[str], list[str], int]:
    focus = min(
        dimensions,
        key=lambda item: (
            _number(item.get("score", 0)),
            next(index for index, spec in enumerate(DIMENSION_SPECS) if spec[0] == item.get("dimension_id")),
        ),
    )
    focus_stage = next(spec[3][0] for spec in DIMENSION_SPECS if spec[0] == focus.get("dimension_id"))
    strengths = [str(item.get("label")) for item in dimensions if _number(item.get("score", 0)) >= 70]
    weaknesses = [str(item.get("label")) for item in dimensions if _number(item.get("score", 0)) < 70]
    total = round(sum(_number(item.get("weighted_score", 0)) for item in dimensions))
    next_steps = [str(focus.get("next_step", "继续练习。"))]
    return focus_stage, strengths, weaknesses, next_steps, total


def apply_ai_candidates(
    attempt: TrainingAttemptLike, dimensions: list[dict[str, object]], candidates: tuple[AssessmentCandidate, ...]
) -> None:
    """Apply only bounded feedback from the model to deterministic assessment output.

    The server-side rubric is the sole owner of scores, weights, totals, and evidence.
    Candidate score is deliberately ignored even when it is finite or in range; a
    model must not be able to manufacture credit without matching student evidence.
    """
    rubric = attempt.problem.rubric or {}
    by_id = {str(item.get("dimension_id")): item for item in dimensions}
    for candidate in candidates:
        target = by_id.get(candidate.dimension_id)
        config = next(
            (item for item in _dict_list(rubric.get("dimensions", [])) if item.get("id") == candidate.dimension_id),
            None,
        )
        if target is None or config is None:
            continue
        sources = answer_sources(attempt, tuple(_string_list(config.get("stage_ids", []))))
        safe_evidence = [
            evidence[:160]
            for evidence in candidate.evidence[:3]
            if evidence and any(evidence in source for source in sources)
        ]
        if candidate.evidence and len(safe_evidence) != len(candidate.evidence[:3]):
            continue
        # Scores, weights, and evidence were produced by deterministic_assessment.
        # The model may only rewrite bounded presentation text after evidence has
        # been verified.  In particular, do not use candidate.score here.
        target["feedback"] = candidate.feedback[:1000]
        target["next_step"] = candidate.next_step[:1000]
