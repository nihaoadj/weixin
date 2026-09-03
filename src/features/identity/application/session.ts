import type { SessionDependencies, SessionPort } from '@/features/identity/domain/ports'
import type { SessionUser, UserRole } from '@/types/records'

export function createSessionService(dependencies: SessionDependencies): SessionPort {
  const { storage, api } = dependencies

  function getSession(): SessionUser | null {
    return storage.readSession()
  }

  return {
    saveSession(user: SessionUser): void {
      api.invalidateApiSession()
      storage.writeSession(user)
    },
    getSession,
    getRole(): UserRole | null {
      return getSession()?.role || null
    },
    clearSession(): void {
      api.clearApiToken()
      storage.clearSession()
    },
  }
}

let configuredSessionService: SessionPort | undefined

export function configureSessionService(dependencies: SessionDependencies): SessionPort {
  configuredSessionService = createSessionService(dependencies)
  return configuredSessionService
}

export function getSessionService(): SessionPort {
  if (!configuredSessionService) throw new Error('身份会话服务尚未装配')
  return configuredSessionService
}

export function saveSession(user: SessionUser): void {
  getSessionService().saveSession(user)
}

export function getSession(): SessionUser | null {
  return getSessionService().getSession()
}

export function getRole(): UserRole | null {
  return getSessionService().getRole()
}

export function clearSession(): void {
  getSessionService().clearSession()
}
