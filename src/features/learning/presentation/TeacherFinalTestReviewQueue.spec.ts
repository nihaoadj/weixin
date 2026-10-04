import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherFinalTestReviewQueue from './TeacherFinalTestReviewQueue.vue'

const api = vi.hoisted(() => ({ read: vi.fn() }))
vi.mock('@/features/learning/public', () => ({ getTeacherFinalTestReviewQueue: api.read }))
const result = (id: string, canReview = true, canRetry = false) => ({
  items: [
    {
      id,
      title: '固定最终测试',
      studentName: id,
      className: '病理班',
      generationState: canRetry ? 'generation_failed' : 'ready',
      reviewState: 'pending_review',
      canReview,
      canRetry,
    },
  ],
  counts: { pendingReview: 1, needsChanges: 0, generationFailed: 0 },
  total: 1,
  offset: 0,
  limit: 20,
})
function render() {
  return mount(TeacherFinalTestReviewQueue, {
    props: { classId: 1 },
    global: {
      stubs: {
        MedState: { props: ['title', 'description'], template: '<div>{{ title }} {{ description }}</div>' },
        TeacherPager: true,
      },
    },
  })
}
describe('teacher final-test actionable queue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  it('ignores a late response from the previous classroom scope', async () => {
    let oldResolve!: (value: unknown) => void
    api.read
      .mockReturnValueOnce(
        new Promise((resolve) => {
          oldResolve = resolve
        }),
      )
      .mockResolvedValueOnce(result('new'))
    const wrapper = render()
    await wrapper.setProps({ classId: 2 })
    await flushPromises()
    expect(wrapper.text()).toContain('new')
    oldResolve(result('old'))
    await flushPromises()
    expect(wrapper.text()).not.toContain('old')
    expect(api.read).toHaveBeenLastCalledWith(expect.objectContaining({ classId: 2, limit: 20, offset: 0 }))
  })
  it('uses explicit retry permission and only navigates to the existing test', async () => {
    api.read.mockResolvedValue(result('failed-test', false, true))
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('测试生成失败')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('openFinalTest')).toEqual([['failed-test']])
  })
  it('does not display successful counts or stale rows after a failed scope change', async () => {
    api.read.mockResolvedValueOnce(result('old')).mockRejectedValueOnce(new Error('权限已变化'))
    const wrapper = render()
    await flushPromises()
    await wrapper.setProps({ classId: 2 })
    await flushPromises()
    expect(wrapper.text()).toContain('权限已变化')
    expect(wrapper.text()).not.toContain('old')
    expect(wrapper.find('.queue-counts').exists()).toBe(false)
  })
})
