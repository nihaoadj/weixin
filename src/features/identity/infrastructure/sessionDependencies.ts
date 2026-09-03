import { clearApiToken, invalidateApiSession } from '@/platform/http/apiClient'
import type { SessionDependencies } from '@/features/identity/domain/ports'
import type { RuntimeMode } from '@/features/identity/domain/ports'
import { createSessionStorage } from './sessionStorage'

export function createSessionDependencies(mode: RuntimeMode): SessionDependencies {
  return {
    storage: createSessionStorage(mode),
    api: { invalidateApiSession, clearApiToken },
  }
}
