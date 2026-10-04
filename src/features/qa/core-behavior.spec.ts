import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiContentRepository } from '@/features/content/infrastructure/apiContentRepository'
import { DemoContentRepository } from '@/features/content/infrastructure/demoContentRepository'
import { ApiQaRepository } from '@/features/qa/infrastructure/apiQaRepository'
import { DemoQaRepository } from '@/features/qa/infrastructure/demoQaRepository'
import { ApiReportRepository } from '@/features/reports/infrastructure/apiReportRepository'
import { DemoReportRepository } from '@/features/reports/infrastructure/demoReportRepository'
import type { ContentRepository } from '@/features/content/domain/ports'
import type { QaRepository } from '@/features/qa/domain/ports'
import type { ReportRepository } from '@/features/reports/domain/ports'
import type { Problem } from '@/types/records'
import { saveSession } from '@/features/identity/public'
import { clearApiCache } from '@/platform/http/apiClient'
import { mockHttp, now, respond } from '@/test/http'
import { upsertProblem as seedProblem, claimProblemOwner } from '@/features/content/infrastructure/demoProblemStore'

const conversation = {
  conversationId: 'conversation',
  messages: [{ id: '1', role: 'user' as const, content: '预览', timestamp: now }],
  createdAt: now,
  updatedAt: now,
}
const conversationDto = {
  id: 1,
  client_id: 'conversation',
  student_id: 1,
  created_at: now,
  updated_at: now,
  messages: [{ id: 1, role: 'user', content: '预览', created_at: now }],
}
const problem: Problem = {
  id: '1',
  title: '题目',
  description: '描述',
  type: '医学常识',
  target: 'all',
  targetIds: [],
  status: 'draft',
  time: now,
}
const login = (role: 'student' | 'teacher') =>
  saveSession({ openid: role, role, nickName: role, avatarUrl: '', createdAt: now })

type FeatureRepositories = {
  qa: QaRepository
  reports: ReportRepository
  content: ContentRepository
}

function createRepositories(mode: 'demo' | 'api'): FeatureRepositories {
  const content: ContentRepository = mode === 'api' ? new ApiContentRepository() : new DemoContentRepository()
  if (mode === 'api') return { qa: new ApiQaRepository(), reports: new ApiReportRepository(), content }

  return { qa: new DemoQaRepository(content), reports: new DemoReportRepository(), content }
}

function failHttp(status: number) {
  vi.mocked(uni.request).mockImplementation((options) => {
    respond(options, { detail: 'failure' }, status)
    return undefined as never
  })
}

describe.each(['demo', 'api'] as const)('%s feature repository contract', (mode) => {
  let repositories: FeatureRepositories
  beforeEach(() => {
    vi.stubEnv('VITE_APP_MODE', mode)
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
    repositories = createRepositories(mode)
    login('student')
  })
  afterEach(() => {
    clearApiCache()
    vi.unstubAllEnvs()
  })

  it('returns empty pages and undefined/null for absent resources', async () => {
    mockHttp((path) =>
      path.endsWith('/summaries')
        ? { items: [], total: 0, limit: 20, offset: 0, pending_count: 0, reviewed_count: 0 }
        : [],
    )
    expect(await repositories.qa.getConversations()).toEqual([])
    expect((await repositories.qa.getConversationSummaries(20, 0)).items).toEqual([])
    expect(await repositories.qa.getStudentQuestions()).toEqual([])
    login('teacher')
    const resources = await repositories.content.getProblems()
    if (mode === 'api') expect(resources).toEqual([])
    else expect(resources.every((item) => item.contentType === 'guided_case')).toBe(true)
    failHttp(404)
    expect(await repositories.content.findProblem('missing')).toBeUndefined()
    if (mode === 'api') {
      expect(await repositories.content.publishProblem('missing')).toBeNull()
      expect(await repositories.content.rejectProblem('missing')).toBeNull()
    } else {
      await expect(repositories.content.publishProblem('missing')).rejects.toMatchObject({
        code: 'RETIRED_FLOW',
        statusCode: 409,
      })
      await expect(repositories.content.rejectProblem('missing')).rejects.toMatchObject({
        code: 'RETIRED_FLOW',
        statusCode: 409,
      })
    }
    login('student')
    expect(await repositories.qa.findConversation('missing')).toBeUndefined()
    expect(await repositories.reports.findReport('missing')).toBeUndefined()
    expect(await repositories.qa.findStudentQuestion('missing')).toBeUndefined()
    expect(await repositories.qa.getQuestionThread('missing')).toBeUndefined()
  })

  it('keeps QA history independent from the retained read-only report history', async () => {
    mockHttp((path) =>
      path === '/conversations/summaries'
        ? {
            items: [
              {
                id: 1,
                client_id: 'conversation',
                message_preview: '预览',
                message_count: 1,
                created_at: now,
                updated_at: now,
                topic_codes: [],
              },
            ],
            total: 1,
            limit: 20,
            offset: 0,
          }
        : conversationDto,
    )
    await repositories.qa.upsertConversation(conversation)
    expect((await repositories.qa.findConversation('conversation'))?.messages).toHaveLength(1)
    expect((await repositories.qa.getConversationSummaries(20, 0)).items[0]).not.toHaveProperty('messages')
    expect((await repositories.qa.getConversationSummaries(20, 0)).items[0]?.reportStatus).toBeUndefined()
    expect('saveDraftReport' in repositories.reports).toBe(false)
    expect('submitReportForReview' in repositories.reports).toBe(false)
    expect('reviewReport' in repositories.reports).toBe(false)
  })

  it('rejects unauthorized writes before returning retired flow errors and hides old questions', async () => {
    failHttp(403)
    await expect(repositories.content.upsertProblem(problem)).rejects.toMatchObject({ code: 'FORBIDDEN' })
    login('teacher')
    claimProblemOwner(problem.id)
    seedProblem({ ...problem, status: '已发布' })
    vi.mocked(uni.request).mockImplementation((options) => {
      const path = new URL(String(options.url)).pathname
      respond(
        options,
        path === '/student/questions'
          ? []
          : {
              detail: {
                code:
                  path.startsWith('/student/questions/') || (path.endsWith('/thread') && options.method !== 'POST')
                    ? 'RESOURCE_NOT_FOUND'
                    : 'RETIRED_FLOW',
                message: '旧讨论题流程已退役',
              },
            },
        path === '/student/questions'
          ? 200
          : path.startsWith('/student/questions/') || (path.endsWith('/thread') && options.method !== 'POST')
            ? 404
            : 409,
      )
      return undefined as never
    })
    await expect(repositories.content.upsertProblem(problem)).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
    await expect(repositories.content.rejectProblem('1')).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
    await expect(repositories.content.publishProblem('1')).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
    login('student')
    const count = vi.mocked(uni.request).mock.calls.length
    expect(await repositories.qa.getStudentQuestions()).toEqual([])
    expect(vi.mocked(uni.request).mock.calls.length - count).toBe(mode === 'api' ? 1 : 0)
    await expect(
      repositories.qa.saveQuestionThread({ questionId: '1', messages: conversation.messages, updatedAt: now }),
    ).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
    expect(await repositories.qa.findStudentQuestion('1')).toBeUndefined()
    expect(await repositories.qa.getQuestionThread('1')).toBeUndefined()
  })
})

it('uses feature public APIs without a legacy aggregate facade', async () => {
  vi.stubEnv('VITE_APP_MODE', 'demo')
  vi.resetModules()
  const identity = await import('@/features/identity/public')
  const content = await import('@/features/content/public')
  const qa = await import('@/features/qa/public')
  const reports = await import('@/features/reports/public')
  const user = (role: 'student' | 'teacher') =>
    identity.saveSession({ openid: role, role, nickName: role, avatarUrl: '', createdAt: now })
  user('teacher')
  const viewProblem = { ...problem, status: '待审核' as const }
  const demoProblems = await import('@/features/content/infrastructure/demoProblemStore')
  demoProblems.claimProblemOwner(viewProblem.id)
  demoProblems.upsertProblem(viewProblem)
  expect((await content.getProblemsAsync()).every((item) => item.contentType === 'guided_case')).toBe(true)
  await expect(content.saveProblemsAsync([viewProblem])).rejects.toMatchObject({
    code: 'RETIRED_FLOW',
    statusCode: 409,
  })
  await expect(content.upsertProblemAsync(viewProblem)).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
  await expect(content.publishProblemAsync('1')).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
  await expect(content.rejectProblemAsync('1')).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
  expect(await content.findProblemAsync('1')).toBeUndefined()
  await expect(content.resetProblemsAsync()).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
  expect(demoProblems.findProblem('1')).toEqual(viewProblem)
  user('student')
  await qa.upsertConversationAsync(conversation)
  expect((await qa.findConversationAsync('conversation'))?.messages).toHaveLength(1)
  expect(await qa.getConversationsAsync()).toHaveLength(1)
  expect(await reports.findReportAsync('conversation')).toBeUndefined()
  expect(await reports.findReportByConversationAsync('conversation')).toBeUndefined()
  expect((await qa.getConversationSummariesAsync()).items[0]?.reportStatus).toBeUndefined()
  expect('saveDraftReportAsync' in reports).toBe(false)
  expect('submitReportForReviewAsync' in reports).toBe(false)
  expect('reviewReportAsync' in reports).toBe(false)
  expect(await qa.getStudentQuestionsAsync()).toEqual([])
  expect(await qa.findStudentQuestionAsync('1')).toBeUndefined()
  await expect(qa.saveQuestionThreadAsync({ questionId: '1', messages: [], updatedAt: now })).rejects.toMatchObject({
    code: 'RETIRED_FLOW',
    statusCode: 409,
  })
  expect(await qa.getQuestionThreadAsync('1')).toBeUndefined()
  vi.unstubAllEnvs()
})

it('does not silently overwrite API data or restore Demo seeds remotely', async () => {
  const content = new ApiContentRepository()
  await expect(content.saveProblems([])).rejects.toMatchObject({ code: 'UNSUPPORTED_OPERATION' })
  await expect(content.resetProblems()).rejects.toMatchObject({ code: 'UNSUPPORTED_OPERATION' })
  vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
  vi.mocked(uni.request).mockImplementation((options) => {
    respond(options, { detail: { code: 'RETIRED_FLOW', message: '旧讨论题流程已退役' } }, 409)
    return undefined as never
  })
  await expect(content.upsertProblem({ ...problem, id: 'new-local-id' })).rejects.toMatchObject({
    code: 'RETIRED_FLOW',
    statusCode: 409,
  })
  expect(vi.mocked(uni.request).mock.calls[0][0].method).toBe('POST')
  clearApiCache()
  vi.unstubAllEnvs()
})
