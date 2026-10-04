export type LearningRouteSourceKind = 'classroom' | 'autonomous'
export type LearningRouteScopeStatus = 'active' | 'inactive'
export type LearningRouteProgress = { completedSteps: number; totalSteps: number }
export type LearningRouteTestSummary = {
  id: string
  title: string
  questionCount: number
  generationState: string
  reviewState: string
  reviewKind: 'teacher' | 'ai_direct' | null
  canStart: boolean
  lockReason?: string
  claimExpiresAt?: string
  retryAllowed: boolean
}
export type LearningRouteSummary = {
  id: string
  title: string
  sourceKind: LearningRouteSourceKind
  scopeStatus: LearningRouteScopeStatus
  sessionLocator: string
  goalPointCodes: string[]
  status: string
  nextAction: string
  progress: LearningRouteProgress
  updatedAt: string
  testSummary: LearningRouteTestSummary
  resultId?: string
  generationState: string
  claimExpiresAt?: string
  retryAllowed: boolean
}
export type LearningRoutePage = { items: LearningRouteSummary[]; total: number; limit: number; offset: number }
export type LearningRouteStep = {
  id: string
  position: number
  kind: 'reading' | 'case'
  title: string
  goalPointCodes: string[]
  status: string
  caseId?: string
  completedAt?: string
}
export type LearningRouteDetail = {
  summary: LearningRouteSummary
  diagnosisSummary: Record<string, unknown>
  steps: LearningRouteStep[]
  testSummary: LearningRouteTestSummary
  canStartTest: boolean
  lockReasons: string[]
  routeVersion: number
}
export type LearningRouteGenerationReceipt = {
  routeId: string
  component: 'route' | 'test'
  generationState: string
  claimExpiresAt?: string
}
export type RouteReadingProgress = { leaseToken?: string; accumulatedSeconds: number; lastSeenAt?: string }
export type ReadingSource = {
  id: string
  title: string
  institution: string
  url?: string
  version?: string
  sourceType?: string
}
export type ReadingSection = { title: string; text: string }
export type LearningRouteReading = {
  routeId: string
  step: LearningRouteStep
  sources: ReadingSource[]
  aiGuide: string
  sections: ReadingSection[]
  learningPoints: string[]
  readingProgress: RouteReadingProgress
}
export type ReadingProgressAction = 'start' | 'heartbeat' | 'pause'
