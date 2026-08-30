from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClassMember, ClassRoom, MedicalReview, Problem, User

SAFETY_NOTICE = "合成教学病例，不构成诊疗建议。"


def showcase_case_payload() -> dict:
    facts = [
        (
            "history_onset",
            "history",
            "起病与病程",
            "3天前受凉后出现发热，最高39.1℃，伴寒战。",
            ["什么时候", "多久", "起病", "发热", "体温", "寒战"],
        ),
        ("history_sputum", "history", "咳嗽咳痰", "咳嗽明显，咳黄色黏痰，不伴咯血。", ["咳嗽", "痰", "咯血", "黄色"]),
        (
            "history_chest_pain",
            "history",
            "胸痛与气促",
            "右侧吸气时胸痛，活动后气促，休息后可缓解。",
            ["胸痛", "气促", "呼吸", "活动"],
        ),
        (
            "history_risk",
            "history",
            "危险因素",
            "近期无住院和抗菌药物使用，无明确误吸；有吸烟史。",
            ["住院", "抗菌", "吸烟", "误吸", "风险"],
        ),
        (
            "history_allergy",
            "history",
            "既往史与过敏",
            "既往无慢性肺病，否认已知药物过敏。",
            ["既往", "过敏", "药物", "慢性病"],
        ),
        (
            "exam_vitals",
            "history",
            "生命体征",
            "体温39.1℃、心率104次/分、呼吸24次/分、血压126/76mmHg，室内空气SpO₂ 93%。",
            ["生命体征", "血压", "心率", "呼吸频率", "血氧", "spo2"],
        ),
        (
            "exam_lung",
            "history",
            "肺部查体",
            "右下肺叩诊浊音，可闻及湿啰音和支气管呼吸音。",
            ["查体", "肺", "听诊", "湿啰音", "叩诊"],
        ),
        ("test_cbc", "test", "血常规与炎症指标", "血常规中性粒细胞增高，炎症指标升高。", ["血常规", "炎症", "白细胞"]),
        ("test_xray", "test", "胸部影像", "胸片/CT提示右下肺新发浸润影。", ["胸片", "ct", "影像", "x线"]),
    ]
    definition = {
        "schema_version": 1,
        "opening": {
            "setting": "呼吸内科门诊",
            "patient_intro": "48岁男性，因发热、咳嗽3天就诊。",
            "chief_complaint": "发热、咳嗽3天",
        },
        "stage_instructions": {
            "history": "通过提问获取现病史、伴随症状、危险因素和既往史。",
            "problem_representation": "用一句话概括患者、时间进程、关键阳性和阴性信息。",
            "differential": "列出至少两个诊断，并说明支持与反对证据。",
            "tests": "选择需要的检查并说明目的和优先级。",
            "management": "给出教学场景下的初步处置、监测和安全考虑。",
        },
        "facts": [
            {
                "id": fid,
                "category": category,
                "label": label,
                "value": value,
                "triggers": triggers,
                "reveal_stage": "history" if category != "test" else "tests",
            }
            for fid, category, label, value, triggers in facts
        ],
        "reference_reasoning": {
            "problem_representation": (
                "48岁男性急性发热、咳黄色痰和右侧胸膜性胸痛，伴低氧及右下肺局灶体征，首先考虑社区获得性肺炎。"
            ),
            "differentials": [
                {
                    "diagnosis": "社区获得性肺炎",
                    "supporting_fact_ids": ["history_onset", "history_sputum", "exam_lung", "test_xray"],
                    "opposing_fact_ids": [],
                    "priority": 1,
                },
                {
                    "diagnosis": "病毒性肺炎",
                    "supporting_fact_ids": ["history_onset"],
                    "opposing_fact_ids": ["history_sputum"],
                    "priority": 2,
                },
                {
                    "diagnosis": "肺结核",
                    "supporting_fact_ids": ["history_sputum"],
                    "opposing_fact_ids": ["history_onset"],
                    "priority": 3,
                },
                {
                    "diagnosis": "肺栓塞",
                    "supporting_fact_ids": ["history_chest_pain"],
                    "opposing_fact_ids": ["history_sputum"],
                    "priority": 4,
                },
            ],
            "tests": [
                {
                    "name": "血常规和炎症指标",
                    "purpose": "评估感染和炎症程度",
                    "priority": "necessary",
                    "result_fact_id": "test_cbc",
                },
                {
                    "name": "胸部影像",
                    "purpose": "确认肺部浸润并评估范围",
                    "priority": "necessary",
                    "result_fact_id": "test_xray",
                },
            ],
            "management": [
                {
                    "action": "评估严重程度和氧合",
                    "rationale": "决定治疗场所并识别恶化风险",
                    "priority": 1,
                    "safety_critical": True,
                },
                {
                    "action": "评估过敏史并制定经验性抗感染原则",
                    "rationale": "保障教学场景下的用药安全",
                    "priority": 2,
                    "safety_critical": True,
                },
                {
                    "action": "支持治疗与复评",
                    "rationale": "监测症状和氧合变化",
                    "priority": 3,
                    "safety_critical": False,
                },
            ],
        },
    }
    rubric_specs = [
        (
            "information_gathering",
            "信息采集",
            20,
            ["history"],
            [
                ("onset", "询问起病与病程", ["起病", "多久", "发热", "体温"], False),
                ("sputum", "询问咳痰", ["咳嗽", "痰"], False),
                ("allergy", "询问药物过敏", ["过敏", "药物"], True),
            ],
        ),
        (
            "problem_representation",
            "问题表征",
            15,
            ["problem_representation"],
            [
                ("patient", "概括患者特征", ["48", "男性"], False),
                ("course", "概括时间进程", ["3天", "急性"], False),
                ("key", "概括核心问题", ["发热", "咳嗽", "肺炎"], False),
            ],
        ),
        (
            "differential_diagnosis",
            "鉴别诊断",
            20,
            ["differential"],
            [
                ("cap", "提出社区获得性肺炎", ["社区获得性肺炎", "肺炎"], False),
                ("viral", "考虑病毒性肺炎", ["病毒", "流感", "新冠"], False),
                ("other", "考虑其他鉴别", ["结核", "肺栓塞"], False),
            ],
        ),
        (
            "evidence_reasoning",
            "证据推理",
            15,
            ["differential"],
            [
                ("support", "说明支持证据", ["发热", "黄痰", "啰音"], False),
                ("oppose", "说明反对证据", ["反对", "无", "不支持"], False),
                ("hypoxia", "结合氧合证据", ["血氧", "spo2", "93"], False),
            ],
        ),
        (
            "test_selection",
            "检查合理性",
            15,
            ["tests"],
            [
                ("image", "选择胸部影像", ["胸片", "ct", "影像"], False),
                ("cbc", "选择血常规", ["血常规", "白细胞"], False),
                ("purpose", "说明检查目的", ["评估", "确认", "判断"], False),
            ],
        ),
        (
            "management_safety",
            "处置与安全意识",
            15,
            ["management"],
            [
                ("oxygen", "评估氧合和严重程度", ["氧合", "血氧", "严重程度"], True),
                ("allergy", "评估药物过敏", ["过敏"], True),
                ("review", "支持治疗和复评", ["支持", "复评", "监测"], False),
            ],
        ),
    ]
    rubric = {
        "dimensions": [
            {
                "id": did,
                "label": label,
                "weight": weight,
                "stage_ids": stages,
                "criteria": [
                    {
                        "id": cid,
                        "label": clabel,
                        "keywords": keywords,
                        "feedback": f"请补充{clabel}。",
                        "critical": critical,
                    }
                    for cid, clabel, keywords, critical in criteria
                ],
            }
            for did, label, weight, stages, criteria in rubric_specs
        ]
    }
    definition["schema_version"] = 2
    definition["practice_blueprints"] = [
        {
            "id": "cap-evidence-blueprint",
            "dimension_id": "evidence_reasoning",
            "stage_id": "differential",
            "learner_level": "undergraduate",
            "public_instruction": "归纳支持首要诊断的两条原文证据，并说明如何排除一个危险鉴别诊断。",
            "allowed_variants": ["使用不同但等价的证据表述"],
            "fixed_facts": ["test_xray", "exam_lung"],
            "fallback_prompt": "仅基于公开教学情境回答，不提供个体处方或剂量。",
            "answer_schema": "evidence_grid",
            "criteria": [
                {
                    "id": "support",
                    "weight": 50,
                    "keywords": ["浸润", "湿啰音", "炎症"],
                    "feedback": "补充支持诊断的原文证据。",
                    "critical": True,
                },
                {
                    "id": "safety",
                    "weight": 50,
                    "keywords": ["危险", "氧合", "排除"],
                    "feedback": "说明危险鉴别和安全边界。",
                    "critical": False,
                },
            ],
        },
        {
            "id": "cap-management-blueprint",
            "dimension_id": "management_safety",
            "stage_id": "management",
            "learner_level": "undergraduate",
            "public_instruction": "列出初步处置、监测和复评要点，避免具体药物剂量。",
            "allowed_variants": [],
            "fixed_facts": ["exam_vitals"],
            "fallback_prompt": "使用教学语言描述监测和升级评估，不给出真实患者处方。",
            "answer_schema": "decision_cards",
            "criteria": [
                {
                    "id": "oxygen",
                    "weight": 60,
                    "keywords": ["氧合", "监测", "复评"],
                    "feedback": "补充氧合和复评计划。",
                    "critical": True,
                },
                {
                    "id": "safety",
                    "weight": 40,
                    "keywords": ["严重程度", "升级", "安全"],
                    "feedback": "补充安全升级边界。",
                    "critical": False,
                },
            ],
        },
    ]
    return {
        "type": "病例分析",
        "title": "社区获得性肺炎：结构化临床推理",
        "description": "面向临床医学本科生的五阶段推理训练。",
        "target": "all",
        "target_label": "全体学生",
        "target_ids": "",
        "status": "published",
        "slug": "cap-undergraduate-showcase",
        "content_type": "guided_case",
        "specialty": "呼吸内科",
        "difficulty": "basic",
        "estimated_minutes": 10,
        "version": 1,
        "case_definition": definition,
        "rubric": rubric,
        "capability_tags": ["differential_diagnosis", "evidence_reasoning", "management_safety"],
    }


def showcase_draft(topic: str = "社区获得性肺炎") -> dict:
    lowered = topic.lower()
    if "胸痛" in lowered:
        return next(
            item for item in showcase_additional_payloads() if item["slug"] == "acute-chest-pain-undergraduate-showcase"
        )
    if "右下腹" in lowered or "阑尾" in lowered:
        return next(
            item
            for item in showcase_additional_payloads()
            if item["slug"] == "right-lower-quadrant-pain-undergraduate-showcase"
        )
    draft = deepcopy(showcase_case_payload())
    if not any(word in topic.lower() for word in ("肺炎", "发热", "咳嗽", "pneumonia")):
        draft["title"] = f"{topic}：结构化临床推理（待教师补全）"
        draft["description"] = "确定性示例骨架，请教师补充为适用的教学病例。"
    return draft


def seed_showcase_case(db: Session) -> Problem:
    from app.api.medical_review import case_digest

    existing = db.scalar(select(Problem).where(Problem.slug == "cap-undergraduate-showcase", Problem.version == 1))
    if existing:
        problem = existing
        if not problem.capability_tags:
            problem.capability_tags = showcase_case_payload()["capability_tags"]
        if problem.case_definition and problem.case_definition.get("schema_version") == 1:
            problem.case_definition = showcase_case_payload()["case_definition"]
    else:
        problem = Problem(**showcase_case_payload())
        db.add(problem)
    db.commit()
    db.refresh(problem)
    teacher = db.scalar(select(User).where(User.external_id == "demo_teacher"))
    if teacher is None:
        teacher = User(external_id="demo_teacher", role="teacher", nickname="示例教师", permissions=[])
        db.add(teacher)
        db.flush()
    reviewer = db.scalar(select(User).where(User.external_id == "demo_reviewer"))
    if reviewer is None:
        reviewer = User(
            external_id="demo_reviewer",
            role="teacher",
            nickname="医学审核专家",
            permissions=["medical_review"],
        )
        db.add(reviewer)
        db.flush()
    student = db.scalar(select(User).where(User.external_id == "demo_student"))
    if student is None:
        student = User(external_id="demo_student", role="student", nickname="示例学生", class_ids=["demo_class_1"])
        db.add(student)
        db.flush()
    classroom = db.scalar(select(ClassRoom).where(ClassRoom.code == "demo_class_1"))
    if classroom is None:
        classroom = ClassRoom(name="临床一班", code="demo_class_1", teacher_id=teacher.id)
        db.add(classroom)
        db.flush()
    if (
        db.scalar(select(ClassMember).where(ClassMember.class_id == classroom.id, ClassMember.student_id == student.id))
        is None
    ):
        db.add(ClassMember(class_id=classroom.id, student_id=student.id))
    problem.author_id = teacher.id
    problem.medical_review_status = "approved"
    digest = case_digest(problem)
    if (
        db.scalar(
            select(MedicalReview).where(
                MedicalReview.problem_id == problem.id,
                MedicalReview.decision == "approved",
                MedicalReview.case_digest == digest,
            )
        )
        is None
    ):
        db.add(
            MedicalReview(
                problem_id=problem.id,
                reviewer_id=reviewer.id,
                decision="approved",
                comment="内置示例病例审核通过",
                problem_version=problem.version,
                case_digest=digest,
            )
        )
    db.commit()
    db.refresh(problem)
    for payload in showcase_additional_payloads():
        item = db.scalar(select(Problem).where(Problem.slug == payload["slug"], Problem.version == 1))
        if item is None:
            item = Problem(**payload, author_id=teacher.id, medical_review_status="approved")
            db.add(item)
            db.flush()
        else:
            item.author_id = teacher.id
            item.medical_review_status = "approved"
        digest = case_digest(item)
        if (
            db.scalar(
                select(MedicalReview).where(
                    MedicalReview.problem_id == item.id,
                    MedicalReview.decision == "approved",
                    MedicalReview.case_digest == digest,
                )
            )
            is None
        ):
            db.add(
                MedicalReview(
                    problem_id=item.id,
                    reviewer_id=reviewer.id,
                    decision="approved",
                    comment="内置示例病例审核通过",
                    problem_version=item.version,
                    case_digest=digest,
                )
            )
    db.commit()
    db.refresh(problem)
    return problem


def showcase_additional_payloads() -> list[dict]:
    base = showcase_case_payload()
    cases = []
    for slug, title, specialty, tags, opening, description in (
        (
            "acute-chest-pain-undergraduate-showcase",
            "急性胸痛：危险分层与证据推理",
            "心血管内科/急诊教学",
            ["differential_diagnosis", "evidence_reasoning", "management_safety"],
            {
                "setting": "急诊留观区",
                "patient_intro": "56岁患者突发胸部不适2小时。",
                "chief_complaint": "突发胸痛2小时",
            },
            "面向本科生的急性胸痛危险分层与安全处置训练。",
        ),
        (
            "right-lower-quadrant-pain-undergraduate-showcase",
            "右下腹痛：问题表征与检查选择",
            "普通外科/急诊教学",
            ["problem_representation", "evidence_reasoning", "test_selection"],
            {
                "setting": "普通外科门诊",
                "patient_intro": "23岁患者腹痛逐渐移向右下腹。",
                "chief_complaint": "右下腹痛1天",
            },
            "面向本科生的右下腹痛鉴别、检查目的与适用性训练。",
        ),
    ):
        item = deepcopy(base)
        item.update(
            {"slug": slug, "title": title, "description": description, "specialty": specialty, "capability_tags": tags}
        )
        item["case_definition"]["opening"] = opening
        if slug == "acute-chest-pain-undergraduate-showcase":
            item["case_definition"]["facts"] = [
                {
                    "id": "chest_onset",
                    "category": "history",
                    "label": "起病",
                    "value": "胸痛突然出现，持续约2小时，活动时加重。",
                    "triggers": ["多久", "起病", "胸痛"],
                    "reveal_stage": "history",
                },
                {
                    "id": "chest_quality",
                    "category": "history",
                    "label": "疼痛性质",
                    "value": "胸骨后压榨样不适，向左肩放射。",
                    "triggers": ["性质", "放射", "压榨"],
                    "reveal_stage": "history",
                },
                {
                    "id": "chest_associated",
                    "category": "history",
                    "label": "伴随表现",
                    "value": "伴出汗和恶心，无咯血。",
                    "triggers": ["出汗", "恶心", "咯血"],
                    "reveal_stage": "history",
                },
                {
                    "id": "chest_risk",
                    "category": "history",
                    "label": "危险因素",
                    "value": "有吸烟和高血压史，近期无外伤。",
                    "triggers": ["吸烟", "高血压", "外伤"],
                    "reveal_stage": "history",
                },
                {
                    "id": "chest_vitals",
                    "category": "exam",
                    "label": "生命体征",
                    "value": "心率102次/分，血压154/92mmHg，血氧96%。",
                    "triggers": ["生命体征", "血压", "血氧"],
                    "reveal_stage": "history",
                },
                {
                    "id": "chest_ecg",
                    "category": "test",
                    "label": "心电图",
                    "value": "心电图提示需要尽快复核的缺血性改变。",
                    "triggers": ["心电图", "心电", "缺血"],
                    "reveal_stage": "tests",
                },
                {
                    "id": "chest_troponin",
                    "category": "test",
                    "label": "实验室检查",
                    "value": "肌钙蛋白结果待结合时间动态复查。",
                    "triggers": ["肌钙蛋白", "化验", "实验室"],
                    "reveal_stage": "tests",
                },
            ]
            item["case_definition"]["reference_reasoning"] = {
                "problem_representation": (
                    "56岁患者突发持续性胸骨后压榨样胸痛，伴自主神经症状并存在心血管危险因素，"
                    "需优先危险分层。"
                ),
                "differentials": [
                    {
                        "diagnosis": "急性冠脉综合征",
                        "supporting_fact_ids": ["chest_quality", "chest_associated", "chest_ecg"],
                        "opposing_fact_ids": [],
                        "priority": 1,
                    },
                    {
                        "diagnosis": "主动脉夹层",
                        "supporting_fact_ids": ["chest_onset"],
                        "opposing_fact_ids": ["chest_quality"],
                        "priority": 2,
                    },
                    {
                        "diagnosis": "肺栓塞",
                        "supporting_fact_ids": ["chest_onset"],
                        "opposing_fact_ids": ["chest_associated"],
                        "priority": 3,
                    },
                    {
                        "diagnosis": "非心源性胸痛",
                        "supporting_fact_ids": [],
                        "opposing_fact_ids": ["chest_quality", "chest_risk"],
                        "priority": 4,
                    },
                ],
                "tests": [
                    {
                        "name": "复核心电图",
                        "purpose": "判断缺血性改变并进行紧急危险分层",
                        "priority": "necessary",
                        "result_fact_id": "chest_ecg",
                    },
                    {
                        "name": "动态心肌损伤标志物",
                        "purpose": "结合起病时间判断动态变化",
                        "priority": "necessary",
                        "result_fact_id": "chest_troponin",
                    },
                ],
                "management": [
                    {
                        "action": "持续监护并复评",
                        "rationale": "及时识别病情恶化和危险心律失常",
                        "priority": 1,
                        "safety_critical": True,
                    },
                    {
                        "action": "启动急诊评估路径",
                        "rationale": "避免对高危胸痛延误评估",
                        "priority": 2,
                        "safety_critical": True,
                    },
                ],
            }
        else:
            item["case_definition"]["facts"] = [
                {
                    "id": "abd_migration",
                    "category": "history",
                    "label": "疼痛迁移",
                    "value": "腹痛先在脐周，数小时后逐渐移向右下腹。",
                    "triggers": ["迁移", "脐周", "多久"],
                    "reveal_stage": "history",
                },
                {
                    "id": "abd_gi",
                    "category": "history",
                    "label": "消化道表现",
                    "value": "伴恶心和食欲下降，无明显腹泻。",
                    "triggers": ["恶心", "食欲", "腹泻"],
                    "reveal_stage": "history",
                },
                {
                    "id": "abd_fever",
                    "category": "history",
                    "label": "发热",
                    "value": "低热37.8℃，无寒战。",
                    "triggers": ["发热", "体温", "寒战"],
                    "reveal_stage": "history",
                },
                {
                    "id": "abd_urinary",
                    "category": "history",
                    "label": "泌尿与妇科",
                    "value": "无尿频尿痛；需结合个体情况补充相关问诊。",
                    "triggers": ["尿频", "尿痛", "妇科"],
                    "reveal_stage": "history",
                },
                {
                    "id": "abd_exam",
                    "category": "exam",
                    "label": "腹部查体",
                    "value": "右下腹压痛，反跳痛需谨慎评估。",
                    "triggers": ["查体", "压痛", "反跳"],
                    "reveal_stage": "history",
                },
                {
                    "id": "abd_blood",
                    "category": "test",
                    "label": "基础检查",
                    "value": "血常规和炎症指标需要结合症状与查体解释。",
                    "triggers": ["血常规", "炎症", "白细胞"],
                    "reveal_stage": "tests",
                },
                {
                    "id": "abd_imaging",
                    "category": "test",
                    "label": "影像检查",
                    "value": "根据年龄、妊娠可能性和资源选择适用影像。",
                    "triggers": ["影像", "超声", "ct"],
                    "reveal_stage": "tests",
                },
            ]
            item["case_definition"]["reference_reasoning"] = {
                "problem_representation": (
                    "23岁患者腹痛由脐周迁移至右下腹，伴恶心、低热和局部压痛，"
                    "需结合适用性选择检查。"
                ),
                "differentials": [
                    {
                        "diagnosis": "急性阑尾炎",
                        "supporting_fact_ids": ["abd_migration", "abd_fever", "abd_exam"],
                        "opposing_fact_ids": [],
                        "priority": 1,
                    },
                    {
                        "diagnosis": "胃肠炎",
                        "supporting_fact_ids": ["abd_gi"],
                        "opposing_fact_ids": ["abd_migration"],
                        "priority": 2,
                    },
                    {
                        "diagnosis": "泌尿系疾病",
                        "supporting_fact_ids": [],
                        "opposing_fact_ids": ["abd_urinary"],
                        "priority": 3,
                    },
                    {
                        "diagnosis": "适用人群的妇科原因",
                        "supporting_fact_ids": ["abd_urinary"],
                        "opposing_fact_ids": [],
                        "priority": 4,
                    },
                ],
                "tests": [
                    {
                        "name": "血常规和炎症指标",
                        "purpose": "结合病程和查体评估炎症证据",
                        "priority": "necessary",
                        "result_fact_id": "abd_blood",
                    },
                    {
                        "name": "适用影像",
                        "purpose": "根据个体适用性确认腹腔内病变范围",
                        "priority": "necessary",
                        "result_fact_id": "abd_imaging",
                    },
                ],
                "management": [
                    {
                        "action": "复核腹部体征和生命体征",
                        "rationale": "识别需要升级评估的腹膜刺激或全身风险",
                        "priority": 1,
                        "safety_critical": True,
                    },
                    {
                        "action": "根据适用性选择检查并请专科评估",
                        "rationale": "兼顾诊断收益和检查适用性",
                        "priority": 2,
                        "safety_critical": False,
                    },
                ],
            }
        item["case_definition"]["practice_blueprints"] = [
            {
                "id": f"{slug}-{dimension}-blueprint",
                "dimension_id": dimension,
                "stage_id": "tests"
                if dimension == "test_selection"
                else "management"
                if dimension == "management_safety"
                else "differential",
                "learner_level": "undergraduate",
                "public_instruction": "结合公开情境列出关键证据、鉴别和安全边界。",
                "allowed_variants": ["等价临床表述"],
                "fixed_facts": [],
                "fallback_prompt": "仅用于合成教学，不提供真实患者处方。",
                "answer_schema": "evidence_grid",
                "criteria": [
                    {
                        "id": "evidence",
                        "weight": 60,
                        "keywords": ["证据", "危险", "目的"],
                        "feedback": "补充可核验证据。",
                        "critical": True,
                    },
                    {
                        "id": "safety",
                        "weight": 40,
                        "keywords": ["安全", "复评", "优先"],
                        "feedback": "补充安全和优先级。",
                        "critical": False,
                    },
                ],
            }
            for dimension in tags
        ]
        cases.append(item)
    return cases
