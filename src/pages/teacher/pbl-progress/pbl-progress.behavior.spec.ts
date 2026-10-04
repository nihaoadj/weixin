import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ClassroomProgressPage from './pbl-progress.vue'

const state = vi.hoisted(() => ({
  load: undefined as undefined | ((query: Record<string, string>) => void),
  back: undefined as undefined | ((event: { from: string }) => unknown),
  allowed: true,
  relaunchTo: vi.fn(),
  handleBackPress: vi.fn(),
}))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: typeof state.load) => {
    state.load = hook
  },
  onBackPress: (hook: typeof state.back) => {
    state.back = hook
  },
}))
vi.mock('@/features/identity/public', () => ({ requireRole: () => state.allowed }))
vi.mock('@/platform/runtime', () => ({ getRuntimeMode: () => 'api' }))
vi.mock('@/platform/navigation', () => ({
  relaunchTo: state.relaunchTo,
  backOrRoute: vi.fn(),
  handleBackPress: state.handleBackPress,
  ROUTES: { teacherInsights: '/insights' },
}))

describe('legacy classroom progress redirect', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    state.allowed = true
    state.load = undefined
    state.back = undefined
  })

  it('opens the single Insights progress owner with the original classroom range', () => {
    mount(ClassroomProgressPage)
    state.load?.({ classId: '3', sessionId: '9', dateFrom: '2026-09-01', dateTo: '2026-09-30', panel: 'knowledge' })
    expect(state.relaunchTo).toHaveBeenCalledWith('/insights', {
      panel: 'progress',
      classId: 3,
      sessionId: 9,
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
  })

  it('drops invalid identifiers and arbitrary return addresses', () => {
    mount(ClassroomProgressPage)
    state.load?.({ classId: '-1', sessionId: 'private-session', returnUrl: '/pbl' })
    expect(state.relaunchTo).toHaveBeenCalledWith('/insights', { panel: 'progress' })
  })

  it('requires teacher access before redirecting and falls back to Insights on native back', () => {
    state.allowed = false
    mount(ClassroomProgressPage)
    state.load?.({ classId: '3', sessionId: '9' })
    expect(state.relaunchTo).not.toHaveBeenCalled()
    state.back?.({ from: 'backbutton' })
    expect(state.handleBackPress).toHaveBeenCalledWith('backbutton', '/insights', { panel: 'progress' })
  })
})
