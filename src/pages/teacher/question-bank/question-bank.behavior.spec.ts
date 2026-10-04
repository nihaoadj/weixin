import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuestionBankIndex from './index.vue'
import QuestionBankDetail from './detail.vue'
import type { TeacherQuestionBankItem, TeacherQuestionBankPage } from '@/features/content/public'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
  back: undefined as undefined | ((event: { from: string }) => unknown),
}))
const identity = vi.hoisted(() => ({ current: null as null | { openid: string; role: 'teacher' | 'student' } }))
const api = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  update: vi.fn(),
  delete: vi.fn(),
  goDetail: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
  showModal: vi.fn(),
  requireRole: vi.fn(),
}))

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query?: Record<string, string>) => void) => {
    hooks.load = hook
  },
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onBackPress: (hook: (event: { from: string }) => unknown) => {
    hooks.back = hook
  },
}))
vi.mock('@/features/content/public', () => ({
  listTeacherQuestionBank: api.list,
  getTeacherQuestionBankItem: api.get,
  updateTeacherQuestionBankItem: api.update,
  deleteTeacherQuestionBankItem: api.delete,
}))
vi.mock('@/features/identity/public', () => ({
  requireRole: api.requireRole,
  getSession: () => identity.current,
}))
vi.mock('@/platform/navigation', () => ({
  goDetail: api.goDetail,
  backOrRoute: api.backOrRoute,
  handleBackPress: api.handleBackPress,
  ROUTES: {
    teacherQuestionBank: '/pages/teacher/question-bank/index',
    teacherQuestionBankDetail: '/pages/teacher/question-bank/detail',
    teacherWorkspace: '/pages/teacher/index/index',
    teacherContent: '/pages/teacher/content/index',
  },
}))

const bankItem = (overrides: Partial<TeacherQuestionBankItem> = {}): TeacherQuestionBankItem => ({
  id: 12,
  version: 1,
  status: 'active',
  taskType: 'retest',
  title: '炎症血管反应目标验证',
  prompt: '解释血流变化与通透性增加的关系。',
  options: ['血流增加', '通透性增加'],
  answer: { correct_option: 1 },
  explanation: '结合两类改变进行解释。',
  pointCodes: ['pathology.inflammation.vascular'],
  dimensionIds: [],
  medicalReviewStatus: 'approved',
  updatedAt: '2026-09-25T03:00:00Z',
  ...overrides,
})
const page = (items: TeacherQuestionBankItem[], total = items.length): TeacherQuestionBankPage => ({
  items,
  total,
  limit: 20,
  offset: 0,
})

function mountList() {
  return mount(QuestionBankIndex, {
    global: { stubs: { picker: true } },
  })
}
function mountDetail() {
  return mount(QuestionBankDetail, {
    global: {
      stubs: {
        picker: {
          template: '<div class="picker-stub" @click="$emit(\'change\', { detail: { value: 1 } })"><slot /></div>',
        },
      },
    },
  })
}

describe('T43 teacher-owned question bank pages', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    hooks.load = undefined
    hooks.show = undefined
    hooks.back = undefined
    identity.current = { openid: 'teacher-1', role: 'teacher' }
    api.requireRole.mockReturnValue(true)
    api.list.mockResolvedValue(page([bankItem()]))
    api.get.mockResolvedValue(bankItem())
    api.update.mockImplementation((_id: number, _version: number, content: Partial<TeacherQuestionBankItem>) =>
      Promise.resolve(bankItem({ ...content, version: 2 })),
    )
    api.delete.mockResolvedValue(undefined)
  })

  it('keeps list filters and routes the selected teacher-owned copy', async () => {
    const wrapper = mountList()
    hooks.load?.({ status: 'archived' })
    await flushPromises()

    expect(api.list).toHaveBeenCalledWith({
      taskType: undefined,
      pointCode: undefined,
      query: undefined,
      limit: 20,
      offset: 0,
    })
    expect(wrapper.get('.page-title').text()).toBe('个人题库')
    expect(wrapper.text()).toContain('教师个人资源')
    expect(wrapper.text()).toContain('不提供组卷或面向全班发布')
    await wrapper.get('.record-open').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/pages/teacher/question-bank/detail', {
      id: 12,
      resource: 'question-bank',
      keyword: undefined,
    })
  })

  it('preserves bank keyword/status through a deep-linked detail and returns to Content', async () => {
    const wrapper = mountDetail()
    hooks.load?.({ id: '12', keyword: '  血管  ', status: 'archived', resource: 'cases', returnUrl: '/pbl' })
    await flushPromises()
    hooks.back?.({ from: 'backbutton' })
    expect(api.handleBackPress).toHaveBeenCalledWith('backbutton', '/pages/teacher/content/index', {
      resource: 'question-bank',
      keyword: '血管',
    })
    wrapper.unmount()
    mountList()
    hooks.load?.({ keyword: '  血管  ', status: 'archived' })
    await flushPromises()
    expect(api.list).toHaveBeenLastCalledWith(expect.objectContaining({ query: '血管', offset: 0 }))
  })

  it('trims both search fields and resets pagination to the first page', async () => {
    const wrapper = mountList()
    hooks.load?.({})
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('  血管反应  ')
    await inputs[1].setValue('  pathology.inflammation.vascular  ')
    await wrapper.get('.search-button').trigger('click')
    await flushPromises()

    expect(api.list).toHaveBeenLastCalledWith({
      taskType: undefined,
      pointCode: 'pathology.inflammation.vascular',
      query: '血管反应',
      limit: 20,
      offset: 0,
    })
  })

  it('ignores legacy status links and renders no lifecycle controls', async () => {
    api.list.mockResolvedValue(page([]))
    const wrapper = mountList()
    hooks.load?.({ status: 'archived' })
    await flushPromises()
    expect(wrapper.text()).toContain('个人题库还是空的')
    expect(wrapper.find('.status-tab').exists()).toBe(false)
    expect(api.list.mock.calls[0][0]).not.toHaveProperty('status')
  })

  it('keeps existing records visible after a pagination error and retries the same page', async () => {
    api.list
      .mockResolvedValueOnce(page([bankItem({ id: 12 })], 2))
      .mockRejectedValueOnce(new Error('下一页暂不可读'))
      .mockResolvedValueOnce(page([bankItem({ id: 13, title: '第二道练习' })], 2))
    const wrapper = mountList()
    hooks.load?.({})
    await flushPromises()

    await wrapper.get('.more-button').trigger('click')
    await flushPromises()
    expect(api.list).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 1 }))
    expect(wrapper.text()).toContain('炎症血管反应目标验证')
    expect(wrapper.text()).toContain('下一页暂不可读')

    await wrapper.get('.inline-error button').trigger('click')
    await flushPromises()
    expect(api.list).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 0 }))
    expect(wrapper.text()).toContain('第二道练习')
    expect(wrapper.find('.inline-error').exists()).toBe(false)
  })

  it('does not let a slow search response overwrite a newer search', async () => {
    let resolveOld!: (value: TeacherQuestionBankPage) => void
    api.list
      .mockReturnValueOnce(new Promise<TeacherQuestionBankPage>((resolve) => (resolveOld = resolve)))
      .mockResolvedValueOnce(page([bankItem({ id: 13, title: '新的搜索结果' })]))
    const wrapper = mountList()
    hooks.load?.({})
    await wrapper.findAll('input')[0].setValue('新的')
    await wrapper.findAll('input')[0].trigger('confirm')
    await flushPromises()
    resolveOld(page([bankItem({ title: '较晚返回的旧结果' })]))
    await flushPromises()
    expect(wrapper.text()).toContain('新的搜索结果')
    expect(wrapper.text()).not.toContain('较晚返回的旧结果')
  })

  it('saves an edited immutable revision using the loaded version', async () => {
    const wrapper = mountDetail()
    hooks.load?.({ id: '12', status: 'active' })
    await flushPromises()

    await wrapper.find('input.field').setValue('修订后的题目标题')
    await wrapper.get('.primary-button').trigger('click')
    await flushPromises()

    expect(api.update).toHaveBeenCalledWith(
      12,
      1,
      expect.objectContaining({
        title: '修订后的题目标题',
        taskType: 'retest',
        options: ['血流增加', '通透性增加'],
        answer: { correct_option: 1 },
        pointCodes: ['pathology.inflammation.vascular'],
      }),
    )
    expect(wrapper.get('.page-title').text()).toBe('修订后的题目标题')
    expect(wrapper.text()).toContain('版本 v2')
    expect(wrapper.findAll('.actions button').map((button) => button.text())).toEqual(['保存修改', '删除题目'])
    expect(wrapper.text()).not.toContain('发布给全班')
  })

  it('deletes after one confirmation and returns with the search context', async () => {
    api.showModal.mockImplementation((options: { success?: (result: { confirm: boolean }) => void }) =>
      options.success?.({ confirm: true }),
    )
    Object.assign(uni, { showModal: api.showModal })
    const wrapper = mountDetail()
    hooks.load?.({ id: '12', keyword: '血管', status: 'archived' })
    await flushPromises()
    await wrapper.get('.delete-button').trigger('click')
    await flushPromises()
    expect(api.showModal).toHaveBeenCalledWith(expect.objectContaining({ title: '删除这道题？', confirmText: '删除' }))
    expect(api.delete).toHaveBeenCalledWith(12, 1, 't64-bank-delete-12-v1')
    expect(api.backOrRoute).toHaveBeenCalledWith('/pages/teacher/content/index', {
      resource: 'question-bank',
      keyword: '血管',
    })
    expect(wrapper.text()).not.toContain('炎症血管反应目标验证')
  })

  it('cancels deletion without writing and permits editing legacy archived data', async () => {
    api.get.mockResolvedValue(bankItem({ status: 'archived' }))
    api.showModal.mockImplementation((options: { success?: (result: { confirm: boolean }) => void }) =>
      options.success?.({ confirm: false }),
    )
    Object.assign(uni, { showModal: api.showModal })
    const wrapper = mountDetail()
    hooks.load?.({ id: '12' })
    await flushPromises()
    expect(wrapper.get('input.field').attributes('disabled')).toBeUndefined()
    await wrapper.get('.delete-button').trigger('click')
    await flushPromises()
    expect(api.delete).not.toHaveBeenCalled()
    expect(api.backOrRoute).not.toHaveBeenCalled()
    expect(wrapper.find('.delete-button').exists()).toBe(true)
    expect(wrapper.text()).not.toMatch(/医学状态|已归档|归档题目/)
  })

  it('retains edited fields and the record after a failed delete', async () => {
    api.delete.mockRejectedValue(new Error('删除暂不可用'))
    api.showModal.mockImplementation((options: { success?: (result: { confirm: boolean }) => void }) =>
      options.success?.({ confirm: true }),
    )
    Object.assign(uni, { showModal: api.showModal })
    const wrapper = mountDetail()
    hooks.load?.({ id: '12' })
    await flushPromises()
    await wrapper.get('input.field').setValue('未保存的修改')
    await wrapper.get('.delete-button').trigger('click')
    await flushPromises()
    expect((wrapper.get('input.field').element as HTMLInputElement).value).toBe('未保存的修改')
    expect(wrapper.text()).toContain('删除暂不可用')
    expect(api.backOrRoute).not.toHaveBeenCalled()
  })

  it('blocks repeated deletion and navigation after the teacher changes during a delete', async () => {
    let resolveDelete!: () => void
    api.delete.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveDelete = resolve
      }),
    )
    api.showModal.mockImplementation((options: { success?: (result: { confirm: boolean }) => void }) =>
      options.success?.({ confirm: true }),
    )
    Object.assign(uni, { showModal: api.showModal })
    const wrapper = mountDetail()
    hooks.load?.({ id: '12' })
    await flushPromises()
    await wrapper.get('.delete-button').trigger('click')
    await wrapper.get('.delete-button').trigger('click')
    expect(api.delete).toHaveBeenCalledTimes(1)
    identity.current = { openid: 'teacher-2', role: 'teacher' }
    hooks.show?.()
    resolveDelete()
    await flushPromises()
    expect(api.backOrRoute).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('教师账号已变更')
  })

  it('deletes a list record without clearing the search or other records', async () => {
    api.list.mockResolvedValue(page([bankItem(), bankItem({ id: 13, title: '保留的题目' })]))
    api.showModal.mockImplementation((options: { success?: (result: { confirm: boolean }) => void }) =>
      options.success?.({ confirm: true }),
    )
    Object.assign(uni, { showModal: api.showModal })
    const wrapper = mountList()
    hooks.load?.({ keyword: '血管' })
    await flushPromises()
    await wrapper.findAll('.record-delete')[0].trigger('click')
    await flushPromises()
    expect(api.delete).toHaveBeenCalledWith(12, 1, 't64-bank-delete-12-v1')
    expect(wrapper.text()).not.toContain('炎症血管反应目标验证')
    expect(wrapper.text()).toContain('保留的题目')
    expect((wrapper.findAll('input')[0].element as HTMLInputElement).value).toBe('血管')
  })

  it('does not query either bank page when the role guard rejects the session', async () => {
    api.requireRole.mockReturnValue(false)
    mountList()
    hooks.load?.({})
    await flushPromises()
    expect(api.list).not.toHaveBeenCalled()

    const detail = mountDetail()
    hooks.load?.({ id: '12' })
    await flushPromises()
    expect(api.get).not.toHaveBeenCalled()
    expect(detail.text()).toContain('教师账号已变更')
  })

  it('clears a pending bank detail response after the teacher account changes', async () => {
    let resolveItem!: (value: TeacherQuestionBankItem) => void
    api.get.mockReturnValueOnce(new Promise<TeacherQuestionBankItem>((resolve) => (resolveItem = resolve)))
    const wrapper = mountDetail()
    hooks.load?.({ id: '12' })

    identity.current = { openid: 'teacher-2', role: 'teacher' }
    hooks.show?.()
    expect(api.backOrRoute).not.toHaveBeenCalled()

    resolveItem(bankItem())
    await flushPromises()
    expect(wrapper.text()).toContain('教师账号已变更')
    expect(wrapper.text()).not.toContain('炎症血管反应目标验证')
  })
})
