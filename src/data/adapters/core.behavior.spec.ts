import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiCoreRepository } from './apiCoreRepository'
import { DemoCoreRepository } from './demoCoreRepository'
import type { CoreRepository } from '@/data/repositories/core'
import type { Problem } from '@/types/records'
import { saveSession } from '@/services/repository'
import { clearApiCache } from '@/services/apiClient'
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
function failHttp(status: number) {
  vi.mocked(uni.request).mockImplementation((options) => {
    respond(options, { detail: 'failure' }, status)
    return undefined as never
  })
}

describe.each(['demo', 'api'] as const)('%s core repository contract', (mode) => {
  let repository: CoreRepository
  beforeEach(() => {
    vi.stubEnv('VITE_APP_MODE', mode)
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
    repository = mode === 'api' ? new ApiCoreRepository() : new DemoCoreRepository()
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
    expect(await repository.getConversations()).toEqual([])
    expect((await repository.getConversationSummaries(20, 0)).items).toEqual([])
    expect(await repository.getReports()).toEqual([])
    expect((await repository.getReportSummaries(20, 0)).total).toBe(0)
    expect(await repository.getStudentQuestions()).toEqual([])
    login('teacher')
    expect(await repository.getProblems()).toEqual([])
    failHttp(404)
    expect(await repository.findProblem('missing')).toBeUndefined()
    expect(await repository.publishProblem('missing')).toBeNull()
    expect(await repository.rejectProblem('missing')).toBeNull()
    expect(await repository.reviewReport('missing', 80, '')).toBeNull()
    login('student')
    expect(await repository.findConversation('missing')).toBeUndefined()
    expect(await repository.findReport('missing')).toBeUndefined()
    expect(await repository.submitReportForReview('missing')).toBeNull()
    expect(await repository.findStudentQuestion('missing')).toBeUndefined()
    expect(await repository.getQuestionThread('missing')).toBeUndefined()
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
    await repository.upsertConversation(conversation)
    expect((await repository.saveDraftReport(draft)).status).toBe('draft')
    expect((await repository.submitReportForReview('conversation'))?.status).toBe('pending_review')
    expect((await repository.findConversation('conversation'))?.messages).toHaveLength(1)
    expect((await repository.getConversationSummaries(20, 0)).items[0]).not.toHaveProperty('messages')
    login('teacher')
    const summary = (await repository.getReportSummaries(20, 0)).items[0]
    expect(summary.status).toBe('pending_review')
    expect(summary).not.toHaveProperty('messages')
    expect((await repository.findReport(summary.id))?.messages).toHaveLength(1)
    expect((await repository.reviewReport(summary.id, 90, '反馈'))?.status).toBe('reviewed')
    login('student')
    failHttp(409)
    await expect(repository.submitReportForReview('conversation')).rejects.toMatchObject({ code: 'STATE_CONFLICT' })
  })
  it('rejects unauthorized writes and resolves answer state without per-question HTTP', async () => {
    failHttp(403)
    await expect(repository.upsertProblem(problem)).rejects.toMatchObject({ code: 'FORBIDDEN' })
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
    expect((await repository.upsertProblem(problem)).status).toBe('draft')
    expect((await repository.rejectProblem('1'))?.status).toBe('rejected')
    expect((await repository.publishProblem('1'))?.status).toBe('published')
    login('student')
    const count = vi.mocked(uni.request).mock.calls.length
    expect((await repository.getStudentQuestions())[0].status).toBe('unanswered')
    expect(vi.mocked(uni.request).mock.calls.length - count).toBe(mode === 'api' ? 1 : 0)
    await repository.saveQuestionThread({ questionId: '1', messages: conversation.messages, updatedAt: now })
    expect((await repository.findStudentQuestion('1'))?.status).toBe('answered')
    expect((await repository.getQuestionThread('1'))?.messages).toHaveLength(1)
  })
})

it('keeps legacy facade views localized and selects its adapter once', async () => {
  vi.stubEnv('VITE_APP_MODE', 'demo')
  vi.resetModules()
  const facade = await import('@/services/repositoryAsync')
  const local = await import('@/services/repository')
  const session = (role: 'student' | 'teacher') =>
    local.saveSession({ openid: role, role, nickName: role, avatarUrl: '', createdAt: now })
  session('teacher')
  const viewProblem = { ...problem, status: '待审核' as const }
  await facade.saveProblemsAsync([viewProblem])
  expect((await facade.getProblemsAsync())[0].status).toBe('待审核')
  expect((await facade.upsertProblemAsync(viewProblem)).status).toBe('待审核')
  expect((await facade.publishProblemAsync('1'))?.status).toBe('已发布')
  expect((await facade.rejectProblemAsync('1'))?.status).toBe('已拒绝')
  expect((await facade.findProblemAsync('1'))?.status).toBe('已拒绝')
  await facade.resetProblemsAsync()
  session('student')
  await facade.upsertConversationAsync(conversation)
  expect((await facade.findConversationAsync('conversation'))?.messages).toHaveLength(1)
  expect(await facade.getConversationsAsync()).toHaveLength(1)
  expect((await facade.saveDraftReportAsync(draft)).status).toBe('草稿')
  expect((await facade.findReportAsync('conversation'))?.status).toBe('草稿')
  expect((await facade.getReportsAsync())[0].status).toBe('草稿')
  expect((await facade.getConversationSummariesAsync()).items[0].reportStatus).toBe('草稿')
  expect((await facade.submitReportForReviewAsync('conversation'))?.status).toBe('待批阅')
  const questions = await facade.getStudentQuestionsAsync()
  if (questions[0]) {
    await facade.findStudentQuestionAsync(questions[0].id)
    await facade.saveQuestionThreadAsync({ questionId: questions[0].id, messages: [], updatedAt: now })
    expect(await facade.getQuestionThreadAsync(questions[0].id)).toBeTruthy()
  }
  session('teacher')
  const report = (await facade.getReportSummariesAsync()).items[0]
  expect((await facade.reviewReportAsync(report.id, 80, '反馈'))?.status).toBe('已批阅')
  vi.stubEnv('VITE_APP_MODE', 'api')
  expect(await facade.getReportsAsync()).toHaveLength(1)
  expect(uni.request).not.toHaveBeenCalled()
  vi.unstubAllEnvs()
})

it('does not silently overwrite API data or restore Demo seeds remotely', async () => {
  const repository = new ApiCoreRepository()
  await expect(repository.saveProblems([])).rejects.toMatchObject({ code: 'UNSUPPORTED_OPERATION' })
  await expect(repository.resetProblems()).rejects.toMatchObject({ code: 'UNSUPPORTED_OPERATION' })
  vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
  mockHttp(() => problemDto)
  expect((await repository.upsertProblem({ ...problem, id: 'new-local-id' })).id).toBe('1')
  expect(vi.mocked(uni.request).mock.calls[0][0].method).toBe('POST')
  clearApiCache()
  vi.unstubAllEnvs()
})
