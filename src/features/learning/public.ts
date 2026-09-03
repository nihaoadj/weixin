import { getApplicationServices } from '@/bootstrap/wiring'

const learning = () => getApplicationServices().learning

export const getKnowledgeCatalog = () => learning().getKnowledgeCatalog()
export const getKnowledgeMap = () => learning().getKnowledgeMap()
export const createExitQuiz = (topicCodes: string[]) => learning().createExitQuiz(topicCodes)
export const getReviewDashboard = () => learning().getReviewDashboard()
export const getDueReviewQueue = () => learning().getDueReviewQueue()
export const gradeObjectiveCard = (cardCode: string, selectedOption: number, confidence: 'low' | 'medium' | 'high') =>
  learning().gradeObjectiveCard(cardCode, selectedOption, confidence)
export const revealRecallCard = (cardId: number) => learning().revealRecallCard(cardId)
export const rateRecallCard = (cardId: number, rating: 'again' | 'hard' | 'good' | 'easy') =>
  learning().rateRecallCard(cardId, rating)
export const captureManualReviewItem = (input: {
  pointCode: string
  sourceType: string
  sourceId: string
  note?: string
}) => learning().captureManualReviewItem(input)
export const dismissReviewItem = (id: number) => learning().dismissReviewItem(id)
export const getLearningProfile = () => learning().getLearningProfile()
export const createLearningPlan = (attemptId: string) => learning().createLearningPlan(attemptId)
export const getCurrentLearningPlan = () => learning().getCurrentLearningPlan()
export const getLearningPlan = (id: number) => learning().getLearningPlan(id)
export const startLearningTask = (id: number) => learning().startLearningTask(id)
export const getLearningTaskAttempt = (id: number) => learning().getLearningTaskAttempt(id)
export const submitLearningTaskAttempt = (id: number, answer: Record<string, unknown>) =>
  learning().submitLearningTaskAttempt(id, answer)
export const completeLearningPlan = (id: number) => learning().completeLearningPlan(id)
export const getLearningNotifications = (unreadOnly = false) => learning().getLearningNotifications(unreadOnly)
export const markLearningNotificationsRead = () => learning().markLearningNotificationsRead()

export type {
  LearningNotification,
  LearningPlan,
  LearningProfile,
  LearningTask,
  LearningTaskAttempt,
} from '@/types/learning'
export type {
  KnowledgePoint,
  KnowledgeMapPoint,
  KnowledgeStatus,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
  ReviewItem,
} from '@/types/knowledge'
