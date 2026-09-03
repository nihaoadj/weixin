import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherProblemList from '@/components/TeacherProblemList.vue'
import ProblemDetail from '@/pages/teacher/problem-detail/problem-detail.vue'

const { findProblem, getProblems, goDetail, backOrRoute, handleBackPress } = vi.hoisted(() => ({
  findProblem: vi.fn(),
  getProblems: vi.fn(),
  goDetail: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
}))
vi.mock('@/features/content/public', () => ({
  findProblemAsync: findProblem,
  getProblemsAsync: getProblems,
  getGuidedCasesAsync: async () => [],
  publishProblemAsync: vi.fn(),
  rejectProblemAsync: vi.fn(),
  resetProblemsAsync: vi.fn(),
  publishGuidedCaseAsync: vi.fn(),
  submitGuidedCaseForReviewAsync: vi.fn(),
}))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true, isDemoRuntime: () => false }))
vi.mock('@/platform/navigation', () => ({
  goDetail,
  backOrRoute,
  handleBackPress,
  ROUTES: {
    teacherWorkspace: '/workspace',
    teacherProblemDetail: '/problem-detail',
    teacherProblemEdit: '/problem-edit',
  },
}))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query: object) => void) => hook({ id: 'test-problem' }),
  onBackPress: vi.fn(),
}))

const problem = {
  id: 'test-problem',
  type: '医学常识',
  title: '教学练习',
  description: '完整题目说明',
  target: 'all',
  status: '待审核',
  time: '2026-08-31',
}
beforeEach(() => {
  getProblems.mockResolvedValue([problem])
  findProblem.mockResolvedValue(problem)
})

describe('content navigation continuity', () => {
  it('makes the whole reading area a button without nesting edit or publish buttons', async () => {
    const wrapper = mount(TeacherProblemList)
    await (wrapper.vm as unknown as { refresh: () => Promise<void> }).refresh()
    const open = wrapper.get('.problem-open')
    expect(open.text()).toContain('完整题目说明')
    expect(open.find('button').exists()).toBe(false)
    expect(open.attributes('hover-start-time')).toBe('0')
    await open.trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/problem-detail', { id: 'test-problem' })
    goDetail.mockClear()
    await wrapper.get('.action.edit').trigger('click')
    expect(goDetail).toHaveBeenCalledTimes(1)
    expect(goDetail).toHaveBeenCalledWith('/problem-edit', { id: 'test-problem' })
  })

  it('shows a readable loading structure then the detail, rather than a blank page', async () => {
    let resolve!: (value: typeof problem) => void
    findProblem.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const wrapper = mount(ProblemDetail)
    expect(wrapper.get('[aria-busy="true"]').attributes('aria-label')).toBe('正在加载问题…')
    resolve(problem)
    await flushPromises()
    expect(wrapper.get('[aria-level="1"]').text()).toBe('教学练习')
    expect(wrapper.find('[aria-busy="true"]').exists()).toBe(false)
  })

  it('exposes retry after a load failure and never quietly creates a replacement item', async () => {
    findProblem.mockRejectedValueOnce(new Error('网络暂不可用'))
    const wrapper = mount(ProblemDetail)
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('网络暂不可用')
    expect(backOrRoute).not.toHaveBeenCalled()
    await wrapper.get('.med-state__action').trigger('click')
    await flushPromises()
    expect(wrapper.get('[aria-level="1"]').text()).toBe('教学练习')
  })

  it('keeps a usable return action available when a deep-linked detail cannot load', async () => {
    findProblem.mockRejectedValueOnce(new Error('网络暂不可用'))
    const wrapper = mount(ProblemDetail)
    await flushPromises()
    await wrapper.get('.med-state__secondary').trigger('click')
    expect(backOrRoute).toHaveBeenCalledWith('/workspace', { tab: 'problems' })
  })
})
