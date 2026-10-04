import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './index.vue'
const hooks = vi.hoisted(() => ({ load: undefined as undefined | ((query?: Record<string, string>) => void) }))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: typeof hooks.load) => {
    hooks.load = hook
  },
}))
describe('retired teacher home compatibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(uni.reLaunch).mockImplementation((options) => {
      options?.complete?.({ errMsg: 'reLaunch:ok' })
    })
  })
  it.each([
    [{}, '/pages/teacher/pbl/index?section=classrooms'],
    [{ tab: 'overview' }, '/pages/teacher/pbl/index?section=classrooms'],
    [{ tab: 'reports', panel: 'students', classId: '8' }, '/pages/teacher/insights/index?panel=students&classId=8'],
    [{ tab: 'problems', section: 'question-bank' }, '/pages/teacher/content/index?resource=question-bank'],
    [
      { tab: 'work-items', classId: '3', reviewKind: 'needs_changes' },
      '/pages/teacher/pbl/test-queue?section=diagnostics&reviewKind=needs_changes&classId=3',
    ],
  ])('redirects %j to its supported destination', (query, url) => {
    const wrapper = mount(Page)
    hooks.load?.(query)
    expect(uni.reLaunch).toHaveBeenCalledWith(expect.objectContaining({ url }))
    expect(wrapper.text()).toBe('')
    wrapper.unmount()
  })
})
