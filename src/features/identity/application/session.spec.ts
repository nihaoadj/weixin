import { describe, expect, it, vi } from 'vitest'
import {
  clearSession,
  configureSessionService,
  createSessionService,
  getRole,
  getSession,
  getSessionService,
  saveSession,
} from './session'
import type { SessionDependencies } from '@/features/identity/domain/ports'
import type { SessionUser } from '@/types/records'

const user: SessionUser = {
  openid: 'student-1',
  role: 'student',
  nickName: '学生',
  avatarUrl: '',
  createdAt: '2026-08-31T00:00:00Z',
}

function dependencies(initial: SessionUser | null = null): SessionDependencies {
  let stored = initial
  return {
    storage: {
      readSession: vi.fn(() => stored),
      writeSession: vi.fn((value: SessionUser) => {
        stored = value
      }),
      clearSession: vi.fn(() => {
        stored = null
      }),
    },
    api: { invalidateApiSession: vi.fn(), clearApiToken: vi.fn() },
  }
}

describe('session application service', () => {
  it('invalidates API state before writes and clears token plus persisted identity on logout', () => {
    const value = dependencies()
    const service = createSessionService(value)

    expect(service.getSession()).toBeNull()
    expect(service.getRole()).toBeNull()
    service.saveSession(user)
    expect(value.api.invalidateApiSession).toHaveBeenCalledOnce()
    expect(value.storage.writeSession).toHaveBeenCalledWith(user)
    expect(service.getSession()).toEqual(user)
    expect(service.getRole()).toBe('student')

    service.clearSession()
    expect(value.api.clearApiToken).toHaveBeenCalledOnce()
    expect(value.storage.clearSession).toHaveBeenCalledOnce()
  })

  it('configures all public session wrappers to the same session port', () => {
    const value = dependencies(user)
    const configured = configureSessionService(value)

    expect(getSessionService()).toBe(configured)
    expect(getSession()).toEqual(user)
    expect(getRole()).toBe('student')
    saveSession({ ...user, role: 'teacher' })
    expect(value.storage.writeSession).toHaveBeenCalledWith({ ...user, role: 'teacher' })
    clearSession()
    expect(value.api.clearApiToken).toHaveBeenCalledOnce()
  })
})
