import { z } from 'zod'
import { apiRequest } from '@/platform/http/apiClient'
import type {
  StudentLearningInsightsAction,
  StudentLearningInsightsDashboard,
  StudentLearningInsightsPage,
  StudentLearningInsightsPort,
  StudentLearningInsightsRecord,
} from '../domain/studentLearningInsights'

const actionSchema = z
  .object({
    kind: z.enum(['discussion', 'route', 'result']),
    session_id: z.string().min(1),
    route_id: z.string().min(1).nullable().optional(),
    label: z.string(),
  })
  .strict()
const trendSchema = z
  .object({
    period_start: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    period_end: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    score: z.number().min(0).max(100).nullable(),
    sample_count: z.number().int().nonnegative(),
  })
  .strict()
const weaknessSchema = z
  .object({
    target_type: z.enum(['knowledge', 'reasoning']),
    target_code: z.string(),
    label: z.string(),
    occurrences: z.number().int().positive(),
    mastery_percentage: z.number().min(0).max(100).nullable(),
  })
  .strict()
const dashboardSchema = z
  .object({
    data_basis: z.enum(['learning_route_results', 'synthetic_demo']),
    period_start: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    period_end: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    mastery_score: z.number().min(0).max(100).nullable(),
    mastery_delta: z.number().min(-100).max(100).nullable(),
    mastery_sample_count: z.number().int().nonnegative(),
    study_minutes: z.number().int().nonnegative(),
    study_duration_basis: z.literal('recorded_reading'),
    plan_completion_rate: z.number().min(0).max(100).nullable(),
    tested_knowledge_count: z.number().int().nonnegative(),
    ai_diagnostic_count: z.number().int().nonnegative(),
    status_label: z.string(),
    trend: z.array(trendSchema),
    weaknesses: z.array(weaknessSchema),
    ai_summary: z.string(),
  })
  .strict()
const recordSchema = z
  .object({
    id: z.string().min(1),
    session: z.object({ id: z.string().min(1), topic_label: z.string(), case_title: z.string() }).strict(),
    summary_text: z.string(),
    updated_at: z.string().min(1),
    action: actionSchema,
  })
  .strict()
export const apiStudentLearningInsightsSchema = z
  .object({
    summary: z.object({ dashboard: dashboardSchema, next_action: actionSchema.nullable().optional() }).strict(),
    items: z.array(recordSchema),
    total: z.number().int().nonnegative(),
    limit: z.number().int().positive(),
    offset: z.number().int().nonnegative(),
  })
  .strict()

type ApiAction = z.infer<typeof actionSchema>
type ApiDashboard = z.infer<typeof dashboardSchema>
type ApiRecord = z.infer<typeof recordSchema>
const mapAction = (value: ApiAction): StudentLearningInsightsAction => ({
  kind: value.kind,
  sessionId: value.session_id,
  routeId: value.route_id || undefined,
  label: value.label,
})
const mapDashboard = (value: ApiDashboard): StudentLearningInsightsDashboard => ({
  dataBasis: value.data_basis,
  periodStart: value.period_start,
  periodEnd: value.period_end,
  masteryScore: value.mastery_score,
  masteryDelta: value.mastery_delta,
  masterySampleCount: value.mastery_sample_count,
  studyMinutes: value.study_minutes,
  studyDurationBasis: value.study_duration_basis,
  planCompletionRate: value.plan_completion_rate,
  testedKnowledgeCount: value.tested_knowledge_count,
  aiDiagnosticCount: value.ai_diagnostic_count,
  statusLabel: value.status_label,
  trend: value.trend.map((item) => ({
    periodStart: item.period_start,
    periodEnd: item.period_end,
    score: item.score,
    sampleCount: item.sample_count,
  })),
  weaknesses: value.weaknesses.map((item) => ({
    targetType: item.target_type,
    targetCode: item.target_code,
    label: item.label,
    occurrences: item.occurrences,
    masteryPercentage: item.mastery_percentage,
  })),
  aiSummary: value.ai_summary,
})
const mapRecord = (value: ApiRecord): StudentLearningInsightsRecord => ({
  id: value.id,
  session: {
    id: value.session.id,
    topicLabel: value.session.topic_label,
    caseTitle: value.session.case_title,
  },
  summaryText: value.summary_text,
  updatedAt: value.updated_at,
  action: mapAction(value.action),
})

export class ApiStudentLearningInsightsRepository implements StudentLearningInsightsPort {
  async getStudentLearningInsights(limit = 20, offset = 0): Promise<StudentLearningInsightsPage> {
    const value = await apiRequest({
      method: 'GET',
      path: '/learning/student-insights',
      query: { limit, offset },
      schema: apiStudentLearningInsightsSchema,
    })
    return {
      summary: {
        dashboard: mapDashboard(value.summary.dashboard),
        nextAction: value.summary.next_action ? mapAction(value.summary.next_action) : undefined,
      },
      items: value.items.map(mapRecord),
      total: value.total,
      limit: value.limit,
      offset: value.offset,
    }
  }
}
