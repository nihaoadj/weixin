import type { LearningNotification, LearningPlan, LearningProfile, LearningTaskAttempt } from '@/types/learning'
import { AppError } from '@/types/errors'
import type { LearningRepository } from '@/features/learning/domain/ports'
import type {
  KnowledgePoint,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
  ReviewItem,
} from '@/types/knowledge'

const baseKnowledgeCatalog: KnowledgePoint[] = [
  {
    code: 'respiratory.cap',
    systemCode: 'respiratory',
    systemLabel: '呼吸系统',
    topic: '感染性疾病',
    title: '社区获得性肺炎',
    objective: '识别教学病例中的典型线索与初步评估重点。',
    reference: '教学版内科学参考',
    cardCount: 1,
    catalogVersion: 'internal-medicine-v1',
  },
  {
    code: 'cardio.acs',
    systemCode: 'cardio',
    systemLabel: '循环系统',
    topic: '缺血性心脏病',
    title: '急性冠脉综合征',
    objective: '识别胸痛危险分层中的关键病史与检查线索。',
    reference: '教学版内科学参考',
    cardCount: 1,
    catalogVersion: 'internal-medicine-v1',
  },
  {
    code: 'digestive.gi-bleed',
    systemCode: 'digestive',
    systemLabel: '消化系统',
    topic: '消化道疾病',
    title: '上消化道出血',
    objective: '识别消化道出血教学情境中的风险线索。',
    reference: '教学版内科学参考',
    cardCount: 1,
    catalogVersion: 'internal-medicine-v1',
  },
  {
    code: 'renal.aki',
    systemCode: 'renal',
    systemLabel: '泌尿系统',
    topic: '肾功能异常',
    title: '急性肾损伤',
    objective: '按病因分类组织急性肾损伤的初步判断。',
    reference: '教学版内科学参考',
    cardCount: 1,
    catalogVersion: 'internal-medicine-v1',
  },
  {
    code: 'hematology.anemia',
    systemCode: 'hematology',
    systemLabel: '血液系统',
    topic: '贫血',
    title: '贫血初步分类',
    objective: '用红细胞指标组织贫血的基础分类。',
    reference: '教学版内科学参考',
    cardCount: 1,
    catalogVersion: 'internal-medicine-v1',
  },
  {
    code: 'endocrine.diabetes',
    systemCode: 'endocrine',
    systemLabel: '内分泌与代谢',
    topic: '糖代谢',
    title: '糖尿病慢病管理',
    objective: '说明糖代谢异常的长期风险评估思路。',
    reference: '教学版内科学参考',
    cardCount: 1,
    catalogVersion: 'internal-medicine-v1',
  },
]
const additionalKnowledgeSeed: Array<[string, string, string, string, string]> = [
  ['respiratory.asthma', '呼吸系统', '气道疾病', '哮喘急性发作', '识别急性气道症状的评估与升级边界。'],
  ['respiratory.copd', '呼吸系统', '慢性气道疾病', '慢阻肺急性加重', '识别慢性气道症状恶化时的风险线索。'],
  ['respiratory.pleural-effusion', '呼吸系统', '胸膜疾病', '胸腔积液基础评估', '组织症状、体征和影像线索的教学解释。'],
  ['cardio.hypertension', '循环系统', '高血压', '高血压基础评估', '说明血压评估需要结合重复测量与整体风险。'],
  ['cardio.heart-failure', '循环系统', '心力衰竭', '急性心力衰竭', '识别容量负荷和灌注改变的教学线索。'],
  ['cardio.arrhythmia', '循环系统', '心律失常', '常见心律失常评估', '说明心悸与晕厥线索的安全评估边界。'],
  ['digestive.pancreatitis', '消化系统', '胰腺疾病', '急性胰腺炎', '建立症状、实验室线索与安全评估的联系。'],
  ['digestive.appendicitis', '消化系统', '急腹症', '右下腹痛与阑尾炎', '组织右下腹痛的病程、体征与鉴别线索。'],
  ['digestive.hepatitis', '消化系统', '肝脏疾病', '肝功能异常基础评估', '关联黄疸、肝功指标和风险因素的教学线索。'],
  ['renal.electrolyte', '泌尿系统', '水电解质', '高钾血症风险', '识别需要优先升级评估的高钾风险线索。'],
  ['renal.ckd', '泌尿系统', '慢性肾脏病', '慢性肾脏病分层', '说明肾功能长期随访与风险管理框架。'],
  ['renal.uti', '泌尿系统', '泌尿系感染', '尿路感染基础判断', '识别症状、尿检与升级评估的教学线索。'],
  ['hematology.bleeding', '血液系统', '凝血', '出血倾向评估', '识别出血风险教学场景中的基础问诊重点。'],
  ['hematology.leukocytosis', '血液系统', '白细胞异常', '白细胞异常解读', '结合病程组织白细胞异常的基础解释。'],
  ['hematology.thrombosis', '血液系统', '血栓与凝血', '静脉血栓风险', '识别血栓风险因素和警示症状的教学重点。'],
  ['endocrine.thyroid', '内分泌与代谢', '甲状腺', '甲状腺功能异常', '区分甲状腺功能异常的常见教学线索。'],
  ['endocrine.dka', '内分泌与代谢', '急性代谢异常', '糖尿病酮症酸中毒风险', '识别高血糖急症中的安全评估线索。'],
  ['endocrine.adrenal', '内分泌与代谢', '肾上腺', '肾上腺功能异常', '组织电解质、血压与激素相关的教学线索。'],
]
const knowledgeCatalog: KnowledgePoint[] = [
  ...baseKnowledgeCatalog,
  ...additionalKnowledgeSeed.map(([code, systemLabel, topic, title, objective]) => ({
    code,
    systemCode: code.startsWith('cardio.')
      ? 'cardio'
      : code.startsWith('digestive.')
        ? 'digestive'
        : code.startsWith('renal.')
          ? 'renal'
          : code.startsWith('hematology.')
            ? 'hematology'
            : code.startsWith('endocrine.')
              ? 'endocrine'
              : 'respiratory',
    systemLabel,
    topic,
    title,
    objective,
    reference: '教学版内科学参考',
    cardCount: 1,
    catalogVersion: 'internal-medicine-v1',
  })),
]
const emptyProfile: LearningProfile = {
  formalDimensions: [],
  recentAssessments: [],
  practiceMastery: {},
  unreadCount: 0,
}

const baseDemoCards: Array<ReviewCard & { correctOption: number; explanation: string }> = [
  {
    cardCode: 'respiratory.cap.basics.1',
    pointCode: 'respiratory.cap',
    prompt: '在发热、咳嗽、气促的教学病例中，哪项信息最有助于初步判断病情严重度？',
    options: ['是否有季节性过敏', '生命体征和血氧情况', '最喜欢的运动', '既往视力'],
    correctOption: 1,
    explanation: '生命体征和氧合情况是识别需要优先评估风险的重要公开线索。',
  },
  {
    cardCode: 'cardio.acs.basics.1',
    pointCode: 'cardio.acs',
    prompt: '突发持续胸骨后压榨样不适伴出汗时，合理的教学推理优先级是？',
    options: ['先做危险分层', '先判断饮食偏好', '等待症状自行消失', '只讨论远期康复'],
    correctOption: 0,
    explanation: '胸痛伴危险线索时，应先完成风险识别和及时评估边界。',
  },
  {
    cardCode: 'digestive.gi-bleed.basics.1',
    pointCode: 'digestive.gi-bleed',
    prompt: '面对疑似消化道出血的教学情境，哪项属于需要优先关注的线索？',
    options: ['循环状态变化', '发型变化', '偏爱的食物', '近期阅读量'],
    correctOption: 0,
    explanation: '循环状态变化提示需要优先进行安全评估。',
  },
  {
    cardCode: 'renal.aki.basics.1',
    pointCode: 'renal.aki',
    prompt: '急性肾功能异常的教学分类常从哪三类原因组织？',
    options: ['肾前性、肾性、肾后性', '春夏秋', '轻中重三个颜色', '仅按年龄'],
    correctOption: 0,
    explanation: '肾前性、肾性与肾后性是基础教学分类框架。',
  },
  {
    cardCode: 'hematology.anemia.basics.1',
    pointCode: 'hematology.anemia',
    prompt: '贫血初步分类时，哪项实验室信息通常有助于组织学习思路？',
    options: ['红细胞指标', '鞋码', '惯用手', '屏幕时间'],
    correctOption: 0,
    explanation: '红细胞相关指标可作为基础分类线索，仍需结合完整临床背景。',
  },
  {
    cardCode: 'endocrine.diabetes.basics.1',
    pointCode: 'endocrine.diabetes',
    prompt: '糖代谢异常的长期学习管理通常应包含什么？',
    options: ['风险因素、生活方式与随访', '只看一次症状', '忽略并发风险', '仅比较体重'],
    correctOption: 0,
    explanation: '慢病学习应把风险、生活方式与持续随访放在同一框架。',
  },
]
const demoCards: Array<ReviewCard & { correctOption: number; explanation: string }> = [
  ...baseDemoCards,
  ...knowledgeCatalog
    .filter((point) => !baseDemoCards.some((card) => card.pointCode === point.code))
    .map((point) => ({
      cardCode: `${point.code}.basics.1`,
      pointCode: point.code,
      prompt: `学习“${point.title}”时，哪种做法最符合安全、可复核的教学推理？`,
      options: ['结合病程、客观线索与风险边界', '只依据单一症状下结论', '忽略危险信号', '自行替代专业评估'],
      correctOption: 0,
      explanation: '教学推理应整合公开临床线索并识别需要升级专业评估的边界。',
    })),
]
let demoReviewItems: ReviewItem[] = []
let demoDueCards: ReviewCard[] = []
let nextDemoItemId = 1

const now = () => new Date().toISOString()
const publicCard = (card: (typeof demoCards)[number]): ReviewCard => ({
  cardCode: card.cardCode,
  pointCode: card.pointCode,
  prompt: card.prompt,
  options: card.options,
})

export const demoLearningRepository: LearningRepository = {
  async getKnowledgeCatalog() {
    return knowledgeCatalog
  },
  async getKnowledgeMap() {
    const weak = new Set(demoReviewItems.filter((item) => item.active).map((item) => item.pointCode))
    const due = new Set(demoDueCards.map((item) => item.pointCode))
    return knowledgeCatalog.map((point) => ({
      ...point,
      status: weak.has(point.code) ? 'weak' : due.has(point.code) ? 'due' : 'not_started',
    }))
  },
  async createExitQuiz(topicCodes: string[]): Promise<ReviewCard[]> {
    return demoCards
      .filter((card) => topicCodes.includes(card.pointCode))
      .slice(0, 3)
      .map(publicCard)
  },
  async getReviewDashboard(): Promise<ReviewDashboard> {
    return {
      dueCount: demoDueCards.length,
      weakPointCodes: [...new Set(demoReviewItems.filter((item) => item.active).map((item) => item.pointCode))],
      items: demoReviewItems.filter((item) => item.active),
    }
  },
  async getDueReviewQueue(): Promise<ReviewCard[]> {
    return demoDueCards.slice(0, 15)
  },
  async gradeObjectiveCard(cardCode, selectedOption, confidence): Promise<ReviewGrade> {
    const card = demoCards.find((item) => item.cardCode === cardCode)
    if (!card) throw new AppError('复习卡不存在', { code: 'RESOURCE_NOT_FOUND' })
    const correct = selectedOption === card.correctOption
    const rating = correct ? ({ low: 'hard', medium: 'good', high: 'easy' } as const)[confidence] : 'again'
    const dueAt = new Date(Date.now() + (rating === 'again' ? 1 : rating === 'easy' ? 4 : 3) * 86_400_000).toISOString()
    if (!correct) {
      demoDueCards = [...demoDueCards.filter((item) => item.cardCode !== cardCode), { ...publicCard(card), dueAt }]
      await this.captureManualReviewItem({
        pointCode: card.pointCode,
        sourceType: 'objective_card',
        sourceId: cardCode,
      })
    } else {
      demoDueCards = demoDueCards.filter((item) => item.cardCode !== cardCode)
    }
    return { cardCode, correct, rating, explanation: card.explanation, dueAt }
  },
  async revealRecallCard(_cardId: number): Promise<RecallReveal> {
    throw new AppError('Demo 模式暂未提供教师审核的回忆卡', { code: 'UNSUPPORTED_OPERATION' })
  },
  async rateRecallCard(_cardId: number, _rating: 'again' | 'hard' | 'good' | 'easy'): Promise<ReviewGrade> {
    throw new AppError('Demo 模式暂未提供教师审核的回忆卡', { code: 'UNSUPPORTED_OPERATION' })
  },
  async captureManualReviewItem(input): Promise<ReviewItem> {
    const existing = demoReviewItems.find(
      (item) =>
        item.pointCode === input.pointCode && item.sourceType === input.sourceType && item.sourceId === input.sourceId,
    )
    if (existing) return existing
    const item: ReviewItem = {
      id: nextDemoItemId++,
      pointCode: input.pointCode,
      sourceType: input.sourceType,
      sourceId: input.sourceId,
      note: input.note || '',
      active: true,
      createdAt: now(),
      updatedAt: now(),
    }
    demoReviewItems = [item, ...demoReviewItems]
    return item
  },
  async dismissReviewItem(id: number): Promise<void> {
    demoReviewItems = demoReviewItems.map((item) =>
      item.id === id ? { ...item, active: false, updatedAt: now() } : item,
    )
  },
  async getLearningProfile(): Promise<LearningProfile> {
    return emptyProfile
  },
  async createLearningPlan(_attemptId: string): Promise<LearningPlan> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async getCurrentLearningPlan(): Promise<LearningPlan | undefined> {
    return undefined
  },
  async getLearningPlan(_id: number): Promise<LearningPlan> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async startLearningTask(_id: number): Promise<{
    mode: 'case_attempt' | 'micro_drill'
    task: LearningPlan['tasks'][number]
    attempt: Record<string, unknown>
  }> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async getLearningTaskAttempt(_id: number): Promise<LearningTaskAttempt> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async submitLearningTaskAttempt(_id: number, _answer: Record<string, unknown>): Promise<LearningTaskAttempt> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async completeLearningPlan(_id: number): Promise<LearningPlan> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async getLearningNotifications(_unreadOnly = false): Promise<{ items: LearningNotification[]; unreadCount: number }> {
    return { items: [], unreadCount: 0 }
  },
  async markLearningNotificationsRead(): Promise<void> {
    return
  },
}
