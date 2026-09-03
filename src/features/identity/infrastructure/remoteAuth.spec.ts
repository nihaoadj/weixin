import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearApiCache, clearApiToken, getApiToken, saveApiToken } from '@/platform/http/apiClient'
import { isWechatMiniProgram, syncDemoLoginWithBackend, syncWechatLoginWithBackend } from '@/features/identity/public'

function mockWechatLogin(result: Promise<{ code?: string }>): void {
  Object.assign(uni, { login: vi.fn(() => result) })
}

function respondLogin(options: UniApp.RequestOptions, data: UniApp.RequestSuccessCallbackResult['data']): void {
  options.success?.({ statusCode: 200, data, header: {}, cookies: [], errMsg: 'request:ok' })
}

function loginResponse(role: 'student' | 'teacher' = 'student') {
  return {
    access_token: 'fresh-token',
    user: {
      id: 1,
      role,
      nickname: '学生',
      avatar_url: '',
      class_ids: [],
      permissions: ['report:read'],
      created_at: '2026-08-30T00:00:00Z',
    },
  }
}

describe('remote authentication', () => {
  afterEach(() => {
    clearApiToken()
    clearApiCache()
    vi.unstubAllEnvs()
  })

  it('exposes a platform capability boolean under the active compile target', () => {
    // Conditional compilation itself is verified by the H5/MP builds. This
    // unit assertion only protects the adapter contract from returning a
    // non-boolean value in the current target.
    expect(typeof isWechatMiniProgram()).toBe('boolean')
  })

  it('syncDemoLoginWithBackend sends student class membership and stores the returned token', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      expect(options.data).toMatchObject({ role: 'student', class_ids: ['demo_class_1'] })
      respondLogin(options, loginResponse())
      return undefined as never
    })

    await syncDemoLoginWithBackend({ role: 'student', openid: 's1', nickName: '学生', avatarUrl: '' })

    expect(getApiToken()).toBe('fresh-token')
  })

  it('syncDemoLoginWithBackend is a no-op in Demo mode and preserves an existing token', async () => {
    vi.stubEnv('VITE_APP_MODE', 'demo')
    saveApiToken('existing-token')

    await expect(
      syncDemoLoginWithBackend({ role: 'student', openid: 's1', nickName: '学生', avatarUrl: '' }),
    ).resolves.toEqual([])

    expect(uni.request).not.toHaveBeenCalled()
    expect(getApiToken()).toBe('existing-token')
  })

  it('syncDemoLoginWithBackend preserves an existing token when the API request fails', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    saveApiToken('existing-token')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.fail?.({ errMsg: 'network unavailable' })
      return undefined as never
    })

    await expect(
      syncDemoLoginWithBackend({ role: 'student', openid: 's1', nickName: '学生', avatarUrl: '' }),
    ).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    expect(getApiToken()).toBe('existing-token')
  })

  it('syncWechatLoginWithBackend saves a complete successful WeChat identity only after a valid response', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    mockWechatLogin(Promise.resolve({ code: 'wechat-code' }))
    vi.mocked(uni.request).mockImplementation((options) => {
      expect(options.data).toMatchObject({ code: 'wechat-code', requested_role: 'student' })
      respondLogin(options, {
        ...loginResponse(),
        user: { ...loginResponse().user, avatar_url: 'https://avatar.test/a.png' },
      })
      return undefined as never
    })

    await expect(
      syncWechatLoginWithBackend({ requestedRole: 'student', nickName: '学生', avatarUrl: '' }),
    ).resolves.toMatchObject({
      openid: 'api-user-1',
      role: 'student',
      avatarUrl: 'https://avatar.test/a.png',
      permissions: ['report:read'],
    })
    expect(getApiToken()).toBe('fresh-token')
  })

  it('syncWechatLoginWithBackend rejects outside API mode without invoking the WeChat SDK or HTTP', async () => {
    vi.stubEnv('VITE_APP_MODE', 'demo')
    saveApiToken('existing-token')
    mockWechatLogin(Promise.resolve({ code: 'unexpected-code' }))

    await expect(
      syncWechatLoginWithBackend({ requestedRole: 'student', nickName: '学生', avatarUrl: '' }),
    ).rejects.toThrow('微信登录仅适用于 API 模式')
    expect(uni.login).not.toHaveBeenCalled()
    expect(uni.request).not.toHaveBeenCalled()
    expect(getApiToken()).toBe('existing-token')
  })

  it('syncWechatLoginWithBackend preserves the existing token when WeChat returns no code', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    saveApiToken('existing-token')
    mockWechatLogin(Promise.resolve({}))

    await expect(
      syncWechatLoginWithBackend({ requestedRole: 'student', nickName: '学生', avatarUrl: '' }),
    ).rejects.toThrow('未获取到微信登录凭证')
    expect(uni.request).not.toHaveBeenCalled()
    expect(getApiToken()).toBe('existing-token')
  })

  it('syncWechatLoginWithBackend preserves the existing token when WeChat login is cancelled', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    saveApiToken('existing-token')
    mockWechatLogin(Promise.reject(new Error('login cancelled')))

    await expect(
      syncWechatLoginWithBackend({ requestedRole: 'student', nickName: '学生', avatarUrl: '' }),
    ).rejects.toThrow('login cancelled')
    expect(uni.request).not.toHaveBeenCalled()
    expect(getApiToken()).toBe('existing-token')
  })

  it('syncWechatLoginWithBackend preserves the existing token when the response DTO is invalid', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    saveApiToken('existing-token')
    mockWechatLogin(Promise.resolve({ code: 'wechat-code' }))
    vi.mocked(uni.request).mockImplementation((options) => {
      respondLogin(options, { ...loginResponse(), user: { ...loginResponse().user, role: 'unexpected-role' } })
      return undefined as never
    })

    await expect(
      syncWechatLoginWithBackend({ requestedRole: 'student', nickName: '学生', avatarUrl: '' }),
    ).rejects.toMatchObject({ code: 'CONTRACT_ERROR' })
    expect(getApiToken()).toBe('existing-token')
  })

  it('syncWechatLoginWithBackend preserves the existing token when the response has no user', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    saveApiToken('existing-token')
    mockWechatLogin(Promise.resolve({ code: 'wechat-code' }))
    vi.mocked(uni.request).mockImplementation((options) => {
      respondLogin(options, { access_token: 'fresh-token' })
      return undefined as never
    })

    await expect(
      syncWechatLoginWithBackend({ requestedRole: 'student', nickName: '学生', avatarUrl: '' }),
    ).rejects.toMatchObject({ code: 'CONTRACT_ERROR' })
    expect(getApiToken()).toBe('existing-token')
  })

  it('syncWechatLoginWithBackend rejects a student response for a teacher request without replacing the old token', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    saveApiToken('existing-token')
    mockWechatLogin(Promise.resolve({ code: 'wechat-code' }))
    vi.mocked(uni.request).mockImplementation((options) => {
      respondLogin(options, loginResponse('student'))
      return undefined as never
    })

    await expect(
      syncWechatLoginWithBackend({ requestedRole: 'teacher', nickName: '教师', avatarUrl: '' }),
    ).rejects.toThrow('当前微信账号尚未开通教师身份')
    expect(getApiToken()).toBe('existing-token')
  })
})
