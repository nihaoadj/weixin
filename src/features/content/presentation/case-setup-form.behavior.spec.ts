import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CaseSetupForm from './CaseSetupForm.vue'

describe('case setup form', () => {
  const props = {
    topic: '社区获得性肺炎',
    level: '临床医学本科生',
    objectives: '训练病史采集',
    busy: false,
    error: '',
  }

  it('keeps the teaching setup labeled and emits field changes', async () => {
    const wrapper = mount(CaseSetupForm, { props })
    expect(wrapper.get('#case-topic-label').text()).toBe('病例主题')
    expect(wrapper.get('#case-objectives-label').text()).toBe('教学目标')
    await wrapper.find('input[name="case-topic"]').trigger('input', { detail: { value: '急性胸痛' } })
    await wrapper.find('textarea[name="case-objectives"]').trigger('input', { detail: { value: '训练危险分层' } })
    expect(wrapper.emitted('update:topic')).toEqual([['急性胸痛']])
    expect(wrapper.emitted('update:objectives')).toEqual([['训练危险分层']])
  })

  it('disables duplicate generation while busy and exposes an actionable error', async () => {
    const wrapper = mount(CaseSetupForm, { props: { ...props, busy: true, error: '网络请求失败' } })
    expect(wrapper.get('[role="alert"]').text()).toContain('网络请求失败')
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    await wrapper.setProps({ busy: false })
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('generate')).toEqual([[]])
  })
})
