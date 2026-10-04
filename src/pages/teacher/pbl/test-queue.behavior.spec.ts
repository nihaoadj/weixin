import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TestQueuePage from './test-queue.vue'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, string>) => void),
  show: undefined as undefined | (() => unknown),
}))
const api = vi.hoisted(() => ({ classes: vi.fn(), refresh: vi.fn(), goDetail: vi.fn(), back: vi.fn() }))
const auth = vi.hoisted(() => ({ session: { role: 'teacher', openid: 'teacher-t54' } }))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (cb: typeof hooks.load) => {
    hooks.load = cb
  },
  onShow: (cb: typeof hooks.show) => {
    hooks.show = cb
  },
  onBackPress: vi.fn(),
}))
vi.mock('@/features/identity/public', () => ({
  getSession: () => auth.session,
  requireRole: vi.fn(),
}))
vi.mock('@/features/classroom/public', () => ({ getTeacherClasses: api.classes }))
vi.mock('@/platform/navigation', () => ({
  ROUTES: { teacherLearningFinalTest: '/teacher/test', teacherPbl: '/teacher/pbl' },
  goDetail: api.goDetail,
  backOrRoute: api.back,
  handleBackPress: vi.fn(),
}))
vi.mock('@/features/learning/presentation/TeacherFinalTestReviewQueue.vue', () => ({
  default: {
    name: 'QueueProbe',
    props: ['classId', 'sessionId', 'initialKind'],
    emits: ['openFinalTest', 'kindChange'],
    setup(_props: unknown, { expose }: { expose: (value: unknown) => void }) {
      expose({ refresh: api.refresh })
    },
    template: '<div class="queue-probe" />',
  },
}))

const mountPage = () =>
  mount(TestQueuePage, {
    global: {
      stubs: {
        picker: { template: '<div><slot /></div>' },
        MedState: { props: ['title'], template: '<div>{{ title }}</div>' },
      },
    },
  })
beforeEach(() => {
  vi.clearAllMocks()
  auth.session = { role: 'teacher', openid: 'teacher-t54' }
  api.classes.mockResolvedValue([{ id: 3, name: '病理班', status: 'active' }])
})
describe('independent teacher test queue', () => {
  it('clears the previous teacher classroom and category when identity changes', async () => {
    const wrapper = mountPage()
    hooks.load?.({ classId: '3', sessionId: '9', reviewKind: 'needs_changes' })
    await hooks.show?.()
    await flushPromises()
    const originalQueue = wrapper.findComponent({ name: 'QueueProbe' })
    expect(originalQueue.props('sessionId')).toBe(9)
    auth.session = { role: 'teacher', openid: 'teacher-t54-other' }
    api.classes.mockResolvedValue([{ id: 4, name: '另一教师班级', status: 'active' }])
    await hooks.show?.()
    await flushPromises()
    const currentQueue = wrapper.findComponent({ name: 'QueueProbe' })
    expect(currentQueue.vm).not.toBe(originalQueue.vm)
    expect(currentQueue.props()).toEqual({ classId: undefined, sessionId: undefined, initialKind: undefined })
    currentQueue.vm.$emit('openFinalTest', 'test-2')
    expect(api.goDetail).toHaveBeenLastCalledWith('/teacher/test', {
      finalTestId: 'test-2',
      classId: undefined,
      sessionId: undefined,
      returnSection: 'diagnostics',
      reviewKind: undefined,
    })
    wrapper.unmount()
  })
  it('preserves class, classroom and category while opening a final test', async () => {
    const wrapper = mountPage()
    hooks.load?.({ classId: '3', sessionId: '9', reviewKind: 'needs_changes' })
    await hooks.show?.()
    await flushPromises()
    const queue = wrapper.findComponent({ name: 'QueueProbe' })
    expect(queue.props()).toEqual({ classId: 3, sessionId: 9, initialKind: 'needs_changes' })
    queue.vm.$emit('openFinalTest', 'test-1')
    expect(api.goDetail).toHaveBeenCalledWith('/teacher/test', {
      finalTestId: 'test-1',
      classId: 3,
      sessionId: 9,
      returnSection: 'diagnostics',
      reviewKind: 'needs_changes',
    })
    await wrapper.get('.queue-back').trigger('click')
    expect(api.back).toHaveBeenCalledWith('/teacher/pbl')
    wrapper.unmount()
  })
  it('does not mount or request the queue for a class outside teacher ownership', async () => {
    const wrapper = mountPage()
    hooks.load?.({ classId: '99', reviewKind: 'generation_failed' })
    await hooks.show?.()
    await flushPromises()
    expect(wrapper.text()).toContain('该班级不在当前教师范围内')
    expect(wrapper.find('.queue-probe').exists()).toBe(false)
    expect(api.refresh).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
