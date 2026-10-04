import { ROUTES } from '@/platform/navigation'
import type { UserRole } from '@/types/domain'

interface SessionActions {
  getRole(): UserRole | null
  clearSession(): void
}

export function requireRole(session: SessionActions, expected: UserRole): boolean {
  if (session.getRole() === expected) return true
  uni.showToast({ title: '请使用正确身份登录', icon: 'none' })
  uni.reLaunch({ url: ROUTES.login })
  return false
}

export function logout(session: SessionActions): void {
  session.clearSession()
  uni.reLaunch({ url: ROUTES.login })
}
