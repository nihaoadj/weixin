import { getApplicationServices } from '@/bootstrap/wiring'
export { buildKnowledgeGraph } from '@/features/learning/application/knowledgeGraph'

const learning = () => getApplicationServices().learning

export const getKnowledgeCatalog = () => learning().getKnowledgeCatalog()
export const getStudyPath = (pointCode: string) => learning().getStudyPath(pointCode)
export const startStudyPath = (input: {
  pointCode: string
  clientId: string
  interactionStyle: 'guided' | 'direct'
  newRound?: boolean
}) => learning().startStudyPath(input)
export const getStudyPractices = (pathId: number) => learning().getStudyPractices(pathId)
export const generateStudyPractice = (pathId: number, cycle: 1 | 2, clientId: string) =>
  learning().generateStudyPractice(pathId, cycle, clientId)
export const getPrivatePractice = (id: number) => learning().getPrivatePractice(id)
export const getPrivatePracticeHistory = () => learning().getPrivatePracticeHistory()
export const answerPrivatePractice = (input: {
  groupId: number
  clientId: string
  questionIndex: number
  selectedOption: number
}) => learning().answerPrivatePractice(input)
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
  KnowledgeGraph,
  KnowledgeGraphEdge,
  KnowledgeGraphIssue,
  KnowledgeGraphModule,
  KnowledgeGraphNode,
  KnowledgeMapPoint,
  KnowledgeStatus,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
  ReviewItem,
} from '@/types/knowledge'
export type {
  PrivatePracticeFeedback,
  PrivatePracticeGroup,
  StudyMaterial,
  StudyPath,
  StudyPathState,
} from '@/types/study'
