import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiContentRepository } from '@/features/content/infrastructure/apiContentRepository'
import { clearApiCache } from '@/platform/http/apiClient'
import { mockHttp, now } from '@/test/http'

const pendingCase = {
  id: 51,
  type: '病例分析',
  title: '独立教学病例',
  description: '用于验证独立病例的医学审核适配。',
  target: 'all',
  target_label: '全体学生',
  status: 'published',
  created_at: now,
  content_type: 'guided_case',
  slug: 'independent-review-case',
  medical_review_status: 'pending',
}

beforeEach(() => {
  vi.stubEnv('VITE_APP_MODE', 'api')
  vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
  clearApiCache()
})

afterEach(() => {
  vi.unstubAllEnvs()
  clearApiCache()
})

describe('independent case medical-review API adapter', () => {
  it('maps submit and reviewer decisions without using retired learning-plan ports', async () => {
    const content = new ApiContentRepository()
    const requests: Array<{ path: string; method: string | undefined; body: unknown }> = []
    mockHttp((path, options) => {
      requests.push({ path, method: options.method, body: options.data })
      return path.endsWith('/medical-review') ? { ...pendingCase, medical_review_status: 'approved' } : pendingCase
    })

    await expect(content.submitGuidedCaseForReviewAsync('independent/51')).resolves.toMatchObject({
      id: '51',
      contentType: 'guided_case',
      medicalReviewStatus: 'pending',
    })
    await expect(
      content.decideGuidedCaseReviewAsync('independent/51', 'approved', '证据链完整'),
    ).resolves.toMatchObject({ id: '51', medicalReviewStatus: 'approved' })

    expect(requests).toEqual([
      {
        path: '/problems/independent%2F51/medical-review/submit',
        method: 'POST',
        body: undefined,
      },
      {
        path: '/problems/independent%2F51/medical-review',
        method: 'POST',
        body: { decision: 'approved', comment: '证据链完整' },
      },
    ])
  })
})
