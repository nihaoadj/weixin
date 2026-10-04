import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PblResponseStylePicker from './PblResponseStylePicker.vue'

describe('PblResponseStylePicker', () => {
  it('shows the current response style and emits a real selection change', async () => {
    const wrapper = mount(PblResponseStylePicker, { props: { modelValue: 'guided' } })
    const picker = wrapper.get('picker')
    expect(picker.attributes('aria-label')).toBe('本轮回应方式，当前为探究引导')
    expect(wrapper.text()).toContain('探究引导')
    await picker.trigger('change', { detail: { value: 1 } })
    expect(wrapper.emitted('update:modelValue')).toEqual([['direct']])
    expect(wrapper.emitted('change')).toEqual([['direct']])
  })

  it('does not emit while disabled', async () => {
    const wrapper = mount(PblResponseStylePicker, { props: { modelValue: 'direct', disabled: true } })
    expect(wrapper.get('picker').attributes('aria-label')).toBe('本轮回应方式，当前为直接讲解')
    expect(wrapper.text()).toContain('直接讲解')
    await wrapper.get('picker').trigger('change', { detail: { value: 0 } })
    expect(wrapper.emitted('change')).toBeUndefined()
  })
})
