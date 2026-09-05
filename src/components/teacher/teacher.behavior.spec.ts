import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TeacherWorkspaceNav from './TeacherWorkspaceNav.vue'
import TeacherOverview from './TeacherOverview.vue'

describe('teacher workspace navigation', () => {
  it('exposes four intent-based destinations and only one current page', async () => {
    const wrapper = mount(TeacherWorkspaceNav, {
      props: { active: 'reports' },
      global: { stubs: { MedIcon: true } },
    })
    expect(wrapper.attributes('aria-label')).toBe('教师主导航')
    expect(wrapper.findAll('button').map((button) => button.text())).toEqual(['待办', '学情', '内容', 'PBL'])
    expect(wrapper.findAll('[aria-current="page"]')).toHaveLength(1)
    expect(wrapper.get('[aria-current="page"]').text()).toBe('学情')
    await wrapper.findAll('button')[2].trigger('click')
    expect(wrapper.emitted('change')).toEqual([['problems']])
  })

  it('supports Enter and Space without relying on a tab widget', async () => {
    const wrapper = mount(TeacherWorkspaceNav, {
      props: { active: 'reports' },
      global: { stubs: { MedIcon: true } },
    })
    await wrapper.findAll('button')[0].trigger('keydown', { key: 'Enter' })
    await wrapper.findAll('button')[2].trigger('keydown', { key: ' ' })
    expect(wrapper.emitted('change')).toEqual([['overview'], ['problems']])
    expect(wrapper.find('[role="tab"]').exists()).toBe(false)
  })
})

describe('teacher overview', () => {
  const props = { loading: false, isReviewer: false, reportError: false, reviewError: false }

  it('distinguishes an empty queue from a failed queue', async () => {
    const wrapper = mount(TeacherOverview, { props: { ...props, pendingReports: 0 } })
    expect(wrapper.text()).toContain('暂无待批阅报告')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    await wrapper.setProps({ pendingReports: undefined, reportError: true })
    expect(wrapper.get('[role="alert"]').text()).toContain('不代表没有待处理内容')
    expect(wrapper.text()).not.toContain('暂无待批阅报告')
    await wrapper.get('.priority-row').trigger('click')
    expect(wrapper.emitted('retry')).toEqual([[]])
    expect(wrapper.emitted('reports')).toBeUndefined()
  })

  it('keeps review entry permission-based and management actions distinct', async () => {
    const wrapper = mount(TeacherOverview, { props })
    expect(wrapper.findAll('.priority-row')).toHaveLength(1)
    await wrapper.setProps({ isReviewer: true, pendingReview: 2 })
    expect(wrapper.findAll('.priority-row')).toHaveLength(2)
    await wrapper.findAll('.priority-row')[1].trigger('click')
    await wrapper.findAll('.management-row')[0].trigger('click')
    await wrapper.findAll('.management-row')[1].trigger('click')
    expect(wrapper.emitted('review')).toEqual([[]])
    expect(wrapper.emitted('classes')).toEqual([[]])
    expect(wrapper.emitted('analytics')).toEqual([[]])
  })
})
