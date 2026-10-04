import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuestionDetail from './question-detail.vue'

const api = vi.hoisted(() => ({
  load: undefined as undefined | ((options?: Record<string, string>) => void),
  allowed: true,
  goReplace: vi.fn(),
  findStudentQuestionAsync: vi.fn(),
  getQuestionThreadAsync: vi.fn(),
  saveQuestionThreadAsync: vi.fn(),
  requestMedicalAssistant: vi.fn(),
}))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (options?: Record<string, string>) => void) => {
    api.load = hook
  },
}))
vi.mock('@/features/identity/public', () => ({ requireRole: () => api.allowed }))
vi.mock('@/features/qa/public', () => ({
  findStudentQuestionAsync: api.findStudentQuestionAsync,
  getQuestionThreadAsync: api.getQuestionThreadAsync,
  saveQuestionThreadAsync: api.saveQuestionThreadAsync,
  requestMedicalAssistant: api.requestMedicalAssistant,
}))
vi.mock('@/platform/navigation', () => ({
  goReplace: api.goReplace,
  ROUTES: { studentCases: '/cases' },
}))

describe('T63 retired student question detail compatibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.allowed = true
    api.load = undefined
  })

  it('replaces old question addresses with cases without reading or writing old answers', () => {
    const wrapper = mount(QuestionDetail)
    api.load?.({ id: 'legacy-question', returnView: 'questions' })
    expect(api.goReplace).toHaveBeenCalledWith('/cases', { view: 'cases' })
    for (const operation of [
      api.findStudentQuestionAsync,
      api.getQuestionThreadAsync,
      api.saveQuestionThreadAsync,
      api.requestMedicalAssistant,
    ])
      expect(operation).not.toHaveBeenCalled()
    expect(wrapper.find('input').exists()).toBe(false)
    wrapper.unmount()
  })

  it('checks the student role before navigation', () => {
    api.allowed = false
    const wrapper = mount(QuestionDetail)
    api.load?.({ id: 'legacy-question' })
    expect(api.goReplace).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
