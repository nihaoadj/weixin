"""Persist the evidence-linked pathology knowledge graph."""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260916_0028"
down_revision = "20260914_0027"
branch_labels = None
depends_on = None

CATALOG_VERSION = "pathology-general-v4"
REFERENCE_NOTE = "基于列明公开权威资料建立；尚待课程负责人或病理学专家签署复核。"
EVIDENCE_STATUS = "source_supported"
REVIEW_STATUS = "pending_expert_review"

MODULES = (
    ("pathology.cell-injury", "细胞损伤与适应", "细胞对应激的适应、损伤机制与细胞死亡。"),
    ("pathology.inflammation", "炎症", "炎症介质、血管与白细胞反应及主要形态模式。"),
    ("pathology.repair", "修复", "组织再生、肉芽组织、基质重塑、愈合与纤维化。"),
    ("pathology.circulatory", "循环障碍", "水肿、血栓栓塞、梗死与休克等血流动力学障碍。"),
    ("pathology.neoplasm", "肿瘤", "肿瘤发生、形态、行为、播散、分级分期与机体影响。"),
)

POINTS = (
    (
        "pathology.cell-injury",
        "adaptation",
        "细胞适应",
        "肥大以细胞体积增大为主，增生以细胞数量增加为主；适应并不等于肿瘤性生长。",
    ),
    (
        "pathology.cell-injury",
        "reversible",
        "可逆性损伤",
        "细胞肿胀可由能量不足及离子泵功能障碍引起；早期改变不能单独证明细胞已经死亡。",
    ),
    (
        "pathology.cell-injury",
        "necrosis",
        "坏死",
        "坏死常伴细胞膜完整性破坏、内容物外泄和炎症；需结合核与组织结构变化判断。",
    ),
    (
        "pathology.cell-injury",
        "apoptosis",
        "凋亡",
        "凋亡是受调控的细胞死亡，常形成膜包裹的凋亡小体，通常不引起显著周围炎症。",
    ),
    (
        "pathology.cell-injury",
        "hypoxia",
        "缺氧性损伤",
        "氧供应不足可抑制氧化磷酸化并减少 ATP；结局取决于程度、持续时间和组织耐受性。",
    ),
    (
        "pathology.cell-injury",
        "oxidative",
        "氧化应激损伤",
        "活性氧产生与清除失衡可损伤膜脂、蛋白和核酸；再灌注也可能伴随氧化应激。",
    ),
    ("pathology.inflammation", "vascular", "炎症血管反应", "血管扩张增加局部血流，通透性增加促进液体与蛋白外渗。"),
    ("pathology.inflammation", "leukocytes", "白细胞募集", "白细胞经边集、滚动、黏附、穿越血管壁和趋化进入损伤区域。"),
    ("pathology.inflammation", "mediators", "炎症介质", "细胞及血浆来源介质共同调节血管变化、白细胞反应和疼痛等表现。"),
    (
        "pathology.inflammation",
        "acute",
        "急性炎症形态",
        "急性炎症可呈浆液性、纤维素性、化脓性等形态；渗出物和优势细胞是描述依据。",
    ),
    (
        "pathology.inflammation",
        "chronic",
        "慢性炎症",
        "慢性炎症常同时出现单核细胞浸润、组织损伤与修复；持续刺激可推动纤维化。",
    ),
    (
        "pathology.inflammation",
        "granuloma",
        "肉芽肿性炎症",
        "肉芽肿以聚集的活化巨噬细胞和上皮样细胞为特征，与修复性肉芽组织不同。",
    ),
    (
        "pathology.repair",
        "regeneration",
        "组织再生",
        "再生依赖存活细胞的增殖能力和支架完整性；结构破坏严重时更可能发生瘢痕修复。",
    ),
    (
        "pathology.repair",
        "granulation",
        "肉芽组织",
        "肉芽组织富含新生毛细血管、成纤维细胞及疏松基质，是修复阶段的组织。",
    ),
    (
        "pathology.repair",
        "matrix",
        "细胞外基质重塑",
        "修复过程中基质合成与降解共同决定组织结构；重塑不等同于单纯胶原堆积。",
    ),
    ("pathology.repair", "wound", "创伤愈合", "创伤愈合包括相互重叠的炎症、增殖修复和重塑阶段。"),
    ("pathology.repair", "fibrosis", "纤维化", "反复损伤及持续修复可导致细胞外基质过度沉积，改变组织结构并影响功能。"),
    ("pathology.repair", "factors", "影响修复的因素", "感染、灌注不足、异物及营养等局部和全身条件会影响愈合。"),
    ("pathology.circulatory", "congestion", "充血与淤血", "充血主要与动脉流入增加有关，淤血主要与静脉回流受阻有关。"),
    (
        "pathology.circulatory",
        "edema",
        "水肿",
        "静水压升高、胶体渗透压降低、通透性增加或淋巴回流障碍均可导致组织液积聚。",
    ),
    ("pathology.circulatory", "thrombosis", "血栓形成", "血栓形成与内皮损伤、血流异常及高凝状态有关。"),
    ("pathology.circulatory", "embolism", "栓塞", "栓塞是异常物质随血流迁移并阻塞远处血管；栓子不只来自血栓。"),
    (
        "pathology.circulatory",
        "infarction",
        "梗死",
        "梗死是局部血供障碍引起的缺血性坏死；形态受血管分布、侧支循环和组织特点影响。",
    ),
    (
        "pathology.circulatory",
        "shock",
        "休克",
        "休克是急性循环衰竭所致组织低灌注和氧输送不足，可导致细胞及多器官损伤。",
    ),
    ("pathology.neoplasm", "atypia", "肿瘤异型性", "异型性包括细胞和组织结构偏离正常的程度；判断需结合整体结构。"),
    ("pathology.neoplasm", "behavior", "良恶性肿瘤区别", "判断良恶性需综合分化、异型性、生长方式以及浸润和转移。"),
    ("pathology.neoplasm", "spread", "浸润与转移", "浸润是向邻近组织扩展，转移是在不连续部位形成继发灶。"),
    (
        "pathology.neoplasm",
        "carcinogenesis",
        "肿瘤发生机制",
        "肿瘤发生通常涉及多步骤遗传及表观遗传改变，影响增殖、存活和基因组稳定性。",
    ),
    (
        "pathology.neoplasm",
        "grading",
        "肿瘤分级与分期",
        "分级侧重组织学特征，分期侧重病变范围；具体体系随肿瘤类型而异。",
    ),
    ("pathology.neoplasm", "effects", "肿瘤对机体的影响", "肿瘤可产生压迫、阻塞、破坏、异常分泌和其他全身影响。"),
)

SOURCES = (
    (
        "S01",
        "Mechanisms and Morphology of Cellular Injury, Adaptation, and Death",
        "NCBI/PMC",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC7171462/",
        "peer_reviewed",
    ),
    (
        "S02",
        "Histology, Cell Death",
        "NCBI Bookshelf",
        "https://www.ncbi.nlm.nih.gov/books/NBK526045/",
        "academic_reference",
    ),
    (
        "S03",
        "Acute Inflammatory Response",
        "NCBI Bookshelf",
        "https://www.ncbi.nlm.nih.gov/books/NBK556083/",
        "academic_reference",
    ),
    (
        "S04",
        "Chronic Inflammation",
        "NCBI Bookshelf",
        "https://www.ncbi.nlm.nih.gov/books/NBK493173/",
        "academic_reference",
    ),
    (
        "S05",
        "Mechanisms of granulomatous inflammation",
        "PubMed",
        "https://pubmed.ncbi.nlm.nih.gov/2488875/",
        "peer_reviewed",
    ),
    (
        "S06",
        "Physiology, Wound Healing",
        "NCBI Bookshelf",
        "https://www.ncbi.nlm.nih.gov/books/NBK535406/",
        "academic_reference",
    ),
    (
        "S07",
        "Principles of Wound Healing",
        "NCBI Bookshelf",
        "https://www.ncbi.nlm.nih.gov/books/NBK534261/",
        "academic_reference",
    ),
    (
        "S08",
        "Physiology, Edema",
        "NCBI Bookshelf",
        "https://www.ncbi.nlm.nih.gov/books/NBK537065/",
        "academic_reference",
    ),
    ("S09", "Virchow Triad", "NCBI Bookshelf", "https://www.ncbi.nlm.nih.gov/books/NBK539697/", "academic_reference"),
    (
        "S10",
        "What Is Cancer?",
        "National Cancer Institute",
        "https://www.cancer.gov/about-cancer/understanding/what-is-cancer",
        "government",
    ),
    (
        "S11",
        "Tumor Grade",
        "National Cancer Institute",
        "https://www.cancer.gov/about-cancer/diagnosis-staging/diagnosis/tumor-grade",
        "government",
    ),
    (
        "S12",
        "Cancer Staging",
        "National Cancer Institute",
        "https://www.cancer.gov/about-cancer/diagnosis-staging/staging",
        "government",
    ),
    (
        "S13",
        "Shock",
        "Merck Manual Professional Edition",
        "https://www.merckmanuals.com/professional/critical-care-medicine/shock-and-fluid-resuscitation/shock",
        "academic_reference",
    ),
    (
        "S14",
        "Infarction MeSH Descriptor",
        "U.S. National Library of Medicine",
        "https://meshb.nlm.nih.gov/record/ui?ui=D007238",
        "government",
    ),
)

POINT_SOURCES = {
    "pathology.cell-injury.adaptation": ("S01",),
    "pathology.cell-injury.reversible": ("S01", "S02"),
    "pathology.cell-injury.necrosis": ("S01", "S02"),
    "pathology.cell-injury.apoptosis": ("S01", "S02"),
    "pathology.cell-injury.hypoxia": ("S01", "S02"),
    "pathology.cell-injury.oxidative": ("S01",),
    "pathology.inflammation.vascular": ("S03",),
    "pathology.inflammation.leukocytes": ("S03", "S04"),
    "pathology.inflammation.mediators": ("S03", "S04"),
    "pathology.inflammation.acute": ("S03",),
    "pathology.inflammation.chronic": ("S04",),
    "pathology.inflammation.granuloma": ("S04", "S05"),
    "pathology.repair.regeneration": ("S06",),
    "pathology.repair.granulation": ("S06", "S07"),
    "pathology.repair.matrix": ("S06", "S07"),
    "pathology.repair.wound": ("S06", "S07"),
    "pathology.repair.fibrosis": ("S04", "S07"),
    "pathology.repair.factors": ("S06",),
    "pathology.circulatory.congestion": ("S08",),
    "pathology.circulatory.edema": ("S08",),
    "pathology.circulatory.thrombosis": ("S09",),
    "pathology.circulatory.embolism": ("S09",),
    "pathology.circulatory.infarction": ("S09", "S14"),
    "pathology.circulatory.shock": ("S13",),
    "pathology.neoplasm.atypia": ("S10", "S11"),
    "pathology.neoplasm.behavior": ("S10",),
    "pathology.neoplasm.spread": ("S10",),
    "pathology.neoplasm.carcinogenesis": ("S10",),
    "pathology.neoplasm.grading": ("S11", "S12"),
    "pathology.neoplasm.effects": ("S10",),
}

# source, target, relation kind, rationale, limitation, confidence, sources
EDGES = (
    (
        "pathology.cell-injury.adaptation",
        "pathology.cell-injury.reversible",
        "response_continuum",
        "适应能力被超过后可出现细胞损伤。",
        "适应不必然进展为损伤，取决于刺激性质、强度和持续时间。",
        "moderate",
        ("S01",),
    ),
    (
        "pathology.cell-injury.hypoxia",
        "pathology.cell-injury.reversible",
        "mechanistic_basis",
        "短暂或较轻缺氧可经 ATP 下降和离子泵障碍产生可逆性改变。",
        "严重或持续缺氧可越过可逆阶段，且组织耐受性不同。",
        "high",
        ("S01", "S02"),
    ),
    (
        "pathology.cell-injury.oxidative",
        "pathology.cell-injury.reversible",
        "mechanistic_basis",
        "活性氧可损伤膜脂、蛋白和核酸，是细胞损伤的重要机制。",
        "结局取决于活性氧负荷、抗氧化能力和暴露时间。",
        "high",
        ("S01",),
    ),
    (
        "pathology.cell-injury.reversible",
        "pathology.cell-injury.necrosis",
        "response_continuum",
        "持续或严重损伤越过不可逆点后可发生坏死。",
        "可逆性损伤不必然发展为坏死，去除刺激后可恢复。",
        "high",
        ("S01", "S02"),
    ),
    (
        "pathology.inflammation.mediators",
        "pathology.inflammation.vascular",
        "mechanistic_basis",
        "炎症介质调控血管扩张和通透性增加。",
        "不同介质作用重叠，单一表现不能反推唯一介质。",
        "high",
        ("S03",),
    ),
    (
        "pathology.inflammation.mediators",
        "pathology.inflammation.leukocytes",
        "mechanistic_basis",
        "细胞因子和趋化因子参与内皮激活、黏附及趋化。",
        "募集还依赖血流、黏附分子和白细胞状态。",
        "high",
        ("S03", "S04"),
    ),
    (
        "pathology.inflammation.vascular",
        "pathology.inflammation.leukocytes",
        "mechanistic_basis",
        "内皮激活和血流变化为白细胞边集、黏附及跨内皮迁移提供条件。",
        "血管反应本身不足以完成募集。",
        "high",
        ("S04",),
    ),
    (
        "pathology.inflammation.vascular",
        "pathology.inflammation.acute",
        "structural_component",
        "血管扩张、通透性增高和渗出是急性炎症的重要组成。",
        "急性炎症形态还取决于病因、渗出物和优势细胞。",
        "high",
        ("S03",),
    ),
    (
        "pathology.inflammation.leukocytes",
        "pathology.inflammation.acute",
        "structural_component",
        "白细胞尤其早期中性粒细胞浸润是急性炎症形态的重要组成。",
        "不同病因和时间点的优势细胞可能不同。",
        "high",
        ("S03",),
    ),
    (
        "pathology.inflammation.mediators",
        "pathology.inflammation.chronic",
        "mechanistic_basis",
        "持续的细胞因子和其他介质信号可维持慢性炎症。",
        "慢性炎症并非必须由急性炎症演变而来。",
        "high",
        ("S04",),
    ),
    (
        "pathology.inflammation.leukocytes",
        "pathology.inflammation.chronic",
        "structural_component",
        "巨噬细胞、淋巴细胞和浆细胞浸润是慢性炎症的核心形态基础。",
        "需要结合持续刺激、组织损伤和修复共同判断。",
        "high",
        ("S04",),
    ),
    (
        "pathology.inflammation.chronic",
        "pathology.inflammation.granuloma",
        "specialized_pattern",
        "肉芽肿是持续刺激下以活化巨噬细胞聚集为特征的特殊慢性炎症模式。",
        "并非所有慢性炎症都形成肉芽肿。",
        "high",
        ("S04", "S05"),
    ),
    (
        "pathology.cell-injury.necrosis",
        "pathology.inflammation.acute",
        "mechanistic_basis",
        "坏死细胞释放的损伤相关信号可诱导急性炎症。",
        "急性炎症也可由感染、免疫反应等其他刺激引起。",
        "high",
        ("S03",),
    ),
    (
        "pathology.inflammation.acute",
        "pathology.repair.granulation",
        "repair_phase_basis",
        "损伤后的炎症期为增殖期、血管新生及肉芽组织形成提供细胞和信号环境。",
        "炎症与修复阶段相互重叠，并非严格串行。",
        "moderate",
        ("S06",),
    ),
    (
        "pathology.repair.granulation",
        "pathology.repair.matrix",
        "structural_component",
        "肉芽组织含成纤维细胞和临时细胞外基质，随后进入基质重塑。",
        "重塑也受组织类型、损伤范围和机械环境影响。",
        "high",
        ("S06", "S07"),
    ),
    (
        "pathology.repair.regeneration",
        "pathology.repair.wound",
        "structural_component",
        "再上皮化及存活细胞增殖是创伤愈合的重要组成。",
        "再生能力受细胞类型和基质支架完整性限制。",
        "high",
        ("S06",),
    ),
    (
        "pathology.repair.granulation",
        "pathology.repair.wound",
        "structural_component",
        "肉芽组织是创伤愈合增殖期的重要结构。",
        "不同创口类型所需肉芽组织的量不同。",
        "high",
        ("S06", "S07"),
    ),
    (
        "pathology.repair.matrix",
        "pathology.repair.wound",
        "structural_component",
        "基质合成、降解和重组参与瘢痕成熟及强度形成。",
        "重塑可持续较长时间，外观闭合不等于完成。",
        "high",
        ("S06", "S07"),
    ),
    (
        "pathology.inflammation.chronic",
        "pathology.repair.fibrosis",
        "mechanistic_basis",
        "持续炎症和修复信号可激活成纤维细胞并促进基质沉积。",
        "纤维化程度受病因、器官和修复调控影响。",
        "high",
        ("S04", "S07"),
    ),
    (
        "pathology.repair.matrix",
        "pathology.repair.fibrosis",
        "mechanistic_basis",
        "细胞外基质合成与降解失衡可造成过度沉积和纤维化。",
        "正常重塑不等于病理性纤维化。",
        "high",
        ("S06", "S07"),
    ),
    (
        "pathology.repair.wound",
        "pathology.repair.factors",
        "assessment_framework",
        "先掌握正常愈合阶段，才能分析感染、氧合、灌注和营养等影响因素。",
        "该边是评估框架，不表示愈合导致这些因素。",
        "high",
        ("S06",),
    ),
    (
        "pathology.circulatory.congestion",
        "pathology.circulatory.edema",
        "mechanistic_basis",
        "静脉回流受阻可升高毛细血管静水压并促进液体滤出。",
        "该边仅指静脉淤血造成的静水压升高，不把主动性充血视为同一水肿机制；低蛋白、通透性增加和淋巴障碍也是其他病因。",
        "high",
        ("S08",),
    ),
    (
        "pathology.inflammation.vascular",
        "pathology.circulatory.edema",
        "mechanistic_basis",
        "炎症性血管通透性增加可导致富蛋白液体外渗和水肿。",
        "并非所有水肿均由炎症引起。",
        "high",
        ("S03", "S08"),
    ),
    (
        "pathology.circulatory.thrombosis",
        "pathology.circulatory.embolism",
        "common_source",
        "血栓可脱落并随血流迁移形成血栓栓塞。",
        "脂肪、气体等也可形成栓子，并非所有栓塞都来自血栓。",
        "high",
        ("S09",),
    ),
    (
        "pathology.circulatory.thrombosis",
        "pathology.circulatory.infarction",
        "occlusive_mechanism",
        "原位血栓闭塞可造成组织缺血并形成梗死。",
        "梗死还受侧支循环、组织耐受性和血管性质影响。",
        "high",
        ("S09", "S14"),
    ),
    (
        "pathology.circulatory.embolism",
        "pathology.circulatory.infarction",
        "occlusive_mechanism",
        "栓塞性血管闭塞可造成组织缺血并形成梗死。",
        "并非所有栓塞均导致梗死，取决于闭塞部位和代偿。",
        "high",
        ("S09", "S14"),
    ),
    (
        "pathology.cell-injury.necrosis",
        "pathology.circulatory.infarction",
        "outcome_definition",
        "梗死是局部血供中断造成的缺血性组织坏死。",
        "脑梗死等器官的坏死形态可不同；该边描述结局定义而非坏死导致缺血。",
        "high",
        ("S09", "S14"),
    ),
    (
        "pathology.neoplasm.carcinogenesis",
        "pathology.neoplasm.atypia",
        "mechanistic_basis",
        "驱动性遗传和表观遗传改变可形成异常增殖及异常表型。",
        "异型性程度在肿瘤间不同，机制改变不能单独预测形态。",
        "moderate",
        ("S10",),
    ),
    (
        "pathology.neoplasm.atypia",
        "pathology.neoplasm.behavior",
        "classification_basis",
        "细胞和组织异型性是良恶性形态评估的重要依据。",
        "异型性不能单独决定良恶性，需结合生长方式、浸润和转移。",
        "high",
        ("S10", "S11"),
    ),
    (
        "pathology.neoplasm.behavior",
        "pathology.neoplasm.spread",
        "classification_basis",
        "理解良恶性行为有助于识别浸润和转移作为恶性行为的核心特征。",
        "该边是分类学习顺序，不表示良性肿瘤必然演变为恶性或发生转移。",
        "high",
        ("S10",),
    ),
    (
        "pathology.neoplasm.atypia",
        "pathology.neoplasm.grading",
        "grading_basis",
        "组织学分级使用分化和细胞异常程度等形态依据。",
        "分级体系随肿瘤类型而异，不能替代分期。",
        "high",
        ("S11",),
    ),
    (
        "pathology.neoplasm.spread",
        "pathology.neoplasm.grading",
        "staging_basis",
        "临床病理分期关注原发范围、区域淋巴结及远处播散。",
        "播散信息属于分期基础，不应被解释为组织学分级依据。",
        "high",
        ("S12",),
    ),
    (
        "pathology.neoplasm.behavior",
        "pathology.neoplasm.effects",
        "classification_basis",
        "良恶性生物学行为影响局部压迫、破坏、复发风险和全身效应的分析。",
        "良性肿瘤也可因位置或分泌产生严重影响。",
        "high",
        ("S10",),
    ),
    (
        "pathology.neoplasm.spread",
        "pathology.neoplasm.effects",
        "classification_basis",
        "浸润和转移可造成局部组织破坏及远隔器官功能损害。",
        "肿瘤对机体的影响并不以发生转移为必要条件。",
        "high",
        ("S10",),
    ),
)


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _create_tables(bind) -> None:
    existing = _tables(bind)
    if "knowledge_catalogs" not in existing:
        op.create_table(
            "knowledge_catalogs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("version", sa.String(80), nullable=False),
            sa.Column("label", sa.String(200), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("reference_note", sa.String(500), nullable=False),
            sa.Column("evidence_status", sa.String(30), nullable=False),
            sa.Column("medical_review_status", sa.String(30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("version", name="uq_knowledge_catalogs_version"),
            sa.CheckConstraint("status IN ('active', 'archived')", name="ck_knowledge_catalog_status"),
            sa.CheckConstraint(
                "evidence_status IN ('source_supported', 'insufficient')", name="ck_knowledge_catalog_evidence_status"
            ),
            sa.CheckConstraint(
                "medical_review_status IN ('pending_expert_review', 'expert_reviewed', 'rejected')",
                name="ck_knowledge_catalog_medical_review_status",
            ),
        )
        op.create_index("ix_knowledge_catalogs_version", "knowledge_catalogs", ["version"])
        op.create_index("ix_knowledge_catalogs_status", "knowledge_catalogs", ["status"])
        op.create_index(
            "uq_knowledge_catalog_single_active",
            "knowledge_catalogs",
            ["status"],
            unique=True,
            sqlite_where=sa.text("status = 'active'"),
            postgresql_where=sa.text("status = 'active'"),
        )
    if "knowledge_modules" not in existing:
        op.create_table(
            "knowledge_modules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "catalog_id", sa.Integer(), sa.ForeignKey("knowledge_catalogs.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("code", sa.String(120), nullable=False),
            sa.Column("label", sa.String(120), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.UniqueConstraint("catalog_id", "code", name="uq_knowledge_module_catalog_code"),
            sa.UniqueConstraint("catalog_id", "position", name="uq_knowledge_module_catalog_position"),
        )
        op.create_index("ix_knowledge_modules_catalog_id", "knowledge_modules", ["catalog_id"])
        op.create_index("ix_knowledge_modules_code", "knowledge_modules", ["code"])
    if "knowledge_points" not in existing:
        op.create_table(
            "knowledge_points",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "catalog_id", sa.Integer(), sa.ForeignKey("knowledge_catalogs.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "module_id", sa.Integer(), sa.ForeignKey("knowledge_modules.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("code", sa.String(120), nullable=False),
            sa.Column("title", sa.String(160), nullable=False),
            sa.Column("objective", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("case_slug", sa.String(160), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("evidence_status", sa.String(30), nullable=False),
            sa.Column("medical_review_status", sa.String(30), nullable=False),
            sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("catalog_id", "code", name="uq_knowledge_point_catalog_code"),
            sa.UniqueConstraint("module_id", "position", name="uq_knowledge_point_module_position"),
            sa.CheckConstraint(
                "evidence_status IN ('source_supported', 'insufficient')", name="ck_knowledge_point_evidence_status"
            ),
            sa.CheckConstraint(
                "medical_review_status IN ('pending_expert_review', 'expert_reviewed', 'rejected')",
                name="ck_knowledge_point_medical_review_status",
            ),
        )
        op.create_index("ix_knowledge_points_catalog_id", "knowledge_points", ["catalog_id"])
        op.create_index("ix_knowledge_points_module_id", "knowledge_points", ["module_id"])
        op.create_index("ix_knowledge_points_code", "knowledge_points", ["code"])
    if "knowledge_study_materials" not in existing:
        op.create_table(
            "knowledge_study_materials",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "catalog_id", sa.Integer(), sa.ForeignKey("knowledge_catalogs.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "point_id", sa.Integer(), sa.ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("version", sa.String(80), nullable=False),
            sa.Column("scenario", sa.Text(), nullable=False),
            sa.Column("background", sa.JSON(), nullable=False),
            sa.Column("example", sa.JSON(), nullable=False),
            sa.Column("remediation", sa.JSON(), nullable=False),
            sa.Column("reference_note", sa.String(500), nullable=False),
            sa.Column("evidence_status", sa.String(30), nullable=False),
            sa.Column("medical_review_status", sa.String(30), nullable=False),
            sa.UniqueConstraint("catalog_id", "point_id", name="uq_knowledge_material_catalog_point"),
            sa.UniqueConstraint("point_id", name="uq_knowledge_study_materials_point_id"),
            sa.CheckConstraint(
                "evidence_status IN ('source_supported', 'insufficient')", name="ck_knowledge_material_evidence_status"
            ),
            sa.CheckConstraint(
                "medical_review_status IN ('pending_expert_review', 'expert_reviewed', 'rejected')",
                name="ck_knowledge_material_medical_review_status",
            ),
        )
        op.create_index("ix_knowledge_study_materials_catalog_id", "knowledge_study_materials", ["catalog_id"])
    if "knowledge_dependencies" not in existing:
        op.create_table(
            "knowledge_dependencies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "catalog_id", sa.Integer(), sa.ForeignKey("knowledge_catalogs.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "prerequisite_point_id",
                sa.Integer(),
                sa.ForeignKey("knowledge_points.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "dependent_point_id",
                sa.Integer(),
                sa.ForeignKey("knowledge_points.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("relation_kind", sa.String(40), nullable=False),
            sa.Column("rationale", sa.Text(), nullable=False),
            sa.Column("limitation", sa.Text(), nullable=False),
            sa.Column("confidence", sa.String(20), nullable=False),
            sa.Column("evidence_status", sa.String(30), nullable=False),
            sa.Column("medical_review_status", sa.String(30), nullable=False),
            sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.UniqueConstraint(
                "catalog_id", "prerequisite_point_id", "dependent_point_id", name="uq_knowledge_dependency_edge"
            ),
            sa.CheckConstraint("prerequisite_point_id <> dependent_point_id", name="ck_knowledge_dependency_no_self"),
            sa.CheckConstraint(
                "relation_kind IN ('response_continuum', 'mechanistic_basis', 'structural_component', "
                "'specialized_pattern', 'repair_phase_basis', 'assessment_framework', 'common_source', "
                "'occlusive_mechanism', 'outcome_definition', 'classification_basis', 'grading_basis', "
                "'staging_basis')",
                name="ck_knowledge_dependency_relation_kind",
            ),
            sa.CheckConstraint("confidence IN ('high', 'moderate')", name="ck_knowledge_dependency_confidence"),
            sa.CheckConstraint(
                "evidence_status IN ('source_supported', 'insufficient')",
                name="ck_knowledge_dependency_evidence_status",
            ),
            sa.CheckConstraint(
                "medical_review_status IN ('pending_expert_review', 'expert_reviewed', 'rejected')",
                name="ck_knowledge_dependency_medical_review_status",
            ),
        )
        op.create_index("ix_knowledge_dependencies_catalog_id", "knowledge_dependencies", ["catalog_id"])
        op.create_index(
            "ix_knowledge_dependencies_prerequisite_point_id", "knowledge_dependencies", ["prerequisite_point_id"]
        )
        op.create_index(
            "ix_knowledge_dependencies_dependent_point_id", "knowledge_dependencies", ["dependent_point_id"]
        )
    if "knowledge_sources" not in existing:
        op.create_table(
            "knowledge_sources",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_key", sa.String(30), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("publisher", sa.String(160), nullable=False),
            sa.Column("url", sa.String(1000), nullable=False),
            sa.Column("source_type", sa.String(40), nullable=False),
            sa.Column("accessed_on", sa.String(10), nullable=False),
            sa.UniqueConstraint("source_key", name="uq_knowledge_sources_source_key"),
            sa.CheckConstraint(
                "source_type IN ('government', 'peer_reviewed', 'academic_reference')", name="ck_knowledge_source_type"
            ),
        )
        op.create_index("ix_knowledge_sources_source_key", "knowledge_sources", ["source_key"])
    if "knowledge_point_sources" not in existing:
        op.create_table(
            "knowledge_point_sources",
            sa.Column(
                "point_id", sa.Integer(), sa.ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True
            ),
            sa.Column(
                "source_id", sa.Integer(), sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), primary_key=True
            ),
            sa.UniqueConstraint("point_id", "source_id", name="uq_knowledge_point_source"),
        )
    if "knowledge_dependency_sources" not in existing:
        op.create_table(
            "knowledge_dependency_sources",
            sa.Column(
                "dependency_id",
                sa.Integer(),
                sa.ForeignKey("knowledge_dependencies.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "source_id", sa.Integer(), sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), primary_key=True
            ),
            sa.UniqueConstraint("dependency_id", "source_id", name="uq_knowledge_dependency_source"),
        )


def seed_baseline(bind, *, include_learning_objectives: bool = False) -> None:
    include_learning_objectives = include_learning_objectives or "learning_objectives" in {
        column["name"] for column in sa.inspect(bind).get_columns("knowledge_study_materials")
    }
    existing = bind.scalar(sa.text("SELECT COUNT(*) FROM knowledge_catalogs"))
    if existing:
        if (
            existing == 1
            and bind.scalar(
                sa.text("SELECT COUNT(*) FROM knowledge_catalogs WHERE version = :version"),
                {"version": CATALOG_VERSION},
            )
            == 1
        ):
            return
        raise RuntimeError("T38 refuses to merge an unknown knowledge catalog")
    bind.execute(
        sa.text(
            "INSERT INTO knowledge_catalogs "
            "(version, label, status, reference_note, evidence_status, medical_review_status) "
            "VALUES (:version, :label, 'active', :reference, :evidence, :review)"
        ),
        {
            "version": CATALOG_VERSION,
            "label": "病理学总论可信知识图谱",
            "reference": REFERENCE_NOTE,
            "evidence": EVIDENCE_STATUS,
            "review": REVIEW_STATUS,
        },
    )
    catalog_id = bind.scalar(
        sa.text("SELECT id FROM knowledge_catalogs WHERE version = :version"), {"version": CATALOG_VERSION}
    )
    for position, (code, label, description) in enumerate(MODULES, 1):
        bind.execute(
            sa.text(
                "INSERT INTO knowledge_modules (catalog_id, code, label, description, position) "
                "VALUES (:catalog, :code, :label, :description, :position)"
            ),
            {"catalog": catalog_id, "code": code, "label": label, "description": description, "position": position},
        )
    module_ids = dict(
        bind.execute(
            sa.text("SELECT code, id FROM knowledge_modules WHERE catalog_id = :catalog"), {"catalog": catalog_id}
        ).all()
    )
    module_positions = {code: 0 for code, _, _ in MODULES}
    for module_code, suffix, title, description in POINTS:
        module_positions[module_code] += 1
        code = f"{module_code}.{suffix}"
        bind.execute(
            sa.text(
                "INSERT INTO knowledge_points "
                "(catalog_id, module_id, code, title, objective, description, case_slug, position, "
                "evidence_status, medical_review_status) VALUES "
                "(:catalog, :module, :code, :title, :objective, :description, :case_slug, :position, "
                ":evidence, :review)"
            ),
            {
                "catalog": catalog_id,
                "module": module_ids[module_code],
                "code": code,
                "title": title,
                "objective": f"解释{title}的机制，并用形态或情境证据支持判断。",
                "description": description,
                "case_slug": f"{module_code}-showcase",
                "position": module_positions[module_code],
                "evidence": EVIDENCE_STATUS,
                "review": REVIEW_STATUS,
            },
        )
    point_rows = (
        bind.execute(
            sa.text("SELECT code, id, title, description FROM knowledge_points WHERE catalog_id = :catalog"),
            {"catalog": catalog_id},
        )
        .mappings()
        .all()
    )
    point_ids = {row["code"]: row["id"] for row in point_rows}
    for row in point_rows:
        background = [
            {"title": "观察与解释", "text": f"围绕{row['title']}，先区分已经观察到的形态或情境线索与机制推断。"},
            {"title": "证据边界", "text": "说明支持当前解释的证据、仍缺少的证据，以及该机制不适用的条件。"},
        ]
        remediation = [
            {"title": "机制回顾", "text": row["description"]},
            {"title": "再次解释", "text": "用机制、支持证据和限制重新组织解释；教学内容不能替代临床诊疗。"},
        ]
        material_values = {
            "catalog": catalog_id,
            "point": row["id"],
            "version": "pathology-study-v2",
            "scenario": f"围绕{row['title']}建立从观察、机制到证据边界的解释。",
            "background": json.dumps(background, ensure_ascii=False),
            "example": json.dumps({"title": "机制要点", "text": row["description"]}, ensure_ascii=False),
            "remediation": json.dumps(remediation, ensure_ascii=False),
            "reference": REFERENCE_NOTE,
            "evidence": EVIDENCE_STATUS,
            "review": REVIEW_STATUS,
        }
        if include_learning_objectives:
            material_values["learning_objectives"] = json.dumps(
                [
                    f"解释{row['title']}的机制，并用形态或情境证据支持判断。",
                    f"结合典型形态或病理情境，区分{row['title']}与相邻概念并说明判断依据。",
                ],
                ensure_ascii=False,
            )
            bind.execute(
                sa.text(
                    "INSERT INTO knowledge_study_materials "
                    "(catalog_id, point_id, version, learning_objectives, scenario, background, example, remediation, "
                    "reference_note, evidence_status, medical_review_status) VALUES "
                    "(:catalog, :point, :version, :learning_objectives, :scenario, :background, :example, "
                    ":remediation, :reference, :evidence, :review)"
                ),
                material_values,
            )
        else:
            bind.execute(
                sa.text(
                    "INSERT INTO knowledge_study_materials "
                    "(catalog_id, point_id, version, scenario, background, example, remediation, reference_note, "
                    "evidence_status, medical_review_status) VALUES "
                    "(:catalog, :point, :version, :scenario, :background, :example, :remediation, :reference, "
                    ":evidence, :review)"
                ),
                material_values,
            )
    for key, title, publisher, url, source_type in SOURCES:
        bind.execute(
            sa.text(
                "INSERT INTO knowledge_sources (source_key, title, publisher, url, source_type, accessed_on) "
                "VALUES (:key, :title, :publisher, :url, :source_type, '2026-09-16')"
            ),
            {"key": key, "title": title, "publisher": publisher, "url": url, "source_type": source_type},
        )
    source_ids = dict(bind.execute(sa.text("SELECT source_key, id FROM knowledge_sources")).all())
    for code, keys in POINT_SOURCES.items():
        for key in keys:
            bind.execute(
                sa.text("INSERT INTO knowledge_point_sources (point_id, source_id) VALUES (:point, :source)"),
                {"point": point_ids[code], "source": source_ids[key]},
            )
    for position, (source, target, kind, rationale, limitation, confidence, keys) in enumerate(EDGES, 1):
        bind.execute(
            sa.text(
                "INSERT INTO knowledge_dependencies "
                "(catalog_id, prerequisite_point_id, dependent_point_id, relation_kind, rationale, limitation, "
                "confidence, evidence_status, medical_review_status, position) VALUES "
                "(:catalog, :source, :target, :kind, :rationale, :limitation, :confidence, :evidence, :review, "
                ":position)"
            ),
            {
                "catalog": catalog_id,
                "source": point_ids[source],
                "target": point_ids[target],
                "kind": kind,
                "rationale": rationale,
                "limitation": limitation,
                "confidence": confidence,
                "evidence": EVIDENCE_STATUS,
                "review": REVIEW_STATUS,
                "position": position,
            },
        )
        dependency_id = bind.scalar(
            sa.text(
                "SELECT id FROM knowledge_dependencies WHERE catalog_id = :catalog "
                "AND prerequisite_point_id = :source AND dependent_point_id = :target"
            ),
            {"catalog": catalog_id, "source": point_ids[source], "target": point_ids[target]},
        )
        for key in keys:
            bind.execute(
                sa.text(
                    "INSERT INTO knowledge_dependency_sources (dependency_id, source_id) VALUES (:dependency, :source)"
                ),
                {"dependency": dependency_id, "source": source_ids[key]},
            )


def validate_baseline(bind) -> None:
    expected = {
        "knowledge_modules": 5,
        "knowledge_points": 30,
        "knowledge_study_materials": 30,
        "knowledge_dependencies": 34,
        "knowledge_sources": 14,
    }
    for table, count in expected.items():
        if bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table}")) != count:
            raise RuntimeError(f"T38 knowledge graph integrity failed for {table}")
    if bind.scalar(sa.text("SELECT COUNT(*) FROM knowledge_point_sources")) < 30:
        raise RuntimeError("T38 every point must have evidence")
    if bind.scalar(
        sa.text(
            "SELECT COUNT(*) FROM knowledge_dependencies d WHERE NOT EXISTS "
            "(SELECT 1 FROM knowledge_dependency_sources ds WHERE ds.dependency_id = d.id)"
        )
    ):
        raise RuntimeError("T38 every dependency must have evidence")


def upgrade() -> None:
    bind = op.get_bind()
    _create_tables(bind)
    seed_baseline(bind)
    validate_baseline(bind)


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)
    if "knowledge_catalogs" in tables:
        if bind.scalar(
            sa.text(
                "SELECT COUNT(*) FROM knowledge_catalogs WHERE version <> :version OR medical_review_status <> :review"
            ),
            {"version": CATALOG_VERSION, "review": REVIEW_STATUS},
        ):
            raise RuntimeError("T38 knowledge catalog changed; use a forward fix or verified backup")
        if "knowledge_points" in tables and bind.scalar(
            sa.text(
                "SELECT COUNT(*) FROM knowledge_points WHERE reviewer_id IS NOT NULL "
                "OR reviewed_at IS NOT NULL OR medical_review_status <> :review"
            ),
            {"review": REVIEW_STATUS},
        ):
            raise RuntimeError("T38 reviewed knowledge points exist; use a forward fix or verified backup")
        if "knowledge_dependencies" in tables and bind.scalar(
            sa.text(
                "SELECT COUNT(*) FROM knowledge_dependencies WHERE reviewer_id IS NOT NULL "
                "OR reviewed_at IS NOT NULL OR medical_review_status <> :review"
            ),
            {"review": REVIEW_STATUS},
        ):
            raise RuntimeError("T38 reviewed knowledge dependencies exist; use a forward fix or verified backup")
    for table in (
        "knowledge_dependency_sources",
        "knowledge_point_sources",
        "knowledge_sources",
        "knowledge_dependencies",
        "knowledge_study_materials",
        "knowledge_points",
        "knowledge_modules",
        "knowledge_catalogs",
    ):
        if table in _tables(bind):
            op.drop_table(table)
