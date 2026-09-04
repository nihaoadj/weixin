"""Content-owned synthetic pathology case drafts; publication requires medical review."""

from app.modules.content.domain.pathology_cases import CASES
from app.modules.content.domain.pathology_data import TOPICS

SAFETY_NOTICE = "合成病理学教学材料，正式使用前须医学审核；不能替代真实诊疗。"
STAGES = {
    "history": "收集病变的背景、时间与形态观察，区分已知和待查信息。",
    "problem_representation": "用一句话概括病理问题，保留关键形态与机制线索。",
    "differential": "提出至少两个解释，逐一列出支持、反对和缺少的证据。",
    "tests": "选择能够区分假设的进一步观察或检查，说明目的与局限。",
    "management": "总结病理机制、判断边界和需要教师复核的疑点。",
}
DIMENSIONS = (
    ("information_gathering", "病理信息采集", 20, "history"),
    ("problem_representation", "病理问题表征", 15, "problem_representation"),
    ("differential_diagnosis", "病理假设比较", 20, "differential"),
    ("evidence_reasoning", "形态与机制证据推理", 15, "differential"),
    ("test_selection", "验证方法选择", 15, "tests"),
    ("management_safety", "解释边界与安全", 15, "management"),
)


def topic_for_draft(topic: str):
    return next(
        (
            key
            for key, title in TOPICS.items()
            if key == topic or title in topic or any(word in topic for word in CASES[key]["keywords"])
        ),
        "pathology.cell-injury",
    )


def showcase_draft(topic: str = "细胞损伤与适应") -> dict[str, object]:
    key = topic_for_draft(topic)
    case = CASES[key]
    def criteria(dim):
        return [
            {
                "id": dim + "_evidence",
                "label": "以形态证据支持机制解释",
                "keywords": case["keywords"],
                "feedback": case["mechanism"],
                "critical": False,
            }
        ]
    facts = [
        {
            "id": "background",
            "category": "history",
            "label": "教学背景",
            "value": case["intro"],
            "triggers": ["背景", "经过", "时间"],
            "reveal_stage": "history",
        },
        {
            "id": "morphology",
            "category": "exam",
            "label": "形态观察",
            "value": case["observation"],
            "triggers": ["形态", "切片", "观察", "表现"],
            "reveal_stage": "history",
        },
        {
            "id": "comparison",
            "category": "test",
            "label": "对照复核",
            "value": "对照相邻区域和另一份标本，复核形态差异。",
            "triggers": ["对照", "复核", "检查"],
            "reveal_stage": "tests",
        },
    ]
    blueprints = [
        {
            "id": key + "." + dim,
            "dimension_id": dim,
            "stage_id": stage,
            "learner_level": "undergraduate",
            "public_instruction": STAGES[stage],
            "allowed_variants": ["调整追问顺序"],
            "fixed_facts": [case["observation"]],
            "fallback_prompt": case["question"] + " " + STAGES[stage],
            "answer_schema": "short_text",
            "criteria": [{**{k: v for k, v in criteria(dim)[0].items() if k != "label"}, "weight": 100}],
        }
        for dim, _, _, stage in DIMENSIONS
    ]
    return {
        "title": case["title"],
        "description": case["question"] + "（开发合成样例）",
        "specialty": "病理学",
        "difficulty": "basic",
        "estimated_minutes": 15,
        "case_definition": {
            "schema_version": 2,
            "opening": {
                "setting": case["setting"],
                "patient_intro": case["intro"],
                "chief_complaint": case["question"],
            },
            "stage_instructions": STAGES.copy(),
            "facts": facts,
            "practice_blueprints": blueprints,
            "reference_reasoning": {
                "problem_representation": case["mechanism"],
                "differentials": [
                    {"diagnosis": name, "supporting_fact_ids": ["morphology"], "opposing_fact_ids": [], "priority": i}
                    for i, name in enumerate(case["alternatives"], 1)
                ],
                "tests": [
                    {
                        "name": "形态对照复核",
                        "purpose": "寻找能区分两种解释的证据",
                        "priority": "necessary",
                        "result_fact_id": "comparison",
                    }
                ],
                "management": [
                    {
                        "action": "向教师核对推理与证据",
                        "rationale": SAFETY_NOTICE,
                        "priority": 1,
                        "safety_critical": True,
                    }
                ],
            },
        },
        "rubric": {
            "dimensions": [
                {"id": dim, "label": label, "weight": weight, "stage_ids": [stage], "criteria": criteria(dim)}
                for dim, label, weight, stage in DIMENSIONS
            ]
        },
    }


__all__ = ["SAFETY_NOTICE", "showcase_draft"]
