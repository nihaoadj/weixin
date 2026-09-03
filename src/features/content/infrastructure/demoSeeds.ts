import type { CaseDraftGenerateResult, CaseFact, CaseRubricDimension } from '@/types/case'

const facts: CaseFact[] = [
  {
    id: 'onset',
    category: 'history',
    label: '起病',
    value: '3天前受凉后出现发热，最高39.1℃，伴寒战。',
    triggers: ['多久', '发热', '体温', '起病'],
    revealStage: 'history',
  },
  {
    id: 'sputum',
    category: 'history',
    label: '咳痰',
    value: '咳嗽明显，咳黄色黏痰，不伴咯血。',
    triggers: ['咳嗽', '痰', '咯血'],
    revealStage: 'history',
  },
  {
    id: 'pain',
    category: 'history',
    label: '胸痛气促',
    value: '右侧吸气时胸痛，活动后气促。',
    triggers: ['胸痛', '气促', '呼吸'],
    revealStage: 'history',
  },
  {
    id: 'allergy',
    category: 'history',
    label: '过敏史',
    value: '既往无慢性肺病，否认已知药物过敏。',
    triggers: ['过敏', '药物', '既往'],
    revealStage: 'history',
  },
  {
    id: 'vitals',
    category: 'history',
    label: '生命体征',
    value: '体温39.1℃、心率104次/分、呼吸24次/分，室内空气血氧93%。',
    triggers: ['生命体征', '血氧', '心率'],
    revealStage: 'history',
  },
]

const dimensions: CaseRubricDimension[] = [
  ['information_gathering', '信息采集', 20, ['history']],
  ['problem_representation', '问题表征', 15, ['problem_representation']],
  ['differential_diagnosis', '鉴别诊断', 20, ['differential']],
  ['evidence_reasoning', '证据推理', 15, ['differential']],
  ['test_selection', '检查合理性', 15, ['tests']],
  ['management_safety', '处置与安全意识', 15, ['management']],
].map(([id, label, weight, stageIds]) => ({
  id: String(id),
  label: String(label),
  weight: Number(weight),
  stageIds: stageIds as CaseRubricDimension['stageIds'],
  criteria: [
    {
      id: `${id}-1`,
      label: `${label}核心要点`,
      keywords: ['发热', '肺炎', '氧合'],
      feedback: `请补充${label}核心证据。`,
      critical: id === 'management_safety',
    },
  ],
}))

export const showcaseDraft: CaseDraftGenerateResult = {
  title: '社区获得性肺炎：结构化临床推理',
  description: '面向临床医学本科生的五阶段推理训练。',
  specialty: '呼吸内科',
  difficulty: 'basic',
  estimatedMinutes: 10,
  generationMode: 'fallback',
  safetyNotice: '合成教学病例，不构成诊疗建议。',
  caseDefinition: {
    schemaVersion: 1,
    opening: {
      setting: '呼吸内科门诊',
      patientIntro: '48岁男性，因发热、咳嗽3天就诊。',
      chiefComplaint: '发热、咳嗽3天',
    },
    stageInstructions: {
      history: '通过提问获取病史。',
      problem_representation: '概括患者和主要问题。',
      differential: '列出鉴别诊断。',
      tests: '选择检查。',
      management: '提出教学场景处置。',
    },
    facts,
    referenceReasoning: {},
  },
  rubric: { dimensions },
}

function additionalDraft(
  title: string,
  description: string,
  specialty: string,
  opening: CaseDraftGenerateResult['caseDefinition']['opening'],
  facts: CaseFact[],
  referenceReasoning: Record<string, unknown>,
  tags: string[],
): CaseDraftGenerateResult {
  const dimensionKeywords: Record<string, string[]> = {
    information_gathering: ['病程', '伴随', '危险因素'],
    problem_representation: ['患者', '时间', '核心问题'],
    differential_diagnosis: ['鉴别', '诊断', '证据'],
    evidence_reasoning: ['支持', '反对', '风险'],
    test_selection: ['检查', '目的', '优先'],
    management_safety: ['监护', '复评', '安全'],
  }
  const additionalDimensions = dimensions.map((dimension) => ({
    ...dimension,
    criteria: [
      {
        ...dimension.criteria[0],
        keywords: dimensionKeywords[dimension.id] || ['证据'],
        feedback: `请补充${dimension.label}的病例证据。`,
      },
    ],
  }))
  return {
    title,
    description,
    specialty,
    difficulty: 'basic',
    estimatedMinutes: 10,
    generationMode: 'fallback',
    safetyNotice: '合成教学病例，不构成诊疗建议。',
    caseDefinition: {
      schemaVersion: 2,
      opening,
      stageInstructions: {
        history: '通过提问获取病程、伴随表现和危险因素。',
        problem_representation: '概括时间进程、关键阳性与阴性信息。',
        differential: '列出至少两个诊断，并说明支持与反对证据。',
        tests: '选择检查并说明目的、优先级和适用性。',
        management: '说明监护、复评和升级评估边界。',
      },
      facts,
      referenceReasoning,
      practiceBlueprints: tags.slice(0, 3).map((dimensionId, index) => ({
        id: `${title}-${dimensionId}`,
        dimensionId,
        stageId:
          dimensionId === 'test_selection'
            ? 'tests'
            : dimensionId === 'management_safety'
              ? 'management'
              : 'differential',
        learnerLevel: 'undergraduate',
        publicInstruction: '根据公开情境归纳关键证据和安全边界。',
        allowedVariants: ['等价临床表述'],
        fixedFacts: [],
        fallbackPrompt: '仅用于合成教学，不提供真实患者处方。',
        answerSchema: index % 2 ? 'decision_cards' : 'evidence_grid',
        criteria: [
          {
            id: `${dimensionId}-evidence`,
            weight: 60,
            keywords: ['证据', '风险'],
            feedback: '补充可核验证据。',
            critical: true,
          },
          {
            id: `${dimensionId}-safety`,
            weight: 40,
            keywords: ['安全', '复评'],
            feedback: '补充安全边界。',
            critical: false,
          },
        ],
      })),
    },
    rubric: { dimensions: additionalDimensions },
  }
}

export const additionalShowcaseDrafts: Record<string, CaseDraftGenerateResult> = {
  'acute-chest-pain-undergraduate-showcase': additionalDraft(
    '急性胸痛：危险分层与证据推理',
    '面向本科生的急性胸痛危险分层与安全处置训练。',
    '心血管内科/急诊教学',
    { setting: '急诊留观区', patientIntro: '56岁患者突发胸部不适2小时。', chiefComplaint: '突发胸痛2小时' },
    [
      {
        id: 'chest_onset',
        category: 'history',
        label: '起病',
        value: '胸痛突然出现，持续约2小时，活动时加重。',
        triggers: ['多久', '起病', '胸痛'],
        revealStage: 'history',
      },
      {
        id: 'chest_quality',
        category: 'history',
        label: '疼痛性质',
        value: '胸骨后压榨样不适，向左肩放射。',
        triggers: ['性质', '放射', '压榨'],
        revealStage: 'history',
      },
      {
        id: 'chest_associated',
        category: 'history',
        label: '伴随表现',
        value: '伴出汗和恶心，无咯血。',
        triggers: ['出汗', '恶心', '咯血'],
        revealStage: 'history',
      },
      {
        id: 'chest_risk',
        category: 'history',
        label: '危险因素',
        value: '有吸烟和高血压史，近期无外伤。',
        triggers: ['吸烟', '高血压', '外伤'],
        revealStage: 'history',
      },
      {
        id: 'chest_vitals',
        category: 'exam',
        label: '生命体征',
        value: '心率102次/分，血压154/92mmHg，血氧96%。',
        triggers: ['生命体征', '血压', '血氧'],
        revealStage: 'history',
      },
      {
        id: 'chest_ecg',
        category: 'test',
        label: '心电图',
        value: '心电图提示需要尽快复核的缺血性改变。',
        triggers: ['心电图', '心电', '缺血'],
        revealStage: 'tests',
      },
      {
        id: 'chest_troponin',
        category: 'test',
        label: '实验室检查',
        value: '肌钙蛋白结果待结合时间动态复查。',
        triggers: ['肌钙蛋白', '化验', '实验室'],
        revealStage: 'tests',
      },
    ],
    {
      problemRepresentation: '56岁患者突发持续性胸骨后压榨样胸痛，伴自主神经症状并存在心血管危险因素，需优先危险分层。',
      differentials: [
        {
          diagnosis: '急性冠脉综合征',
          supportingFactIds: ['chest_quality', 'chest_associated', 'chest_ecg'],
          opposingFactIds: [],
          priority: 1,
        },
        {
          diagnosis: '主动脉夹层',
          supportingFactIds: ['chest_onset'],
          opposingFactIds: ['chest_quality'],
          priority: 2,
        },
        { diagnosis: '肺栓塞', supportingFactIds: ['chest_onset'], opposingFactIds: ['chest_associated'], priority: 3 },
        {
          diagnosis: '非心源性胸痛',
          supportingFactIds: [],
          opposingFactIds: ['chest_quality', 'chest_risk'],
          priority: 4,
        },
      ],
      tests: [
        {
          name: '复核心电图',
          purpose: '判断缺血性改变并进行紧急危险分层',
          priority: 'necessary',
          resultFactId: 'chest_ecg',
        },
        {
          name: '动态心肌损伤标志物',
          purpose: '结合起病时间判断动态变化',
          priority: 'necessary',
          resultFactId: 'chest_troponin',
        },
      ],
      management: [
        { action: '持续监护并复评', rationale: '及时识别病情恶化和危险心律失常', priority: 1, safetyCritical: true },
        { action: '启动急诊评估路径', rationale: '避免对高危胸痛延误评估', priority: 2, safetyCritical: true },
      ],
    },
    ['differential_diagnosis', 'evidence_reasoning', 'management_safety'],
  ),
  'right-lower-quadrant-pain-undergraduate-showcase': additionalDraft(
    '右下腹痛：问题表征与检查选择',
    '面向本科生的右下腹痛鉴别、检查目的与适用性训练。',
    '普通外科/急诊教学',
    { setting: '普通外科门诊', patientIntro: '23岁患者腹痛逐渐移向右下腹。', chiefComplaint: '右下腹痛1天' },
    [
      {
        id: 'abd_migration',
        category: 'history',
        label: '疼痛迁移',
        value: '腹痛先在脐周，数小时后逐渐移向右下腹。',
        triggers: ['迁移', '脐周', '多久'],
        revealStage: 'history',
      },
      {
        id: 'abd_gi',
        category: 'history',
        label: '消化道表现',
        value: '伴恶心和食欲下降，无明显腹泻。',
        triggers: ['恶心', '食欲', '腹泻'],
        revealStage: 'history',
      },
      {
        id: 'abd_fever',
        category: 'history',
        label: '发热',
        value: '低热37.8℃，无寒战。',
        triggers: ['发热', '体温', '寒战'],
        revealStage: 'history',
      },
      {
        id: 'abd_urinary',
        category: 'history',
        label: '泌尿与妇科',
        value: '无尿频尿痛；需结合个体情况补充相关问诊。',
        triggers: ['尿频', '尿痛', '妇科'],
        revealStage: 'history',
      },
      {
        id: 'abd_exam',
        category: 'exam',
        label: '腹部查体',
        value: '右下腹压痛，反跳痛需谨慎评估。',
        triggers: ['查体', '压痛', '反跳'],
        revealStage: 'history',
      },
      {
        id: 'abd_blood',
        category: 'test',
        label: '基础检查',
        value: '血常规和炎症指标需要结合症状与查体解释。',
        triggers: ['血常规', '炎症', '白细胞'],
        revealStage: 'tests',
      },
      {
        id: 'abd_imaging',
        category: 'test',
        label: '影像检查',
        value: '根据年龄、妊娠可能性和资源选择适用影像。',
        triggers: ['影像', '超声', 'ct'],
        revealStage: 'tests',
      },
    ],
    {
      problemRepresentation: '23岁患者腹痛由脐周迁移至右下腹，伴恶心、低热和局部压痛，需结合适用性选择检查。',
      differentials: [
        {
          diagnosis: '急性阑尾炎',
          supportingFactIds: ['abd_migration', 'abd_fever', 'abd_exam'],
          opposingFactIds: [],
          priority: 1,
        },
        { diagnosis: '胃肠炎', supportingFactIds: ['abd_gi'], opposingFactIds: ['abd_migration'], priority: 2 },
        { diagnosis: '泌尿系疾病', supportingFactIds: [], opposingFactIds: ['abd_urinary'], priority: 3 },
        { diagnosis: '适用人群的妇科原因', supportingFactIds: ['abd_urinary'], opposingFactIds: [], priority: 4 },
      ],
      tests: [
        {
          name: '血常规和炎症指标',
          purpose: '结合病程和查体评估炎症证据',
          priority: 'necessary',
          resultFactId: 'abd_blood',
        },
        {
          name: '适用影像',
          purpose: '根据个体适用性确认腹腔内病变范围',
          priority: 'necessary',
          resultFactId: 'abd_imaging',
        },
      ],
      management: [
        {
          action: '复核腹部体征和生命体征',
          rationale: '识别需要升级评估的腹膜刺激或全身风险',
          priority: 1,
          safetyCritical: true,
        },
        {
          action: '根据适用性选择检查并请专科评估',
          rationale: '兼顾诊断收益和检查适用性',
          priority: 2,
          safetyCritical: false,
        },
      ],
    },
    ['problem_representation', 'evidence_reasoning', 'test_selection'],
  ),
}
