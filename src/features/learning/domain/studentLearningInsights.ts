export type StudentLearningInsightsActionKind = 'discussion' | 'route' | 'result'

export type StudentLearningInsightsAction = {
  kind: StudentLearningInsightsActionKind
  sessionId: string
  routeId?: string
  label: string
}

export type StudentLearningInsightsTrend = {
  periodStart: string
  periodEnd: string
  score: number | null
  sampleCount: number
}

export type StudentLearningInsightsWeakness = {
  targetType: 'knowledge' | 'reasoning'
  targetCode: string
  label: string
  occurrences: number
  masteryPercentage: number | null
}

export type StudentLearningInsightsDashboard = {
  dataBasis: 'learning_route_results' | 'synthetic_demo'
  periodStart: string
  periodEnd: string
  masteryScore: number | null
  masteryDelta: number | null
  masterySampleCount: number
  studyMinutes: number
  studyDurationBasis: 'recorded_reading'
  planCompletionRate: number | null
  testedKnowledgeCount: number
  aiDiagnosticCount: number
  statusLabel: string
  trend: StudentLearningInsightsTrend[]
  weaknesses: StudentLearningInsightsWeakness[]
  aiSummary: string
}

export type StudentLearningInsightsRecord = {
  id: string
  session: { id: string; topicLabel: string; caseTitle: string }
  summaryText: string
  updatedAt: string
  action: StudentLearningInsightsAction
}

export type StudentLearningInsightsPage = {
  summary: {
    dashboard: StudentLearningInsightsDashboard
    nextAction?: StudentLearningInsightsAction | null
  }
  items: StudentLearningInsightsRecord[]
  total: number
  limit: number
  offset: number
}

export interface StudentLearningInsightsPort {
  getStudentLearningInsights(limit?: number, offset?: number): Promise<StudentLearningInsightsPage>
}
