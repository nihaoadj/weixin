"""Versioned, read-only teaching knowledge catalog for T08.

The catalog contains only synthetic teaching prompts.  It is intentionally
separate from student-specific progress so a future content revision cannot
rewrite a learner's historical review evidence.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeCard:
    code: str
    point_code: str
    prompt: str
    options: tuple[str, ...]
    correct_option: int
    explanation: str
    reference: str


@dataclass(frozen=True, slots=True)
class KnowledgePoint:
    code: str
    system: str
    topic: str
    title: str
    objective: str
    reference: str


CATALOG_VERSION = "internal-medicine-v1"

POINTS: tuple[KnowledgePoint, ...] = (
    KnowledgePoint(
        "respiratory.cap",
        "respiratory",
        "感染性疾病",
        "社区获得性肺炎",
        "识别教学病例中的典型线索与初步评估重点。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "respiratory.asthma",
        "respiratory",
        "气道疾病",
        "哮喘急性发作",
        "识别急性气道症状的评估与升级边界。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "cardio.acs",
        "cardio",
        "缺血性心脏病",
        "急性冠脉综合征",
        "识别胸痛危险分层中的关键病史与检查线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "cardio.hypertension",
        "cardio",
        "高血压",
        "高血压基础评估",
        "说明血压评估需要结合重复测量与整体风险。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "digestive.gi-bleed",
        "digestive",
        "消化道疾病",
        "上消化道出血",
        "识别消化道出血教学情境中的风险线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "digestive.pancreatitis",
        "digestive",
        "胰腺疾病",
        "急性胰腺炎",
        "建立症状、实验室线索与安全评估的联系。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "renal.aki", "renal", "肾功能异常", "急性肾损伤", "按病因分类组织急性肾损伤的初步判断。", "教学版内科学参考"
    ),
    KnowledgePoint(
        "renal.electrolyte",
        "renal",
        "水电解质",
        "高钾血症风险",
        "识别需要优先升级评估的高钾风险线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "hematology.anemia",
        "hematology",
        "贫血",
        "贫血初步分类",
        "用红细胞指标组织贫血的基础分类。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "hematology.bleeding",
        "hematology",
        "凝血",
        "出血倾向评估",
        "识别出血风险教学场景中的基础问诊重点。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "endocrine.diabetes",
        "endocrine",
        "糖代谢",
        "糖尿病慢病管理",
        "说明糖代谢异常的长期风险评估思路。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "endocrine.thyroid",
        "endocrine",
        "甲状腺",
        "甲状腺功能异常",
        "区分甲状腺功能异常的常见教学线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "respiratory.copd",
        "respiratory",
        "慢性气道疾病",
        "慢阻肺急性加重",
        "识别慢性气道症状恶化时的风险线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "respiratory.pleural-effusion",
        "respiratory",
        "胸膜疾病",
        "胸腔积液基础评估",
        "组织症状、体征和影像线索的教学解释。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "cardio.heart-failure",
        "cardio",
        "心力衰竭",
        "急性心力衰竭",
        "识别容量负荷和灌注改变的教学线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "cardio.arrhythmia",
        "cardio",
        "心律失常",
        "常见心律失常评估",
        "说明心悸与晕厥线索的安全评估边界。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "digestive.appendicitis",
        "digestive",
        "急腹症",
        "右下腹痛与阑尾炎",
        "组织右下腹痛的病程、体征与鉴别线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "digestive.hepatitis",
        "digestive",
        "肝脏疾病",
        "肝功能异常基础评估",
        "关联黄疸、肝功指标和风险因素的教学线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "renal.ckd", "renal", "慢性肾脏病", "慢性肾脏病分层", "说明肾功能长期随访与风险管理框架。", "教学版内科学参考"
    ),
    KnowledgePoint(
        "renal.uti",
        "renal",
        "泌尿系感染",
        "尿路感染基础判断",
        "识别症状、尿检与升级评估的教学线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "hematology.leukocytosis",
        "hematology",
        "白细胞异常",
        "白细胞异常解读",
        "结合病程组织白细胞异常的基础解释。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "hematology.thrombosis",
        "hematology",
        "血栓与凝血",
        "静脉血栓风险",
        "识别血栓风险因素和警示症状的教学重点。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "endocrine.dka",
        "endocrine",
        "急性代谢异常",
        "糖尿病酮症酸中毒风险",
        "识别高血糖急症中的安全评估线索。",
        "教学版内科学参考",
    ),
    KnowledgePoint(
        "endocrine.adrenal",
        "endocrine",
        "肾上腺",
        "肾上腺功能异常",
        "组织电解质、血压与激素相关的教学线索。",
        "教学版内科学参考",
    ),
)

CARDS: tuple[KnowledgeCard, ...] = (
    KnowledgeCard(
        "respiratory.cap.basics.1",
        "respiratory.cap",
        "在发热、咳嗽、气促的教学病例中，哪项信息最有助于初步判断病情严重度？",
        ("是否有季节性过敏", "生命体征和血氧情况", "最喜欢的运动", "既往视力"),
        1,
        "生命体征和氧合情况是识别需要优先评估风险的重要公开线索。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "respiratory.asthma.basics.1",
        "respiratory.asthma",
        "出现进行性呼吸困难时，教学训练中首先应强调什么？",
        ("延后评估", "仅记录症状名称", "识别危险信号并升级评估", "自行调整处方"),
        2,
        "本系统用于教学；出现危险信号应优先升级线下专业评估。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "cardio.acs.basics.1",
        "cardio.acs",
        "突发持续胸骨后压榨样不适伴出汗时，合理的教学推理优先级是？",
        ("先做危险分层", "先判断饮食偏好", "等待症状自行消失", "只讨论远期康复"),
        0,
        "胸痛伴危险线索时，应先完成风险识别和及时评估边界。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "cardio.hypertension.basics.1",
        "cardio.hypertension",
        "对血压异常的学习性判断，哪项表述更合适？",
        ("单次读数即可完成所有判断", "应结合规范重复测量和整体风险", "只根据年龄判断", "无需记录测量条件"),
        1,
        "教学中应强调测量质量、重复确认和综合风险，而非用单次读数替代评估。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "digestive.gi-bleed.basics.1",
        "digestive.gi-bleed",
        "面对疑似消化道出血的教学情境，哪项属于需要优先关注的线索？",
        ("循环状态变化", "发型变化", "偏爱的食物", "近期阅读量"),
        0,
        "循环状态变化提示需要优先进行安全评估。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "digestive.pancreatitis.basics.1",
        "digestive.pancreatitis",
        "急性腹痛教学推理中，检查选择应首先说明什么？",
        ("检查目的和适用性", "检查名称越多越好", "不需要结合病程", "只考虑费用"),
        0,
        "检查决策应说明目的、优先级和与病程/查体的关系。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "renal.aki.basics.1",
        "renal.aki",
        "急性肾功能异常的教学分类常从哪三类原因组织？",
        ("肾前性、肾性、肾后性", "春夏秋", "轻中重三个颜色", "仅按年龄"),
        0,
        "肾前性、肾性与肾后性是基础教学分类框架。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "renal.electrolyte.basics.1",
        "renal.electrolyte",
        "电解质异常教学中出现心律相关症状时，应优先强调什么？",
        ("延迟复评", "安全风险与升级评估", "只做长期记录", "自行试药"),
        1,
        "可能危及生命的线索应触发及时专业评估，而非线上自处置。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "hematology.anemia.basics.1",
        "hematology.anemia",
        "贫血初步分类时，哪项实验室信息通常有助于组织学习思路？",
        ("红细胞指标", "鞋码", "惯用手", "屏幕时间"),
        0,
        "红细胞相关指标可作为基础分类线索，仍需结合完整临床背景。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "hematology.bleeding.basics.1",
        "hematology.bleeding",
        "出血倾向教学问诊中，哪项信息与风险评估直接相关？",
        ("出血部位、持续时间和用药史", "最爱颜色", "通勤方式", "收藏数量"),
        0,
        "出血模式和可能影响凝血的用药是重要教学线索。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "endocrine.diabetes.basics.1",
        "endocrine.diabetes",
        "糖代谢异常的长期学习管理通常应包含什么？",
        ("风险因素、生活方式与随访", "只看一次症状", "忽略并发风险", "仅比较体重"),
        0,
        "慢病学习应把风险、生活方式与持续随访放在同一框架。",
        "教学版内科学参考",
    ),
    KnowledgeCard(
        "endocrine.thyroid.basics.1",
        "endocrine.thyroid",
        "面对可能的甲状腺功能异常，哪种学习策略更合理？",
        ("孤立解读单一症状", "结合症状、体征和规范检查解释", "依据网络投票判断", "自行调整药物"),
        1,
        "教学推理应综合公开临床信息和规范检查，不提供个体化处方。",
        "教学版内科学参考",
    ),
) + tuple(
    KnowledgeCard(
        f"{point.code}.basics.1",
        point.code,
        f"学习“{point.title}”时，哪种做法最符合安全、可复核的教学推理？",
        ("结合病程、客观线索与风险边界", "只依据单一症状下结论", "忽略危险信号", "自行替代专业评估"),
        0,
        "教学推理应整合公开临床线索并识别需要升级专业评估的边界。",
        point.reference,
    )
    for point in POINTS
    if point.code
    not in {
        "respiratory.cap",
        "respiratory.asthma",
        "cardio.acs",
        "cardio.hypertension",
        "digestive.gi-bleed",
        "digestive.pancreatitis",
        "renal.aki",
        "renal.electrolyte",
        "hematology.anemia",
        "hematology.bleeding",
        "endocrine.diabetes",
        "endocrine.thyroid",
    }
)


def tree_view() -> list[dict[str, object]]:
    systems = {
        "respiratory": "呼吸系统",
        "cardio": "循环系统",
        "digestive": "消化系统",
        "renal": "泌尿系统",
        "hematology": "血液系统",
        "endocrine": "内分泌与代谢",
    }
    return [
        {
            "code": point.code,
            "system_code": point.system,
            "system_label": systems[point.system],
            "topic": point.topic,
            "title": point.title,
            "objective": point.objective,
            "reference": point.reference,
            "card_count": len([card for card in CARDS if card.point_code == point.code]),
            "catalog_version": CATALOG_VERSION,
        }
        for point in POINTS
    ]


def point_view(code: str) -> dict[str, object] | None:
    return next((item for item in tree_view() if item["code"] == code), None)


def card_for_code(code: str) -> KnowledgeCard | None:
    return next((card for card in CARDS if card.code == code), None)


def cards_for_points(point_codes: tuple[str, ...]) -> tuple[KnowledgeCard, ...]:
    allowed = set(point_codes)
    return tuple(card for card in CARDS if card.point_code in allowed)
