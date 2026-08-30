import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiCaseRepository } from './apiCaseRepository'
import { DemoCaseRepository } from './demoCaseRepository'
import { saveSession } from '@/services/repository'
import { clearApiCache } from '@/services/apiClient'
import { now, respond } from '@/test/http'

afterEach(() => {
  clearApiCache()
  vi.unstubAllEnvs()
})
describe.each(['demo', 'api'] as const)('%s case repository semantics', (mode) => {
  it('distinguishes missing optional reads from role and state errors', async () => {
    vi.stubEnv('VITE_APP_MODE', mode)
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
    const repository = mode === 'api' ? new ApiCaseRepository() : new DemoCaseRepository()
    let status = 404
    vi.mocked(uni.request).mockImplementation((options) => {
      respond(options, { detail: 'failure' }, status)
      return undefined as never
    })
    saveSession({ openid: 'student', role: 'student', nickName: '学生', avatarUrl: '', createdAt: now })
    expect(await repository.getCaseAttemptAsync('missing')).toBeUndefined()
    expect(await repository.getCaseAssessmentAsync('missing')).toBeUndefined()
    status = 403
    await expect(repository.cloneCaseVersionAsync('missing')).rejects.toMatchObject({ code: 'FORBIDDEN' })
    saveSession({ openid: 'author', role: 'teacher', nickName: '老师', avatarUrl: '', createdAt: now })
    if (mode === 'demo') {
      const draft = await repository.generateCaseDraftAsync({
        topic: '练习',
        learnerLevel: '本科',
        learningObjectives: ['学习'],
      })
      const saved = await repository.saveGuidedCaseAsync(draft)
      expect(saved.status).toBe('draft')
      await expect(repository.publishGuidedCaseAsync(saved.id)).rejects.toMatchObject({ code: 'STATE_CONFLICT' })
    } else {
      status = 409
      await expect(repository.publishGuidedCaseAsync('1')).rejects.toMatchObject({ code: 'STATE_CONFLICT' })
    }
  })
})
