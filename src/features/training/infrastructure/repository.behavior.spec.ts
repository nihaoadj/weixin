import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiContentRepository } from '@/features/content/infrastructure/apiContentRepository'
import { DemoContentRepository } from '@/features/content/infrastructure/demoContentRepository'
import { demoCaseCatalog } from '@/features/content/infrastructure/demoCaseContentStore'
import { ApiTrainingRepository } from '@/features/training/infrastructure/apiTrainingRepository'
import { DemoTrainingRepository } from '@/features/training/infrastructure/demoTrainingRepository'
import { saveSession } from '@/features/identity/public'
import { clearApiCache } from '@/platform/http/apiClient'
import { now, respond } from '@/test/http'

afterEach(() => {
  clearApiCache()
  vi.unstubAllEnvs()
})
describe.each(['demo', 'api'] as const)('%s case repository semantics', (mode) => {
  it('distinguishes missing optional reads from role and state errors', async () => {
    vi.stubEnv('VITE_APP_MODE', mode)
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
    const content = mode === 'api' ? new ApiContentRepository() : new DemoContentRepository()
    const training =
      mode === 'api' ? new ApiTrainingRepository() : new DemoTrainingRepository({ findCaseDraft: demoCaseCatalog })
    let status = 404
    vi.mocked(uni.request).mockImplementation((options) => {
      respond(options, { detail: 'failure' }, status)
      return undefined as never
    })
    saveSession({ openid: 'student', role: 'student', nickName: '学生', avatarUrl: '', createdAt: now })
    expect(await training.getCaseAttemptAsync('missing')).toBeUndefined()
    expect(await training.getCaseAssessmentAsync('missing')).toBeUndefined()
    status = 403
    await expect(content.cloneCaseVersionAsync('missing')).rejects.toMatchObject({ code: 'FORBIDDEN' })
    saveSession({ openid: 'author', role: 'teacher', nickName: '老师', avatarUrl: '', createdAt: now })
    if (mode === 'demo') {
      const draft = await content.generateCaseDraftAsync({
        topic: '练习',
        learnerLevel: '本科',
        learningObjectives: ['学习'],
      })
      const saved = await content.saveGuidedCaseAsync(draft)
      expect(saved).toMatchObject({ status: 'published', medicalReviewStatus: 'not_required' })
      await expect(content.publishGuidedCaseAsync(saved.id)).rejects.toMatchObject({ code: 'RETIRED_FLOW' })
    } else {
      status = 409
      await expect(content.publishGuidedCaseAsync('1')).rejects.toMatchObject({ code: 'STATE_CONFLICT' })
    }
  })
})
