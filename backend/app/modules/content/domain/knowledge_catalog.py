"""The single versioned pathology catalog; public exports never contain answers."""

from dataclasses import dataclass

from app.modules.content.domain.pathology_data import POINT_DATA, TOPICS

CATALOG_VERSION = "pathology-general-v2"
REFERENCE = "合成病理学总论教学材料；正式使用前须教师审核"


@dataclass(frozen=True, slots=True)
class KnowledgePoint:
    code: str
    system: str
    topic: str
    title: str
    objective: str
    reference: str
    description: str = ""
    prerequisite_codes: tuple[str, ...] = ()
    related_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeCard:
    code: str
    point_code: str
    prompt: str
    options: tuple[str, ...]
    correct_option: int
    explanation: str
    reference: str
    card_type: str = "single_choice"


def _points() -> tuple[KnowledgePoint, ...]:
    result = []
    prerequisites_by_suffix = {
        "reversible": ("pathology.cell-injury.adaptation",),
        "necrosis": ("pathology.cell-injury.reversible",),
        "apoptosis": ("pathology.cell-injury.necrosis",),
        "hypoxia": ("pathology.cell-injury.reversible",),
        "oxidative": ("pathology.cell-injury.reversible",),
        "leukocytes": ("pathology.inflammation.vascular",),
        "mediators": ("pathology.inflammation.vascular",),
        "acute": ("pathology.inflammation.leukocytes", "pathology.inflammation.mediators"),
        "chronic": ("pathology.inflammation.acute",),
        "granuloma": ("pathology.inflammation.chronic",),
        "regeneration": ("pathology.cell-injury.adaptation",),
        "granulation": ("pathology.inflammation.acute",),
        "matrix": ("pathology.repair.granulation",),
        "wound": ("pathology.repair.regeneration", "pathology.repair.matrix"),
        "fibrosis": ("pathology.repair.matrix",),
        "factors": ("pathology.repair.wound",),
        "edema": ("pathology.inflammation.vascular",),
        "embolism": ("pathology.circulatory.thrombosis",),
        "infarction": ("pathology.circulatory.embolism", "pathology.cell-injury.necrosis"),
        "shock": ("pathology.circulatory.congestion", "pathology.cell-injury.hypoxia"),
        "behavior": ("pathology.neoplasm.atypia",),
        "spread": ("pathology.neoplasm.behavior",),
        "grading": ("pathology.neoplasm.atypia", "pathology.neoplasm.spread"),
        "effects": ("pathology.neoplasm.spread",),
    }
    for topic, rows in POINT_DATA.items():
        for index, row in enumerate(rows):
            code = f"{topic}.{row[0]}"
            prerequisites = prerequisites_by_suffix.get(row[0], ())
            related = (f"{topic}.{rows[(index + 1) % len(rows)][0]}",)
            result.append(
                KnowledgePoint(
                    code,
                    topic,
                    TOPICS[topic],
                    row[1],
                    f"解释{row[1]}的机制，并用形态或情境证据支持判断。",
                    REFERENCE,
                    row[2],
                    prerequisites,
                    related,
                )
            )
    return tuple(result)


POINTS = _points()


def _cards() -> tuple[KnowledgeCard, ...]:
    result = []
    for topic, rows in POINT_DATA.items():
        for index, row in enumerate(rows):
            for offset, (kind, question, options) in enumerate(
                (("practice", row[3], row[4]), ("retest", row[5], row[6]))
            ):
                rotation = (index + offset) % 4
                choices = options[-rotation:] + options[:-rotation] if rotation else options
                result.append(
                    KnowledgeCard(
                        f"{topic}.{row[0]}.{kind}", f"{topic}.{row[0]}", question, choices, rotation, row[2], REFERENCE
                    )
                )
    return tuple(result)


CARDS = _cards()
RECALL_CARDS = tuple(
    KnowledgeCard(
        f"{point.code}.recall",
        point.code,
        f"请先回忆：如何解释{point.title}，并举出一条可以核对的证据？",
        (),
        -1,
        point.description,
        REFERENCE,
        "recall",
    )
    for point in POINTS
)


def tree_view() -> list[dict[str, object]]:
    return [
        {
            "code": p.code,
            "system_code": p.system,
            "system_label": TOPICS[p.system],
            "topic": p.topic,
            "title": p.title,
            "objective": p.objective,
            "reference": p.reference,
            "card_count": 3,
            "catalog_version": CATALOG_VERSION,
            "parent_code": p.system,
            "description": p.description,
            "prerequisite_codes": list(p.prerequisite_codes),
            "related_codes": list(p.related_codes),
            "relationship_note": "先复习前置概念，再比较本主题相关机制；关系不代表个人掌握程度。",
            "case_slug": f"{p.system}-showcase",
        }
        for p in POINTS
    ]


def point_view(code: str) -> dict[str, object] | None:
    return next((item for item in tree_view() if item["code"] == code), None)


def card_for_code(code: str) -> KnowledgeCard | None:
    return next((card for card in (*CARDS, *RECALL_CARDS) if card.code == code), None)


def cards_for_points(point_codes: tuple[str, ...]) -> tuple[KnowledgeCard, ...]:
    return tuple(card for card in CARDS if card.point_code in point_codes)


def pathology_topics() -> dict[str, str]:
    return dict(TOPICS)
