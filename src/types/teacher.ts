export interface TeacherClass {
  id: number
  name: string
  code: string
  status: string
  teacherId: number
  createdAt?: string
}

export interface TeacherStudent {
  id: number
  nickname: string
  externalId: string
  joinedAt: string
}

/** Minimal student-facing class membership fact for report submission (T29). */
export interface StudentActiveClass {
  id: number
  name: string
  code: string
}

export interface AnalyticsDimension {
  dimensionId: string
  label: string
  averageScore: number | null
  baselineScore?: number | null
  currentScore?: number | null
  delta?: number | null
  studentCount?: number
  rate?: number | null
  sampleCount?: number
}

export interface AnalyticsCoverage {
  studentCount: number
  participantCount: number
  evidenceCount: number
  updatedAt: string | null
}

export interface AnalyticsCompletion {
  formalTaskRate: number | null
  formalTaskCompleted: number
  formalTaskAttempted: number
  classroomPblRate: number | null
  classroomPblCompleted: number
  classroomPblStarted: number
  caseRate: number | null
  caseCompleted: number
}

export interface AnalyticsAttentionItem {
  kind: string
  studentCount: number
  route: string
}

export interface AnalyticsAttention {
  supportNeeded: number
  formalRepeatedFailure: number
  inactive: number
  items: AnalyticsAttentionItem[]
}

export interface AnalyticsKnowledgeRow {
  pointCode: string
  label?: string
  participantCount: number
  evidenceCount: number
  correctCount?: number
  rate: number | null
  trend?: number | null
}

export interface AnalyticsActivitySource {
  sourceType: string
  eventCount: number
  participantCount: number
}

export interface AnalyticsStudentSummary {
  studentId: number
  nickname: string
  formalActivityCompleted: number
  formalActivityExpected: number | null
  formalActivityRate: number | null
  recentResult: string | null
  attentionCodes: string[]
  pblStatus: string | null
  lastEvidenceAt: string | null
  completed: number
  assigned: number | null
  averageScore: number | null
}

export interface AnalyticsOverview {
  scope: { classId: number | null; className: string | null; dateFrom: string; dateTo: string }
  coverage: AnalyticsCoverage
  completion: AnalyticsCompletion
  attention: AnalyticsAttention
  knowledge: AnalyticsKnowledgeRow[]
  activitySources: AnalyticsActivitySource[]
  sourceSummary: AnalyticsActivitySource[]
  privacy: { minimumCohortSize: number; rankingsSuppressed: boolean }
  updatedAt: string | null
  studentCount: number
  publishedCaseCount: number
  eligiblePairs: number
  startedPairs: number
  completedPairs: number
  completionRate: number | null
  currentAverageScore: number | null
  averageImprovement: number | null
  dimensions: AnalyticsDimension[]
  weakDimensions: AnalyticsDimension[]
  cases: Array<{
    problemId: number
    title: string
    completed: number
    assigned: number | null
    averageScore: number | null
  }>
  students: AnalyticsStudentSummary[]
}

export interface AnalyticsCase {
  problem: { id: number; title: string; version: number; slug?: string | null }
  eligiblePairs: number | null
  startedPairs: number | null
  completedPairs: number | null
  completionRate: number | null
  currentAverageScore: number | null
  averageImprovement: number | null
  averageDurationMinutes: number | null
  dimensions: AnalyticsDimension[]
  distribution: Record<string, number>
  students: Array<{
    studentId: number
    nickname: string
    status: string
    baseline: number | null
    current: number | null
    delta: number | null
    focusStage: string | null
    lastAssessedAt: string | null
  }>
}

export interface AnalyticsStudent {
  student: { id: number; nickname: string }
  assigned: number | null
  started: number | null
  completed: number | null
  completionRate: number | null
  currentAverageScore: number | null
  averageImprovement: number | null
  dimensions: AnalyticsDimension[]
  cases: Array<{
    problemId: number
    title: string
    version: number
    firstScore: number | null
    latestScore: number | null
    delta: number | null
    attemptCount: number
    focusStage: string | null
    lastAssessedAt: string | null
  }>
  timeline: Array<{ attemptId: number; problemId: number; score: number; assessedAt: string | null }>
  learningPlan: { id: number; status: string; targetDimensionIds: string[]; dueAt: string } | null
  practiceMastery: Record<string, { averageScore: number; attemptCount: number }>
}

export interface AnalyticsKnowledge {
  classId: number
  className: string
  participantCount: number
  dueBacklog: number | null
  objectiveCorrectRate: number | null
  weakPoints: Array<{ pointCode: string; studentCount: number }>
  rankingsSuppressed: boolean
}
