import { clearSession, getRole } from '@/services/repository'
import { clearApiToken } from '@/services/apiClient'
import { ROUTES } from '@/services/navigation'
import type { UserRole } from '@/types/domain'

export function requireRole(expected: UserRole): boolean {
  if (getRole() === expected) return true
  uni.showToast({ title: '请使用正确身份登录', icon: 'none' })
  uni.reLaunch({ url: ROUTES.login })
  return false
}

export function logout(): void {
  clearSession()
  clearApiToken()
  uni.reLaunch({ url: ROUTES.login })
}
