import { describe, expect, it } from 'vitest'
import { syncNativeFieldA11y } from './nativeFieldA11y'

describe('H5 field accessibility adapter', () => {
  it('names native fields and updates validation metadata without changing input values', () => {
    const root = globalThis.document.createElement('div')
    const wrapper = globalThis.document.createElement('uni-input')
    const input = globalThis.document.createElement('input')
    input.value = '80'
    wrapper.setAttribute('aria-label', '教师评分')
    wrapper.setAttribute('data-native-name', 'teacher-score')
    wrapper.setAttribute('aria-invalid', 'true')
    wrapper.setAttribute('aria-describedby', 'score-error')
    wrapper.append(input)
    root.append(wrapper)
    syncNativeFieldA11y({ $el: root })
    expect(input.getAttribute('aria-label')).toBe('教师评分')
    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(input.getAttribute('aria-describedby')).toBe('score-error')
    expect(input.getAttribute('name')).toBe('teacher-score')
    expect(input.value).toBe('80')
    wrapper.removeAttribute('aria-describedby')
    wrapper.setAttribute('aria-invalid', 'false')
    syncNativeFieldA11y(root)
    expect(input.hasAttribute('aria-describedby')).toBe(false)
    expect(input.getAttribute('aria-invalid')).toBe('false')
  })

  it('supports textarea wrappers and ignores unavailable or native-only roots', () => {
    const root = globalThis.document.createElement('div')
    const wrapper = globalThis.document.createElement('uni-textarea')
    wrapper.setAttribute('aria-label', '教师反馈')
    wrapper.setAttribute('name', 'feedback')
    const textarea = globalThis.document.createElement('textarea')
    wrapper.append(textarea)
    root.append(wrapper)
    syncNativeFieldA11y(root)
    expect(textarea.getAttribute('aria-label')).toBe('教师反馈')
    expect(textarea.getAttribute('name')).toBe('feedback')
    expect(() => syncNativeFieldA11y(null)).not.toThrow()
    expect(() => syncNativeFieldA11y({})).not.toThrow()
    expect(() => syncNativeFieldA11y(globalThis.document.createElement('input'))).not.toThrow()
  })
})
