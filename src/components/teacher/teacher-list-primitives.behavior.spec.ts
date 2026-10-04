import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TeacherPager from './TeacherPager.vue'

describe('teacher pager', () => {
  it('hides paging controls when the result fits on one page', () => {
    const wrapper = mount(TeacherPager, { props: { total: 1, offset: 0 } })
    expect(wrapper.findAll('button')).toHaveLength(0)
    expect(wrapper.text()).toBe('')
  })

  it('pages multi-page results with range, total and end-disabled buttons', async () => {
    const first = mount(TeacherPager, { props: { total: 45, offset: 0 } })
    expect(first.text()).toContain('第 1–20 项 · 共 45 项')
    const firstButtons = first.findAll('button')
    expect(firstButtons[0].attributes('disabled')).toBeDefined()
    expect(firstButtons[1].attributes('disabled')).toBeUndefined()
    await firstButtons[1].trigger('click')
    await firstButtons[1].trigger('keydown', { key: 'Enter' })
    expect(first.emitted('next')).toHaveLength(2)
    expect(first.emitted('previous')).toBeUndefined()

    const last = mount(TeacherPager, { props: { total: 45, offset: 40 } })
    expect(last.text()).toContain('第 41–45 项 · 共 45 项')
    const lastButtons = last.findAll('button')
    expect(lastButtons[0].attributes('disabled')).toBeUndefined()
    expect(lastButtons[1].attributes('disabled')).toBeDefined()
    await lastButtons[0].trigger('click')
    expect(last.emitted('previous')).toHaveLength(1)
  })
})
