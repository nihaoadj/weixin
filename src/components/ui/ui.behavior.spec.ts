import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import MedIcon from './MedIcon.vue'
import MedState from './MedState.vue'
import SafetyBanner from './SafetyBanner.vue'
import StudentNav from './StudentNav.vue'
import StudentPrimaryNav from './StudentPrimaryNav.vue'

const goPrimary = vi.hoisted(() => vi.fn())

vi.mock('@/platform/navigation', () => ({
  ROUTES: {
    studentChat: '/student/chat',
    studentCases: '/student/question',
    studentLearning: '/student/learning',
    studentPbl: '/student/pbl',
    studentInsights: '/student/insights',
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

  it('keeps the default state on the bordered card surface', () => {
    const wrapper = mount(MedState, {
      props: { icon: 'history', title: '暂无内容', description: '还没有可展示的记录。' },
    })
    expect(wrapper.classes()).toContain('card')
    expect(wrapper.find('.med-state__body').exists()).toBe(true)
  })

  it('renders a compact list state without the card boundary while keeping actions', async () => {
    const wrapper = mount(MedState, {
      props: {
        variant: 'error',
        icon: 'retry',
        title: '加载失败',
        description: '网络异常，内容保留。',
        actionLabel: '重新加载',
        size: 'compact',
      },
    })
    expect(wrapper.classes()).toContain('med-state--compact')
    expect(wrapper.classes()).not.toContain('card')
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(1)
    expect(buttons[0].text()).toBe('重新加载')
    await buttons[0].trigger('click')
    expect(wrapper.emitted('action')).toHaveLength(1)
  })

  it('keeps the safety copy visible and supports a custom slot', () => {
    const wrapper = mount(SafetyBanner, { slots: { default: '仅用于测试' } })
    expect(wrapper.text()).toContain('教学辅助 · 非临床诊疗')
    expect(wrapper.text()).toContain('仅用于测试')
  })

  it('navigates every student tab and marks the active tab', async () => {
    const wrapper = mount(StudentNav, { props: { active: 'learning' } })
    expect(wrapper.findAll('.active')).toHaveLength(1)
    expect(wrapper.findAll('.student-nav-icon')).toHaveLength(3)
    expect(wrapper.findAll('image')).toHaveLength(0)
    expect(wrapper.get('.active .student-nav-icon').classes()).toContain('student-nav-icon--book')
    for (const item of wrapper.findAll('.student-nav__item')) await item.trigger('click')
    expect(wrapper.findAll('.student-nav__item').map((item) => item.text())).toEqual(['研讨', '学习', '学情'])
    expect(goPrimary).toHaveBeenCalledTimes(3)
    expect(goPrimary.mock.calls.map(([route]) => route)).toEqual([
      '/student/pbl',
      '/student/learning',
      '/student/insights',
    ])
  })

  it('keeps the primary student navigation in a reusable fixed shell', () => {
    const wrapper = mount(StudentPrimaryNav, { props: { active: 'pbl' } })
    expect(wrapper.classes()).toContain('student-primary-nav')
    expect(wrapper.find('[aria-current="page"]').text()).toBe('研讨')
  })
})
