import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiAnalyticsRepository } from './apiAnalyticsRepository'

const http = vi.hoisted(() => ({ request: vi.fn(), responses: [] as unknown[] }))
vi.mock('@/platform/http/apiClient', () => ({
  apiRequest: http.request,
  encodePathSegment: (value: string | number) => encodeURIComponent(String(value)),
}))

const scope = {
  class_id: 7,
  class_name: '炎症班',
  class_ids: [7, 8],
  session_id: null,
  date_from: '2026-09-20',
  date_to: '2026-09-21',
  timezone: 'Asia/Shanghai',
  as_of: '2026-09-21T12:00:00+00:00',
  metric_basis: {
    progress: 'published_route_cohort',
    results: 'completed_test_window',
    diagnoses: 'completed_diagnosis_window',
  },
}
const cohort = { published_routes: 2, completed_tests: 1, completion_rate: 50, grading_tests: 1 }
const periodResults = { completed_tests: 1, average_score: 0, format_counts: { mixed_v2: 1 } }
const student = {
  student_id: 11,
  student_name: '甲同学',
  class_ids: [7],
  cohort,
  period_results: periodResults,
  diagnosis_count: 1,
  last_completed_at: '2026-09-21T09:00:00+00:00',
  discussion_progress: { participated: 2, active: 1, completed: 1 },
}
const knowledge = {
  point_code: 'pathology.inflammation',
  correct_count: 0,
  objective_count: 1,
  invalid_objective_count: 0,
  accuracy_rate: 0,
  short_answer_count: 1,
  invalid_short_answer_count: 0,
  points_awarded: 0,
  points_possible: 30,
  short_answer_score_rate: 0,
}
const diagnosis = {
  participation_id: 51,
  session_id: 41,
  class_id: 7,
  class_name: '炎症班',
  student_id: 11,
  student_name: '甲同学',
  completed_at: '2026-09-20T07:00:00+00:00',
  knowledge_gap_codes: ['pathology.inflammation'],
  reasoning_issue_codes: ['evidence_reasoning'],
  knowledge_gaps: [{ code: 'pathology.inflammation', summary: '机制解释需要补充依据。' }],
  reasoning_issues: [{ code: 'evidence_reasoning', summary: '需要关联观察与结论。' }],
}
const result = {
  result_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  route_id: '11111111-1111-4111-8111-111111111111',
  class_id: 7,
  session_id: 41,
  student_id: 11,
  score: 0,
  completed_at: '2026-09-21T09:00:00+00:00',
  format_version: 'mixed_v2',
}
const route = {
  route_id: result.route_id,
  student_id: 11,
  class_id: 7,
  session_id: 41,
  published_at: '2026-09-20T07:00:00+00:00',
  result_id: result.result_id,
  test_generation_state: 'ready',
  test_review_state: 'released',
  attempt_status: 'submitted',
  completed_steps: 2,
  total_steps: 2,
  reading_seconds: 30,
}

const overview = {
  scope,
  cohort,
  period_results: periodResults,
  diagnosis_count: 1,
  student_count: 1,
}
const students = { scope, items: [student], total: 1, limit: 10, offset: 5 }
const detail = {
  scope,
  summary: student,
  discussions: [
    {
      participation_id: 52,
      session_id: 41,
      class_id: 7,
      student_id: 11,
      phase: 'hypothesis',
      status: 'active',
      started_at: '2026-09-20T07:00:00Z',
      completed_at: null,
    },
  ],
  routes: [route],
  results: [result],
  diagnoses: [diagnosis],
  knowledge: [knowledge],
}
const knowledgePage = { scope, items: [knowledge], result_count: 1 }
const diagnostics = {
  scope,
  items: [diagnosis],
  total: 1,
  limit: 20,
  offset: 0,
  knowledge_gaps: [
    { code: 'pathology.inflammation', student_count: 1, diagnosis_count: 1, last_completed_at: diagnosis.completed_at },
  ],
  reasoning_issues: [
    { code: 'evidence_reasoning', student_count: 1, diagnosis_count: 1, last_completed_at: diagnosis.completed_at },
  ],
}

beforeEach(() => {
  http.responses = [overview, students, detail, knowledgePage, diagnostics]
  http.request.mockReset()
  http.request.mockImplementation(
    (options: { schema: { safeParse(value: unknown): { success: boolean; data?: unknown; error?: unknown } } }) => {
      const response = http.responses.shift()
      const parsed = options.schema.safeParse(response)
      return parsed.success ? Promise.resolve(parsed.data) : Promise.reject(parsed.error)
    },
  )
})

describe('teacher insights API adapter', () => {
  it('maps all five strict snake_case read DTOs and sends their exact route and query fields', async () => {
    const filters = { classId: 7, sessionId: '41', dateFrom: '2026-09-20', dateTo: '2026-09-21' }
    await expect(apiAnalyticsRepository.getTeacherInsightsOverview(filters)).resolves.toMatchObject({
      scope: { classId: 7, classIds: [7, 8], timezone: 'Asia/Shanghai', dateFrom: filters.dateFrom },
      cohort: { completedTests: 1, completionRate: 50, gradingTests: 1 },
      periodResults: { completedTests: 1, averageScore: 0, formatCounts: { mixed_v2: 1 } },
    })
    await expect(apiAnalyticsRepository.getTeacherInsightsStudents(filters, 10, 5)).resolves.toMatchObject({
      items: [{ studentId: 11, studentName: '甲同学', periodResults: { averageScore: 0 } }],
      total: 1,
      limit: 10,
    })
    await expect(
      apiAnalyticsRepository.getTeacherInsightsStudent(11, { ...filters, classId: 7 }),
    ).resolves.toMatchObject({
      routes: [{ routeId: result.route_id, sessionId: 41, completedSteps: 2 }],
      results: [{ resultId: result.result_id, score: 0, formatVersion: 'mixed_v2' }],
      diagnoses: [{ knowledgeGaps: [{ code: 'pathology.inflammation', summary: '机制解释需要补充依据。' }] }],
      knowledge: [{ accuracyRate: 0, shortAnswerScoreRate: 0 }],
    })
    await expect(apiAnalyticsRepository.getTeacherInsightsKnowledge(filters)).resolves.toMatchObject({
      resultCount: 1,
      items: [{ objectiveCount: 1, shortAnswerCount: 1, pointsAwarded: 0 }],
    })
    await expect(apiAnalyticsRepository.getTeacherInsightsDiagnostics(filters, 10, 5)).resolves.toMatchObject({
      items: [{ participationId: 51, reasoningIssues: [{ code: 'evidence_reasoning' }] }],
      knowledgeGaps: [{ studentCount: 1, diagnosisCount: 1 }],
      total: 1,
      limit: 20,
    })

    expect(http.request.mock.calls.map(([options]) => options.path)).toEqual([
      '/analytics/teacher-insights/overview',
      '/analytics/teacher-insights/students',
      '/analytics/teacher-insights/students/11',
      '/analytics/teacher-insights/knowledge',
      '/analytics/teacher-insights/diagnostics',
    ])
    expect(http.request.mock.calls[1][0].query).toEqual({
      class_id: 7,
      session_id: 41,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      limit: 10,
      offset: 5,
    })
    expect(http.request.mock.calls[2][0].query).toEqual({
      class_id: 7,
      session_id: 41,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
    })
    expect(http.request.mock.calls.every(([options]) => !('cacheTtlMs' in options))).toBe(true)
  })

  it('rejects invalid response fields and propagates API failures without Demo fallback', async () => {
    http.responses = [{ ...overview, private_answer: 'not allowed' }]
    await expect(apiAnalyticsRepository.getTeacherInsightsOverview()).rejects.toBeInstanceOf(Error)

    const failure = new Error('service unavailable')
    http.request.mockRejectedValueOnce(failure)
    await expect(apiAnalyticsRepository.getTeacherInsightsOverview()).rejects.toBe(failure)
  })

  it('rejects Demo string session identifiers before they become invalid API query values', async () => {
    await expect(apiAnalyticsRepository.getTeacherInsightsOverview({ sessionId: 'demo-pbl-1' })).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
    })
    expect(http.request).not.toHaveBeenCalled()
  })
})
