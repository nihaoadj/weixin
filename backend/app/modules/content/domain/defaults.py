from __future__ import annotations

from app.modules.content.domain.templates import showcase_draft


def deterministic_case_draft(topic: str, learner_level: str, objectives: list[str]) -> dict[str, object]:
    """Build the approved AI-disabled draft without importing bootstrap seed code."""

    draft = showcase_draft(topic)
    objective_text = "、".join(item.strip() for item in objectives if item.strip())
    draft["description"] = (
        f"{draft['description']} 学习层级：{learner_level}。教学目标：{objective_text or '完成结构化临床推理。'}"
    )
    return draft


__all__ = ["deterministic_case_draft"]
