import { computed, defineComponent, h, provide, ref, type Ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  teacherScreenKey,
  useTeacherScreenLoad,
  useTeacherScreenShow,
  type TeacherScreenContext,
} from './teacherScreenContext'

/* eslint-disable vue/one-component-per-file -- Local provider/screen probes keep this lifecycle test self-contained. */
vi.mock('@dcloudio/uni-app', () => ({ onLoad: () => undefined, onShow: () => undefined }))

const wrappers: Array<ReturnType<typeof mount>> = []

function createContext(panel: 'overview' | 'knowledge' | 'students', active: Ref<boolean>, show: Ref<number>) {
  return {
    active,
    show,
    query: { panel },
    panel,
    insights: ref(undefined),
    position: computed(() => 1),
    selectPanel: () => undefined,
    block: () => undefined,
    ready: () => undefined,
  } satisfies TeacherScreenContext
}

function mountPane(context: TeacherScreenContext, events: string[]) {
  const screen = defineComponent({
    setup() {
      useTeacherScreenLoad((query) => events.push(`load:${query?.panel}`))
      useTeacherScreenShow(() => events.push(`show:${context.panel}`))
      return () => h('div')
    },
  })
  const wrapper = mount(
    defineComponent({
      setup() {
        provide(teacherScreenKey, context)
        return () => h(screen)
      },
    }),
  )
  wrappers.push(wrapper)
  return wrapper
}

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

describe('teacher screen context lifecycle', () => {
  it('loads each prepared screen and refreshes only the active screen on later page shows', async () => {
    const activeOverview = ref(true)
    const activeKnowledge = ref(false)
    const show = ref(0)
    const events: string[] = []
    mountPane(createContext('overview', activeOverview, show), events)
    mountPane(createContext('knowledge', activeKnowledge, show), events)

    await flushPromises()
    expect(events).toContain('load:overview')
    expect(events).toContain('load:knowledge')
    expect(events).toContain('show:overview')
    expect(events).toContain('show:knowledge')

    events.length = 0
    show.value += 1
    await flushPromises()
    expect(events).toEqual(['show:overview'])

    activeOverview.value = false
    activeKnowledge.value = true
    await flushPromises()
    events.length = 0
    show.value += 1
    await flushPromises()
    expect(events).toEqual(['show:knowledge'])
  })

  it('does not mark an unloaded pane ready when its pending refresh resolves', async () => {
    const active = ref(false)
    const show = ref(0)
    const context = createContext('knowledge', active, show)
    const ready = vi.fn()
    context.ready = ready
    let finishRefresh!: () => void
    const screen = defineComponent({
      setup() {
        useTeacherScreenShow(() => new Promise<void>((resolve) => (finishRefresh = resolve)))
        return () => h('div')
      },
    })
    const wrapper = mount(
      defineComponent({
        setup() {
          provide(teacherScreenKey, context)
          return () => h(screen)
        },
      }),
    )
    wrappers.push(wrapper)
    await flushPromises()
    expect(finishRefresh).toBeTypeOf('function')

    wrapper.unmount()
    finishRefresh()
    await flushPromises()
    expect(ready).not.toHaveBeenCalled()
  })
})
