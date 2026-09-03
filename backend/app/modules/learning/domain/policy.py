from __future__ import annotations

import hashlib
import json
import re
from typing import Protocol

from app.modules.training.public import CASE_DIMENSION_ORDER, CASE_DIMENSION_STAGES
from app.shared.errors import AppError

PRACTICE_PROMPT_VERSION = "practice-v1"
DIMENSION_ORDER = CASE_DIMENSION_ORDER


class ProblemLike(Protocol):
    @property
    def id(self) -> int: ...

    @property
    def difficulty(self) -> str: ...

    @property
    def rubric(self) -> dict[str, object]: ...

    @property
    def case_definition(self) -> dict[str, object]: ...


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _number(value: object, default: float = 0.0) -> float:
    return float(value) if isinstance(value, int | float) else default


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def target_dimensions(dimensions: tuple[dict[str, object], ...]) -> list[str]:
    ordered = sorted(
        dimensions,
        key=lambda item: (_number(item.get("score", 0)), DIMENSION_ORDER.get(str(item.get("dimension_id", "")), 99)),
    )
    below = [item for item in ordered if _number(item.get("score", 0)) < 70]
    if len(below) >= 2:
        return [str(item["dimension_id"]) for item in below[:2]]
    if len(below) == 1:
        fallback = (
            str(ordered[1].get("dimension_id", below[0]["dimension_id"]))
            if len(ordered) > 1
            else str(below[0]["dimension_id"])
        )
        return [str(below[0]["dimension_id"]), fallback]
    return [str(ordered[0]["dimension_id"])]


def stage_for_dimension(dimension_id: str) -> str:
    return str(CASE_DIMENSION_STAGES[dimension_id])


def dimension_config(problem: ProblemLike, dimension_id: str) -> dict[str, object]:
    return next(
        (item for item in _dict_list((problem.rubric or {}).get("dimensions", [])) if item.get("id") == dimension_id),
        {"id": dimension_id, "criteria": []},
    )


def blueprint(problem: ProblemLike, dimension_id: str) -> dict[str, object] | None:
    return next(
        (
            item
            for item in _dict_list((problem.case_definition or {}).get("practice_blueprints", []))
            if item.get("dimension_id") == dimension_id
        ),
        None,
    )


def fallback_blueprint(problem: ProblemLike, dimension_id: str) -> dict[str, object]:
    config = dimension_config(problem, dimension_id)
    source_criteria = _dict_list(config.get("criteria", []))
    criteria: list[dict[str, object]] = [
        {
            "id": item.get("id", f"criterion-{index}"),
            "weight": round(100 / max(1, len(source_criteria)), 2),
            "keywords": item.get("keywords", []),
            "feedback": item.get("feedback", "补充结构化证据。"),
            "critical": item.get("critical", False),
        }
        for index, item in enumerate(source_criteria, start=1)
    ]
    if criteria:
        criteria[-1]["weight"] = round(
            _number(criteria[-1].get("weight")) + 100 - sum(_number(item.get("weight")) for item in criteria),
            2,
        )
    else:
        criteria = [
            {"id": "evidence", "weight": 100, "keywords": [], "feedback": "补充可核验的原文证据。", "critical": False}
        ]
    return {
        "id": f"fallback-{problem.id}-{dimension_id}",
        "dimension_id": dimension_id,
        "stage_id": stage_for_dimension(dimension_id),
        "learner_level": "undergraduate",
        "public_instruction": f"围绕{dimension_id}完成一段结构化推理，并说明依据。",
        "allowed_variants": [],
        "fixed_facts": [],
        "fallback_prompt": "请基于教学情境给出不含处方剂量的结构化回答。",
        "answer_schema": "short_text",
        "criteria": criteria,
    }


def blueprint_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def require_unlocked(position: int, previous_status: str | None) -> None:
    if position > 1 and previous_status != "completed":
        raise AppError("STATE_CONFLICT", "STATE_CONFLICT", 409)


def answer_text(answer: object) -> str:
    if isinstance(answer, str):
        return answer.strip()
    if isinstance(answer, list):
        return " ".join(answer_text(item) for item in answer)
    if isinstance(answer, dict):
        return " ".join(answer_text(value) for key, value in answer.items() if key not in {"id", "stage_id"})
    return ""


def _snippet(text: str, keyword: str) -> str | None:
    for chunk in re.split(r"[。！？；\n]", text):
        if keyword.lower() in chunk.lower() and chunk.strip():
            return chunk.strip()[:160]
    return None


def assess_micro(answer: dict[str, object], rubric: dict[str, object]) -> tuple[float, list[str], str, str]:
    text = answer_text(answer)
    criteria = _dict_list(rubric.get("criteria", []))
    hits: list[dict[str, object]] = []
    evidence: list[str] = []
    weighted = 0.0
    for criterion in criteria:
        keywords = [str(item) for item in _string_list(criterion.get("keywords", []))]
        match = not keywords or any(keyword.lower() in text.lower() for keyword in keywords)
        if match:
            hits.append(criterion)
            weighted += _number(criterion.get("weight", 0))
            for keyword in keywords:
                snippet = _snippet(text, keyword)
                if snippet and snippet not in evidence:
                    evidence.append(snippet)
    score = min(100.0, round(weighted, 1))
    if any(item.get("critical") and item not in hits for item in criteria):
        score = min(score, 69.0)
    missing = next((item for item in criteria if item not in hits), None)
    feedback = "证据较完整。" if missing is None else str(missing.get("feedback", "补充结构化证据。"))
    next_step = "继续保持结构化推理。" if missing is None else "补充缺失证据后再次练习。"
    return score, evidence[:3] or [text[:160] or "未提供可核验原文证据"], feedback, next_step
