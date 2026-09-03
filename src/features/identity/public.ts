import { getApplicationServices } from '@/bootstrap/wiring'
import type { SessionUser, UserRole } from '@/types/domain'

const session = () => getApplicationServices().session

export const clearSession = () => session().clearSession()
export const getRole = () => session().getRole()
export const getSession = () => session().getSession()
export const saveSession = (user: SessionUser) => session().saveSession(user)
export type { SessionPort } from '@/features/identity/domain/ports'
import { requireRole as guardRequireRole, logout as guardLogout } from '@/features/identity/presentation/authGuard'
export const requireRole = (expected: UserRole) => guardRequireRole(session(), expected)
export const logout = () => guardLogout(session())
export {
  isWechatMiniProgram,
  syncDemoLoginWithBackend,
  syncWechatLoginWithBackend,
} from '@/features/identity/infrastructure/remoteAuth'
export type { SessionUser, UserRole } from '@/types/domain'

export function isApiRuntime(): boolean {
  return getApplicationServices().mode === 'api'
}

export function isDemoRuntime(): boolean {
  return !isApiRuntime()
}
