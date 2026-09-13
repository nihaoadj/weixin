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
import type { PrivatePracticeFeedback, PrivatePracticeGroup, StudyPathState } from '@/types/study'
import { getSessionContext } from '@/platform/session/context'

import catalog from '@/features/content/infrastructure/pathologyCatalog.generated.json'

type DemoDialoguePort = {
  createDialogue(input: {
    clientSessionId: string
    classId?: string
    interactionStyle: 'guided' | 'direct'
    goalPointCodes: string[]
  }): Promise<{ session: { id: string } }>
  dialogue(id: string): Promise<{ participation?: { currentPhase: string } }>
}
type DemoTeacherFeedbackPort = {
  teacherFeedbackNotifications(): Promise<
    Array<{
      id: number
      sessionId: string
      actionType: 'feedback_only' | 'task_published' | 'closed'
      body: string
      createdAt: string
    }>
  >
}
let demoDialogues: DemoDialoguePort | undefined
let demoTeacherFeedback: DemoTeacherFeedbackPort | undefined
export const configureDemoStudyDialogues = (dialogues: DemoDialoguePort) => {
  demoDialogues = dialogues
}
export const configureDemoTeacherFeedback = (feedback: DemoTeacherFeedbackPort) => {
  demoTeacherFeedback = feedback
}

const knowledgeCatalog = (): KnowledgePoint[] =>
  catalog.map((p) => ({
    code: p.code,
    systemCode: p.system_code,
    systemLabel: p.system_label,
    topic: p.topic,
    title: p.title,
    objective: p.objective,
    reference: p.reference,
    cardCount: p.card_count,
    catalogVersion: p.catalog_version,
    description: p.description,
    prerequisiteCodes: p.prerequisite_codes,
    relatedCodes: p.related_codes,
    caseSlug: p.case_slug,
  }))
const emptyProfile: LearningProfile = {
  formalDimensions: [],
  recentAssessments: [],
  practiceMastery: {},
  unreadCount: 0,
}
const demoFeedbackReadAt = new Map<string, string>()
const demoFeedbackNotifications = async (): Promise<LearningNotification[]> => {
  if (!demoTeacherFeedback) return []
  return (await demoTeacherFeedback.teacherFeedbackNotifications()).map((item) => ({
    id: item.id,
    type: 'pbl_teacher_feedback',
    entityType: 'pbl_session',
    entityId: item.sessionId,
    title:
      item.actionType === 'task_published'
        ? '教师已发布 PBL 任务'
        : item.actionType === 'closed'
          ? '教师已关闭本次研讨'
          : '教师已回应你的 PBL 研讨',
    body: item.body,
    readAt: demoFeedbackReadAt.get(`${currentStudentKey()}:${item.id}`),
    createdAt: item.createdAt,
  }))
}

// Demo questions are explicitly synthetic and do not expose the API catalog's answer keys.
const demoCards = (): Array<ReviewCard & { correctOption: number; explanation: string }> =>
  knowledgeCatalog().flatMap((point) =>
    ['practice', 'retest'].map((kind) => ({
      cardCode: `${point.code}.${kind}`,
      pointCode: point.code,
      prompt: `演示练习：学习“${point.title}”时，应如何核对自己的机制解释？`,
      options: ['列出形态观察，再比较可能的机制', '仅记住结论', '忽略不同解释', '把相关性当成因果'],
      correctOption: 0,
      explanation: '这是 Demo 操作演示。正式题目由服务端提供并判分。',
    })),
  )
let demoReviewItems: ReviewItem[] = []
let demoDueCards: ReviewCard[] = []
let nextDemoItemId = 1
let nextDemoStudyPathId = 1
const demoStudyPaths = new Map<string, StudyPathState>()
let nextDemoPracticeId = 1
const demoPractices = new Map<number, PrivatePracticeGroup>()
const demoPracticeOwners = new Map<number, string>()

const now = () => new Date().toISOString()
const currentStudentKey = () => {
  const session = getSessionContext()
  if (!session) throw new AppError('请先登录', { code: 'AUTH_REQUIRED' })
  return session.openid
}
const studyKey = (pointCode: string) => `${currentStudentKey()}:${pointCode}`
const studyMaterial = (pointCode: string) => {
  const point = knowledgeCatalog().find((item) => item.code === pointCode)
  if (!point) throw new AppError('知识点不存在', { code: 'RESOURCE_NOT_FOUND' })
  return {
    version: 'pathology-study-v1-demo',
    pointCode,
    title: point.title,
    objective: point.objective,
    scenario: `围绕“${point.title}”，请先描述题目给出的观察线索，并提出需要核对的机制。`,
    background: [{ title: '观察与解释', text: '先区分已观察到的形态或情境线索，以及据此作出的推断。' }],
    example: { title: '引导实例', text: point.description ?? '' },
    remediation: [{ title: '机制回顾', text: point.description ?? '' }],
    reference: point.reference,
    reviewStatus: 'unreviewed' as const,
  }
}
const publicCard = (card: ReturnType<typeof demoCards>[number]): ReviewCard => ({
  cardCode: card.cardCode,
  pointCode: card.pointCode,
  prompt: card.prompt,
  options: card.options,
})

export const demoLearningRepository: LearningRepository = {
  async getStudyPath(pointCode): Promise<StudyPathState> {
    const saved = demoStudyPaths.get(studyKey(pointCode))
    if (saved) {
      if (demoDialogues && saved.path) {
        const dialogue = await demoDialogues.dialogue(saved.path.sessionId)
        const completed = dialogue.participation?.currentPhase === 'completed'
        saved.phase = dialogue.participation?.currentPhase || saved.phase
        saved.practiceUnlocked = completed
        saved.reviewUnlocked =
          completed &&
          [...demoPractices.values()].some((group) => group.pathId === saved.path?.id && group.attempts.length > 0)
        saved.lockReason = completed ? '' : '请先完成本知识点的四阶段研讨。'
      }
      return structuredClone(saved)
    }
    return {
      material: studyMaterial(pointCode),
      phase: 'not_started',
      practiceUnlocked: false,
      reviewUnlocked: false,
      legacyAccess: false,
      summary: '',
      lockReason: '请先完成本知识点的四阶段研讨。',
      history: [],
    }
  },
  async startStudyPath(input): Promise<StudyPathState> {
    const state = await this.getStudyPath(input.pointCode)
    if (state.path && !input.newRound) return state
    if (!demoDialogues) throw new AppError('Demo 研讨服务未装配', { code: 'SERVICE_UNAVAILABLE' })
    const dialogue = await demoDialogues.createDialogue({
      clientSessionId: `study-${input.clientId}`,
      interactionStyle: input.interactionStyle,
      goalPointCodes: [input.pointCode],
    })
    const path = {
      id: nextDemoStudyPathId++,
      pointCode: input.pointCode,
      sessionId: dialogue.session.id,
      materialVersion: state.material.version,
    }
    const next = { ...state, path, history: [path], phase: 'problem_framing' }
    demoStudyPaths.set(studyKey(input.pointCode), next)
    return structuredClone(next)
  },
  async getStudyPractices(pathId): Promise<PrivatePracticeGroup[]> {
    const owner = currentStudentKey()
    return [...demoPractices.entries()]
      .filter(([id, item]) => item.pathId === pathId && demoPracticeOwners.get(id) === owner)
      .map(([, item]) => structuredClone(item))
  },
  async generateStudyPractice(pathId, cycle, _clientId): Promise<PrivatePracticeGroup> {
    const owner = currentStudentKey()
    const path = [...demoStudyPaths.entries()].find(
      ([key, item]) => key.startsWith(`${owner}:`) && item.path?.id === pathId,
    )?.[1]
    if (!path || !path.practiceUnlocked) throw new AppError('完成研讨后可生成练习', { code: 'STATE_CONFLICT' })
    const existing = [...demoPractices.entries()].find(
      ([id, item]) => demoPracticeOwners.get(id) === owner && item.pathId === pathId && item.cycle === cycle,
    )?.[1]
    if (existing) return structuredClone(existing)
    const group: PrivatePracticeGroup = {
      id: nextDemoPracticeId++,
      pathId,
      cycle,
      status: 'ready',
      attempts: [],
      dueIndexes: [],
      canRetest: false,
      exhausted: false,
      questions: [
        {
          index: 0,
          pointCode: path.path!.pointCode,
          prompt: `Demo 未审核 AI 练习：${path.material.scenario}`,
          options: ['用机制和证据共同解释', '只记住结论', '忽略不同证据', '把相关性当成因果'],
        },
      ],
    }
    demoPractices.set(group.id, group)
    demoPracticeOwners.set(group.id, currentStudentKey())
    return structuredClone(group)
  },
  async getPrivatePractice(id): Promise<PrivatePracticeGroup> {
    const group = demoPractices.get(id)
    if (!group || demoPracticeOwners.get(id) !== currentStudentKey())
      throw new AppError('未审核 AI 练习不存在', { code: 'RESOURCE_NOT_FOUND' })
    return structuredClone(group)
  },
  async getPrivatePracticeHistory(): Promise<PrivatePracticeGroup[]> {
    const owner = currentStudentKey()
    return [...demoPractices.entries()]
      .filter(([id]) => demoPracticeOwners.get(id) === owner)
      .map(([, item]) => structuredClone(item))
  },
  async answerPrivatePractice(input): Promise<PrivatePracticeFeedback> {
    const group = demoPractices.get(input.groupId)
    const question = group?.questions.find((item) => item.index === input.questionIndex)
    if (
      !group ||
      demoPracticeOwners.get(input.groupId) !== currentStudentKey() ||
      !question ||
      input.selectedOption < 0 ||
      input.selectedOption >= question.options.length
    )
      throw new AppError('未审核 AI 练习不存在', { code: 'RESOURCE_NOT_FOUND' })
    const existing = group.attempts.find((item) => item.questionIndex === input.questionIndex)
    if (existing)
      return { ...existing, explanation: '这是 Demo 合成反馈，正式运行按 AI 参考答案反馈。', referenceOption: 0 }
    const correct = input.selectedOption === 0
    const attempt = {
      id: group.attempts.length + 1,
      questionIndex: input.questionIndex,
      selectedOption: input.selectedOption,
      correct,
      dueAt: new Date(Date.now() + (correct ? 3 : 1) * 86_400_000).toISOString(),
      createdAt: now(),
    }
    group.attempts.push(attempt)
    if (group.cycle === 1) group.canRetest = !correct
    if (group.cycle === 2) group.exhausted = !correct
    return { ...attempt, explanation: '这是 Demo 合成反馈，正式运行按 AI 参考答案反馈。', referenceOption: 0 }
  },
  async getKnowledgeCatalog() {
    return knowledgeCatalog()
  },
  async getKnowledgeMap() {
    const weak = new Set(demoReviewItems.filter((item) => item.active).map((item) => item.pointCode))
    const due = new Set(demoDueCards.map((item) => item.pointCode))
    return knowledgeCatalog().map((point) => ({
      ...point,
      status: weak.has(point.code) ? 'weak' : due.has(point.code) ? 'due' : 'not_started',
    }))
  },
  async createExitQuiz(topicCodes: string[]): Promise<ReviewCard[]> {
    return demoCards()
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
    const card = demoCards().find((item) => item.cardCode === cardCode)
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
    const unreadCount = (await demoFeedbackNotifications()).filter((item) => !item.readAt).length
    return { ...emptyProfile, unreadCount }
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
  async getLearningNotifications(unreadOnly = false): Promise<{ items: LearningNotification[]; unreadCount: number }> {
    const all = await demoFeedbackNotifications()
    const unreadCount = all.filter((item) => !item.readAt).length
    return { items: unreadOnly ? all.filter((item) => !item.readAt) : all, unreadCount }
  },
  async markLearningNotificationsRead(): Promise<void> {
    const readAt = new Date().toISOString()
    for (const item of await demoFeedbackNotifications())
      demoFeedbackReadAt.set(`${currentStudentKey()}:${item.id}`, readAt)
  },
}
