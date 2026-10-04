export type FinalTestFormat = 'single_choice_v1' | 'mixed_v2'
export type FinalTestQuestionType = 'single_choice' | 'multiple_choice' | 'short_answer'
export type FinalTestAnswer = number | number[] | string
export type FinalTestOptionSet = [string, string, string, string]
export type FinalTestRubricCriterion = {
  criterionId: string
  description: string
  maxPoints: 10
}
export type FinalTestRubricResult = {
  criterionId: string
  earnedPoints: number
  evidence: string
}
type FinalTestQuestionFields = {
  id: string
  position: number
  pointCode: string
  prompt: string
  questionType: FinalTestQuestionType
}
export type StudentFinalTestQuestion = FinalTestQuestionFields & {
  options: string[]
}
type TeacherFinalTestQuestionFields = Omit<FinalTestQuestionFields, 'id' | 'pointCode'> & {
  id: string | null
  primaryPointCode: string
  explanation: string
  sourceDigest?: string
}
export type TeacherFinalTestQuestion =
  | (TeacherFinalTestQuestionFields & {
      questionType: 'single_choice'
      options: FinalTestOptionSet
      correctOption: number
      correctOptions?: never
      referenceAnswer?: never
      rubric?: never
    })
  | (TeacherFinalTestQuestionFields & {
      questionType: 'multiple_choice'
      options: FinalTestOptionSet
      correctOption?: never
      correctOptions: number[]
      referenceAnswer?: never
      rubric?: never
    })
  | (TeacherFinalTestQuestionFields & {
      questionType: 'short_answer'
      options?: never
      correctOption?: never
      correctOptions?: never
      referenceAnswer: string
      rubric: FinalTestRubricCriterion[]
    })
type WithoutSourceDigest<T> = T extends unknown ? Omit<T, 'sourceDigest'> : never
export type EditableTeacherFinalTestQuestion = WithoutSourceDigest<TeacherFinalTestQuestion>
export type FinalTestAttempt = {
  id: string
  status: string
  version: number
  answers: Record<string, FinalTestAnswer>
  savedAt?: string
  submittedAt?: string
}
export type StudentFinalTest = {
  id: string
  title: string
  reviewKind: 'teacher' | 'ai_direct' | null
  formatVersion: FinalTestFormat
  releasedVersion: number
  releasedDigest: string
  questions: StudentFinalTestQuestion[]
  attempt?: FinalTestAttempt | null
}
export type TeacherFinalTest = {
  id: string
  routeId: string
  title: string
  sourceKind: 'classroom'
  classId: number
  sessionId: number
  studentId: number
  diagnosisSummary: Record<string, unknown>
  goalPointCodes: string[]
  generationState: string
  reviewState: string
  reviewKind: 'teacher' | 'ai_direct' | null
  currentScopeActive: boolean
  formatVersion: FinalTestFormat
  version: number
  draftDigest: string
  questions: TeacherFinalTestQuestion[]
  releasedAt?: string
  feedbackDraft: string
}
export type TeacherFinalTestReviewQueueKind = 'pending_review' | 'needs_changes' | 'generation_failed'
export type TeacherFinalTestReviewQueueFilters = {
  classId?: number
  sessionId?: number | string
  kind?: TeacherFinalTestReviewQueueKind
  limit?: number
  offset?: number
}
export type TeacherFinalTestReviewQueueItem = {
  id: string
  routeId: string
  title: string
  classId: number
  className: string
  sessionId: number | string
  studentId: number
  studentName: string
  generationState: 'ready' | 'generation_failed'
  reviewState: 'pending_review' | 'needs_changes'
  updatedAt: string
  canReview: boolean
  canRetry: boolean
  actionReason: 'REVIEW_READY' | 'GENERATION_FAILED'
}
export type TeacherFinalTestReviewQueueCounts = {
  pendingReview: number
  needsChanges: number
  generationFailed: number
}
export type TeacherFinalTestReviewQueuePage = {
  items: TeacherFinalTestReviewQueueItem[]
  counts: TeacherFinalTestReviewQueueCounts
  total: number
  limit: number
  offset: number
  asOf: string
}
export type LearningResultQuestion = StudentFinalTestQuestion & {
  selectedOption?: number
  correctOption?: number
  selectedOptions?: number[]
  correctOptions?: number[]
  selectedText?: string
  referenceAnswer?: string
  rubricResults?: FinalTestRubricResult[]
  gradingFeedback?: string
  pointsAwarded?: number
  pointsPossible?: number
  explanation: string
}
export type LearningResult = {
  id: string
  routeId: string
  sourceKind: 'classroom' | 'autonomous'
  goalPointCodes: string[]
  routeSummary: Record<string, unknown>
  correctCount: number
  questionCount: number
  score: number
  submittedAt: string
  questions: LearningResultQuestion[]
  reviewKind: 'teacher' | 'ai_direct' | null
  formatVersion: FinalTestFormat
}
export type TeacherLearningResult = LearningResult & {
  studentId: number
  classId: number
  sessionId: number
}
export type FinalTestGradingStatus = {
  status: 'grading' | 'completed'
  testId: string
  routeId: string
  resultId?: string
  retryAllowed: boolean
  errorCode?: string
}
export type LearningResultTutorMessage = {
  id: string
  role: 'student' | 'assistant'
  questionId: string
  content: string
  sequence: number
  createdAt: string
}
export type LearningResultTutorThread = {
  resultId: string
  revision: number
  processingState: 'idle' | 'processing' | 'retry_allowed'
  pendingMessageId?: string
  messages: LearningResultTutorMessage[]
}
export type FinalTestReleaseReceipt = {
  testId: string
  releasedVersion: number
  releasedDigest: string
  releasedAt: string
}
