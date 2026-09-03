import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProblemEdit from './problem-edit.vue'
import type { Problem } from '@/types/domain'

const { findProblem, upsertProblem, backOrRoute, handleBackPress, routeOptions } = vi.hoisted(() => ({
  findProblem: vi.fn(),
  upsertProblem: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
  routeOptions: { value: {} as Record<string, string> },
}))

vi.mock('@/features/content/public', () => ({ findProblemAsync: findProblem, upsertProblemAsync: upsertProblem }))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true }))
vi.mock('@/platform/navigation', () => ({
  backOrRoute,
  handleBackPress,
  ROUTES: { teacherWorkspace: '/workspace' },
}))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query: Record<string, string>) => void) => hook(routeOptions.value),
  onBackPress: vi.fn(),
}))

function exampleProblem(overrides: Partial<Problem> = {}): Problem {
  return {
    id: 'problem-editor-test',
    type: '医学常识',
    title: '抗菌药物合理使用',
    description: '请结合适应证与不良反应监测说明。',
    target: 'all',
    targetIds: [],
    targetLabel: '全体学生',
    status: '待审核',
    time: '2026-08-31',
    ...overrides,
  }
}

beforeEach(() => {
  routeOptions.value = {}
  findProblem.mockReset()
  upsertProblem.mockReset().mockResolvedValue(exampleProblem())
  backOrRoute.mockReset()
})

describe('teacher problem editor', () => {
  it('provides a stack-safe return action before any draft is saved', async () => {
    const wrapper = mount(ProblemEdit)
    const returnButton = wrapper.findAll('button').find((button) => button.text() === '返回')
    await returnButton?.trigger('click')
    expect(backOrRoute).toHaveBeenCalledWith('/workspace', { tab: 'problems' })
  })

  it('confirms before leaving when the current problem has unsaved changes', async () => {
    const wrapper = mount(ProblemEdit)
    await wrapper.get('#problem-title').setValue('尚未保存的问题')
    const returnButton = wrapper.findAll('button').find((button) => button.text() === '返回')
    await returnButton?.trigger('click')

    expect(uni.showModal).toHaveBeenCalledWith(
      expect.objectContaining({ title: '离开问题编写？', confirmText: '离开' }),
    )
    expect(backOrRoute).not.toHaveBeenCalled()

    const options = vi.mocked(uni.showModal).mock.calls[0]?.[0]
    if (!options) {
      throw new Error('Expected the leave-confirmation modal to be opened.')
    }
    options.success?.({ confirm: true, cancel: false, content: '' })
    expect(backOrRoute).toHaveBeenCalledWith('/workspace', { tab: 'problems' })
  })

  it('separates task content, audience choice, and the pending-review save state', () => {
    const wrapper = mount(ProblemEdit)
    expect(wrapper.get('[aria-level="1"]').text()).toBe('新建教学问题')
    expect(wrapper.get('.form').text()).toContain('题目内容')
    expect(wrapper.get('.scope-panel').text()).toContain('发布范围')
    expect(wrapper.findAll('.type-choice')).toHaveLength(3)
    expect(wrapper.findAll('.target-choice')).toHaveLength(3)
    expect(wrapper.get('#problem-title').attributes('maxlength')).toBe('200')
    expect(wrapper.get('.target-choice.active .target-check').text()).toBe('✓')
    for (const button of [...wrapper.findAll('.type-choice'), ...wrapper.findAll('.target-choice')]) {
      expect(button.attributes('role')).toBe('button')
      expect(button.attributes('tabindex')).toBe('0')
      expect(button.attributes('aria-disabled')).toBe('false')
    }
    expect(wrapper.get('.save-panel').text()).toContain('保存不会直接向学生发布')
    expect(wrapper.find('label[for="problem-title"]').exists()).toBe(true)
    expect(wrapper.find('label[for="problem-description"]').exists()).toBe(true)
  })

  it('keeps validation visible and does not save a title-less problem', async () => {
    const wrapper = mount(ProblemEdit)
    await wrapper.get('.save').trigger('click')
    await flushPromises()
    expect(wrapper.get('#problem-title-error').text()).toContain('请填写问题标题')
    expect(wrapper.get('#problem-title').attributes('aria-invalid')).toBe('true')
    expect(upsertProblem).not.toHaveBeenCalled()
  })

  it('saves a target-specific task only when its label and IDs are complete', async () => {
    const wrapper = mount(ProblemEdit)
    await wrapper.get('#problem-title').setValue('肺炎鉴别诊断训练')
    await wrapper.get('.target-choice:nth-child(2)').trigger('click')
    await wrapper.get('.save').trigger('click')
    await flushPromises()
    expect(wrapper.get('#target-error').text()).toContain('发布对象名称和 ID')
    expect(upsertProblem).not.toHaveBeenCalled()

    await wrapper.get('#target-label').setValue('临床一班')
    await wrapper.get('#target-ids').setValue('class-a, class-b')
    await wrapper.get('.save').trigger('click')
    await flushPromises()
    expect(upsertProblem).toHaveBeenCalledWith(
      expect.objectContaining({
        title: '肺炎鉴别诊断训练',
        target: 'class',
        targetLabel: '临床一班',
        targetIds: ['class-a', 'class-b'],
        status: '待审核',
      }),
    )
    expect(backOrRoute).toHaveBeenCalledWith('/workspace', { tab: 'problems' })
  })

  it('preserves an unknown existing type and blocks a missing editor route from creating a new task', async () => {
    routeOptions.value = { id: 'missing-problem' }
    findProblem.mockResolvedValueOnce(undefined)
    const missing = mount(ProblemEdit)
    await flushPromises()
    expect(missing.get('.editor-unavailable').text()).toContain('题目不存在')
    expect(missing.find('.form').exists()).toBe(false)
    await missing.get('.return-button').trigger('click')
    expect(backOrRoute).toHaveBeenCalledWith('/workspace', { tab: 'problems' })

    routeOptions.value = { id: 'extended-type' }
    findProblem.mockResolvedValueOnce(exampleProblem({ id: 'extended-type', type: '病例单选' }))
    const existing = mount(ProblemEdit)
    await flushPromises()
    expect(existing.get('[aria-level="1"]').text()).toBe('调整教学问题')
    expect(existing.get('.type-choice.active').text()).toBe('病例单选')
    expect(existing.findAll('.type-choice')).toHaveLength(4)
  })

  it('disables duplicate saves while an asynchronous save is in flight', async () => {
    let resolveSave: () => void = () => {}
    upsertProblem.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveSave = resolve
        }),
    )
    const wrapper = mount(ProblemEdit)
    await wrapper.get('#problem-title').setValue('肺炎鉴别诊断训练')
    await wrapper.get('.save').trigger('click')
    await wrapper.get('.save').trigger('click')
    expect(upsertProblem).toHaveBeenCalledTimes(1)
    expect(wrapper.get('.save').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.save').attributes('aria-disabled')).toBe('true')
    for (const button of [...wrapper.findAll('.type-choice'), ...wrapper.findAll('.target-choice')]) {
      expect(button.attributes('disabled')).toBeDefined()
      expect(button.attributes('aria-disabled')).toBe('true')
      expect(button.attributes('tabindex')).toBe('-1')
    }
    resolveSave()
    await flushPromises()
  })
})
