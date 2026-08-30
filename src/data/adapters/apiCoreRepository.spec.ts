import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearApiCache } from '@/services/apiClient'
import { ApiCoreRepository } from './apiCoreRepository'

describe('API core repository', () => {
  afterEach(() => {
    clearApiCache()
    vi.unstubAllEnvs()
  })

  it.each([1, 250])('uses one HTTP call for %i student questions', async (count) => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({
        statusCode: 200,
        data: Array.from({ length: count }, (_, id) => ({
          id,
          title: '题目',
          type: '医学常识',
          published_at: '2026-08-30',
          status: 'unanswered',
        })),
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
      return undefined as never
    })
    expect(await new ApiCoreRepository().getStudentQuestions()).toHaveLength(count)
    expect(uni.request).toHaveBeenCalledTimes(1)
  })

  it('uses direct detail routes instead of downloading resource lists', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      const url = String(options.url)
      const data = url.includes('/conversations/by-client/')
        ? {
            id: 1,
            client_id: 'conversation/a',
            student_id: 2,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            messages: [],
          }
        : {
            id: 3,
            conversation_id: 1,
            conversation_client_id: 'conversation/a',
            student_id: 2,
            student_name: '学生',
            status: 'pending_review',
            ai_score: 80,
            ai_summary: 'summary',
            messages: [],
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          }
      options.success?.({ statusCode: 200, data, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })
    const repository = new ApiCoreRepository()

    await expect(repository.findConversation('conversation/a')).resolves.toMatchObject({
      conversationId: 'conversation/a',
    })
    await expect(repository.findReport('conversation/a')).resolves.toMatchObject({ id: '3' })
    const urls = vi.mocked(uni.request).mock.calls.map(([options]) => String(options.url))
    expect(urls).toEqual([
      'https://api.example.com/conversations/by-client/conversation%2Fa',
      'https://api.example.com/reports/by-conversation/conversation%2Fa',
    ])
  })

  it('loads student answer states with one feed request', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({
        statusCode: 200,
        data: [
          {
            id: 7,
            type: '医学常识',
            title: '题目',
            description: '',
            published_at: '2026-01-01T00:00:00Z',
            status: 'answered',
          },
        ],
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
      return undefined as never
    })

    await expect(new ApiCoreRepository().getStudentQuestions()).resolves.toEqual([
      expect.objectContaining({ id: '7', status: 'answered' }),
    ])
    expect(uni.request).toHaveBeenCalledTimes(1)
    expect(vi.mocked(uni.request).mock.calls[0][0].url).toBe('https://api.example.com/student/questions')
  })
})
