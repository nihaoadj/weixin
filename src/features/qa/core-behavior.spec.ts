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
const problemDto = {
  id: 1,
  title: '题目',
  description: '描述',
  type: '医学常识',
  target: 'all',
  target_label: '全体学生',
  status: 'draft',
  created_at: now,
}
const draft = { ...conversation, analysis: { errors: [], score: 80, summary: '摘要' } }
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

  const reportsRef: { current?: ReportRepository } = {}
  const qa = new DemoQaRepository(content, {
    getReports: () => reportsRef.current?.getReports() || Promise.resolve([]),
  })
  const reports = new DemoReportRepository(qa)
  reportsRef.current = reports
  return { qa, reports, content }
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
    expect(await repositories.reports.getReports()).toEqual([])
    expect((await repositories.reports.getReportSummaries(20, 0)).total).toBe(0)
    expect(await repositories.qa.getStudentQuestions()).toEqual([])
    login('teacher')
    expect(await repositories.content.getProblems()).toEqual([])
    failHttp(404)
    expect(await repositories.content.findProblem('missing')).toBeUndefined()
    expect(await repositories.content.publishProblem('missing')).toBeNull()
    expect(await repositories.content.rejectProblem('missing')).toBeNull()
    expect(await repositories.reports.reviewReport('missing', 80, '')).toBeNull()
    login('student')
    expect(await repositories.qa.findConversation('missing')).toBeUndefined()
    expect(await repositories.reports.findReport('missing')).toBeUndefined()
    expect(await repositories.reports.submitReportForReview('missing')).toBeNull()
    expect(await repositories.qa.findStudentQuestion('missing')).toBeUndefined()
    expect(await repositories.qa.getQuestionThread('missing')).toBeUndefined()
  })

  it('preserves report state transitions and summary/detail separation', async () => {
    let state = 'draft'
    const dto = () => ({
      id: 1,
      conversation_id: 1,
      conversation_client_id: 'conversation',
      student_id: 1,
      student_name: 'student',
      status: state,
      ai_score: 80,
      ai_summary: '摘要',
      messages: conversationDto.messages,
      created_at: now,
      updated_at: now,
    })
    mockHttp((path) => {
      if (path.endsWith('/submit')) state = 'pending_review'
      if (path.endsWith('/review')) state = 'reviewed'
      if (path === '/conversations/summaries')
        return {
          items: [
            {
              id: 1,
              client_id: 'conversation',
              message_preview: '预览',
              message_count: 1,
              report_status: state,
              created_at: now,
              updated_at: now,
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }
      if (path === '/reports/summaries')
        return {
          items: [{ ...dto(), message_preview: '预览', message_count: 1 }],
          total: 1,
          pending_count: 1,
          reviewed_count: 0,
          limit: 20,
          offset: 0,
        }
      return path.startsWith('/conversations') ? conversationDto : dto()
    })
    await repositories.qa.upsertConversation(conversation)
    expect((await repositories.reports.saveDraftReport(draft)).status).toBe('draft')
    expect((await repositories.reports.submitReportForReview('conversation'))?.status).toBe('pending_review')
    expect((await repositories.qa.findConversation('conversation'))?.messages).toHaveLength(1)
    expect((await repositories.qa.getConversationSummaries(20, 0)).items[0]).not.toHaveProperty('messages')
    login('teacher')
    const summary = (await repositories.reports.getReportSummaries(20, 0)).items[0]
    expect(summary.status).toBe('pending_review')
    expect(summary).not.toHaveProperty('messages')
    expect((await repositories.reports.findReport(summary.id))?.messages).toHaveLength(1)
    expect((await repositories.reports.reviewReport(summary.id, 90, '反馈'))?.status).toBe('reviewed')
    login('student')
    failHttp(409)
    await expect(repositories.reports.submitReportForReview('conversation')).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
    })
  })

  it('rejects unauthorized writes and resolves answer state without per-question HTTP', async () => {
    failHttp(403)
    await expect(repositories.content.upsertProblem(problem)).rejects.toMatchObject({ code: 'FORBIDDEN' })
    login('teacher')
    let answered = false
    mockHttp((path, options) => {
      if (path.endsWith('/thread')) {
        if (options.method === 'POST') answered = true
        return { question_id: 1, messages: conversationDto.messages, updated_at: now }
      }
      if (path === '/student/questions')
        return [{ ...problemDto, published_at: now, status: answered ? 'answered' : 'unanswered' }]
      if (path.startsWith('/student/questions/'))
        return { ...problemDto, published_at: now, status: answered ? 'answered' : 'unanswered' }
      return {
        ...problemDto,
        status: path.endsWith('/publish') ? 'published' : path.endsWith('/reject') ? 'rejected' : 'draft',
      }
    })
    expect((await repositories.content.upsertProblem(problem)).status).toBe('draft')
    expect((await repositories.content.rejectProblem('1'))?.status).toBe('rejected')
    expect((await repositories.content.publishProblem('1'))?.status).toBe('published')
    login('student')
    const count = vi.mocked(uni.request).mock.calls.length
    expect((await repositories.qa.getStudentQuestions())[0].status).toBe('unanswered')
    expect(vi.mocked(uni.request).mock.calls.length - count).toBe(mode === 'api' ? 1 : 0)
    await repositories.qa.saveQuestionThread({ questionId: '1', messages: conversation.messages, updatedAt: now })
    expect((await repositories.qa.findStudentQuestion('1'))?.status).toBe('answered')
    expect((await repositories.qa.getQuestionThread('1'))?.messages).toHaveLength(1)
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
  await content.saveProblemsAsync([viewProblem])
  expect((await content.getProblemsAsync())[0].status).toBe('待审核')
  expect((await content.upsertProblemAsync(viewProblem)).status).toBe('待审核')
  expect((await content.publishProblemAsync('1'))?.status).toBe('已发布')
  expect((await content.rejectProblemAsync('1'))?.status).toBe('已拒绝')
  expect((await content.findProblemAsync('1'))?.status).toBe('已拒绝')
  await content.resetProblemsAsync()
  user('student')
  await qa.upsertConversationAsync(conversation)
  expect((await qa.findConversationAsync('conversation'))?.messages).toHaveLength(1)
  expect(await qa.getConversationsAsync()).toHaveLength(1)
  expect((await reports.saveDraftReportAsync(draft)).status).toBe('草稿')
  expect((await reports.findReportAsync('conversation'))?.status).toBe('草稿')
  expect((await reports.getReportsAsync())[0].status).toBe('草稿')
  expect((await qa.getConversationSummariesAsync()).items[0].reportStatus).toBe('草稿')
  expect((await reports.submitReportForReviewAsync('conversation'))?.status).toBe('待批阅')
  const questions = await qa.getStudentQuestionsAsync()
  if (questions[0]) {
    await qa.findStudentQuestionAsync(questions[0].id)
    await qa.saveQuestionThreadAsync({ questionId: questions[0].id, messages: [], updatedAt: now })
    expect(await qa.getQuestionThreadAsync(questions[0].id)).toBeTruthy()
  }
  user('teacher')
  const report = (await reports.getReportSummariesAsync()).items[0]
  expect((await reports.reviewReportAsync(report.id, 80, '反馈'))?.status).toBe('已批阅')
  vi.unstubAllEnvs()
})

it('does not silently overwrite API data or restore Demo seeds remotely', async () => {
  const content = new ApiContentRepository()
  await expect(content.saveProblems([])).rejects.toMatchObject({ code: 'UNSUPPORTED_OPERATION' })
  await expect(content.resetProblems()).rejects.toMatchObject({ code: 'UNSUPPORTED_OPERATION' })
  vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
  mockHttp(() => problemDto)
  expect((await content.upsertProblem({ ...problem, id: 'new-local-id' })).id).toBe('1')
  expect(vi.mocked(uni.request).mock.calls[0][0].method).toBe('POST')
  clearApiCache()
  vi.unstubAllEnvs()
})
