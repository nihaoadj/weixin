import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatComposer from './ChatComposer.vue'

const stubs = { MedIcon: true, StudentNav: true, SafetyBanner: true }

describe('chat presentation', () => {
  it('labels the input and send action, preserving the model value', async () => {
    const wrapper = mount(ChatComposer, {
      props: { modelValue: '', loading: false, canGenerateReport: false, canRetry: false },
      global: { stubs },
    })
    expect(wrapper.get('label').attributes('for')).toBe('medical-question')
    expect(wrapper.get('.message-input').attributes('aria-label')).toBe('医学学习问题')
    expect(wrapper.get('.send-button').attributes('aria-label')).toBe('发送消息')
    expect(wrapper.get('.send-button').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.send-button').attributes('aria-disabled')).toBe('true')
    await wrapper.get('input').setValue('病例分析')
    expect(wrapper.emitted('update:modelValue')).toEqual([['病例分析']])
    await wrapper.setProps({ modelValue: '病例分析', canGenerateReport: true })
    await wrapper.get('.send-button').trigger('click')
    await wrapper.get('.report-button').trigger('click')
    expect(wrapper.emitted('send')).toHaveLength(1)
    expect(wrapper.emitted('report')).toHaveLength(1)
  })

  it('keeps retry explicit and disables actions during a request', async () => {
    const wrapper = mount(ChatComposer, {
      props: { modelValue: '病例分析', loading: true, canGenerateReport: true, canRetry: true },
      global: { stubs },
    })
    for (const selector of ['input', '.send-button', '.report-button', '.retry-button']) {
      expect(wrapper.get(selector).attributes('disabled')).toBeDefined()
    }
    await wrapper.get('.retry-button').trigger('click')
    expect(wrapper.emitted('retry')).toBeUndefined()
    await wrapper.setProps({ loading: false })
    await wrapper.get('.retry-button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
    await wrapper.setProps({ canRetry: false })
    expect(wrapper.find('.retry-button').exists()).toBe(false)
  })

  it('uses the compact two-level composer only for dialogue pages', () => {
    const wrapper = mount(ChatComposer, {
      props: { modelValue: '阶段证据', loading: false, multiline: true, appearance: 'dialogue' },
      global: { stubs },
    })
    expect(wrapper.get('.composer').classes()).toContain('is-dialogue')
    expect(wrapper.get('.composer-context').text()).toBe('阶段作答')
    expect(wrapper.find('.send-button-surface').exists()).toBe(true)
    expect(wrapper.get('.send-glyph').text()).toBe('↑')
    expect(wrapper.get('.send-button').attributes('aria-label')).toBe('发送消息')
  })

  it('replaces the default dialogue context with a named slot', () => {
    const wrapper = mount(ChatComposer, {
      props: { modelValue: '阶段证据', loading: false, multiline: true, appearance: 'dialogue' },
      slots: { context: '<text class="custom-context">本轮回应方式</text>' },
      global: { stubs },
    })
    expect(wrapper.get('.custom-context').text()).toBe('本轮回应方式')
    expect(wrapper.find('.composer-context').exists()).toBe(false)
  })

  it('keeps a quoted selection inside the dialogue bubble', () => {
    const wrapper = mount(ChatComposer, {
      props: { modelValue: '', loading: false, multiline: true, appearance: 'dialogue' },
      slots: { quote: '<view class="quote-preview">引用内容</view>' },
      global: { stubs },
    })
    expect(wrapper.get('.composer-bar').find('.quote-preview').text()).toBe('引用内容')
  })

  it('moves the dialogue composer above the mobile keyboard and restores it after blur', async () => {
    const wrapper = mount(ChatComposer, {
      props: { modelValue: '', loading: false, multiline: true, appearance: 'dialogue' },
      global: { stubs },
    })
    const textarea = wrapper.get('textarea')
    expect(textarea.attributes('adjust-position')).toBe('false')

    await textarea.trigger('keyboardheightchange', { detail: { height: 280 } })
    expect(wrapper.get('.composer').classes()).toContain('is-keyboard-open')
    expect(wrapper.emitted('keyboard-height-change')).toEqual([[280]])

    await textarea.trigger('blur')
    expect(wrapper.get('.composer').classes()).not.toContain('is-keyboard-open')
    expect(wrapper.emitted('keyboard-height-change')).toEqual([[280], [0]])
  })
})
