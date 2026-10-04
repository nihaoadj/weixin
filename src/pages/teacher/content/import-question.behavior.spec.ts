import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ImportQuestionPage from './import-question.vue'
import type { TeacherQuestionBankSource } from '@/features/content/public'

const sourceId = '91111111-1111-4111-8111-111111111111'
const sourceId2 = '92222222-2222-4222-8222-222222222222'
const finalTestId = 'a1111111-1111-4111-8111-111111111111'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, unknown>) => void),
  show: undefined as undefined | (() => void),
  hide: undefined as undefined | (() => void),
  unload: undefined as undefined | (() => void),
  back: undefined as undefined | ((event: { from: 'backbutton' | 'navigateBack' }) => boolean | void),
}))
const auth = vi.hoisted(() => ({ allowed: true, session: { role: 'teacher', openid: 'teacher-a' } }))
const api = vi.hoisted(() => ({
  getSource: vi.fn(),
  importItem: vi.fn(),
  createRequestId: vi.fn(),
  backOrRoute: vi.fn(),
  goDetail: vi.fn(),
  handleBackPress: vi.fn(),
}))

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query?: Record<string, unknown>) => void) => {
    hooks.load = hook
  },
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onHide: (hook: () => void) => {
    hooks.hide = hook
  },
  onUnload: (hook: () => void) => {
    hooks.unload = hook
  },
  onBackPress: (hook: (event: { from: 'backbutton' | 'navigateBack' }) => boolean | void) => {
    hooks.back = hook
  },
}))
vi.mock('@/features/identity/public', () => ({
  getSession: () => auth.session,
  requireRole: () => auth.allowed,
}))
vi.mock('@/features/content/public', () => ({
  getTeacherQuestionBankSource: api.getSource,
  importTeacherQuestionBankItem: api.importItem,
}))
vi.mock('@/features/learning/public', () => ({ createLearningRequestId: api.createRequestId }))
vi.mock('@/platform/navigation', () => ({
  backOrRoute: api.backOrRoute,
  goDetail: api.goDetail,
  handleBackPress: api.handleBackPress,
  ROUTES: {
    teacherContent: '/pages/teacher/content/index',
    teacherLearningFinalTest: '/pages/teacher/learning/final-test',
    teacherQuestionBank: '/pages/teacher/question-bank/index',
    teacherQuestionBankDetail: '/pages/teacher/question-bank/detail',
  },
}))

const makeSource = (overrides: Partial<TeacherQuestionBankSource> = {}): TeacherQuestionBankSource => ({
  sourceType: 'route_test_question',
  sourceId,
  sourceDigest: 'a'.repeat(64),
  taskType: 'retest',
  title: '炎症血管反应',
  prompt: '炎症时哪项变化最有助于液体外渗？',
  options: ['通透性增加', '通透性降低', '血流停止', '胶原增多'],
  answer: { correct_option: 0 },
  explanation: '通透性增加可使液体和蛋白质进入组织间隙。',
  pointCodes: ['pathology.inflammation.vascular'],
  dimensionIds: ['reasoning.evidence'],
  ...overrides,
})

const importedItem = {
  id: 17,
  version: 1,
  status: 'active',
  medicalReviewStatus: null,
  updatedAt: '2026-09-30T04:00:00Z',
  taskType: 'retest',
  title: '炎症血管反应',
  prompt: '炎症时哪项变化最有助于液体外渗？',
  options: ['通透性增加', '通透性降低', '血流停止', '胶原增多'],
  answer: { correct_option: 0 },
  explanation: '通透性增加可使液体和蛋白质进入组织间隙。',
  pointCodes: ['pathology.inflammation.vascular'],
  dimensionIds: ['reasoning.evidence'],
}
let requestSequence = 0

function mountPage() {
  return mount(ImportQuestionPage, {
    global: {
      stubs: {
        MedState: {
          props: ['variant', 'icon', 'title', 'description', 'actionLabel', 'secondaryActionLabel'],
          emits: ['action', 'secondaryAction'],
          template:
            '<section class="med-state"><strong>{{ title }}</strong><span>{{ description }}</span><button v-if="actionLabel" class="med-action" @click="$emit(\'action\')">{{ actionLabel }}</button><button v-if="secondaryActionLabel" class="med-secondary" @click="$emit(\'secondaryAction\')">{{ secondaryActionLabel }}</button></section>',
        },
        'checkbox-group': {
          name: 'CheckboxGroupStub',
          emits: ['change'],
          template: '<div class="checkbox-group"><slot /></div>',
        },
        checkbox: { template: '<span class="checkbox" />' },
      },
    },
  })
}

async function showPage(query: Record<string, unknown> = { sourceId, finalTestId }) {
  const wrapper = mountPage()
  hooks.load?.(query)
  hooks.show?.()
  await flushPromises()
  return wrapper
}

async function confirmDeidentification(wrapper: ReturnType<typeof mountPage>) {
  wrapper.findComponent({ name: 'CheckboxGroupStub' }).vm.$emit('change', { detail: { value: ['confirm'] } })
  await flushPromises()
}

describe('teacher question-bank source import page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    hooks.load = undefined
    hooks.show = undefined
    hooks.hide = undefined
    hooks.unload = undefined
    hooks.back = undefined
    auth.allowed = true
    auth.session = { role: 'teacher', openid: 'teacher-a' }
    api.getSource.mockResolvedValue(makeSource())
    api.importItem.mockResolvedValue(importedItem)
    requestSequence = 0
    api.createRequestId.mockImplementation((operation: string) => `${operation}-${++requestSequence}`)
    api.handleBackPress.mockReturnValue(false)
  })

  it('validates the source link and teacher role before reading the authorized source', async () => {
    const invalid = await showPage({ sourceId: 'not-a-uuid' })
    expect(invalid.text()).toContain('题目来源链接无效')
    expect(api.getSource).not.toHaveBeenCalled()

    const invalidTestLink = await showPage({ sourceId, finalTestId: 'not-a-uuid' })
    expect(invalidTestLink.text()).toContain('题目来源链接无效')
    expect(api.getSource).not.toHaveBeenCalled()

    auth.allowed = false
    const denied = await showPage()
    expect(denied.text()).toContain('教师身份已变化')
    expect(api.getSource).not.toHaveBeenCalled()
  })

  it('renders an immutable source preview, gates exact import, and retries with the same request payload', async () => {
    api.importItem.mockRejectedValueOnce(new Error('题库暂不可用')).mockResolvedValueOnce(importedItem)
    const wrapper = await showPage()

    expect(api.getSource).toHaveBeenCalledWith(sourceId)
    expect(wrapper.text()).toContain('炎症时哪项变化最有助于液体外渗？')
    expect(wrapper.text()).toContain('正确答案')
    expect(wrapper.text()).toContain('通透性增加可使液体和蛋白质进入组织间隙。')
    expect(wrapper.findAll('input, textarea, picker')).toHaveLength(0)
    expect(wrapper.get('#import-source-question').attributes('disabled')).toBeDefined()

    await confirmDeidentification(wrapper)
    await wrapper.get('#import-source-question').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('题库暂不可用')
    expect(wrapper.get('#import-source-question').text()).toContain('重试加入同一副本')

    await wrapper.get('#import-source-question').trigger('click')
    await flushPromises()

    expect(api.importItem).toHaveBeenCalledTimes(2)
    expect(api.importItem.mock.calls[0]).toEqual(api.importItem.mock.calls[1])
    expect(api.importItem.mock.calls[1][0]).toEqual({
      ...makeSource(),
      clientRequestId: 'question-bank-import-1',
      deidentified: true,
    })
    expect(wrapper.text()).toContain('已加入独立题库副本')
    expect(wrapper.get('.success-panel').text()).toContain('原题和来源测试保持不变')

    await wrapper.get('.success-panel .primary').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/pages/teacher/question-bank/detail', { id: 17, status: 'active' })
    expect(api.backOrRoute).not.toHaveBeenCalled()
    await wrapper.get('.success-panel .quiet').trigger('click')
    expect(api.backOrRoute).toHaveBeenCalledWith('/pages/teacher/learning/final-test', { finalTestId })
  })

  it('prevents duplicate saves while in flight and keeps the request id after cancel and reentry', async () => {
    let resolveImport!: (value: typeof importedItem) => void
    api.importItem
      .mockRejectedValueOnce(new Error('请求结果暂未确认'))
      .mockReturnValueOnce(new Promise<typeof importedItem>((resolve) => (resolveImport = resolve)))
    const first = await showPage()
    await confirmDeidentification(first)
    await first.get('#import-source-question').trigger('click')
    await flushPromises()
    const firstRequestId = api.importItem.mock.calls[0][0].clientRequestId
    expect(first.text()).toContain('请求结果暂未确认')

    await first.get('.actions .quiet').trigger('click')
    const reopened = await showPage()
    await confirmDeidentification(reopened)
    await reopened.get('#import-source-question').trigger('click')
    await flushPromises()
    expect(reopened.get('#import-source-question').attributes('disabled')).toBeDefined()
    expect(hooks.back?.({ from: 'backbutton' })).toBe(true)
    await reopened.get('#import-source-question').trigger('click')
    expect(api.importItem).toHaveBeenCalledTimes(2)
    expect(api.importItem.mock.calls[1][0].clientRequestId).toBe(firstRequestId)

    resolveImport(importedItem)
    await flushPromises()
    expect(reopened.text()).toContain('已加入独立题库副本')
    expect(api.importItem).toHaveBeenCalledTimes(2)
  })

  it('requires reload and renewed confirmation after the source digest changes', async () => {
    const original = makeSource({ sourceId: sourceId2 })
    const updated = makeSource({
      sourceId: sourceId2,
      sourceDigest: 'b'.repeat(64),
      prompt: '更新后的炎症题干？',
    })
    api.getSource.mockResolvedValueOnce(original).mockResolvedValueOnce(updated)
    api.importItem
      .mockRejectedValueOnce(Object.assign(new Error('来源题目已更新，请重新预览'), { code: 'STATE_CONFLICT' }))
      .mockResolvedValueOnce(importedItem)
    const wrapper = await showPage({ sourceId: sourceId2, finalTestId })
    await confirmDeidentification(wrapper)
    await wrapper.get('#import-source-question').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('重新读取授权来源')
    expect(wrapper.get('#import-source-question').attributes('disabled')).toBeDefined()
    await wrapper.get('.conflict button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('来源内容已更新')
    expect(wrapper.text()).toContain('更新后的炎症题干？')
    expect(wrapper.get('#import-source-question').attributes('disabled')).toBeDefined()
    await confirmDeidentification(wrapper)
    await wrapper.get('#import-source-question').trigger('click')
    await flushPromises()

    expect(api.getSource).toHaveBeenCalledTimes(2)
    expect(api.importItem).toHaveBeenCalledTimes(2)
    expect(api.importItem.mock.calls[0][0].clientRequestId).not.toBe(api.importItem.mock.calls[1][0].clientRequestId)
    expect(api.importItem.mock.calls[1][0]).toMatchObject({
      sourceDigest: 'b'.repeat(64),
      prompt: '更新后的炎症题干？',
    })
  })

  it('keeps load errors recoverable and cancellation returns to the source test without importing', async () => {
    api.getSource.mockRejectedValueOnce(new Error('来源暂不可用')).mockResolvedValueOnce(makeSource())
    const wrapper = await showPage()
    expect(wrapper.text()).toContain('来源暂不可用')
    await wrapper.get('.med-action').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('炎症血管反应')
    await wrapper.get('.actions .quiet').trigger('click')
    expect(api.backOrRoute).toHaveBeenCalledWith('/pages/teacher/learning/final-test', { finalTestId })
    expect(api.importItem).not.toHaveBeenCalled()

    const withoutTest = await showPage({ sourceId })
    await withoutTest.get('.actions .quiet').trigger('click')
    expect(api.backOrRoute).toHaveBeenLastCalledWith('/pages/teacher/question-bank/index', { status: 'active' })
  })

  it('ignores a slow response from the previous teacher identity', async () => {
    let resolvePrevious!: (value: TeacherQuestionBankSource) => void
    api.getSource
      .mockReturnValueOnce(new Promise<TeacherQuestionBankSource>((resolve) => (resolvePrevious = resolve)))
      .mockResolvedValueOnce(makeSource({ sourceId, title: '新教师授权的来源' }))
    const wrapper = mountPage()
    hooks.load?.({ sourceId, finalTestId })
    hooks.show?.()
    await flushPromises()

    auth.session = { role: 'teacher', openid: 'teacher-b' }
    hooks.show?.()
    await flushPromises()
    resolvePrevious(makeSource({ title: '旧教师来源' }))
    await flushPromises()

    expect(api.getSource).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('新教师授权的来源')
    expect(wrapper.text()).not.toContain('旧教师来源')
  })
})
