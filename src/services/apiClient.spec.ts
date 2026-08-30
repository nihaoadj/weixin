import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, getApiToken, saveApiToken, toApiError } from './apiClient'

describe('api client', () => {
  afterEach(() => vi.unstubAllEnvs())

  it('preserves status metadata in API errors', () => {
    const error = toApiError({ detail: '未登录' }, 401)
    expect(error.message).toBe('未登录')
    expect(error.code).toBe('AUTH_REQUIRED')
    expect(error.statusCode).toBe(401)
  })

  it('adds bearer auth and resolves successful data', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    saveApiToken('token-1')
    vi.mocked(uni.request).mockImplementation((options) => {
      expect(options.header).toMatchObject({ Authorization: 'Bearer token-1' })
      options.success?.({ statusCode: 200, data: { ok: true }, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })

    await expect(apiRequest<{ ok: boolean }>({ path: '/health' })).resolves.toEqual({ ok: true })
  })

  it('clears a stale token after a 401 response', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    saveApiToken('stale')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({ statusCode: 401, data: { detail: 'expired' }, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })

    await expect(apiRequest({ path: '/reports' })).rejects.toMatchObject({ statusCode: 401 })
    expect(getApiToken()).toBe('')
  })
})
