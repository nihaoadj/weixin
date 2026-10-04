import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { useHorizontalSwipe } from '../../../components/teacher/useHorizontalSwipe'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherContentResources from './TeacherContentResources.vue'

const api = vi.hoisted(() => ({
  getCases: vi.fn(),
  getCatalog: vi.fn(),
  listBank: vi.fn(),
  deleteCase: vi.fn(),
  deleteBank: vi.fn(),
  goDetail: vi.fn(),
  showModal: vi.fn(),
  showToast: vi.fn(),
}))
const identity = vi.hoisted(() => ({ current: { openid: 'teacher-1', role: 'teacher' } }))
vi.mock('@/features/identity/public', () => ({ getSession: () => identity.current }))
vi.mock('@/features/content/public', () => ({
  getGuidedCasesAsync: api.getCases,
  listTeacherQuestionBank: api.listBank,
  deleteGuidedCaseAsync: api.deleteCase,
  deleteTeacherQuestionBankItem: api.deleteBank,
}))
vi.mock('@/features/learning/public', () => ({ getKnowledgeCatalog: api.getCatalog }))
vi.mock('@/platform/navigation', () => ({
  goDetail: api.goDetail,
  ROUTES: {
    teacherProblemDetail: '/problem-detail',
    teacherCaseEdit: '/case-edit',
    teacherQuestionBank: '/question-bank',
    teacherQuestionBankDetail: '/question-bank-detail',
  },
}))
const problem = {
  id: 'case-1',
  type: '病例分析',
  title: '炎症病例',
  description: '病程与组织学观察',
  target: 'all',
  status: '已发布',
  time: '2026-10-03',
  contentType: 'guided_case',
  medicalReviewStatus: 'pending',
  allowedActions: ['edit', 'delete'],
}
const bank = {
  id: 9,
  title: '炎症单选',
  prompt: '病理表现',
  pointCodes: ['point-1'],
  updatedAt: '2026-10-03',
  version: 2,
  status: 'active',
}
beforeEach(() => {
  vi.clearAllMocks()
  identity.current = { openid: 'teacher-1', role: 'teacher' }
  api.getCatalog.mockResolvedValue([])
  api.getCases.mockResolvedValue([problem])
  api.listBank.mockResolvedValue({ items: [bank], total: 1, limit: 20, offset: 0 })
  api.deleteCase.mockResolvedValue(undefined)
  api.deleteBank.mockResolvedValue(undefined)
  api.showModal.mockImplementation((options) => options.success({ confirm: false }))
  vi.stubGlobal('uni', { showModal: api.showModal, showToast: api.showToast })
})
afterEach(() => vi.unstubAllGlobals())
async function ready(resource: 'cases' | 'question-bank' = 'cases', keyword = '') {
  const wrapper = mount(TeacherContentResources, { props: { resource, keyword } })
  await flushPromises()
  return wrapper
}
describe('T64 simple content resources', () => {
  it('opens create, case view and case editor through native taps', async () => {
    const wrapper = await ready()
    await wrapper.get('.create-action').trigger('tap')
    expect(api.goDetail).toHaveBeenLastCalledWith('/case-edit', expect.objectContaining({ resource: 'cases' }))
    await wrapper.get('.view-resource').trigger('tap')
    expect(api.goDetail).toHaveBeenLastCalledWith('/problem-detail', expect.objectContaining({ id: 'case-1' }))
    await wrapper.get('.edit-resource').trigger('tap')
    expect(api.goDetail).toHaveBeenLastCalledWith('/case-edit', expect.objectContaining({ id: 'case-1' }))
    await wrapper.get('.search-input').setValue('  炎症  ')
    await wrapper.get('.search-button').trigger('tap')
    expect(wrapper.emitted('filtersChange')).toEqual([[{ resource: 'cases', keyword: '炎症' }]])
  })
  it('lets a normal control tap propagate without starting a horizontal swipe', async () => {
    const onSwipe = vi.fn(),
      onDrag = vi.fn(),
      onStart = vi.fn()
    const parent = defineComponent({
      setup() {
        const swipe = useHorizontalSwipe(onSwipe, { onDrag, viewportWidth: () => 375 })
        onStart.mockImplementation(swipe.touchstart)
        return () =>
          h('view', { onTouchstart: onStart, onTouchmove: swipe.touchmove, onTouchend: swipe.touchend }, [
            h(TeacherContentResources, { resource: 'cases' }),
          ])
      },
    })
    const wrapper = mount(parent)
    await flushPromises()
    const button = wrapper.get('.create-action')
    await button.trigger('touchstart', { touches: [{ clientX: 120, clientY: 80 }] })
    await button.trigger('touchmove', { touches: [{ clientX: 122, clientY: 81 }] })
    await button.trigger('touchend', { touches: [], changedTouches: [{ clientX: 122, clientY: 81 }] })
    expect(onStart).toHaveBeenCalledTimes(1)
    expect(onDrag).not.toHaveBeenCalled()
    expect(onSwipe).not.toHaveBeenCalled()
    await button.trigger('tap')
    expect(api.goDetail).toHaveBeenCalledWith('/case-edit', expect.objectContaining({ resource: 'cases' }))
  })

  it('loads on first mount without depending on a parent component ref', async () => {
    const wrapper = mount(TeacherContentResources, { props: { resource: 'cases' } })
    await flushPromises()
    expect(api.getCases).toHaveBeenCalledTimes(1)
    expect(wrapper.get('.row-title-text').text()).toBe('炎症病例')
  })
  it('shows catalog titles for actual bound codes without changing search scope', async () => {
    api.getCases.mockResolvedValue([{ ...problem, knowledgePointCodes: ['point-1'] }])
    api.getCatalog.mockResolvedValue([{ code: 'point-1', title: '急性炎症' }])
    const wrapper = await ready()
    expect(wrapper.get('.row-meta').text()).toBe('知识点：急性炎症')
    await wrapper.setProps({ keyword: '急性炎症' })
    await flushPromises()
    expect(wrapper.find('.resource-row').exists()).toBe(false)
  })
  it('keeps multiple bindings concise while showing their actual total', async () => {
    api.getCases.mockResolvedValue([{ ...problem, knowledgePointCodes: ['point-1', 'point-2'] }])
    api.getCatalog.mockResolvedValue([
      { code: 'point-1', title: '急性炎症' },
      { code: 'point-2', title: '慢性炎症' },
    ])
    const wrapper = await ready()
    expect(wrapper.get('.row-meta').text()).toBe('知识点：急性炎症 等2项')
  })
  it('keeps usable rows and a true binding count when catalog fails or lacks a code', async () => {
    api.getCatalog.mockRejectedValueOnce(new Error('目录暂不可用'))
    const wrapper = await ready('question-bank')
    expect(wrapper.get('.row-meta').text()).toBe('知识点：1 项')
    expect(wrapper.find('.edit-resource').exists()).toBe(true)
    await wrapper.vm.refresh()
    await flushPromises()
    expect(wrapper.get('.row-meta').text()).toBe('知识点：1 项')
    expect(wrapper.find('.inline-error').exists()).toBe(false)
  })
  it('discards delayed catalog labels after switching resources', async () => {
    let resolveCatalog: ((value: unknown[]) => void) | undefined
    api.getCases.mockResolvedValue([{ ...problem, knowledgePointCodes: ['point-1'] }])
    api.getCatalog.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCatalog = resolve
        }),
    )
    const wrapper = mount(TeacherContentResources, { props: { resource: 'cases' } })
    await flushPromises()
    await wrapper.setProps({ resource: 'question-bank' })
    await flushPromises()
    resolveCatalog?.([{ code: 'point-1', title: '过期标签' }])
    await flushPromises()
    expect(wrapper.get('.row-meta').text()).toBe('知识点：1 项')
    expect(wrapper.text()).not.toContain('过期标签')
  })

  it('keeps two resource lists without lifecycle filters or review actions', async () => {
    const wrapper = await ready()
    expect(wrapper.findAll('.resource-tab').map((tab) => tab.text())).toEqual(['病例库', '个人题库'])
    expect(wrapper.find('.status-options').exists()).toBe(false)
    for (const text of ['审核中', '待发布', '归档', '医学审核']) expect(wrapper.text()).not.toContain(text)
    expect(wrapper.findAll('.edit-resource')).toHaveLength(1)
    expect(wrapper.findAll('.delete-resource')).toHaveLength(1)
  })
  it('keeps other-author and missing projections read only', async () => {
    api.getCases.mockResolvedValue([
      { ...problem, allowedActions: [] },
      { ...problem, id: 'other', allowedActions: undefined },
    ])
    const wrapper = await ready()
    expect(wrapper.find('.edit-resource').exists()).toBe(false)
    expect(wrapper.find('.delete-resource').exists()).toBe(false)
  })
  it('preserves search and resource context without a status', async () => {
    const wrapper = await ready('question-bank', '炎症')
    expect(api.listBank).toHaveBeenCalledWith({ query: '炎症', limit: 20, offset: 0 })
    await wrapper.get('.row-title').trigger('tap')
    expect(api.goDetail).toHaveBeenCalledWith(
      '/question-bank-detail',
      expect.objectContaining({ id: 9, resource: 'question-bank', keyword: '炎症' }),
    )
    expect(api.goDetail.mock.calls[0][1]).not.toHaveProperty('status')
    await wrapper.findAll('.resource-tab')[0].trigger('tap')
    expect(wrapper.emitted('filtersChange')).toEqual([[{ resource: 'cases', keyword: '炎症' }]])
  })
  it('leaves records intact when deletion is cancelled', async () => {
    const wrapper = await ready()
    await wrapper.get('.delete-resource').trigger('tap')
    expect(api.deleteCase).not.toHaveBeenCalled()
    expect(wrapper.findAll('.resource-row')).toHaveLength(1)
  })
  it('deletes a confirmed case and removes its row', async () => {
    api.showModal.mockImplementation((options) => options.success({ confirm: true }))
    const wrapper = await ready()
    await wrapper.get('.delete-resource').trigger('tap')
    await flushPromises()
    expect(api.deleteCase).toHaveBeenCalledWith('case-1')
    expect(wrapper.findAll('.resource-row')).toHaveLength(0)
  })
  it('deletes a confirmed bank item using its version and updates total', async () => {
    api.showModal.mockImplementation((options) => options.success({ confirm: true }))
    const wrapper = await ready('question-bank')
    await wrapper.get('.delete-resource').trigger('tap')
    await flushPromises()
    expect(api.deleteBank).toHaveBeenCalledWith(9, 2, expect.any(String))
    expect(wrapper.get('.section-total').text()).toBe('0 道')
  })
  it('keeps the record on failure and allows retry', async () => {
    api.showModal.mockImplementation((options) => options.success({ confirm: true }))
    api.deleteCase.mockRejectedValueOnce(new Error('网络失败'))
    const wrapper = await ready()
    await wrapper.get('.delete-resource').trigger('tap')
    await flushPromises()
    expect(wrapper.findAll('.resource-row')).toHaveLength(1)
    expect(api.showToast).toHaveBeenCalledWith({ title: '网络失败', icon: 'none' })
    await wrapper.get('.delete-resource').trigger('tap')
    await flushPromises()
    expect(api.deleteCase).toHaveBeenCalledTimes(2)
  })
  it('rejects delayed confirmation after an identity change', async () => {
    let confirm: ((value: { confirm: boolean }) => void) | undefined
    api.showModal.mockImplementation((options) => {
      confirm = options.success
    })
    const wrapper = await ready()
    await wrapper.get('.delete-resource').trigger('tap')
    identity.current = { openid: 'teacher-2', role: 'teacher' }
    confirm?.({ confirm: true })
    await flushPromises()
    expect(api.deleteCase).not.toHaveBeenCalled()
  })
  it('locks duplicate confirmation and deletion while a request is pending', async () => {
    let confirm: ((value: { confirm: boolean }) => void) | undefined
    let finish: (() => void) | undefined
    api.showModal.mockImplementation((options) => {
      confirm = options.success
    })
    api.deleteCase.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve
        }),
    )
    const wrapper = await ready()
    await wrapper.get('.delete-resource').trigger('tap')
    await wrapper.get('.delete-resource').trigger('tap')
    expect(api.showModal).toHaveBeenCalledTimes(1)
    confirm?.({ confirm: true })
    await flushPromises()
    expect(wrapper.get('.delete-resource').attributes('disabled')).toBeDefined()
    finish?.()
    await flushPromises()
    expect(api.deleteCase).toHaveBeenCalledTimes(1)
  })
  it('ignores an obsolete list response after switching resource', async () => {
    let resolveCases: ((value: unknown[]) => void) | undefined
    api.getCases.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCases = resolve
        }),
    )
    const wrapper = mount(TeacherContentResources, { props: { resource: 'cases' } })
    const pending = wrapper.vm.refresh()
    await wrapper.setProps({ resource: 'question-bank' })
    await flushPromises()
    resolveCases?.([problem])
    await pending
    await flushPromises()
    expect(wrapper.text()).toContain('炎症单选')
    expect(wrapper.text()).not.toContain('炎症病例')
  })
})
