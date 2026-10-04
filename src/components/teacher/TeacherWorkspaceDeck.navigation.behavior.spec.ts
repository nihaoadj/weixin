import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherPageFrame from './TeacherPageFrame.vue'
import TeacherWorkspaceDeck from './TeacherWorkspaceDeck.vue'

const state = vi.hoisted(() => ({
  showHooks: [] as Array<() => unknown>,
  preferencePanel: 'overview',
  navigation: {
    switchWorkspace: vi.fn(),
    clearEntry: vi.fn(),
    prepareEntry: vi.fn(),
    takeEntry: vi.fn(),
  },
  runtime: {} as Record<string, ReturnType<typeof vi.fn>>,
}))

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: () => undefined,
  onShow: (hook: () => unknown) => state.showHooks.push(hook),
}))
vi.mock('@/features/identity/public', () => ({
  getSession: () => ({ openid: 'teacher-a', role: 'teacher' }),
  logout: vi.fn(),
}))
vi.mock('@/platform/navigation/teacherPreferences', () => ({
  readTeacherInsightsPreference: () => ({ panel: state.preferencePanel }),
}))
vi.mock('@/platform/navigation/teacherSwipeMotion', () => ({
  clearTeacherSwipeEntry: state.navigation.clearEntry,
  prepareTeacherSwipeEntry: state.navigation.prepareEntry,
  takeTeacherSwipeEntry: state.navigation.takeEntry,
}))
vi.mock('@/platform/navigation/teacher', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/platform/navigation/teacher')>()),
  switchTeacherWorkspace: state.navigation.switchWorkspace,
}))
vi.mock('./TeacherWorkspacePane.vue', async () => {
  const { defineComponent, h, ref } = await import('vue')
  return {
    default: defineComponent({
      name: 'NavigationPaneProbe',
      props: { index: Number, current: Number, context: Object },
      setup(props) {
        const ready = ref(false)
        const blocked = ref(false)
        const context = props.context as {
          ready: () => void
          block: (value: boolean) => void
          selectPanel: (panel: 'students') => void
          panel?: string
        }
        return () =>
          h('section', { class: 'navigation-pane-probe', 'data-index': props.index, 'data-current': props.current }, [
            !ready.value ? h('p', { class: 'pane-loading' }, '正在读取班级范围') : null,
            h('span', { class: 'pane-panel' }, context.panel || 'pbl/content'),
            h(
              'button',
              {
                class: 'pane-ready',
                onClick: () => {
                  ready.value = true
                  context.ready()
                },
              },
              'ready',
            ),
            h(
              'button',
              {
                class: 'pane-select-students',
                onClick: () => context.selectPanel('students'),
              },
              'students',
            ),
            h(
              'button',
              {
                class: 'pane-toggle-block',
                onClick: () => {
                  blocked.value = !blocked.value
                  context.block(blocked.value)
                },
              },
              'block',
            ),
          ])
      },
    }),
  }
})

const wrappers: Array<ReturnType<typeof mount>> = []

function mountDeck() {
  const wrapper = mount(TeacherWorkspaceDeck, {
    props: { initialWorkspace: 'pbl', query: {} },
    global: { stubs: { MedIcon: true, 'scroll-view': true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

function pane(wrapper: ReturnType<typeof mount>, index: number) {
  return wrapper.find(`.teacher-deck__pane .navigation-pane-probe[data-index="${index}"]`)
}

async function swipe(wrapper: ReturnType<typeof mount>, direction: 'left' | 'right') {
  const startX = direction === 'left' ? 260 : 100
  const endX = startX + (direction === 'left' ? -180 : 180)
  const deck = wrapper.get('.teacher-deck')
  await deck.trigger('touchstart', { touches: [{ clientX: startX, clientY: 80 }], changedTouches: [] })
  await vi.advanceTimersByTimeAsync(40)
  await deck.trigger('touchmove', { touches: [{ clientX: endX, clientY: 80 }], changedTouches: [] })
  await vi.advanceTimersByTimeAsync(10)
  await deck.trigger('touchend', { touches: [], changedTouches: [{ clientX: endX, clientY: 80 }] })
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  state.showHooks.length = 0
  state.preferencePanel = 'overview'
  state.runtime = {
    getWindowInfo: vi.fn(() => ({ windowWidth: 400 })),
    setNavigationBarTitle: vi.fn(),
    onWindowResize: vi.fn(),
    offWindowResize: vi.fn(),
    reLaunch: vi.fn(),
  }
  vi.stubGlobal('uni', state.runtime)
})

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  vi.clearAllTimers()
  vi.useRealTimers()
})

describe('managed teacher workspace navigation', () => {
  it('routes bubbling native Deck taps, activates unready targets, and always opens the overview from the bottom navigation', async () => {
    const wrapper = mountDeck()
    await wrapper.vm.$nextTick()
    const nav = (id: 'pbl' | 'insights' | 'content') => wrapper.get(`#teacher-nav-${id}`)

    expect(wrapper.findComponent(TeacherPageFrame).exists()).toBe(false)
    await nav('insights').get('.teacher-deck-navigation__image').trigger('tap')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('insights')
    expect(nav('insights').attributes('aria-current')).toBe('page')
    expect(wrapper.findAll('.teacher-deck__pane')[1]?.attributes('aria-hidden')).toBe('false')
    expect(pane(wrapper, 1).get('.pane-loading').text()).toBe('正在读取班级范围')

    await pane(wrapper, 1).get('.pane-select-students').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('insights')
    expect(pane(wrapper, 3).exists()).toBe(true)
    expect(wrapper.find('.teacher-deck__pane .navigation-pane-probe[data-index="3"] .pane-loading').exists()).toBe(true)

    await nav('pbl').trigger('tap')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('pbl')
    await nav('insights').trigger('tap')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('insights')
    expect(pane(wrapper, 1).attributes('data-current')).toBe('1')

    await nav('content').trigger('tap')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('content')
    await nav('pbl').trigger('tap')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('pbl')
    await nav('insights').trigger('tap')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('insights')
    expect(pane(wrapper, 1).attributes('data-current')).toBe('1')
    expect(state.runtime.reLaunch).not.toHaveBeenCalled()
    expect(state.navigation.switchWorkspace).not.toHaveBeenCalled()
  })

  it('lets a bottom-nav tap cancel settling and keeps the blocked and unready-swipe guards', async () => {
    const wrapper = mountDeck()
    await wrapper.vm.$nextTick()
    const nav = (id: 'pbl' | 'insights' | 'content') => wrapper.get(`#teacher-nav-${id}`)
    await pane(wrapper, 1).get('.pane-ready').trigger('click')

    await swipe(wrapper, 'left')
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('pbl')
    await nav('content').trigger('tap')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('content')
    await vi.advanceTimersByTimeAsync(300)
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('content')

    await pane(wrapper, 4).get('.pane-toggle-block').trigger('click')
    await nav('pbl').trigger('tap')
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('content')
    await pane(wrapper, 4).get('.pane-toggle-block').trigger('click')

    await swipe(wrapper, 'right')
    await vi.advanceTimersByTimeAsync(240)
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('content')
    expect(nav('content').attributes('aria-current')).toBe('page')
    expect(state.runtime.reLaunch).not.toHaveBeenCalled()
    expect(state.navigation.switchWorkspace).not.toHaveBeenCalled()
  })

  it('keeps the native nav selection and active icon in sync after swiping to content', async () => {
    const wrapper = mountDeck()
    await wrapper.vm.$nextTick()

    for (let current = 0; current < 4; current += 1) {
      const next = pane(wrapper, current + 1)
      expect(next.exists()).toBe(true)
      await next.get('.pane-ready').trigger('click')
      await swipe(wrapper, 'left')
      await vi.advanceTimersByTimeAsync(240)
      await wrapper.vm.$nextTick()
    }

    const contentNav = wrapper.get('#teacher-nav-content')
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('content')
    expect(contentNav.classes()).toContain('teacher-deck-navigation__item--active')
    expect(contentNav.attributes('aria-current')).toBe('page')
    expect(contentNav.get('.teacher-deck-navigation__image').attributes('src')).toBe(
      '/static/teacher-content-active.svg',
    )
    expect(wrapper.get('#teacher-nav-pbl').attributes('aria-current')).toBeUndefined()
    expect(state.runtime.reLaunch).not.toHaveBeenCalled()
  })

  it('uses the managed Frame emit fallback when no Deck controller is provided', async () => {
    const wrapper = mount(TeacherPageFrame, {
      props: { active: 'pbl', title: '课堂教学', managed: true },
      global: { stubs: { MedIcon: true, 'scroll-view': true } },
    })
    wrappers.push(wrapper)

    await wrapper.get('#teacher-nav-insights').trigger('click')
    expect(wrapper.emitted('navigate')).toEqual([['insights']])
    expect(state.navigation.switchWorkspace).not.toHaveBeenCalled()
  })
})
