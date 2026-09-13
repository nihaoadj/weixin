"""Versioned synthetic reading material, composed from the existing authored catalog."""

from app.modules.content.domain.knowledge_catalog import POINTS, REFERENCE
from app.modules.content.domain.pathology_data import POINT_DATA

MATERIAL_VERSION = "pathology-study-v1"


def study_material(point_code: str) -> dict | None:
    point = next((p for p in POINTS if p.code == point_code), None)
    if point is None:
        return None
    row = next(r for r in POINT_DATA[point.system] if point.code == f"{point.system}.{r[0]}")
    return {
        "version": MATERIAL_VERSION,
        "point_code": point_code,
        "title": point.title,
        "objective": point.objective,
        "scenario": row[3],
        "background": [
            {
                "title": "观察与解释",
                "text": f"围绕{point.title}，先记录题目已经提供的形态或情境线索，将观察与推断分开。",
            },
            {"title": "研讨准备", "text": "提出一种可能的机制，并说明还需要什么证据；不确定之处可以直接带入研讨。"},
        ],
        "example": {"title": "比较情境", "text": row[5]},
        "remediation": [
            {"title": "机制回顾", "text": point.description},
            {"title": "再次解释", "text": "对照研讨中发现的薄弱点，用机制、支持证据和限制重新组织解释。"},
        ],
        "reference": REFERENCE,
        "review_status": "unreviewed",
    }
