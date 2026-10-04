import type {
  LearningRouteDetail,
  LearningRouteGenerationReceipt,
  LearningRoutePage,
  LearningRouteReading,
  ReadingProgressAction,
} from './learningRoutes'
import type { RouteCaseMessageResult, RouteCaseRead } from './routeCases'
import type {
  FinalTestReleaseReceipt,
  FinalTestAnswer,
  FinalTestGradingStatus,
  LearningResult,
  LearningResultTutorThread,
  StudentFinalTest,
  TeacherLearningResult,
  TeacherFinalTest,
  EditableTeacherFinalTestQuestion,
  TeacherFinalTestReviewQueueFilters,
  TeacherFinalTestReviewQueuePage,
} from './finalTests'

export interface LearningRoutesPort {
  getLearningRoutes(status?: 'active' | 'completed', limit?: number, offset?: number): Promise<LearningRoutePage>
  getLearningRoute(routeId: string): Promise<LearningRouteDetail>
  retryLearningRouteGeneration(
    routeId: string,
    component: 'route' | 'test',
    clientRequestId: string,
  ): Promise<LearningRouteGenerationReceipt>
  getLearningRouteStep(stepId: string): Promise<LearningRouteReading>
  saveRouteReadingProgress(
    stepId: string,
    action: ReadingProgressAction,
    clientRequestId: string,
    leaseToken?: string,
  ): Promise<LearningRouteReading['readingProgress']>
  completeRouteReading(stepId: string, clientRequestId: string): Promise<LearningRouteDetail>
  getRouteCase(caseId: string): Promise<RouteCaseRead>
  sendRouteCaseMessage(
    caseId: string,
    content: string,
    clientMessageId: string,
    expectedRevision: number,
  ): Promise<RouteCaseMessageResult>
  startFinalTest(testId: string, clientRequestId: string): Promise<StudentFinalTest>
  getFinalTest(routeId: string): Promise<StudentFinalTest>
  saveFinalTestDraft(
    testId: string,
    clientRequestId: string,
    expectedVersion: number,
    releasedDigest: string,
    answers: Record<string, FinalTestAnswer>,
  ): Promise<NonNullable<StudentFinalTest['attempt']>>
  submitFinalTest(
    testId: string,
    clientSubmissionId: string,
    expectedVersion: number,
    releasedDigest: string,
    answers: Record<string, FinalTestAnswer>,
  ): Promise<LearningResult | FinalTestGradingStatus>
  getFinalTestGrading(testId: string): Promise<FinalTestGradingStatus>
  retryFinalTestGrading(testId: string, clientRequestId: string): Promise<FinalTestGradingStatus>
  getLearningRouteResult(routeId: string): Promise<LearningResult>
  getLearningResultTutor(resultId: string): Promise<LearningResultTutorThread>
  sendLearningResultTutorMessage(
    resultId: string,
    clientMessageId: string,
    questionId: string,
    expectedRevision: number,
    content: string,
  ): Promise<LearningResultTutorThread>
  getTeacherFinalTestReviewQueue(filters?: TeacherFinalTestReviewQueueFilters): Promise<TeacherFinalTestReviewQueuePage>
  getTeacherFinalTest(testId: string): Promise<TeacherFinalTest>
  saveTeacherFinalTest(
    testId: string,
    clientRequestId: string,
    expectedVersion: number,
    questions: EditableTeacherFinalTestQuestion[],
    feedbackDraft: string,
  ): Promise<TeacherFinalTest>
  requestTeacherTestChanges(
    testId: string,
    clientRequestId: string,
    expectedVersion: number,
    note?: string,
  ): Promise<TeacherFinalTest>
  retryTeacherTestGeneration(testId: string, clientRequestId: string): Promise<LearningRouteGenerationReceipt>
  releaseTeacherFinalTest(
    testId: string,
    clientRequestId: string,
    expectedVersion: number,
    draftDigest: string,
    feedback?: string,
  ): Promise<FinalTestReleaseReceipt>
  getTeacherRouteResult(resultId: string): Promise<TeacherLearningResult>
}
