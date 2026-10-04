import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherWorkspaceDeck from './TeacherWorkspaceDeck.vue'

const state = vi.hoisted(() => ({
  panes: [] as Array<{ index: number; context: unknown; unmounted: boolean }>,
  showHooks: [] as Array<() => unknown>,
  actor: { openid: 'teacher-a', role: 'teacher' },
  preferencePanel: 'overview',
  runtime: {} as Record<string, ReturnType<typeof vi.fn>>,
}))

vi.mock('@dcloudio/uni-app', () => ({ onShow: (hook: () => unknown) => state.showHooks.push(hook) }))
vi.mock('@/features/identity/public', () => ({ getSession: () => state.actor }))
vi.mock('@/platform/navigation/teacherPreferences', () => ({
  readTeacherInsightsPreference: () => ({ panel: state.preferencePanel }),
}))
vi.mock('./TeacherWorkspacePane.vue', async () => {
  const { defineComponent: component, h: createElement, onUnmounted } = await import('vue')
  return {
    default: component({
      name: 'DeckPaneProbe',
      props: { index: Number, current: Number, context: Object },
      setup(props) {
        const record = { index: Number(props.index), context: props.context, unmounted: false }
        const context = props.context as { ready: () => void; selectPanel: (panel: string) => void }
        state.panes.push(record)
        onUnmounted(() => {
          record.unmounted = true
        })
        return () =>
          createElement(
            'section',
            { class: 'deck-pane-probe', 'data-index': props.index, 'data-current': props.current },
            [
              createElement('button', { class: 'pane-ready', onClick: context.ready }, 'ready'),
              createElement(
                'button',
                { class: 'select-students', onClick: () => context.selectPanel('students') },
                'students',
              ),
            ],
          )
      },
    }),
  }
})

const wrappers: Array<ReturnType<typeof mount>> = []

function mountDeck(initialWorkspace: 'pbl' | 'insights' | 'content' = 'pbl', query: Record<string, string> = {}) {
  const wrapper = mount(TeacherWorkspaceDeck, { props: { initialWorkspace, query } })
  wrappers.push(wrapper)
  return wrapper
}

function pane(wrapper: ReturnType<typeof mount>, index: number) {
  return wrapper.find(`.teacher-deck__pane .deck-pane-probe[data-index="${index}"]`)
}

function paneStyle(wrapper: ReturnType<typeof mount>, index: number) {
  return wrapper.findAll('.teacher-deck__pane')[index]?.attributes('style') || ''
}

function touchPoint(clientX: number, clientY = 80) {
  return { clientX, clientY }
}

async function swipe(wrapper: ReturnType<typeof mount>, direction: 'left' | 'right', distance = 180) {
  await drag(wrapper, direction, distance)
  await vi.advanceTimersByTimeAsync(10)
  const startX = direction === 'left' ? 260 : 100
  const endX = startX + (direction === 'left' ? -distance : distance)
  await wrapper.get('.teacher-deck').trigger('touchend', { touches: [], changedTouches: [touchPoint(endX)] })
}

async function drag(wrapper: ReturnType<typeof mount>, direction: 'left' | 'right', distance = 180) {
  const startX = direction === 'left' ? 260 : 100
  const endX = startX + (direction === 'left' ? -distance : distance)
  const deck = wrapper.get('.teacher-deck')
  await deck.trigger('touchstart', { touches: [touchPoint(startX)], changedTouches: [] })
  await vi.advanceTimersByTimeAsync(40)
  await deck.trigger('touchmove', { touches: [touchPoint(endX)], changedTouches: [] })
}

beforeEach(() => {
  vi.useFakeTimers()
  state.panes.length = 0
  state.showHooks.length = 0
  state.actor = { openid: 'teacher-a', role: 'teacher' }
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

describe('teacher workspace deck', () => {
  it('hides inactive panes while idle and reveals them only during swipe motion without remounting', async () => {
    const wrapper = mountDeck('pbl')
    const inactive = () =>
      wrapper.findAll('.teacher-deck__pane').find((node) => node.find('[data-index="1"]').exists())!
    expect(inactive().classes()).toContain('teacher-deck__pane--hidden')
    await pane(wrapper, 1).get('.pane-ready').trigger('click')
    await drag(wrapper, 'left')
    expect(inactive().classes()).not.toContain('teacher-deck__pane--hidden')
    await wrapper.get('.teacher-deck').trigger('touchend', { touches: [], changedTouches: [touchPoint(80)] })
    await vi.advanceTimersByTimeAsync(240)
    expect(inactive().classes()).not.toContain('teacher-deck__pane--hidden')
    expect(
      wrapper
        .findAll('.teacher-deck__pane')
        .find((node) => node.find('[data-index="0"]').exists())!
        .classes(),
    ).toContain('teacher-deck__pane--hidden')
    expect(state.panes.filter(({ index }) => index === 1)).toHaveLength(1)
    expect(state.panes.find(({ index }) => index === 0)?.unmounted).toBe(false)
  })

  it('observes child touch events without stopping their propagation at the deck', async () => {
    const wrapper = mountDeck()
    const observe = vi.fn()
    wrapper.element.addEventListener('touchstart', observe)
    await pane(wrapper, 0)
      .get('.pane-ready')
      .trigger('touchstart', { touches: [touchPoint(150)], changedTouches: [] })
    expect(observe).toHaveBeenCalledTimes(1)
    wrapper.element.removeEventListener('touchstart', observe)
  })

  it('preloads only the real neighbor and leaves it still until that pane reports ready', async () => {
    const wrapper = mountDeck('pbl')
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.teacher-deck__pane')).toHaveLength(2)
    expect(pane(wrapper, 0).exists()).toBe(true)
    expect(pane(wrapper, 1).exists()).toBe(true)
    await swipe(wrapper, 'left')
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('pbl')
    expect(paneStyle(wrapper, 0)).toContain('translate3d(0px,0,0)')
    expect(paneStyle(wrapper, 1)).toContain('translate3d(400px,0,0)')

    await vi.advanceTimersByTimeAsync(240)
    await pane(wrapper, 1).get('.pane-ready').trigger('click')
    await drag(wrapper, 'left')
    expect(paneStyle(wrapper, 0)).toContain('translate3d(-180px,0,0)')
    expect(paneStyle(wrapper, 1)).toContain('translate3d(220px,0,0)')
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('pbl')
    expect(state.runtime.reLaunch).not.toHaveBeenCalled()
    await wrapper.get('.teacher-deck').trigger('touchcancel')
  })

  it('settles both panes before changing the active index without reloading or relaunching', async () => {
    const wrapper = mountDeck('pbl')
    await wrapper.vm.$nextTick()
    await pane(wrapper, 1).get('.pane-ready').trigger('click')
    const before = state.panes.map(({ index }) => index)

    await swipe(wrapper, 'left')
    expect(paneStyle(wrapper, 0)).toContain('translate3d(-400px,0,0)')
    expect(paneStyle(wrapper, 1)).toContain('translate3d(0px,0,0)')
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('pbl')
    await vi.advanceTimersByTimeAsync(239)
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('pbl')
    await vi.advanceTimersByTimeAsync(1)
    await wrapper.vm.$nextTick()

    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('insights')
    expect(state.panes.filter(({ index }) => index === 0)).toHaveLength(1)
    expect(state.panes.filter(({ index }) => index === 1)).toHaveLength(1)
    expect(state.panes.find(({ index }) => index === 0)?.unmounted).toBe(false)
    expect(state.panes.find(({ index }) => index === 1)?.unmounted).toBe(false)
    expect(before).toEqual([0, 1])
    expect(state.runtime.reLaunch).not.toHaveBeenCalled()
  })

  it('activates an unready clicked destination immediately without spanning missing panes', async () => {
    const wrapper = mountDeck('pbl')
    await wrapper.vm.$nextTick()
    await wrapper.get('#teacher-nav-content').trigger('tap')
    await wrapper.vm.$nextTick()

    expect(pane(wrapper, 4).exists()).toBe(true)
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('content')
    expect(pane(wrapper, 4).attributes('data-current')).toBe('4')
    await pane(wrapper, 4).get('.pane-ready').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('content')
    expect(state.runtime.reLaunch).not.toHaveBeenCalled()
  })

  it.each(['pbl', 'content'] as const)(
    'opens overview from %s even when the saved preference is students',
    async (initialWorkspace) => {
      state.preferencePanel = 'students'
      const wrapper = mountDeck(initialWorkspace)
      await wrapper.vm.$nextTick()
      await wrapper.get('#teacher-nav-insights').trigger('tap')
      await wrapper.vm.$nextTick()

      expect(pane(wrapper, 1).exists()).toBe(true)
      expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe('insights')
      expect(pane(wrapper, 1).attributes('data-current')).toBe('1')
      expect(state.panes.find(({ index }) => index === 1)?.context).toMatchObject({ panel: 'overview' })
      expect(state.runtime.reLaunch).not.toHaveBeenCalled()
    },
  )

  it.each([
    ['pbl', 'right', 0],
    ['content', 'left', 4],
  ] as Array<['pbl' | 'content', 'left' | 'right', number]>)(
    'keeps the deck at the %s end',
    async (initialWorkspace, direction, index) => {
      const wrapper = mountDeck(initialWorkspace)
      await wrapper.vm.$nextTick()
      await swipe(wrapper, direction)
      await vi.advanceTimersByTimeAsync(240)
      await wrapper.vm.$nextTick()
      expect(wrapper.get('.teacher-deck-shell').attributes('data-workspace')).toBe(initialWorkspace)
      expect(pane(wrapper, index).exists()).toBe(true)
      expect(state.runtime.reLaunch).not.toHaveBeenCalled()
    },
  )

  it('shares scope selection and position across insights pane contexts', async () => {
    const wrapper = mountDeck('insights', { panel: 'overview' })
    await wrapper.vm.$nextTick()
    await pane(wrapper, 2).get('.select-students').trigger('click')
    await wrapper.vm.$nextTick()
    await pane(wrapper, 2).get('.pane-ready').trigger('click')
    await pane(wrapper, 3).get('.pane-ready').trigger('click')
    const overview = state.panes.find((item) => item.index === 1)?.context as {
      insights: { value?: { classId?: number; sessionId?: number | string } }
      position: { value: number }
    }
    const knowledge = state.panes.find((item) => item.index === 2)?.context as typeof overview
    const students = state.panes.find((item) => item.index === 3)?.context as typeof overview

    expect(overview.insights).toBe(knowledge.insights)
    expect(knowledge.insights).toBe(students.insights)
    overview.insights.value = { classId: 8, sessionId: 9 }
    expect(knowledge.insights.value).toEqual({ classId: 8, sessionId: 9 })
    expect(students.insights.value).toEqual({ classId: 8, sessionId: 9 })
    expect(overview.position).toBe(knowledge.position)
    expect(knowledge.position).toBe(students.position)
    expect(overview.position.value).toBe(3)
  })
})
