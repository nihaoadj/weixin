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

import catalog from '@/features/content/infrastructure/pathologyCatalog.generated.json'

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

const now = () => new Date().toISOString()
const publicCard = (card: ReturnType<typeof demoCards>[number]): ReviewCard => ({
  cardCode: card.cardCode,
  pointCode: card.pointCode,
  prompt: card.prompt,
  options: card.options,
})

export const demoLearningRepository: LearningRepository = {
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
