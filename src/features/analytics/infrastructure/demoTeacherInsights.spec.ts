import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { configureSessionReader } from '@/platform/session/context'
import { demoAnalyticsRepository } from './demoAnalyticsRepository'
import {
  configureDemoTeacherInsightsFacts,
  type DemoTeacherInsightsDiagnosisFact,
  type DemoTeacherInsightsFactsPort,
  type DemoTeacherInsightsRouteFact,
} from './demoTeacherInsights'

const teacher = { openid: 'demo_teacher', role: 'teacher' as const, nickName: '演示教师', avatarUrl: '', createdAt: '' }
const dateFrom = '2026-09-20'
const dateTo = '2026-09-22'

function route(
  input: Partial<DemoTeacherInsightsRouteFact> &
    Pick<DemoTeacherInsightsRouteFact, 'routeId' | 'classId' | 'sessionId' | 'studentId'>,
): DemoTeacherInsightsRouteFact {
  return {
    ...input,
    title: input.title ?? '课堂学习路线',
    className: input.className ?? (input.classId === 1 ? '炎症班' : '肿瘤班'),
    studentName: input.studentName ?? `学生${input.studentId}`,
    publishedAt: input.publishedAt ?? null,
    updatedAt: input.updatedAt ?? '2026-09-22T05:00:00.000Z',
    stepProgress: input.stepProgress ?? { completedSteps: 2, totalSteps: 2 },
    steps: input.steps ?? [],
    accumulatedReadingSeconds: input.accumulatedReadingSeconds ?? 120,
    test: input.test ?? {
      id: `test-${input.routeId}`,
      generationState: 'ready',
      reviewState: 'released',
      attemptStatus: input.result ? 'submitted' : null,
      resultId: input.result?.id ?? null,
    },
  }
}

const routeFacts: DemoTeacherInsightsRouteFact[] = [
  route({
    routeId: 'route-mixed',
    classId: 1,
    sessionId: 42,
    studentId: 1,
    publishedAt: '2026-09-20T03:00:00.000Z',
    result: {
      id: 'result-mixed',
      score: 0,
      correctCount: 0,
      questionCount: 4,
      submittedAt: '2026-09-22T03:00:00.000Z',
      formatVersion: 'mixed_v2',
      questions: [
        { questionType: 'single_choice', pointCode: 'point-single', selectedOption: 0, correctOption: 1 },
        {
          questionType: 'multiple_choice',
          pointCode: 'point-multi',
          selectedOptions: [0, 2],
          correctOptions: [2, 0],
        },
        { questionType: 'short_answer', pointCode: 'point-short', pointsAwarded: 15, pointsPossible: 30 },
        { questionType: 'single_choice', pointCode: 'point-invalid' },
      ],
    },
  }),
  route({
    routeId: 'route-grading',
    classId: 1,
    sessionId: 42,
    studentId: 2,
    publishedAt: '2026-09-20T04:00:00.000Z',
    test: {
      id: 'test-route-grading',
      generationState: 'ready',
      reviewState: 'released',
      attemptStatus: 'grading',
      resultId: null,
    },
  }),
  route({
    routeId: 'route-other-class',
    classId: 2,
    sessionId: 42,
    studentId: 4,
    publishedAt: '2026-09-20T04:00:00.000Z',
    result: {
      id: 'result-other-class',
      score: 100,
      correctCount: 1,
      questionCount: 1,
      submittedAt: '2026-09-20T05:00:00.000Z',
      formatVersion: 'single_choice_v1',
      questions: [{ questionType: 'single_choice', pointCode: 'private-point', selectedOption: 1, correctOption: 1 }],
    },
  }),
  route({
    routeId: 'route-legacy',
    classId: 1,
    sessionId: 43,
    studentId: 1,
    publishedAt: null,
    result: {
      id: 'result-legacy',
      score: 90,
      correctCount: 1,
      questionCount: 1,
      submittedAt: '2026-09-22T04:00:00.000Z',
      formatVersion: 'single_choice_v1',
      questions: [{ questionType: 'single_choice', pointCode: 'point-old', selectedOption: 1, correctOption: 1 }],
    },
  }),
]

const diagnosisFacts: DemoTeacherInsightsDiagnosisFact[] = [
  {
    participationId: 'demo-participation-1',
    sessionId: 'demo-pbl-1',
    classId: 1,
    className: '炎症班',
    studentId: 3,
    studentName: '学生3',
    completedAt: '2026-09-20T04:00:00.000Z',
    knowledgeGapCodes: ['point-single'],
    reasoningIssueCodes: ['evidence_reasoning'],
    knowledgeGaps: [{ code: 'point-single', summary: '机制解释需要补足组织学依据。' }],
    reasoningIssues: [{ code: 'evidence_reasoning', summary: '需要说明观察与推断之间的依据。' }],
  },
  {
    participationId: 88,
    sessionId: 44,
    classId: 2,
    className: '肿瘤班',
    studentId: 4,
    studentName: '学生4',
    completedAt: '2026-09-20T04:00:00.000Z',
    knowledgeGapCodes: ['private-point'],
    reasoningIssueCodes: [],
    knowledgeGaps: [{ code: 'private-point', summary: '其他班级诊断。' }],
    reasoningIssues: [],
  },
]

describe('T53 Demo teacher insights facts projection', () => {
  const readScope = vi.fn(async () => ({
    classes: [
      { id: 1, name: '炎症班', code: 'inflammation', status: 'active' },
      { id: 2, name: '肿瘤班', code: 'neoplasia', status: 'active' },
    ],
    students: [
      { id: 1, name: '学生1', classIds: [1] },
      { id: 2, name: '学生2', classIds: [1] },
      { id: 3, name: '学生3', classIds: [1] },
      { id: 4, name: '学生4', classIds: [2] },
    ],
  }))
  const readRoutes = vi.fn(async () => routeFacts)
  const readDiagnoses = vi.fn(async () => diagnosisFacts)
  const factsPort: DemoTeacherInsightsFactsPort = { readScope, readRoutes, readDiagnoses, readDiscussions: () => [] }

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-30T08:00:00.000Z'))
    configureSessionReader(() => teacher)
    readScope.mockClear()
    readRoutes.mockClear()
    readDiagnoses.mockClear()
    configureDemoTeacherInsightsFacts(factsPort)
  })

  afterEach(() => {
    configureSessionReader(() => null)
    configureDemoTeacherInsightsFacts({
      readScope: () => ({ classes: [], students: [] }),
      readRoutes: () => [],
      readDiagnoses: () => [],
      readDiscussions: () => [],
    })
    vi.useRealTimers()
  })

  it('includes unfinished discussions without routes and leaves undated historical counts unavailable', async () => {
    configureDemoTeacherInsightsFacts({
      ...factsPort,
      readDiscussions: () => [
        {
          participationId: 'current',
          sessionId: 10,
          classId: 1,
          studentId: 99,
          studentName: '历史学生',
          phase: 'hypothesis',
          status: 'active',
          startedAt: '2026-09-21T01:00:00Z',
          completedAt: null,
        },
        {
          participationId: 'outside',
          sessionId: 10,
          classId: 1,
          studentId: 99,
          studentName: '历史学生',
          phase: 'completed',
          status: 'completed',
          startedAt: '2026-08-01T01:00:00Z',
          completedAt: '2026-09-21T01:00:00Z',
        },
        {
          participationId: 'undated',
          sessionId: 10,
          classId: 1,
          studentId: 98,
          studentName: '缺日期学生',
          phase: 'evidence',
          status: 'active',
          startedAt: null,
          completedAt: null,
        },
        {
          participationId: 'foreign',
          sessionId: 11,
          classId: 999,
          studentId: 100,
          studentName: '其他班',
          phase: 'evidence',
          status: 'active',
          startedAt: '2026-09-21T01:00:00Z',
          completedAt: null,
        },
      ],
    })
    const page = await demoAnalyticsRepository.getTeacherInsightsStudents({ classId: 1, dateFrom, dateTo })
    expect(page.items.find((item) => item.studentId === 99)?.discussionProgress).toEqual({
      participated: 1,
      active: 1,
      completed: 0,
    })
    expect(page.items.find((item) => item.studentId === 98)?.discussionProgress).toBeUndefined()
    expect(page.items.some((item) => item.studentId === 100)).toBe(false)
    const overview = await demoAnalyticsRepository.getTeacherInsightsOverview({ classId: 1, dateFrom, dateTo })
    // Dated facts cover the original three students and the new unfinished participant;
    // an undated historical participation remains readable but cannot prove a period sample.
    expect(overview.studentCount).toBe(4)
    const detail = await demoAnalyticsRepository.getTeacherInsightsStudent(99, { classId: 1, dateFrom, dateTo })
    expect(detail.routes).toEqual([])
    expect(detail.discussions?.map((item) => item.participationId)).toEqual(['current'])
    expect(detail.discussions?.[0]).not.toHaveProperty('studentName')
    const unknown = await demoAnalyticsRepository.getTeacherInsightsStudent(98, { classId: 1, dateFrom, dateTo })
    expect(unknown.discussions?.[0].startedAt).toBeNull()
  })

  it('uses separate publish, completion, and diagnosis windows and retains valid zeroes', async () => {
    const overview = await demoAnalyticsRepository.getTeacherInsightsOverview({
      classId: 1,
      dateFrom,
      dateTo: '2026-09-20',
    })
    expect(overview).toMatchObject({
      scope: {
        classId: 1,
        className: '炎症班',
        classIds: [1],
        dateFrom,
        dateTo: '2026-09-20',
        timezone: 'Asia/Shanghai',
        metricBasis: {
          progress: 'published_route_cohort',
          results: 'completed_test_window',
          diagnoses: 'completed_diagnosis_window',
        },
      },
      cohort: { publishedRoutes: 2, completedTests: 1, completionRate: 50, gradingTests: 1 },
      periodResults: { completedTests: 0, averageScore: null, formatCounts: {} },
      diagnosisCount: 1,
      studentCount: 3,
    })
    expect(overview.scope.asOf).toBe('2026-09-30T08:00:00.000Z')

    const completedWindow = await demoAnalyticsRepository.getTeacherInsightsOverview({
      classId: 1,
      dateFrom: '2026-09-22',
      dateTo: '2026-09-22',
    })
    expect(completedWindow).toMatchObject({
      cohort: { publishedRoutes: 0, completedTests: 0, completionRate: null },
      periodResults: {
        completedTests: 2,
        averageScore: 45,
        formatCounts: { mixed_v2: 1, single_choice_v1: 1 },
      },
    })

    const knowledge = await demoAnalyticsRepository.getTeacherInsightsKnowledge({ classId: 1, dateFrom, dateTo })
    expect(knowledge).toMatchObject({ resultCount: 2 })
    expect(knowledge.items).toEqual(
      expect.arrayContaining([
        {
          pointCode: 'point-multi',
          correctCount: 1,
          objectiveCount: 1,
          invalidObjectiveCount: 0,
          accuracyRate: 100,
          shortAnswerCount: 0,
          invalidShortAnswerCount: 0,
          pointsAwarded: 0,
          pointsPossible: 0,
          shortAnswerScoreRate: null,
        },
        {
          pointCode: 'point-short',
          correctCount: 0,
          objectiveCount: 0,
          invalidObjectiveCount: 0,
          accuracyRate: null,
          shortAnswerCount: 1,
          invalidShortAnswerCount: 0,
          pointsAwarded: 15,
          pointsPossible: 30,
          shortAnswerScoreRate: 50,
        },
        {
          pointCode: 'point-invalid',
          correctCount: 0,
          objectiveCount: 0,
          invalidObjectiveCount: 1,
          accuracyRate: null,
          shortAnswerCount: 0,
          invalidShortAnswerCount: 0,
          pointsAwarded: 0,
          pointsPossible: 0,
          shortAnswerScoreRate: null,
        },
        {
          pointCode: 'point-old',
          correctCount: 1,
          objectiveCount: 1,
          invalidObjectiveCount: 0,
          accuracyRate: 100,
          shortAnswerCount: 0,
          invalidShortAnswerCount: 0,
          pointsAwarded: 0,
          pointsPossible: 0,
          shortAnswerScoreRate: null,
        },
      ]),
    )

    const students = await demoAnalyticsRepository.getTeacherInsightsStudents(
      { classId: 1, dateFrom, dateTo: '2026-09-20' },
      20,
      0,
    )
    expect(students.items.map((item) => item.studentId)).toEqual([1, 2, 3])
    expect(students.items.find((item) => item.studentId === 3)).toMatchObject({
      classIds: [1],
      cohort: { publishedRoutes: 0, completedTests: 0, completionRate: null },
      periodResults: { completedTests: 0, averageScore: null, formatCounts: {} },
    })
  })

  it('returns only authorized class/session facts and safe fixed-diagnosis summaries', async () => {
    const diagnostics = await demoAnalyticsRepository.getTeacherInsightsDiagnostics({
      classId: 1,
      sessionId: 'demo-pbl-1',
      dateFrom,
      dateTo: '2026-09-20',
    })
    expect(diagnostics).toMatchObject({
      scope: { classIds: [1], sessionId: 'demo-pbl-1' },
      total: 1,
      items: [
        {
          participationId: 'demo-participation-1',
          knowledgeGapCodes: ['point-single'],
          knowledgeGaps: [{ code: 'point-single', summary: '机制解释需要补足组织学依据。' }],
          reasoningIssues: [{ code: 'evidence_reasoning' }],
        },
      ],
      knowledgeGaps: [{ code: 'point-single', studentCount: 1, diagnosisCount: 1 }],
    })
    expect(JSON.stringify(diagnostics)).not.toContain('其他班级')

    readRoutes.mockClear()
    readDiagnoses.mockClear()
    await expect(demoAnalyticsRepository.getTeacherInsightsOverview({ classId: 99 })).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    expect(readRoutes).not.toHaveBeenCalled()
    expect(readDiagnoses).not.toHaveBeenCalled()
  })

  it('keeps student detail restricted to a class and includes roster members with no period activity', async () => {
    const detail = await demoAnalyticsRepository.getTeacherInsightsStudent(3, {
      classId: 1,
      dateFrom,
      dateTo: '2026-09-20',
    })
    expect(detail.summary).toMatchObject({
      studentId: 3,
      classIds: [1],
      cohort: { publishedRoutes: 0, completionRate: null },
      periodResults: { completedTests: 0, averageScore: null },
      diagnosisCount: 1,
    })
    expect(detail.routes).toEqual([])
    expect(detail.results).toEqual([])

    await expect(
      demoAnalyticsRepository.getTeacherInsightsStudent(4, {
        classId: 1,
        dateFrom,
        dateTo,
      }),
    ).rejects.toMatchObject({ code: 'RESOURCE_NOT_FOUND' })
  })

  it('validates teacher, dates, and positive pagination before reading route facts', async () => {
    await expect(
      demoAnalyticsRepository.getTeacherInsightsOverview({ classId: 1, dateFrom: '2026-02-30' }),
    ).rejects.toMatchObject({
      code: 'INVALID_DATE_RANGE',
    })
    await expect(demoAnalyticsRepository.getTeacherInsightsDiagnostics({ classId: 1 }, 101, 0)).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
    })
    expect(readScope).not.toHaveBeenCalled()
    expect(readRoutes).not.toHaveBeenCalled()

    configureSessionReader(() => ({ ...teacher, role: 'student' }))
    await expect(demoAnalyticsRepository.getTeacherInsightsOverview()).rejects.toMatchObject({ code: 'FORBIDDEN' })
    expect(readScope).not.toHaveBeenCalled()
  })
})
