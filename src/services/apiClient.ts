import { getApiBaseUrl, isApiMode } from '@/config/runtime'
import { ROUTES } from '@/services/navigation'
import { AppError } from '@/types/errors'

const TOKEN_KEY = 'apiAccessToken'
let handlingUnauthorized = false

function redirectExpiredSession(): void {
  if (handlingUnauthorized) return
  handlingUnauthorized = true
  for (const key of ['userInfo', 'role', 'openid', TOKEN_KEY]) uni.removeStorageSync(key)
  uni.showToast({ title: '登录已失效，请重新登录', icon: 'none' })
  uni.reLaunch({
    url: ROUTES.login,
    complete: () => {
      handlingUnauthorized = false
    },
  })
}

export interface ApiRequestOptions<TBody = unknown> {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  path: string
  body?: TBody
  auth?: boolean
}

export function isRemoteApiEnabled(): boolean {
  return isApiMode()
}

export function saveApiToken(token: string): void {
  uni.setStorageSync(TOKEN_KEY, token)
}

export function getApiToken(): string {
  return String(uni.getStorageSync(TOKEN_KEY) || '')
}

export function clearApiToken(): void {
  uni.removeStorageSync(TOKEN_KEY)
}

function resolveErrorMessage(data: unknown, statusCode: number): string {
  if (data && typeof data === 'object' && 'detail' in data) return String((data as { detail?: unknown }).detail)
  if (data && typeof data === 'object' && 'message' in data) return String((data as { message?: unknown }).message)
  return `API 请求失败: ${statusCode}`
}

export function toApiError(data: unknown, statusCode: number): AppError {
  return new AppError(resolveErrorMessage(data, statusCode), {
    code: statusCode === 401 ? 'AUTH_REQUIRED' : 'API_ERROR',
    statusCode,
  })
}

export function apiRequest<TResponse, TBody = unknown>(options: ApiRequestOptions<TBody>): Promise<TResponse> {
  const baseUrl = getApiBaseUrl()
  if (!baseUrl) return Promise.reject(new AppError('未配置 VITE_API_BASE_URL', { code: 'API_CONFIG_ERROR' }))

  const token = getApiToken()
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  if (options.auth !== false && token) header.Authorization = `Bearer ${token}`

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${baseUrl}${options.path}`,
      method: (options.method || 'GET') as UniApp.RequestOptions['method'],
      data: options.body as UniApp.RequestOptions['data'],
      header,
      timeout: 30000,
      success: (response: UniApp.RequestSuccessCallbackResult) => {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data as TResponse)
          return
        }
        if (response.statusCode === 401) {
          clearApiToken()
          if (options.auth !== false) redirectExpiredSession()
        }
        reject(toApiError(response.data, response.statusCode))
      },
      fail: (error: UniApp.GeneralCallbackResult) =>
        reject(new AppError(error.errMsg || 'API 服务不可用', { code: 'NETWORK_ERROR', cause: error })),
    })
  })
}

export { getApiBaseUrl }
