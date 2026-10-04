import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PblConversationBoundary from './PblConversationBoundary.vue'

describe('PblConversationBoundary', () => {
  it('states the frozen evidence and private visibility boundary', () => {
    const wrapper = mount(PblConversationBoundary)
    expect(wrapper.attributes('role')).toBe('note')
    expect(wrapper.text()).toContain('四阶段证据已冻结')
    expect(wrapper.text()).toContain('仅你自己可见')
    expect(wrapper.text()).toContain('不提交教师')
    expect(wrapper.text()).toContain('不进入诊断或学习统计')
  })
})
