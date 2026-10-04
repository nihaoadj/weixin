import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearSession, saveSession } from '@/features/identity/public'
import { clearApiCache } from '@/platform/http/apiClient'
import { respond } from '@/test/http'
import { DemoQaRepository } from './demoQaRepository'
import { ApiQaRepository } from './apiQaRepository'
import * as history from './demoQuestionStore'

const login = (role: 'student' | 'teacher') =>
  saveSession({ openid: `t63-${role}`, role, nickName: role, avatarUrl: '', createdAt: new Date(0).toISOString() })
const thread = { questionId: 't63-old-question', messages: [], updatedAt: new Date(0).toISOString() }
const getProblems = vi.fn()
const repository = new DemoQaRepository({ getProblems })
afterEach(() => {
  clearApiCache()
  vi.unstubAllEnvs()
})

describe('T63 Demo discussion retirement', () => {
  it('hides retained historical threads and does not replace them or read the content repository', async () => {
    login('student')
    history.saveQuestionThread(thread)
    getProblems.mockClear()
    expect(await repository.getStudentQuestions()).toEqual([])
    expect(await repository.findStudentQuestion(thread.questionId)).toBeUndefined()
    expect(await repository.getQuestionThread(thread.questionId)).toBeUndefined()
    await expect(repository.saveQuestionThread({ ...thread, updatedAt: '2026-10-03T00:00:00Z' })).rejects.toMatchObject(
      { code: 'RETIRED_FLOW', statusCode: 409 },
    )
    expect(history.getQuestionThread(thread.questionId)).toEqual(thread)
    expect(getProblems).not.toHaveBeenCalled()
  })

  it('requires student authorization for every compatibility method', async () => {
    const actions = [
      () => repository.getStudentQuestions(),
      () => repository.findStudentQuestion('1'),
      () => repository.getQuestionThread('1'),
      () => repository.saveQuestionThread(thread),
    ]
    clearSession()
    for (const action of actions)
      await expect(action()).rejects.toMatchObject({ code: 'AUTH_REQUIRED', statusCode: 401 })
    login('teacher')
    for (const action of actions) await expect(action()).rejects.toMatchObject({ code: 'FORBIDDEN', statusCode: 403 })
  })

  it('matches API absent discussions and retired thread writes', async () => {
    login('student')
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
    vi.mocked(uni.request).mockImplementation((options) => {
      const list = String(options.url).endsWith('/student/questions')
      const write = options.method === 'POST'
      respond(
        options,
        list ? [] : { detail: { code: write ? 'RETIRED_FLOW' : 'RESOURCE_NOT_FOUND', message: '旧流程已退役' } },
        list ? 200 : write ? 409 : 404,
      )
      return undefined as never
    })
    for (const adapter of [repository, new ApiQaRepository()]) {
      expect(await adapter.getStudentQuestions()).toEqual([])
      expect(await adapter.findStudentQuestion('1')).toBeUndefined()
      expect(await adapter.getQuestionThread('1')).toBeUndefined()
      await expect(adapter.saveQuestionThread(thread)).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
    }
  })
})
