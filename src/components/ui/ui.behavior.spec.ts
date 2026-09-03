import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import MedIcon from './MedIcon.vue'
import MedState from './MedState.vue'
import SafetyBanner from './SafetyBanner.vue'
import StudentNav from './StudentNav.vue'

const goPrimary = vi.hoisted(() => vi.fn())

vi.mock('@/platform/navigation', () => ({
  ROUTES: {
    studentChat: '/student/chat',
    studentCases: '/student/question',
    studentLearning: '/student/learning',
    studentHistory: '/student/history',
  },
  goPrimary,
}))

describe('shared UI behavior', () => {
  it('renders icon source and size contract', () => {
    const wrapper = mount(MedIcon, { props: { name: 'brand', size: 'lg' } })
    expect(wrapper.attributes('src')).toBe('/static/icons/brand.svg')
    expect(wrapper.classes()).toContain('med-icon--lg')
  })

  it('renders empty/error actions and emits their observable events', async () => {
    const wrapper = mount(MedState, {
      props: {
        variant: 'error',
        icon: 'retry',
        title: '失败',
        description: '网络失败',
        actionLabel: '重试',
        secondaryActionLabel: '返回',
      },
    })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(2)
    await buttons[0].trigger('click')
    await buttons[1].trigger('click')
    expect(wrapper.emitted('action')).toHaveLength(1)
    expect(wrapper.emitted('secondaryAction')).toHaveLength(1)
  })

  it('keeps the safety copy visible and supports a custom slot', () => {
    const wrapper = mount(SafetyBanner, { slots: { default: '仅用于测试' } })
    expect(wrapper.text()).toContain('教学辅助 · 非临床诊疗')
    expect(wrapper.text()).toContain('仅用于测试')
  })

  it('navigates every student tab and marks the active tab', async () => {
    const wrapper = mount(StudentNav, { props: { active: 'learning' } })
    expect(wrapper.findAll('.active')).toHaveLength(1)
    for (const item of wrapper.findAll('.student-nav__item')) await item.trigger('click')
    expect(goPrimary).toHaveBeenCalledTimes(4)
    expect(goPrimary.mock.calls.map(([route]) => route)).toEqual([
      '/student/chat',
      '/student/question',
      '/student/learning',
      '/student/history',
    ])
  })
})
