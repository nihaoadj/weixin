import type { LearningNotification, LearningPlan, LearningProfile, LearningTaskAttempt } from '@/types/learning'

export interface LearningRepository {
  getLearningProfile(): Promise<LearningProfile>
  createLearningPlan(attemptId: string): Promise<LearningPlan>
  getCurrentLearningPlan(): Promise<LearningPlan | undefined>
  getLearningPlan(id: number): Promise<LearningPlan>
  startLearningTask(id: number): Promise<{
    mode: 'case_attempt' | 'micro_drill'
    task: LearningPlan['tasks'][number]
    attempt: Record<string, unknown>
  }>
  getLearningTaskAttempt(id: number): Promise<LearningTaskAttempt>
  submitLearningTaskAttempt(id: number, answer: Record<string, unknown>): Promise<LearningTaskAttempt>
  completeLearningPlan(id: number): Promise<LearningPlan>
  getLearningNotifications(unreadOnly?: boolean): Promise<{ items: LearningNotification[]; unreadCount: number }>
  markLearningNotificationsRead(): Promise<void>
}
