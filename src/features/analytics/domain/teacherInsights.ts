export type TeacherInsightsSessionId = number | string

export interface TeacherInsightsFilters {
  classId?: number
  sessionId?: TeacherInsightsSessionId
  dateFrom?: string
  dateTo?: string
}

export interface TeacherInsightsStudentFilters extends TeacherInsightsFilters {
  classId: number
}

export interface TeacherInsightsMetricBasis {
  progress: 'published_route_cohort'
  results: 'completed_test_window'
  diagnoses: 'completed_diagnosis_window'
}

export interface TeacherInsightsScope {
  classId: number | null
  className: string | null
  classIds: number[]
  sessionId: TeacherInsightsSessionId | null
  dateFrom: string
  dateTo: string
  timezone: 'Asia/Shanghai'
  asOf: string
  metricBasis: TeacherInsightsMetricBasis
}

export interface TeacherInsightsCohortProgress {
  publishedRoutes: number
  completedTests: number
  completionRate: number | null
  gradingTests: number
}

export interface TeacherInsightsPeriodResults {
  completedTests: number
  averageScore: number | null
  formatCounts: Record<string, number>
}

export interface TeacherInsightsOverview {
  scope: TeacherInsightsScope
  cohort: TeacherInsightsCohortProgress
  periodResults: TeacherInsightsPeriodResults
  diagnosisCount: number
  studentCount: number
}

export interface TeacherInsightsDiscussionProgress {
  participated: number
  active: number
  completed: number
}

export interface TeacherInsightsDiscussion {
  participationId: TeacherInsightsSessionId
  sessionId: TeacherInsightsSessionId
  classId: number
  studentId: number
  phase: string
  status: string
  startedAt: string | null
  completedAt: string | null
}

export interface TeacherInsightsStudent {
  studentId: number
  studentName: string
  classIds: number[]
  cohort: TeacherInsightsCohortProgress
  periodResults: TeacherInsightsPeriodResults
  diagnosisCount: number
  lastCompletedAt: string | null
  discussionProgress?: TeacherInsightsDiscussionProgress
}

export interface TeacherInsightsStudentPage {
  scope: TeacherInsightsScope
  items: TeacherInsightsStudent[]
  total: number
  limit: number
  offset: number
}

export interface TeacherInsightsKnowledgeRow {
  pointCode: string
  correctCount: number
  objectiveCount: number
  invalidObjectiveCount: number
  accuracyRate: number | null
  shortAnswerCount: number
  invalidShortAnswerCount: number
  pointsAwarded: number
  pointsPossible: number
  shortAnswerScoreRate: number | null
}

export interface TeacherInsightsKnowledgePage {
  scope: TeacherInsightsScope
  items: TeacherInsightsKnowledgeRow[]
  resultCount: number
}

export interface TeacherInsightsFinding {
  code: string
  summary: string
}

export interface TeacherInsightsDiagnosis {
  participationId: TeacherInsightsSessionId
  sessionId: TeacherInsightsSessionId
  classId: number
  className: string
  studentId: number
  studentName: string
  completedAt: string
  knowledgeGapCodes: string[]
  reasoningIssueCodes: string[]
  knowledgeGaps: TeacherInsightsFinding[]
  reasoningIssues: TeacherInsightsFinding[]
}

export interface TeacherInsightsFindingGroup {
  code: string
  studentCount: number
  diagnosisCount: number
  lastCompletedAt: string
}

export interface TeacherInsightsDiagnosisPage {
  scope: TeacherInsightsScope
  items: TeacherInsightsDiagnosis[]
  total: number
  limit: number
  offset: number
  knowledgeGaps: TeacherInsightsFindingGroup[]
  reasoningIssues: TeacherInsightsFindingGroup[]
}

export interface TeacherInsightsResultSummary {
  resultId: string
  routeId: string
  classId: number
  sessionId: TeacherInsightsSessionId
  studentId: number
  score: number
  completedAt: string
  formatVersion: 'single_choice_v1' | 'mixed_v2'
}

export interface TeacherInsightsRouteProgress {
  routeId: string
  studentId: number
  classId: number
  sessionId: TeacherInsightsSessionId
  publishedAt: string
  resultId: string | null
  testGenerationState: string | null
  testReviewState: string | null
  attemptStatus: string | null
  completedSteps: number | null
  totalSteps: number | null
  readingSeconds: number | null
}

export interface TeacherInsightsStudentDetail {
  discussions?: TeacherInsightsDiscussion[]
  scope: TeacherInsightsScope
  summary: TeacherInsightsStudent
  routes: TeacherInsightsRouteProgress[]
  results: TeacherInsightsResultSummary[]
  diagnoses: TeacherInsightsDiagnosis[]
  knowledge: TeacherInsightsKnowledgeRow[]
}
