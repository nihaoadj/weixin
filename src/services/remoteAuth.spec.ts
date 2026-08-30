import { afterEach, describe, expect, it, vi } from 'vitest'
import { getApiToken } from './apiClient'
import { syncDemoLoginWithBackend } from './remoteAuth'

describe('remote demo auth', () => {
  afterEach(() => vi.unstubAllEnvs())

  it('sends class membership and stores the returned token', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      expect(options.data).toMatchObject({ role: 'student', class_ids: ['demo_class_1'] })
      options.success?.({
        statusCode: 200,
        data: { access_token: 'fresh-token' },
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
      return undefined as never
    })

    await syncDemoLoginWithBackend({ role: 'student', openid: 's1', nickName: '学生', avatarUrl: '' })
    expect(getApiToken()).toBe('fresh-token')
  })
})
