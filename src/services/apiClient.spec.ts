import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { apiRequest, clearApiCache, getApiToken, saveApiToken, toApiError } from './apiClient'

describe('api client', () => {
  afterEach(() => {
    clearApiCache()
    vi.unstubAllEnvs()
  })

  it('preserves status metadata in API errors', () => {
    const error = toApiError({ detail: '未登录' }, 401)
    expect(error.message).toBe('未登录')
    expect(error.code).toBe('AUTH_REQUIRED')
    expect(error.statusCode).toBe(401)
  })

  it('reads stable structured API errors', () => {
    const error = toApiError({ detail: { code: 'STATE_CONFLICT', message: '状态已变化' } }, 409)
    expect(error).toMatchObject({ code: 'STATE_CONFLICT', message: '状态已变化', statusCode: 409 })
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

  it('rejects a successful response that violates its runtime schema', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({ statusCode: 200, data: { ok: 'yes' }, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })

    await expect(apiRequest({ path: '/health', schema: z.object({ ok: z.boolean() }) })).rejects.toMatchObject({
      code: 'CONTRACT_ERROR',
    })
  })

  it('deduplicates concurrent GET requests and serves the short-lived cache', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    let success: UniApp.RequestOptions['success']
    vi.mocked(uni.request).mockImplementation((options) => {
      success = options.success
      return undefined as never
    })

    const first = apiRequest<{ ok: boolean }>({ path: '/cached', cacheTtlMs: 30_000 })
    const second = apiRequest<{ ok: boolean }>({ path: '/cached', cacheTtlMs: 30_000 })
    expect(uni.request).toHaveBeenCalledTimes(1)
    success?.({ statusCode: 200, data: { ok: true }, header: {}, cookies: [], errMsg: 'request:ok' })
    await expect(Promise.all([first, second])).resolves.toEqual([{ ok: true }, { ok: true }])
    await expect(apiRequest({ path: '/cached', cacheTtlMs: 30_000 })).resolves.toEqual({ ok: true })
    expect(uni.request).toHaveBeenCalledTimes(1)
  })

  it('invalidates matching GET cache entries after a mutation', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({ statusCode: 200, data: { ok: true }, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })

    await apiRequest({ path: '/reports/summaries', cacheTtlMs: 30_000 })
    await apiRequest({ path: '/reports/1/review', method: 'POST', invalidateCache: ['/reports'] })
    await apiRequest({ path: '/reports/summaries', cacheTtlMs: 30_000 })
    expect(uni.request).toHaveBeenCalledTimes(3)
  })
})
