import { getApplicationServices } from '@/bootstrap/wiring'
import type { FinalTestAnswer } from './domain/finalTests'
export { buildKnowledgeGraph, crossModuleDependenciesForModule } from '@/features/learning/application/knowledgeGraph'
export type { KnowledgeCrossModuleRelation } from '@/features/learning/application/knowledgeGraph'

const learning = () => getApplicationServices().learning
const learningRoutes = () => getApplicationServices().learningRoutes
const studentInsights = () => getApplicationServices().studentInsights

export const getStudentLearningInsights = (limit = 20, offset = 0) =>
  studentInsights().getStudentLearningInsights(limit, offset)
export type {
  StudentLearningInsightsAction,
  StudentLearningInsightsActionKind,
  StudentLearningInsightsDashboard,
  StudentLearningInsightsPage,
  StudentLearningInsightsRecord,
  StudentLearningInsightsTrend,
  StudentLearningInsightsWeakness,
} from './domain/studentLearningInsights'

export const getLearningRoutes = (status: 'active' | 'completed' = 'active', limit = 20, offset = 0) =>
  learningRoutes().getLearningRoutes(status, limit, offset)
export const getLearningRoute = (routeId: string) => learningRoutes().getLearningRoute(routeId)
export const retryLearningRouteGeneration = (routeId: string, component: 'route' | 'test', clientRequestId: string) =>
  learningRoutes().retryLearningRouteGeneration(routeId, component, clientRequestId)
export const getLearningRouteStep = (stepId: string) => learningRoutes().getLearningRouteStep(stepId)
export const saveRouteReadingProgress = (
  stepId: string,
  action: import('./domain/learningRoutes').ReadingProgressAction,
  clientRequestId: string,
  leaseToken?: string,
) => learningRoutes().saveRouteReadingProgress(stepId, action, clientRequestId, leaseToken)
export const completeRouteReading = (stepId: string, clientRequestId: string) =>
  learningRoutes().completeRouteReading(stepId, clientRequestId)
export const getRouteCase = (caseId: string) => learningRoutes().getRouteCase(caseId)
export const sendRouteCaseMessage = (
  caseId: string,
  content: string,
  clientMessageId: string,
  expectedRevision: number,
) => learningRoutes().sendRouteCaseMessage(caseId, content, clientMessageId, expectedRevision)
export const startFinalTest = (testId: string, clientRequestId: string) =>
  learningRoutes().startFinalTest(testId, clientRequestId)
export const getFinalTest = (routeId: string) => learningRoutes().getFinalTest(routeId)
export const saveFinalTestDraft = (
  testId: string,
  clientRequestId: string,
  expectedVersion: number,
  releasedDigest: string,
  answers: Record<string, FinalTestAnswer>,
) => learningRoutes().saveFinalTestDraft(testId, clientRequestId, expectedVersion, releasedDigest, answers)
export const submitFinalTest = (
  testId: string,
  clientSubmissionId: string,
  expectedVersion: number,
  releasedDigest: string,
  answers: Record<string, FinalTestAnswer>,
) => learningRoutes().submitFinalTest(testId, clientSubmissionId, expectedVersion, releasedDigest, answers)
export const getFinalTestGrading = (testId: string) => learningRoutes().getFinalTestGrading(testId)
export const retryFinalTestGrading = (testId: string, clientRequestId: string) =>
  learningRoutes().retryFinalTestGrading(testId, clientRequestId)
export const getLearningRouteResult = (routeId: string) => learningRoutes().getLearningRouteResult(routeId)
export const getLearningResultTutor = (resultId: string) => learningRoutes().getLearningResultTutor(resultId)
export const sendLearningResultTutorMessage = (
  resultId: string,
  clientMessageId: string,
  questionId: string,
  expectedRevision: number,
  content: string,
) => learningRoutes().sendLearningResultTutorMessage(resultId, clientMessageId, questionId, expectedRevision, content)
export const getTeacherFinalTestReviewQueue = (
  filters: import('./domain/finalTests').TeacherFinalTestReviewQueueFilters = {},
) => learningRoutes().getTeacherFinalTestReviewQueue(filters)
export const getTeacherFinalTest = (testId: string) => learningRoutes().getTeacherFinalTest(testId)
export const saveTeacherFinalTest = (
  testId: string,
  clientRequestId: string,
  expectedVersion: number,
  questions: import('./domain/finalTests').EditableTeacherFinalTestQuestion[],
  feedbackDraft: string,
) => learningRoutes().saveTeacherFinalTest(testId, clientRequestId, expectedVersion, questions, feedbackDraft)
export const requestTeacherTestChanges = (
  testId: string,
  clientRequestId: string,
  expectedVersion: number,
  note?: string,
) => learningRoutes().requestTeacherTestChanges(testId, clientRequestId, expectedVersion, note)
export const retryTeacherTestGeneration = (testId: string, clientRequestId: string) =>
  learningRoutes().retryTeacherTestGeneration(testId, clientRequestId)
export const releaseTeacherFinalTest = (
  testId: string,
  clientRequestId: string,
  expectedVersion: number,
  draftDigest: string,
  feedback?: string,
) => learningRoutes().releaseTeacherFinalTest(testId, clientRequestId, expectedVersion, draftDigest, feedback)
export const getTeacherRouteResult = (resultId: string) => learningRoutes().getTeacherRouteResult(resultId)
export const createLearningRequestId = (operation = 'learning') =>
  `${operation}-${Date.now()}-${Math.random().toString(36).slice(2, 14)}`
export { learningGoalLabel } from './presentation/goalLabel'
export type {
  LearningRoutePage,
  LearningRouteSummary,
  LearningRouteDetail,
  LearningRouteStep,
  LearningRouteReading,
  LearningRouteTestSummary,
  LearningRouteGenerationReceipt,
  ReadingProgressAction,
} from './domain/learningRoutes'
export type { RouteCaseRead, RouteCaseMessage, RouteCaseMessageResult } from './domain/routeCases'
export { ROUTE_CASE_STAGES } from './domain/routeCases'
export type {
  StudentFinalTest,
  TeacherFinalTest,
  TeacherFinalTestReviewQueueKind,
  TeacherFinalTestReviewQueueFilters,
  TeacherFinalTestReviewQueueItem,
  TeacherFinalTestReviewQueueCounts,
  TeacherFinalTestReviewQueuePage,
  TeacherFinalTestQuestion,
  EditableTeacherFinalTestQuestion,
  LearningResult,
  TeacherLearningResult,
  FinalTestAttempt,
  FinalTestAnswer,
  FinalTestFormat,
  FinalTestGradingStatus,
  FinalTestQuestionType,
  FinalTestRubricCriterion,
  FinalTestRubricResult,
  LearningResultQuestion,
  LearningResultTutorMessage,
  LearningResultTutorThread,
} from './domain/finalTests'

export const getKnowledgeCatalog = () => learning().getKnowledgeCatalog()
export const getStudyPath = (pointCode: string) => learning().getStudyPath(pointCode)
export const startStudyPath = (input: { pointCode: string; clientId: string; interactionStyle: 'guided' | 'direct' }) =>
  learning().startStudyPath(input)
export const getKnowledgeMap = () => learning().getKnowledgeMap()
export type {
  KnowledgePoint,
  KnowledgeGraph,
  KnowledgeGraphEdge,
  KnowledgeGraphIssue,
  KnowledgeGraphModule,
  KnowledgeGraphNode,
  KnowledgeMapPoint,
  KnowledgeStatus,
} from '@/types/knowledge'
export type { StudyMaterial, StudySession, StudyPathState } from '@/types/study'
