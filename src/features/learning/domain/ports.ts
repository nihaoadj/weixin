import type { LearningNotification, LearningPlan, LearningProfile, LearningTaskAttempt } from '@/types/learning'
import type {
  KnowledgePoint,
  KnowledgeMapPoint,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
  ReviewItem,
} from '@/types/knowledge'

export interface LearningRepository {
  getKnowledgeCatalog(): Promise<KnowledgePoint[]>
  getKnowledgeMap(): Promise<KnowledgeMapPoint[]>
  createExitQuiz(topicCodes: string[]): Promise<ReviewCard[]>
  getReviewDashboard(): Promise<ReviewDashboard>
  getDueReviewQueue(): Promise<ReviewCard[]>
  gradeObjectiveCard(
    cardCode: string,
    selectedOption: number,
    confidence: 'low' | 'medium' | 'high',
  ): Promise<ReviewGrade>
  revealRecallCard(cardId: number): Promise<RecallReveal>
  rateRecallCard(cardId: number, rating: 'again' | 'hard' | 'good' | 'easy'): Promise<ReviewGrade>
  captureManualReviewItem(input: {
    pointCode: string
    sourceType: string
    sourceId: string
    note?: string
  }): Promise<ReviewItem>
  dismissReviewItem(id: number): Promise<void>
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
