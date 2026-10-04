import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import TeacherPageFrame from './TeacherPageFrame.vue'

const navigation = vi.hoisted(() => ({
  switchWorkspace: vi.fn(),
  prepareEntry: vi.fn(),
  clearEntry: vi.fn(),
  takeEntry: vi.fn(),
}))
vi.mock('@/features/identity/public', () => ({ logout: vi.fn() }))
vi.mock('@/platform/navigation/teacher', () => ({ switchTeacherWorkspace: navigation.switchWorkspace }))
vi.mock('@/platform/navigation/teacherSwipeMotion', () => ({
  clearTeacherSwipeEntry: navigation.clearEntry,
  prepareTeacherSwipeEntry: navigation.prepareEntry,
  takeTeacherSwipeEntry: navigation.takeEntry,
}))

const runtime = {
  getWindowInfo: vi.fn<() => { windowWidth: number }>(),
  onWindowResize: vi.fn<(callback: () => void) => void>(),
  offWindowResize: vi.fn<(callback: () => void) => void>(),
}
const wrappers: Array<ReturnType<typeof mount>> = []

function mountFrame(props: Record<string, unknown>, slots: Record<string, string> = {}) {
  const wrapper = mount(TeacherPageFrame, {
    props: { active: 'pbl', title: '课堂教学', referenceLayout: true, ...props },
    slots,
    global: { stubs: { MedIcon: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

function unmount(wrapper: ReturnType<typeof mount>) {
  wrapper.unmount()
  const index = wrappers.indexOf(wrapper)
  if (index >= 0) wrappers.splice(index, 1)
}

async function swipe(wrapper: ReturnType<typeof mount>, direction: 'left' | 'right', distance = 100, duration = 40) {
  const startX = direction === 'left' ? 220 : 100
  const endX = startX + (direction === 'left' ? -distance : distance)
  await wrapper.trigger('touchstart', {
    touches: [{ clientX: startX, clientY: 80 }],
    changedTouches: [],
  })
  await vi.advanceTimersByTimeAsync(duration)
  await wrapper.trigger('touchmove', {
    touches: [{ clientX: endX, clientY: 80 }],
    changedTouches: [],
  })
  await vi.advanceTimersByTimeAsync(10)
  await wrapper.trigger('touchend', {
    touches: [],
    changedTouches: [{ clientX: endX, clientY: 80 }],
  })
  await nextTick()
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-03T00:00:00Z'))
  for (const mock of Object.values(navigation)) mock.mockReset()
  runtime.getWindowInfo.mockReset().mockReturnValue({ windowWidth: 375 })
  runtime.onWindowResize.mockReset()
  runtime.offWindowResize.mockReset()
  const baseUni = uni as unknown as Record<string, unknown>
  vi.stubGlobal('uni', { ...baseUni, ...runtime })
})

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  vi.clearAllTimers()
  vi.useRealTimers()
})

describe('teacher page frame swipe motion', () => {
  it('shows PBL, insights, and content in the shared navigation order', () => {
    const wrapper = mountFrame({ active: 'pbl' })
    expect(wrapper.findAll('.teacher-frame__nav-item').map((item) => item.text())).toEqual(['PBL', '学情', '内容'])
  })

  it('keeps navigation available with fixed content and restores outer scrolling when it is disabled', async () => {
    const wrapper = mountFrame(
      { active: 'insights', fixedContent: true },
      { default: '<div class="record-content">学生列表</div>' },
    )
    expect(wrapper.find('.teacher-frame__scroll').exists()).toBe(false)
    expect(wrapper.get('.teacher-frame__fixed .record-content').text()).toBe('学生列表')
    await wrapper.findAll('.teacher-frame__nav-item')[0]!.trigger('click')
    expect(navigation.switchWorkspace).toHaveBeenCalledWith('pbl')

    await wrapper.setProps({ fixedContent: false })
    expect(wrapper.find('.teacher-frame__fixed').exists()).toBe(false)
    expect(wrapper.get('.teacher-frame__scroll .record-content').text()).toBe('学生列表')
  })

  it('commits swipes once after their leave animation and never wraps at workspace ends', async () => {
    const pbl = mountFrame({ active: 'pbl' })
    pbl.setProps({})
    await swipe(pbl, 'left')
    expect(pbl.get('.teacher-frame__body').classes()).toContain('teacher-frame__body--moving')
    expect(navigation.switchWorkspace).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(179)
    expect(navigation.switchWorkspace).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(navigation.switchWorkspace).toHaveBeenCalledExactlyOnceWith('insights')
    expect(navigation.prepareEntry).toHaveBeenCalledExactlyOnceWith('insights', 'left')
    unmount(pbl)

    navigation.switchWorkspace.mockReset()
    navigation.prepareEntry.mockReset()
    const insights = mountFrame({ active: 'insights' })
    await swipe(insights, 'left')
    await vi.advanceTimersByTimeAsync(180)
    expect(navigation.switchWorkspace).toHaveBeenCalledExactlyOnceWith('content')
    unmount(insights)

    navigation.switchWorkspace.mockReset()
    navigation.prepareEntry.mockReset()
    const content = mountFrame({ active: 'content' })
    await swipe(content, 'right')
    await vi.advanceTimersByTimeAsync(180)
    expect(navigation.switchWorkspace).toHaveBeenCalledExactlyOnceWith('insights')
    expect(navigation.prepareEntry).toHaveBeenCalledExactlyOnceWith('insights', 'right')
    unmount(content)

    navigation.switchWorkspace.mockReset()
    const firstEdge = mountFrame({ active: 'pbl' })
    await swipe(firstEdge, 'right')
    expect(firstEdge.get('.teacher-frame__body').classes()).toContain('teacher-frame__body--moving')
    await swipe(firstEdge, 'left')
    expect(navigation.switchWorkspace).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(240)
    expect(firstEdge.get('.teacher-frame__body').classes()).not.toContain('teacher-frame__body--moving')
    unmount(firstEdge)

    const lastEdge = mountFrame({ active: 'content' })
    await swipe(lastEdge, 'left')
    await vi.advanceTimersByTimeAsync(240)
    expect(navigation.switchWorkspace).not.toHaveBeenCalled()
    unmount(lastEdge)
  })

  it('emits drag progress and animates same-page context handoff without root navigation', async () => {
    const wrapper = mountFrame({ active: 'insights', panelSwipes: true, swipeContext: 'overview' })
    await swipe(wrapper, 'left')
    expect(wrapper.emitted('swipeProgress')?.[0]?.[0]).toEqual({ direction: 'left', progress: 100 / 375 })
    expect(wrapper.emitted('horizontalSwipe')).toBeUndefined()

    await vi.advanceTimersByTimeAsync(180)
    expect(wrapper.emitted('horizontalSwipe')).toEqual([['left']])
    expect(navigation.switchWorkspace).not.toHaveBeenCalled()
    await wrapper.setProps({ swipeContext: 'knowledge' })
    await nextTick()
    await nextTick()

    const body = wrapper.get('.teacher-frame__body').element as HTMLElement
    expect(body.style.transform).toBe('translate3d(375px, 0, 0)')
    expect(body.style.transition).toBe('none')
    await vi.advanceTimersByTimeAsync(32)
    expect((wrapper.get('.teacher-frame__body').element as HTMLElement).style.transform).toBe('translate3d(0px, 0, 0)')
    await vi.advanceTimersByTimeAsync(240)
    expect(wrapper.get('.teacher-frame__body').classes()).not.toContain('teacher-frame__body--moving')
  })

  it('enters from the matching workspace direction after render', async () => {
    navigation.takeEntry.mockReturnValueOnce('left')
    const wrapper = mountFrame({ active: 'insights' })
    await nextTick()
    await nextTick()
    expect(navigation.takeEntry).toHaveBeenCalledExactlyOnceWith('insights')
    const body = wrapper.get('.teacher-frame__body').element as HTMLElement
    expect(body.style.transform).toBe('translate3d(375px, 0, 0)')
    expect(body.style.transition).toBe('none')

    await vi.advanceTimersByTimeAsync(32)
    expect((wrapper.get('.teacher-frame__body').element as HTMLElement).style.transform).toBe('translate3d(0px, 0, 0)')
    await vi.advanceTimersByTimeAsync(240)
    expect(wrapper.get('.teacher-frame__body').classes()).not.toContain('teacher-frame__body--moving')
  })

  it('blocks gestures while disabled and during the return animation', async () => {
    const wrapper = mountFrame({ active: 'insights', swipeDisabled: true })
    await swipe(wrapper, 'left')
    expect(navigation.switchWorkspace).not.toHaveBeenCalled()
    expect(wrapper.emitted('swipeProgress')).toBeUndefined()

    await wrapper.setProps({ swipeDisabled: false })
    await swipe(wrapper, 'left', 20, 100)
    expect(wrapper.get('.teacher-frame__body').classes()).toContain('teacher-frame__body--moving')
    await swipe(wrapper, 'left')
    expect(navigation.switchWorkspace).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(189)
    expect(wrapper.get('.teacher-frame__body').classes()).toContain('teacher-frame__body--moving')
    await vi.advanceTimersByTimeAsync(1)
    expect(wrapper.get('.teacher-frame__body').classes()).not.toContain('teacher-frame__body--moving')
  })

  it('resets on viewport resize and removes its resize listener on unmount', async () => {
    const wrapper = mountFrame({ active: 'insights' })
    const resize = runtime.onWindowResize.mock.calls[0]?.[0]
    expect(resize).toBeDefined()

    await wrapper.trigger('touchstart', { touches: [{ clientX: 150, clientY: 80 }], changedTouches: [] })
    await wrapper.trigger('touchmove', { touches: [{ clientX: 110, clientY: 80 }], changedTouches: [] })
    expect(wrapper.get('.teacher-frame__body').classes()).toContain('teacher-frame__body--moving')
    runtime.getWindowInfo.mockReturnValue({ windowWidth: 500 })
    resize?.()
    await nextTick()
    expect(wrapper.get('.teacher-frame__body').classes()).not.toContain('teacher-frame__body--moving')

    unmount(wrapper)
    expect(runtime.offWindowResize).toHaveBeenCalledExactlyOnceWith(resize)
  })
})
