import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import {
  apiRequest,
  clearApiCache,
  clearApiToken,
  encodePathSegment,
  getApiToken,
  saveApiToken,
  toApiError,
} from './apiClient'
import { clearSession, saveSession } from './repository'
import { mockHttp, now, respond } from '@/test/http'

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
  clearApiCache()
})
afterEach(() => {
  clearApiCache()
  vi.unstubAllEnvs()
  vi.useRealTimers()
})

describe('transport concurrency and privacy', () => {
  it('expires cache by TTL and clears all resources on logout', async () => {
    vi.useFakeTimers()
    mockHttp(() => ({ value: 1 }))
    const options = { path: '/reports/1', cacheTtlMs: 30_000, schema: z.object({ value: z.number() }) }
    await apiRequest(options)
    await apiRequest(options)
    expect(uni.request).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(30_001)
    await apiRequest(options)
    expect(uni.request).toHaveBeenCalledTimes(2)
    clearSession()
    await apiRequest(options)
    expect(uni.request).toHaveBeenCalledTimes(3)
  })
  it('does not dedupe a refreshed read against a stale in-flight read after mutation', async () => {
    const requests: UniApp.RequestOptions[] = []
    vi.mocked(uni.request).mockImplementation((options) => {
      requests.push(options)
      return undefined as never
    })
    const first = apiRequest({ path: '/reports/1', cacheTtlMs: 30_000 })
    const other = apiRequest({ path: '/problems/1', cacheTtlMs: 30_000 })
    respond(requests[1], { revision: 1 })
    await other
    const write = apiRequest({ path: '/reports/1/review', method: 'POST', invalidateCache: ['/reports'] })
    respond(requests[2], { ok: true })
    await write
    const refreshed = apiRequest({ path: '/reports/1', cacheTtlMs: 30_000 })
    expect(requests).toHaveLength(4)
    respond(requests[3], { revision: 2 })
    await refreshed
    respond(requests[0], { revision: 1 })
    await first
    expect(await apiRequest({ path: '/reports/1', cacheTtlMs: 30_000 })).toEqual({ revision: 2 })
    await apiRequest({ path: '/problems/1', cacheTtlMs: 30_000 })
    expect(requests).toHaveLength(4)
  })
  it('invalidates even when a successful mutation response has an invalid contract', async () => {
    mockHttp(() => ({ value: 1 }))
    await apiRequest({ path: '/reports', cacheTtlMs: 30_000 })
    await expect(
      apiRequest({ path: '/reports', method: 'POST', schema: z.string(), invalidateCache: ['/reports'] }),
    ).rejects.toMatchObject({ code: 'CONTRACT_ERROR' })
    await apiRequest({ path: '/reports', cacheTtlMs: 30_000 })
    expect(uni.request).toHaveBeenCalledTimes(3)
  })
  it('rejects results from an old login without clearing a newer token', async () => {
    let request: UniApp.RequestOptions | undefined
    vi.mocked(uni.request).mockImplementation((options) => {
      request = options
      return undefined as never
    })
    saveApiToken('old')
    const pending = apiRequest({ path: '/reports', cacheTtlMs: 30_000 })
    saveApiToken('new')
    if (!request) throw new Error('request missing')
    respond(request, { detail: 'expired' }, 401)
    await expect(pending).rejects.toMatchObject({ code: 'STALE_SESSION' })
    expect(getApiToken()).toBe('new')
    expect(uni.reLaunch).not.toHaveBeenCalled()
    const next = apiRequest({ path: '/reports' })
    saveSession({ openid: 'different', role: 'student', nickName: '学生', avatarUrl: '', createdAt: now })
    respond(request, [])
    await expect(next).rejects.toMatchObject({ code: 'STALE_SESSION' })
    clearApiToken()
  })
  it('validates each consumer of cached/deduplicated data', async () => {
    let request: UniApp.RequestOptions | undefined
    vi.mocked(uni.request).mockImplementation((options) => {
      request = options
      return undefined as never
    })
    const first = apiRequest({ path: '/shared', schema: z.object({ value: z.number() }), cacheTtlMs: 30_000 })
    const second = apiRequest({ path: '/shared', schema: z.string() })
    if (!request) throw new Error('request missing')
    respond(request, { value: 1 })
    await expect(first).resolves.toEqual({ value: 1 })
    await expect(second).rejects.toMatchObject({ code: 'CONTRACT_ERROR' })
    await expect(apiRequest({ path: '/shared', cacheTtlMs: 30_000, schema: z.string() })).rejects.toMatchObject({
      code: 'CONTRACT_ERROR',
    })
    expect(uni.request).toHaveBeenCalledTimes(1)
  })
  it('encodes URL parts and normalizes network/config/legacy errors', async () => {
    mockHttp(() => ({}))
    await apiRequest({
      path: `/items/${encodePathSegment('a/b ?')}`,
      query: { z: 'a&b', a: false, missing: undefined },
      auth: false,
    })
    expect(vi.mocked(uni.request).mock.calls[0][0]).toMatchObject({
      url: 'https://example.test/items/a%2Fb%20%3F?a=false&z=a%26b',
      timeout: 30000,
    })
    await apiRequest({ path: '/items?first=1', query: { next: 2 } })
    expect(toApiError({ detail: [] }, 422).code).toBe('VALIDATION_ERROR')
    expect(toApiError({ message: 'old error' }, 500).message).toBe('old error')
    expect(toApiError(null, 503).code).toBe('SERVICE_ERROR')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.fail?.({ errMsg: 'timeout' })
      return undefined as never
    })
    await expect(apiRequest({ path: '/fail' })).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    vi.stubEnv('VITE_API_BASE_URL', '')
    await expect(apiRequest({ path: '/fail' })).rejects.toMatchObject({ code: 'API_CONFIG_ERROR' })
  })
})
