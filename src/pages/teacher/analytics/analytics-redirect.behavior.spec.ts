import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AnalyticsRedirect from './index.vue'

const { relaunchTo, requireRole } = vi.hoisted(() => ({ relaunchTo: vi.fn(), requireRole: vi.fn(() => true) }))
vi.mock('@/features/identity/public', () => ({ requireRole }))
vi.mock('@/platform/navigation', () => ({
  relaunchTo,
  handleBackPress: vi.fn(),
  ROUTES: { teacherWorkspace: '/workspace' },
}))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: () => void) => hook(),
  onBackPress: vi.fn(),
}))

describe('legacy teacher analytics route', () => {
  beforeEach(() => {
    relaunchTo.mockClear()
    requireRole.mockReset().mockReturnValue(true)
  })

  it('redirects into the analytics section of the insights workspace', () => {
    const wrapper = mount(AnalyticsRedirect)
    expect(wrapper.text()).toContain('教学统计已统一归入教师学情工作区')
    expect(relaunchTo).toHaveBeenCalledWith('/workspace', { tab: 'reports', section: 'analytics' })
  })

  it('does not redirect before the teacher role guard succeeds', () => {
    requireRole.mockReturnValueOnce(false)
    mount(AnalyticsRedirect)
    expect(relaunchTo).not.toHaveBeenCalled()
  })
})
