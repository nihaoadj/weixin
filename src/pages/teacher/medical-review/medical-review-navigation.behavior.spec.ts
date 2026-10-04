import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReviewList from './review-list.vue'
import ReviewDetail from './review-detail.vue'
const hooks = vi.hoisted(() => ({ show: [] as Array<() => void>, allowed: true, relaunch: vi.fn() }))
vi.mock('@dcloudio/uni-app', () => ({
  onShow: (callback: () => void) => hooks.show.push(callback),
  onBackPress: vi.fn(),
}))
vi.mock('@/features/identity/public', () => ({ requireRole: () => hooks.allowed }))
vi.mock('@/platform/navigation', () => ({ handleBackPress: vi.fn() }))
vi.mock('@/platform/navigation/teacher', () => ({ relaunchToTeacherWorkspace: hooks.relaunch }))
beforeEach(() => {
  hooks.show = []
  hooks.allowed = true
  vi.clearAllMocks()
})
describe('T64 retired case review addresses', () => {
  it.each([ReviewList, ReviewDetail])('returns teacher to cases without an approval interface', (component) => {
    const wrapper = mount(component)
    hooks.show.forEach((callback) => callback())
    expect(hooks.relaunch).toHaveBeenCalledWith({ workspace: 'content', resource: 'cases' })
    expect(wrapper.find('button').exists()).toBe(false)
  })
  it.each([ReviewList, ReviewDetail])('does not redirect a rejected role', (component) => {
    hooks.allowed = false
    mount(component)
    hooks.show.forEach((callback) => callback())
    expect(hooks.relaunch).not.toHaveBeenCalled()
  })
})
