import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProblemDetail from './problem-detail.vue'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
}))
const actor = vi.hoisted(() => ({ openid: 'teacher-1', role: 'teacher' }))
const api = vi.hoisted(() => ({
  find: vi.fn(),
  delete: vi.fn(),
  modal: vi.fn(),
  back: vi.fn(),
  detail: vi.fn(),
  toast: vi.fn(),
}))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: typeof hooks.load) => {
    hooks.load = hook
  },
  onShow: (hook: typeof hooks.show) => {
    hooks.show = hook
  },
  onBackPress: vi.fn(),
}))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true, getSession: () => actor }))
vi.mock('@/features/content/public', () => ({ findProblemAsync: api.find, deleteGuidedCaseAsync: api.delete }))
vi.mock('@/platform/navigation', () => ({
  backOrRoute: api.back,
  goDetail: api.detail,
  handleBackPress: vi.fn(),
  ROUTES: { teacherContent: '/content', teacherCaseEdit: '/edit' },
}))
const record = {
  id: 'case-1',
  title: '本人教学病例',
  contentType: 'guided_case',
  status: '待审核',
  description: '教学简介',
  allowedActions: ['edit', 'delete'],
  time: '2026-10-03',
  target: 'individual',
  targetLabel: '隐藏的学生姓名',
  publishTime: '2026-10-03',
}
function mountPage() {
  const wrapper = mount(ProblemDetail)
  hooks.load?.({ id: 'case-1', keyword: '炎症', status: 'approved' })
  return wrapper
}
beforeEach(() => {
  vi.resetAllMocks()
  actor.openid = 'teacher-1'
  actor.role = 'teacher'
  api.find.mockResolvedValue({ ...record })
  api.delete.mockResolvedValue(undefined)
  vi.stubGlobal('uni', { showModal: api.modal, showToast: api.toast })
})
describe('teacher case maintenance detail', () => {
  it('exposes owner edit and delete without review states or student targets', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).not.toMatch(/待审核|发布对象|发布日期|隐藏的学生姓名/)
    await wrapper.get('.edit').trigger('click')
    expect(api.detail).toHaveBeenCalledWith('/edit', { id: 'case-1', resource: 'cases', keyword: '炎症' })
    expect(wrapper.get('.delete-button').text()).toBe('删除病例')
  })
  it('does not expose owner operations for a system case', async () => {
    api.find.mockResolvedValue({ ...record, allowedActions: [] })
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('.edit').exists()).toBe(false)
    expect(wrapper.find('.delete-button').exists()).toBe(false)
  })
  it('cancels deletion without writing', async () => {
    api.modal.mockImplementation(({ success }) => success({ confirm: false }))
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.get('.delete-button').trigger('click')
    await flushPromises()
    expect(api.delete).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(record.title)
  })
  it('keeps the case after a failed delete and permits retry', async () => {
    api.modal.mockImplementation(({ success }) => success({ confirm: true }))
    api.delete.mockRejectedValueOnce(new Error('删除失败'))
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.get('.delete-button').trigger('click')
    await flushPromises()
    expect(api.back).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(record.title)
    expect(wrapper.get('.delete-button').attributes('disabled')).toBeUndefined()
  })
  it('confirms once, writes once and returns with the keyword', async () => {
    let resolveDelete!: () => void
    api.modal.mockImplementation(({ success }) => success({ confirm: true }))
    api.delete.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveDelete = resolve
      }),
    )
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.get('.delete-button').trigger('click')
    await wrapper.get('.delete-button').trigger('click')
    expect(api.modal).toHaveBeenCalledTimes(1)
    expect(api.delete).toHaveBeenCalledOnce()
    expect(api.delete).toHaveBeenCalledWith('case-1')
    resolveDelete()
    await flushPromises()
    expect(api.back).toHaveBeenCalledWith('/content', { resource: 'cases', keyword: '炎症' })
  })
  it('does not write after changing identity while the confirmation is open', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.get('.delete-button').trigger('click')
    actor.openid = 'teacher-2'
    hooks.show?.()
    api.modal.mock.calls[0][0].success({ confirm: true })
    await flushPromises()
    expect(api.delete).not.toHaveBeenCalled()
    expect(api.back).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain(record.title)
  })
  it('does not navigate or announce success after identity changes during deletion', async () => {
    let resolveDelete!: () => void
    api.modal.mockImplementation(({ success }) => success({ confirm: true }))
    api.delete.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveDelete = resolve
      }),
    )
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.get('.delete-button').trigger('click')
    actor.openid = 'teacher-2'
    hooks.show?.()
    resolveDelete()
    await flushPromises()
    expect(api.back).not.toHaveBeenCalled()
    expect(api.toast).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain(record.title)
  })
})
