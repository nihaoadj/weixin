import { computed, defineComponent, h, provide, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherPageFrame from './TeacherPageFrame.vue'
import { teacherScreenKey, type TeacherScreenContext } from './teacherScreenContext'

const navigation = vi.hoisted(() => ({ switchWorkspace: vi.fn(), horizontalSwipe: vi.fn(), swipeProgress: vi.fn() }))
vi.mock('@/features/identity/public', () => ({ logout: vi.fn() }))
vi.mock('@/platform/navigation/teacher', () => ({ switchTeacherWorkspace: navigation.switchWorkspace }))
vi.mock('@/platform/navigation/teacherSwipeMotion', () => ({
  clearTeacherSwipeEntry: vi.fn(),
  prepareTeacherSwipeEntry: vi.fn(),
  takeTeacherSwipeEntry: vi.fn(),
}))

const runtime = {
  getWindowInfo: vi.fn(() => ({ windowWidth: 375 })),
  onWindowResize: vi.fn(),
  offWindowResize: vi.fn(),
}
const wrappers: Array<ReturnType<typeof mount>> = []

function createContext(): TeacherScreenContext {
  return {
    active: ref(true),
    show: ref(0),
    query: {},
    insights: ref(undefined),
    position: computed(() => 1),
    selectPanel: vi.fn(),
    block: vi.fn(),
    ready: vi.fn(),
  }
}

function mountEmbeddedFrame() {
  const context = createContext()
  const wrapper = mount(
    defineComponent({
      setup() {
        provide(teacherScreenKey, context)
        return () =>
          h(
            TeacherPageFrame,
            {
              active: 'insights',
              title: '学情',
              panelSwipes: true,
              swipeContext: 'overview',
              onHorizontalSwipe: navigation.horizontalSwipe,
              onSwipeProgress: navigation.swipeProgress,
            },
            { default: () => h('div', { class: 'embedded-content' }, '正文') },
          )
      },
    }),
    { global: { stubs: { MedIcon: true, 'scroll-view': true } } },
  )
  wrappers.push(wrapper)
  return wrapper
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  vi.stubGlobal('uni', runtime)
})

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  vi.clearAllTimers()
  vi.useRealTimers()
})

describe('teacher page frame embedded mode', () => {
  it('keeps navigation inside the deck and does not install legacy swipes or bottom navigation', async () => {
    const wrapper = mountEmbeddedFrame()
    const frame = wrapper.get('.teacher-frame')
    expect(frame.classes()).toContain('teacher-frame--embedded')
    expect(wrapper.find('.teacher-frame__navigation').exists()).toBe(false)

    await frame.trigger('touchstart', { touches: [{ clientX: 250, clientY: 80 }], changedTouches: [] })
    await vi.advanceTimersByTimeAsync(40)
    await frame.trigger('touchmove', { touches: [{ clientX: 80, clientY: 80 }], changedTouches: [] })
    await vi.advanceTimersByTimeAsync(10)
    await frame.trigger('touchend', { touches: [], changedTouches: [{ clientX: 80, clientY: 80 }] })
    await vi.advanceTimersByTimeAsync(300)

    expect(navigation.horizontalSwipe).not.toHaveBeenCalled()
    expect(navigation.swipeProgress).not.toHaveBeenCalled()
    expect(navigation.switchWorkspace).not.toHaveBeenCalled()
    expect(wrapper.get('.teacher-frame__body').classes()).not.toContain('teacher-frame__body--moving')

    await frame.trigger('touchstart', { touches: [{ clientX: 180, clientY: 80 }], changedTouches: [] })
    await frame.trigger('touchcancel')
    expect(wrapper.get('.teacher-frame__body').classes()).not.toContain('teacher-frame__body--moving')
    expect((wrapper.get('.teacher-frame__body').element as HTMLElement).style.transform).toBe('none')
  })
})
