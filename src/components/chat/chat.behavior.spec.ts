import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatComposer from './ChatComposer.vue'
import ChatWelcome from './ChatWelcome.vue'

const stubs = { MedIcon: true, StudentNav: true, SafetyBanner: true }

describe('chat presentation', () => {
  it('exposes suggested questions as named buttons', async () => {
    const question = '如何整理鉴别诊断？'
    const wrapper = mount(ChatWelcome, { props: { questions: [question] }, global: { stubs } })
    const action = wrapper.get('button.quick-item')
    expect(action.attributes('aria-label')).toBe(`提问：${question}`)
    await action.trigger('click')
    expect(wrapper.emitted('ask')).toEqual([[question]])
  })

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
})
