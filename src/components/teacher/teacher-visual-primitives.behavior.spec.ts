import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import TeacherModuleSection from './TeacherModuleSection.vue'
import TeacherStatusTag from './TeacherStatusTag.vue'
import { displayTopicCode } from '../../features/pbl/presentation/teacherPresentation'

describe('teacher module section', () => {
  it('renders title, description, meta, body and action slots in the fixed order', () => {
    const wrapper = mount(TeacherModuleSection, {
      props: { title: '系统判定', description: '按版本化规则自动判定' },
      slots: {
        meta: '<text class="meta-stub">第 2 / 2 轮</text>',
        default: '<view class="body-stub">判定内容</view>',
        actions: '<button class="action-stub">发送</button>',
      },
    })
    expect(wrapper.get('.tms__title').text()).toBe('系统判定')
    expect(wrapper.get('.tms__title-tab').text()).toBe('系统判定')
    expect(wrapper.get('.tms__title').attributes('role')).toBe('heading')
    expect(wrapper.get('.tms__title').attributes('aria-level')).toBe('2')
    expect(wrapper.get('.meta-stub').text()).toBe('第 2 / 2 轮')
    expect(wrapper.find('.body-stub').exists()).toBe(true)
    expect(wrapper.find('.action-stub').exists()).toBe(true)
    const text = wrapper.text()
    expect(text.indexOf('系统判定')).toBeLessThan(text.indexOf('判定内容'))
    expect(text.indexOf('判定内容')).toBeLessThan(text.indexOf('发送'))
  })

  it('exposes the five tones, compact mode and a level-3 heading, and omits empty blocks', () => {
    for (const tone of ['default', 'focus', 'reference', 'editor', 'safety'] as const) {
      const wrapper = mount(TeacherModuleSection, { props: { title: '模块', tone } })
      expect(wrapper.get('.tms').classes()).toContain(`tms--${tone}`)
    }
    const compact = mount(TeacherModuleSection, {
      props: { title: '模块', compact: true, headingLevel: 3 },
    })
    expect(compact.get('.tms').classes()).toContain('tms--compact')
    expect(compact.get('.tms__title').attributes('aria-level')).toBe('3')
    expect(compact.find('.tms__description').exists()).toBe(false)
    expect(compact.find('.tms__actions').exists()).toBe(false)
  })

  it('keeps long titles on one heading without wrapping slot content in cards', () => {
    const longTitle = '需要补强的目标'.repeat(8)
    const wrapper = mount(TeacherModuleSection, {
      props: { title: longTitle },
      slots: { default: '<view class="plain-row">记录行</view>' },
    })
    expect(wrapper.get('.tms__title').text()).toBe(longTitle)
    expect(wrapper.get('.plain-row').classes()).not.toContain('tms')
    expect(wrapper.findAll('.tms').length).toBe(1)
  })
})

describe('teacher status tag', () => {
  it('renders the five tones with the caller label verbatim', () => {
    for (const tone of ['neutral', 'active', 'success', 'safety', 'danger'] as const) {
      const wrapper = mount(TeacherStatusTag, { props: { label: '未达标', tone } })
      expect(wrapper.get('.tst').classes()).toContain(`tst--${tone}`)
      expect(wrapper.get('.tst').text()).toBe('未达标')
    }
  })

  it('defaults to the neutral tone and never rewrites the label', () => {
    const wrapper = mount(TeacherStatusTag, { props: { label: '两轮后仍需支持' } })
    expect(wrapper.get('.tst').classes()).toContain('tst--neutral')
    expect(wrapper.get('.tst').text()).toBe('两轮后仍需支持')
  })
})

describe('teacher presentation mapper', () => {
  it('maps known classroom topics', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(displayTopicCode('pathology.inflammation')).toBe('炎症')
    warn.mockRestore()
  })

  it('falls back to neutral copy for unknown topic codes without exposing raw paths', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(displayTopicCode('pathology.cell-injury.necrosis')).toBe('其他教学主题')
    expect(displayTopicCode('肾病理')).toBe('肾病理')
    expect(displayTopicCode('')).toBe('')
    expect(warn.mock.calls.some((call) => String(call[0]).includes('pathology'))).toBe(false)
    warn.mockRestore()
  })
})
