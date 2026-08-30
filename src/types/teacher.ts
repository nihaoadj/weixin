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

export interface AnalyticsDimension {
  dimensionId: string
  label: string
  averageScore: number | null
  baselineScore?: number | null
  currentScore?: number | null
  delta?: number | null
  studentCount?: number
  rate?: number | null
}

export interface AnalyticsOverview {
  scope: { classId: number | null; className: string | null; dateFrom: string; dateTo: string }
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
  cases: Array<{ problemId: number; title: string; completed: number; assigned: number; averageScore: number | null }>
  students: Array<{
    studentId: number
    nickname: string
    completed: number
    assigned: number
    averageScore: number | null
  }>
}

export interface AnalyticsCase {
  problem: { id: number; title: string; version: number; slug?: string | null }
  eligiblePairs: number
  startedPairs: number
  completedPairs: number
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
  assigned: number
  started: number
  completed: number
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
