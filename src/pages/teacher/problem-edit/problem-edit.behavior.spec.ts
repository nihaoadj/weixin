import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './problem-edit.vue'

const state = vi.hoisted(() => ({ role: true, show: undefined as undefined | (() => void), redirect: vi.fn() }))
vi.mock('@dcloudio/uni-app', () => ({
  onShow: (hook: () => void) => {
    state.show = hook
  },
}))
vi.mock('@/features/identity/public', () => ({ requireRole: (role: string) => role === 'teacher' && state.role }))
vi.mock('@/platform/navigation/teacher', () => ({ relaunchToTeacherWorkspace: state.redirect }))
beforeEach(() => {
  state.role = true
  state.show = undefined
  state.redirect.mockClear()
})

describe('open discussion retired compatibility route', () => {
  it('has no editor and takes teachers directly to the case library', () => {
    const wrapper = mount(Page)
    state.show?.()
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(state.redirect).toHaveBeenCalledWith({ workspace: 'content', resource: 'cases' })
  })
  it('does not navigate when the teacher role check fails', () => {
    state.role = false
    mount(Page)
    state.show?.()
    expect(state.redirect).not.toHaveBeenCalled()
  })
})
