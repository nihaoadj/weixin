import { ROUTES } from '@/platform/navigation'
import type { UserRole } from '@/types/domain'
import type { SessionPort } from '@/features/identity/domain/ports'

export function requireRole(session: SessionPort, expected: UserRole): boolean {
  if (session.getRole() === expected) return true
  uni.showToast({ title: '请使用正确身份登录', icon: 'none' })
  uni.reLaunch({ url: ROUTES.login })
  return false
}

export function logout(session: SessionPort): void {
  session.clearSession()
  uni.reLaunch({ url: ROUTES.login })
}
