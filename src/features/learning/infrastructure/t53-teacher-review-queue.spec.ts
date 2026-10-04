import { readTeacherTestFixtures } from '@/test/demoTeacherTestFixtures'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiLearningRoutes } from './apiLearningRoutes'

const http = vi.hoisted(() => ({ request: vi.fn(), response: undefined as unknown }))
vi.mock('@/platform/http/apiClient', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/platform/http/apiClient')>()),
  apiRequest: http.request,
  encodePathSegment: (id: string) => encodeURIComponent(id),
}))

const reviewRouteId = '10000000-0000-4000-8000-000000000005'
const reviewTestId = 'f0000000-0000-4000-8000-000000000005'
const timestamp = '2026-09-30T02:00:00Z'
const queueItem = {
  id: reviewTestId,
  route_id: reviewRouteId,
  title: '课堂最终测试',
  class_id: 1,
  class_name: '病理学演示班',
  session_id: 5,
  student_id: 1,
  student_name: '演示学生',
  generation_state: 'ready',
  review_state: 'needs_changes',
  updated_at: timestamp,
  can_review: true,
  can_retry: false,
  action_reason: 'REVIEW_READY',
}
const apiQueuePage = {
  items: [queueItem],
  counts: { pending_review: 2, needs_changes: 1, generation_failed: 1 },
  total: 1,
  limit: 10,
  offset: 4,
  as_of: timestamp,
}

const storageRouteKey = 'learningRoutes:t44-demo'
const storageVersionKey = `${storageRouteKey}:seed-version`
const routeUuid = (suffix: string) => `10000000-0000-4000-8000-${suffix.padStart(12, '0')}`
const testUuid = (suffix: string) => `f0000000-0000-4000-8000-${suffix.padStart(12, '0')}`
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
type QueueFixtureTestSummary = {
  id: string
  generationState: string
  reviewState: string
  retryAllowed: boolean
  claimExpiresAt?: string
}
type QueueFixtureState = {
  studentOpenid: string
  summary: {
    id: string
    title: string
    status: string
    scopeStatus: string
    generationState: string
    updatedAt: string
    resultId?: string
    testSummary: QueueFixtureTestSummary
  }
  detail: {
    summary: { id: string; title: string; testSummary: QueueFixtureTestSummary }
    testSummary: QueueFixtureTestSummary
  }
  teacherTest: {
    id: string
    routeId: string
    title: string
    sessionId: number
    studentId: number
    generationState: string
    reviewState: string
    reviewKind: 'teacher' | 'ai_direct' | null
    releasedAt?: string
  }
  test: {
    id: string
    attempt: null | { id: string; status: string; version: number; answers: Record<string, number>; savedAt?: string }
  }
  result?: unknown
}

async function loadDemoUser(openid: string, role: 'student' | 'teacher') {
  vi.resetModules()
  const [demo, identity] = await Promise.all([import('./demoLearningRoutes'), import('@/features/identity/public')])
  identity.saveSession({
    openid,
    role,
    nickName: role === 'teacher' ? '演示教师' : '演示学生',
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
  })
  return demo
}
const loadDemoTeacher = () => loadDemoUser('demo_teacher', 'teacher')

function cloneQueueCandidate(
  source: QueueFixtureState,
  suffix: string,
  reviewState: 'pending_review' | 'needs_changes',
  generationState: 'ready' | 'failed' = 'ready',
  claimExpiresAt?: string,
) {
  const candidate = clone(source)
  const routeId = routeUuid(suffix)
  const testId = testUuid(suffix)
  candidate.studentOpenid = 'demo_student_b'
  candidate.summary.id = routeId
  candidate.summary.title = `课堂路线 ${suffix}`
  candidate.summary.status = 'waiting_teacher'
  candidate.summary.scopeStatus = 'active'
  candidate.summary.generationState = 'published'
  candidate.summary.updatedAt = timestamp
  delete candidate.summary.resultId
  candidate.summary.testSummary.id = testId
  candidate.summary.testSummary.generationState = generationState
  candidate.summary.testSummary.reviewState = reviewState
  candidate.summary.testSummary.retryAllowed = generationState === 'failed'
  if (claimExpiresAt) candidate.summary.testSummary.claimExpiresAt = claimExpiresAt
  else delete candidate.summary.testSummary.claimExpiresAt
  candidate.detail.summary = clone(candidate.summary)
  candidate.detail.testSummary.id = testId
  candidate.detail.testSummary.generationState = generationState
  candidate.detail.testSummary.reviewState = reviewState
  candidate.detail.testSummary.retryAllowed = generationState === 'failed'
  if (claimExpiresAt) candidate.detail.testSummary.claimExpiresAt = claimExpiresAt
  else delete candidate.detail.testSummary.claimExpiresAt
  candidate.teacherTest.id = testId
  candidate.teacherTest.routeId = routeId
  candidate.teacherTest.title = candidate.summary.title
  candidate.teacherTest.sessionId = Number(suffix)
  candidate.teacherTest.studentId = 2
  candidate.teacherTest.generationState = generationState
  candidate.teacherTest.reviewState = reviewState
  candidate.teacherTest.reviewKind = null
  delete candidate.teacherTest.releasedAt
  candidate.test.id = testId
  candidate.test.attempt = null
  delete candidate.result
  return candidate
}

beforeEach(() => {
  http.request.mockReset()
  http.request.mockImplementation(async (options: { schema: { parse(value: unknown): unknown } }) =>
    options.schema.parse(http.response),
  )
  uni.removeStorageSync(storageRouteKey)
  uni.removeStorageSync(storageVersionKey)
})

describe('T53 teacher final-test review queue', () => {
  it('maps the strict queue page, sends filters, and propagates API errors without fallback', async () => {
    http.response = apiQueuePage
    const mapped = await apiLearningRoutes.getTeacherFinalTestReviewQueue({
      classId: 1,
      sessionId: 5,
      kind: 'needs_changes',
      limit: 10,
      offset: 4,
    })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        path: '/learning/teacher/final-test-review-queue',
        query: { class_id: 1, session_id: 5, kind: 'needs_changes', limit: 10, offset: 4 },
        cacheTtlMs: 0,
      }),
    )
    expect(mapped).toEqual({
      items: [
        {
          id: reviewTestId,
          routeId: reviewRouteId,
          title: '课堂最终测试',
          classId: 1,
          className: '病理学演示班',
          sessionId: 5,
          studentId: 1,
          studentName: '演示学生',
          generationState: 'ready',
          reviewState: 'needs_changes',
          updatedAt: timestamp,
          canReview: true,
          canRetry: false,
          actionReason: 'REVIEW_READY',
        },
      ],
      counts: { pendingReview: 2, needsChanges: 1, generationFailed: 1 },
      total: 1,
      limit: 10,
      offset: 4,
      asOf: timestamp,
    })

    http.response = { ...apiQueuePage, items: [{ ...queueItem, diagnosis_summary: { secret: true } }] }
    await expect(apiLearningRoutes.getTeacherFinalTestReviewQueue()).rejects.toThrow()
    const apiError = new Error('network unavailable')
    http.request.mockRejectedValueOnce(apiError)
    await expect(apiLearningRoutes.getTeacherFinalTestReviewQueue()).rejects.toBe(apiError)
  })

  it('counts only current actionable Demo scopes before kind filtering and pagination', async () => {
    const demo = await loadDemoTeacher()
    const initial = await demo.demoLearningRoutes.getTeacherFinalTestReviewQueue()
    expect(initial.items).toHaveLength(1)
    expect(initial.items[0]).toMatchObject({
      generationState: 'ready',
      reviewState: 'pending_review',
      canReview: true,
      canRetry: false,
      actionReason: 'REVIEW_READY',
    })
    const routes = uni.getStorageSync(storageRouteKey) as QueueFixtureState[]
    const pending = routes.find((route) => route.summary.id === routeUuid('5'))!
    routes.push(
      cloneQueueCandidate(pending, '11', 'needs_changes'),
      cloneQueueCandidate(pending, '12', 'pending_review', 'failed'),
      cloneQueueCandidate(pending, '13', 'pending_review', 'failed', '2999-01-01T00:00:00Z'),
    )
    const inProgress = cloneQueueCandidate(pending, '14', 'pending_review')
    inProgress.test.attempt = {
      id: routeUuid('14'),
      status: 'in_progress',
      version: 1,
      answers: {},
      savedAt: timestamp,
    }
    routes.push(inProgress)
    uni.setStorageSync(storageRouteKey, routes)

    const reloaded = await loadDemoTeacher()
    const all = await reloaded.demoLearningRoutes.getTeacherFinalTestReviewQueue({ limit: 2, offset: 0 })
    expect(all.counts).toEqual({ pendingReview: 1, needsChanges: 1, generationFailed: 1 })
    expect(all.total).toBe(3)
    expect(all.items).toHaveLength(2)
    expect(all.items.every((item) => item.canReview || item.canRetry)).toBe(true)
    const next = await reloaded.demoLearningRoutes.getTeacherFinalTestReviewQueue({ limit: 2, offset: 2 })
    expect(next.items).toHaveLength(1)
    expect([...all.items, ...next.items].map((item) => item.id)).toEqual(
      expect.arrayContaining([reviewTestId, testUuid('11'), testUuid('12')]),
    )
    const failures = await reloaded.demoLearningRoutes.getTeacherFinalTestReviewQueue({ kind: 'generation_failed' })
    expect(failures.total).toBe(1)
    expect(failures.items[0]).toMatchObject({
      generationState: 'generation_failed',
      canReview: false,
      canRetry: true,
      actionReason: 'GENERATION_FAILED',
    })
    const changes = await reloaded.demoLearningRoutes.getTeacherFinalTestReviewQueue({ kind: 'needs_changes' })
    expect(changes.total).toBe(1)
    expect(changes.counts).toEqual(all.counts)
    expect(changes.items[0]).toMatchObject({ reviewState: 'needs_changes', studentName: '演示学生（二）' })
    const scoped = await reloaded.demoLearningRoutes.getTeacherFinalTestReviewQueue({ classId: 1, sessionId: 11 })
    expect(scoped.total).toBe(1)
    expect(scoped.items[0].reviewState).toBe('needs_changes')
    await expect(reloaded.demoLearningRoutes.getTeacherFinalTestReviewQueue({ classId: 99 })).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
      statusCode: 404,
    })
    expect(initial.total).toBe(1)
  }, 15_000)

  it('returns empty reads without a Demo-owned class and rejects explicit cross-scope or non-teacher reads', async () => {
    const otherTeacher = await loadDemoUser('other_teacher', 'teacher')
    await expect(otherTeacher.demoLearningRoutes.getTeacherFinalTestReviewQueue()).resolves.toMatchObject({
      items: [],
      counts: { pendingReview: 0, needsChanges: 0, generationFailed: 0 },
      total: 0,
    })
    expect(otherTeacher.readDemoTeacherInsightsFacts()).toEqual([])
    await expect(otherTeacher.demoLearningRoutes.getTeacherFinalTestReviewQueue({ classId: 1 })).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
      statusCode: 404,
    })

    const student = await loadDemoUser('demo_student', 'student')
    await expect(student.demoLearningRoutes.getTeacherFinalTestReviewQueue()).rejects.toMatchObject({
      code: 'FORBIDDEN',
      statusCode: 403,
    })
    expect(() => student.readDemoTeacherInsightsFacts()).toThrow(
      expect.objectContaining({ code: 'FORBIDDEN', statusCode: 403 }),
    )
  })

  it('records seed and new-route publication time once, independent of later route edits', async () => {
    vi.useFakeTimers()
    try {
      const seedPublishedTime = new Date('2026-09-30T02:00:00Z')
      vi.setSystemTime(seedPublishedTime)
      const demo = await loadDemoTeacher()
      const seedBefore = demo.readDemoTeacherInsightsFacts().find((fact) => fact.routeId === routeUuid('5'))!
      expect(seedBefore.publishedAt).toBe(seedPublishedTime.toISOString())

      const nextActivityTime = new Date('2026-09-30T03:00:00Z')
      vi.setSystemTime(nextActivityTime)
      const teacherTest = await demo.demoLearningRoutes.getTeacherFinalTest(testUuid('5'))
      const edited = await demo.demoLearningRoutes.saveTeacherFinalTest(
        teacherTest.id,
        't53-publication-edit',
        teacherTest.version,
        teacherTest.questions,
        '更新时间不应重置发布时间',
      )
      const seedAfter = demo.readDemoTeacherInsightsFacts().find((fact) => fact.routeId === routeUuid('5'))!
      expect(edited.version).toBe(teacherTest.version + 1)
      expect(seedAfter.publishedAt).toBe(seedBefore.publishedAt)

      const sourceSessionId = 'demo-1893456000000'
      const created = await demo.ensureDemoRouteCompletion({
        sessionId: sourceSessionId,
        studentOpenid: 'demo_student_b',
        sourceKind: 'classroom',
        goalPointCodes: ['pathology.inflammation.acute'],
      })
      const createdFact = demo.readDemoTeacherInsightsFacts().find((fact) => fact.routeId === created.learningRouteId)!
      expect(createdFact.publishedAt).toBe(nextActivityTime.toISOString())
      expect(createdFact.sessionId).toBe(sourceSessionId)

      const reloaded = await loadDemoTeacher()
      const reloadedFact = reloaded
        .readDemoTeacherInsightsFacts()
        .find((fact) => fact.routeId === created.learningRouteId)!
      expect(reloadedFact.sessionId).toBe(sourceSessionId)
      const scopedQueue = await reloaded.demoLearningRoutes.getTeacherFinalTestReviewQueue({
        sessionId: sourceSessionId,
      })
      expect(scopedQueue.items.map((item) => item.id)).toEqual([created.finalTestId])
      expect(scopedQueue.items[0].sessionId).toBe(sourceSessionId)
      expect((await reloaded.readDemoTeacherClassroomRoutes(1, sourceSessionId)).map((item) => item.routeId)).toEqual([
        created.learningRouteId,
      ])
    } finally {
      vi.useRealTimers()
    }
  })

  it('keeps a legacy route with no stored publication time unknown instead of backfilling updatedAt', async () => {
    const demo = await loadDemoTeacher()
    await readTeacherTestFixtures(demo, 1)
    const routes = uni.getStorageSync(storageRouteKey) as Array<{
      summary: { id: string; updatedAt: string }
      publishedAt?: string
    }>
    const legacyRoute = routes.find((route) => route.summary.id === routeUuid('8'))!
    delete legacyRoute.publishedAt
    uni.setStorageSync(storageRouteKey, routes)
    const storedLegacyRoutes = clone(routes)

    const reloaded = await loadDemoTeacher()
    const legacyFact = reloaded.readDemoTeacherInsightsFacts().find((fact) => fact.routeId === routeUuid('8'))!
    expect(legacyFact.publishedAt).toBeNull()
    expect(legacyFact.updatedAt).toBeTruthy()
    expect(uni.getStorageSync(storageRouteKey)).toEqual(storedLegacyRoutes)
  })

  it('sets the first publication time when route retry publishes and preserves it on replay and refresh', async () => {
    vi.useFakeTimers()
    try {
      const demo = await loadDemoUser('demo_student', 'student')
      const routeId = routeUuid('10')
      const before = await demo.demoLearningRoutes.getLearningRoute(routeId)
      expect(before.summary.generationState).toBe('generation_failed')
      expect(
        (
          uni.getStorageSync(storageRouteKey) as Array<{
            summary: { id: string; updatedAt: string }
            publishedAt?: string
          }>
        ).find((route) => route.summary.id === routeId)?.publishedAt,
      ).toBeUndefined()

      const firstPublishTime = new Date('2026-09-30T04:00:00Z')
      vi.setSystemTime(firstPublishTime)
      await demo.demoLearningRoutes.retryLearningRouteGeneration(routeId, 'route', 't53-route-publish')
      let storedRoute = (
        uni.getStorageSync(storageRouteKey) as Array<{
          summary: { id: string; updatedAt: string }
          publishedAt?: string
        }>
      ).find((route) => route.summary.id === routeId)!
      expect(storedRoute.publishedAt).toBe(firstPublishTime.toISOString())

      const refreshedAt = new Date('2026-09-30T05:00:00Z')
      vi.setSystemTime(refreshedAt)
      const published = await demo.demoLearningRoutes.getLearningRoute(routeId)
      const readingStep = published.steps.find((step) => step.kind === 'reading')!
      const refreshed = await demo.demoLearningRoutes.completeRouteReading(readingStep.id, 't53-route-after-publish')
      expect(refreshed.steps.find((step) => step.id === readingStep.id)?.completedAt).toBe(refreshedAt.toISOString())
      storedRoute = (
        uni.getStorageSync(storageRouteKey) as Array<{
          summary: { id: string; updatedAt: string }
          publishedAt?: string
        }>
      ).find((route) => route.summary.id === routeId)!
      expect(storedRoute.publishedAt).toBe(firstPublishTime.toISOString())

      vi.setSystemTime(new Date('2026-09-30T06:00:00Z'))
      await demo.demoLearningRoutes.retryLearningRouteGeneration(routeId, 'route', 't53-route-publish')
      storedRoute = (
        uni.getStorageSync(storageRouteKey) as Array<{
          summary: { id: string; updatedAt: string }
          publishedAt?: string
        }>
      ).find((route) => route.summary.id === routeId)!
      expect(storedRoute.publishedAt).toBe(firstPublishTime.toISOString())
    } finally {
      vi.useRealTimers()
    }
  })

  it('projects read-only teacher insights without private result text and leaves stored Demo data unchanged', async () => {
    const demo = await loadDemoTeacher()
    await readTeacherTestFixtures(demo, 1)
    const before = clone(uni.getStorageSync(storageRouteKey))
    const facts = demo.readDemoTeacherInsightsFacts()
    const resultFact = facts.find((fact) => fact.routeId === routeUuid('8'))!
    const result = resultFact.result!
    expect(facts.find((fact) => fact.routeId === routeUuid('5'))).toMatchObject({
      className: '病理学演示班',
      stepProgress: { totalSteps: 2 },
      accumulatedReadingSeconds: 95,
      test: { generationState: 'ready', reviewState: 'pending_review', attemptStatus: null },
    })
    expect(result.questions[0]).toMatchObject({
      questionType: 'single_choice',
      pointCode: 'pathology.inflammation.acute',
      selectedOption: expect.any(Number),
      correctOption: expect.any(Number),
      pointsAwarded: expect.any(Number),
      pointsPossible: expect.any(Number),
    })
    expect(result).toMatchObject({ formatVersion: 'mixed_v2' })
    expect(resultFact.publishedAt).toEqual(expect.any(String))
    expect(JSON.stringify(facts)).not.toMatch(/selectedText|referenceAnswer|diagnosis|messages|publicScenario/)
    expect(JSON.stringify(facts)).not.toContain('尚不能判断。')
    expect(uni.getStorageSync(storageRouteKey)).toEqual(before)
  })
})
