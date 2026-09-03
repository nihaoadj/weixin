import { getApiBaseUrl, isApiMode } from '@/platform/runtime'
import { z } from 'zod'
import { storage, storageKeys } from '@/platform/storage/storage'
import { ROUTES } from '@/platform/navigation'
import { AppError } from '@/types/errors'

const TOKEN_KEY = storageKeys.apiToken
let handlingUnauthorized = false
let authEpoch = 0
let cacheEpoch = 0

interface CacheEntry {
  expiresAt: number
  path: string
  value: unknown
}

const responseCache = new Map<string, CacheEntry>()
const pendingRequests = new Map<string, { path: string; promise: Promise<unknown> }>()

function redirectExpiredSession(): void {
  if (handlingUnauthorized) return
  handlingUnauthorized = true
  for (const key of [storageKeys.user, storageKeys.role, storageKeys.openid, TOKEN_KEY]) storage.remove(key)
  clearApiCache()
  uni.showToast({ title: '登录已失效，请重新登录', icon: 'none' })
  uni.reLaunch({
    url: ROUTES.login,
    complete: () => {
      handlingUnauthorized = false
    },
  })
}

type QueryValue = string | number | boolean | undefined

export interface ApiRequestOptions<TBody = unknown, TResponse = unknown> {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  path: string
  query?: Record<string, QueryValue>
  body?: TBody
  auth?: boolean
  cacheTtlMs?: number
  invalidateCache?: string[]
  schema?: ResponseSchema<TResponse>
}

interface ResponseSchema<T> {
  safeParse(value: unknown): { success: true; data: T } | { success: false; error: unknown }
}

export function isRemoteApiEnabled(): boolean {
  return isApiMode()
}

export function encodePathSegment(value: string | number): string {
  return encodeURIComponent(String(value))
}

export function clearApiCache(pathPrefixes?: string[]): void {
  cacheEpoch += 1
  if (!pathPrefixes?.length) {
    responseCache.clear()
    pendingRequests.clear()
    return
  }
  for (const [key, entry] of responseCache) {
    if (pathPrefixes.some((prefix) => entry.path.startsWith(prefix))) responseCache.delete(key)
  }
  for (const [key, entry] of pendingRequests) {
    if (pathPrefixes.some((prefix) => entry.path.startsWith(prefix))) pendingRequests.delete(key)
  }
}

export function saveApiToken(token: string): void {
  storage.write(TOKEN_KEY, token, z.string())
  invalidateApiSession()
}

export function invalidateApiSession(): void {
  authEpoch += 1
  clearApiCache()
}

export function getApiToken(): string {
  return storage.read(TOKEN_KEY, z.string(), '')
}

export function clearApiToken(): void {
  storage.remove(TOKEN_KEY)
  authEpoch += 1
  clearApiCache()
}

function resolveError(data: unknown, statusCode: number): { code: string; message: string } {
  const statusCodes: Record<number, string> = {
    400: 'VALIDATION_ERROR',
    401: 'AUTH_REQUIRED',
    403: 'FORBIDDEN',
    404: 'RESOURCE_NOT_FOUND',
    409: 'STATE_CONFLICT',
    422: 'VALIDATION_ERROR',
  }
  const fallback = statusCodes[statusCode] || 'SERVICE_ERROR'
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail?: unknown }).detail
    if (detail && typeof detail === 'object') {
      const structured = detail as { code?: unknown; message?: unknown }
      return {
        code: typeof structured.code === 'string' ? structured.code : fallback,
        message: typeof structured.message === 'string' ? structured.message : `API 请求失败: ${statusCode}`,
      }
    }
    if (typeof detail === 'string') {
      return { code: fallback, message: detail }
    }
  }
  if (data && typeof data === 'object' && 'message' in data) {
    const message = (data as { message?: unknown }).message
    if (typeof message === 'string') return { code: fallback, message }
  }
  return { code: fallback, message: `API 请求失败: ${statusCode}` }
}

export function toApiError(data: unknown, statusCode: number): AppError {
  const resolved = resolveError(data, statusCode)
  return new AppError(resolved.message, { code: resolved.code, statusCode })
}

export function undefinedOnNotFound<T>(error: unknown): T | undefined {
  if (error instanceof AppError && error.statusCode === 404) return undefined
  throw error
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const baseUrl = getApiBaseUrl()
  if (!baseUrl) throw new AppError('未配置 VITE_API_BASE_URL', { code: 'API_CONFIG_ERROR' })
  const entries = Object.entries(query || {})
    .filter((entry): entry is [string, string | number | boolean] => entry[1] !== undefined)
    .sort(([a], [b]) => a.localeCompare(b))
  const suffix = entries.length
    ? `${path.includes('?') ? '&' : '?'}${entries
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
        .join('&')}`
    : ''
  return `${baseUrl}${path}${suffix}`
}

function decodeResponse<T>(data: unknown, schema?: ResponseSchema<T>): T {
  if (!schema) return data as T
  const parsed = schema.safeParse(data)
  if (parsed.success) return parsed.data
  throw new AppError('服务响应不符合数据契约', { code: 'CONTRACT_ERROR', cause: parsed.error })
}

export function apiRequest<TResponse, TBody = unknown>(
  options: ApiRequestOptions<TBody, TResponse>,
): Promise<TResponse> {
  const method = options.method || 'GET'
  let url: string
  try {
    url = buildUrl(options.path, options.query)
  } catch (error) {
    return Promise.reject(error)
  }
  const requestAuthEpoch = authEpoch
  const requestCacheEpoch = cacheEpoch
  const cacheKey = `${authEpoch}:${options.auth !== false}:${method}:${url}`
  const now = Date.now()
  if (method === 'GET' && options.cacheTtlMs) {
    const cached = responseCache.get(cacheKey)
    if (cached && cached.expiresAt > now) {
      try {
        return Promise.resolve(decodeResponse(cached.value, options.schema))
      } catch (error) {
        return Promise.reject(error)
      }
    }
    if (cached) responseCache.delete(cacheKey)
  }
  if (method === 'GET') {
    const pending = pendingRequests.get(cacheKey)
    if (pending) return pending.promise.then((data) => decodeResponse(data, options.schema))
  }

  const token = getApiToken()
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  if (options.auth !== false && token) header.Authorization = `Bearer ${token}`

  const request = new Promise<unknown>((resolve, reject) => {
    uni.request({
      url,
      method: method as UniApp.RequestOptions['method'],
      data: options.body as UniApp.RequestOptions['data'],
      header,
      timeout: 30000,
      success: (response: UniApp.RequestSuccessCallbackResult) => {
        if (requestAuthEpoch !== authEpoch) {
          reject(new AppError('会话已变更，请重新加载', { code: 'STALE_SESSION' }))
          return
        }
        if (response.statusCode >= 200 && response.statusCode < 300) {
          try {
            if (method !== 'GET') clearApiCache(options.invalidateCache)
            // Cache raw data; each consumer validates its own boundary, including deduplicated calls.
            decodeResponse(response.data, options.schema)
            if (method === 'GET' && options.cacheTtlMs && requestCacheEpoch === cacheEpoch) {
              if (responseCache.size >= 128) {
                const oldestKey = responseCache.keys().next()
                if (!oldestKey.done) responseCache.delete(oldestKey.value)
              }
              responseCache.set(cacheKey, {
                value: response.data,
                path: options.path,
                expiresAt: Date.now() + options.cacheTtlMs,
              })
            }
            resolve(response.data)
          } catch (error) {
            reject(error)
          }
          return
        }
        if (response.statusCode === 401 && options.auth !== false) {
          clearApiToken()
          redirectExpiredSession()
        }
        reject(toApiError(response.data, response.statusCode))
      },
      fail: (error: UniApp.GeneralCallbackResult) =>
        reject(new AppError(error.errMsg || 'API 服务不可用', { code: 'NETWORK_ERROR', cause: error })),
    })
  })
  if (method === 'GET') {
    pendingRequests.set(cacheKey, { path: options.path, promise: request })
    const cleanup = () => {
      if (pendingRequests.get(cacheKey)?.promise === request) pendingRequests.delete(cacheKey)
    }
    request.then(cleanup, cleanup)
  }
  return request.then((data) => decodeResponse(data, options.schema))
}

export { getApiBaseUrl }
