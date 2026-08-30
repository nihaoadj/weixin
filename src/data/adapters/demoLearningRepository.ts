import type { LearningNotification, LearningPlan, LearningProfile, LearningTaskAttempt } from '@/types/learning'
import { AppError } from '@/types/errors'
import type { LearningRepository } from '@/data/repositories/learning'
const emptyProfile: LearningProfile = {
  formalDimensions: [],
  recentAssessments: [],
  practiceMastery: {},
  unreadCount: 0,
}

export const demoLearningRepository: LearningRepository = {
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
