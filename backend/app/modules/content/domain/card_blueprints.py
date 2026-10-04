"""Development-only authored card blueprints.

These rows seed ``knowledge_card_contributions``. They are not a runtime
knowledge-point or dependency registry; the active catalog is read from the
database through ``KnowledgeCatalogPort``.
"""

from dataclasses import dataclass

from app.modules.content.domain.pathology_data import POINT_DATA

REFERENCE = "合成病理学总论教学材料；正式使用前须教师审核"


@dataclass(frozen=True, slots=True)
class KnowledgeCardBlueprint:
    code: str
    point_code: str
    prompt: str
    options: tuple[str, ...]
    correct_option: int
    explanation: str
    reference: str
    card_type: str = "single_choice"


def _cards() -> tuple[KnowledgeCardBlueprint, ...]:
    result = []
    for topic, rows in POINT_DATA.items():
        for index, row in enumerate(rows):
            for offset, (kind, question, options) in enumerate(
                (("practice", row[3], row[4]), ("retest", row[5], row[6]))
            ):
                rotation = (index + offset) % 4
                choices = options[-rotation:] + options[:-rotation] if rotation else options
                result.append(
                    KnowledgeCardBlueprint(
                        f"{topic}.{row[0]}.{kind}",
                        f"{topic}.{row[0]}",
                        question,
                        choices,
                        rotation,
                        row[2],
                        REFERENCE,
                    )
                )
                second_rotation = (rotation + 1) % 4
                result.append(
                    KnowledgeCardBlueprint(
                        f"{topic}.{row[0]}.{kind}.v2",
                        f"{topic}.{row[0]}",
                        f"等价变式：{question}",
                        options[-second_rotation:] + options[:-second_rotation],
                        second_rotation,
                        f"从不同表述再次核对同一目标：{row[2]}",
                        REFERENCE,
                    )
                )
    return tuple(result)


CARDS = _cards()
RECALL_CARDS = tuple(
    KnowledgeCardBlueprint(
        f"{topic}.{row[0]}.recall",
        f"{topic}.{row[0]}",
        f"请先回忆：如何解释{row[1]}，并举出一条可以核对的证据？",
        (),
        -1,
        row[2],
        REFERENCE,
        "recall",
    )
    for topic, rows in POINT_DATA.items()
    for row in rows
)
