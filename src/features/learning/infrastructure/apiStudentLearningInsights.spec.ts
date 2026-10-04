import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiStudentLearningInsightsRepository } from './apiStudentLearningInsights'

const http = vi.hoisted(() => ({ request: vi.fn(), response: undefined as unknown }))
vi.mock('@/platform/http/apiClient', () => ({ apiRequest: http.request }))

const dashboard = {
  data_basis: 'learning_route_results',
  period_start: '2026-09-28',
  period_end: '2026-10-04',
  mastery_score: 0,
  mastery_delta: null,
  mastery_sample_count: 1,
  study_minutes: 12,
  study_duration_basis: 'recorded_reading',
  plan_completion_rate: 0,
  tested_knowledge_count: 0,
  ai_diagnostic_count: 2,
  status_label: '本周完成 1 次最终测试',
  trend: [{ period_start: '2026-09-28', period_end: '2026-10-04', score: 0, sample_count: 1 }],
  weaknesses: [
    {
      target_type: 'knowledge',
      target_code: 'pathology.inflammation.acute',
      label: '急性炎症',
      occurrences: 2,
      mastery_percentage: 0,
    },
  ],
  ai_summary: '基于结构化学习证据。',
}
const page = {
  summary: {
    dashboard,
    next_action: { kind: 'result', session_id: 'pbl-1', route_id: 'route-1', label: '查看结果解析' },
  },
  items: [
    {
      id: 'pbl-1',
      session: { id: 'pbl-1', topic_label: '急性炎症', case_title: '课堂病例' },
      summary_text: '最终测试得分 0 分，可查看本次结果解析。',
      updated_at: '2026-09-30T09:00:00+08:00',
      action: { kind: 'result', session_id: 'pbl-1', route_id: 'route-1', label: '查看结果解析' },
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
}

beforeEach(() => {
  http.request.mockReset()
  http.request.mockImplementation(
    (options: { schema: { safeParse(value: unknown): { success: boolean; data?: unknown; error?: unknown } } }) => {
      const parsed = options.schema.safeParse(http.response)
      return parsed.success ? Promise.resolve(parsed.data) : Promise.reject(parsed.error)
    },
  )
})

describe('student learning insights API adapter', () => {
  it('maps the strict snake_case contract while preserving zero and null', async () => {
    http.response = page
    const repository = new ApiStudentLearningInsightsRepository()

    http.response = { ...page, limit: 10, offset: 5 }
    await expect(repository.getStudentLearningInsights(10, 5)).resolves.toMatchObject({
      summary: {
        dashboard: {
          dataBasis: 'learning_route_results',
          masteryScore: 0,
          masteryDelta: null,
          trend: [{ periodStart: '2026-09-28', score: 0, sampleCount: 1 }],
          weaknesses: [{ targetType: 'knowledge', targetCode: 'pathology.inflammation.acute', masteryPercentage: 0 }],
        },
        nextAction: { kind: 'result', sessionId: 'pbl-1', routeId: 'route-1' },
      },
      items: [
        { session: { id: 'pbl-1', topicLabel: '急性炎症', caseTitle: '课堂病例' }, action: { sessionId: 'pbl-1' } },
      ],
      limit: 10,
      offset: 5,
    })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        path: '/learning/student-insights',
        query: { limit: 10, offset: 5 },
      }),
    )
    expect(http.request.mock.calls[0][0]).not.toHaveProperty('cacheTtlMs')
  })

  it('requests fresh data each time and rejects unknown contract fields', async () => {
    http.response = page
    const repository = new ApiStudentLearningInsightsRepository()
    await repository.getStudentLearningInsights()
    await repository.getStudentLearningInsights()
    expect(http.request).toHaveBeenCalledTimes(2)

    http.response = { ...page, private_message: 'must not be accepted' }
    await expect(repository.getStudentLearningInsights()).rejects.toBeInstanceOf(Error)
  })

  it('propagates API errors without falling back to local Demo data', async () => {
    const failure = new Error('network unavailable')
    http.request.mockRejectedValueOnce(failure)

    await expect(new ApiStudentLearningInsightsRepository().getStudentLearningInsights()).rejects.toBe(failure)
  })
})
