import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProblemDetail from '@/pages/teacher/problem-detail/problem-detail.vue'

const { findProblem, goDetail, backOrRoute, handleBackPress, query } = vi.hoisted(() => ({
  findProblem: vi.fn(),
  goDetail: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
  query: { id: 'test-problem' } as Record<string, string>,
}))
vi.mock('@/features/content/public', () => ({
  findProblemAsync: findProblem,
}))
vi.mock('@/features/identity/public', () => ({
  requireRole: () => true,
  getSession: () => ({ openid: 'teacher-1', role: 'teacher' }),
  isDemoRuntime: () => false,
}))
vi.mock('@/platform/navigation', () => ({
  goDetail,
  backOrRoute,
  handleBackPress,
  ROUTES: {
    teacherContent: '/content',
    teacherProblemDetail: '/problem-detail',
    teacherProblemEdit: '/problem-edit',
    teacherCaseEdit: '/case-edit',
  },
}))
vi.mock('@dcloudio/uni-app', () => ({
  onShow: vi.fn(),
  onLoad: (hook: (query: object) => void) => hook(query),
  onBackPress: vi.fn(),
}))

const problem = {
  id: 'test-problem',
  type: '医学常识',
  contentType: 'guided_case',
  title: '教学练习',
  description: '完整题目说明',
  target: 'all',
  status: '待审核',
  allowedActions: ['edit'],
  time: '2026-08-31T08:30:00.000Z',
}
beforeEach(() => {
  vi.resetAllMocks()
  Object.keys(query).forEach((key) => delete query[key])
  query.id = 'test-problem'
  findProblem.mockResolvedValue(problem)
})

describe('content navigation continuity', () => {
  it('shows a readable loading structure then the detail, rather than a blank page', async () => {
    let resolve!: (value: typeof problem) => void
    findProblem.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const wrapper = mount(ProblemDetail)
    expect(wrapper.get('[aria-busy="true"]').attributes('aria-label')).toBe('正在加载病例…')
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
    expect(backOrRoute).toHaveBeenCalledWith('/content', { resource: 'cases' })
  })

  it('does not expose an editor without projected permission and gives cases their own editor', async () => {
    findProblem.mockResolvedValueOnce({ ...problem, allowedActions: [] })
    const readonly = mount(ProblemDetail)
    await flushPromises()
    expect(readonly.find('.edit').exists()).toBe(false)
    findProblem.mockResolvedValueOnce({ ...problem, contentType: 'guided_case' })
    const caseDetail = mount(ProblemDetail)
    await flushPromises()
    await caseDetail.get('.edit').trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/case-edit', { id: 'test-problem', resource: 'cases' })
  })

  it('preserves resource filters through editing and returning without accepting another owner', async () => {
    Object.assign(query, { keyword: '  炎症  ', status: 'published', resource: 'cases', returnUrl: '/pbl' })
    const wrapper = mount(ProblemDetail)
    await flushPromises()
    await wrapper.get('.edit').trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/case-edit', {
      id: 'test-problem',
      resource: 'cases',
      keyword: '炎症',
    })
  })
})
