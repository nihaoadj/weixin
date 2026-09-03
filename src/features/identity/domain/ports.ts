import type { SessionUser, UserRole } from '@/types/records'

export type RuntimeMode = 'demo' | 'api'

export interface SessionStoragePort {
  readSession(): SessionUser | null
  writeSession(user: SessionUser): void
  clearSession(): void
}

export interface SessionApiPort {
  invalidateApiSession(): void
  clearApiToken(): void
}

export interface SessionDependencies {
  storage: SessionStoragePort
  api: SessionApiPort
}

export interface SessionPort {
  saveSession(user: SessionUser): void
  getSession(): SessionUser | null
  getRole(): UserRole | null
  clearSession(): void
}
