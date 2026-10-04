import { flushPromises, mount } from '@vue/test-utils'
import { computed, nextTick, ref, type Ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import InsightsRoot from '@/features/analytics/presentation/TeacherInsightsScreen.vue'
import {
  teacherScreenKey,
  type InsightsSelection,
  type TeacherScreenContext,
} from '@/components/teacher/teacherScreenContext'
import { relaunchTo } from '@/platform/navigation'
import {
  readTeacherClassPreference,
  readTeacherInsightsPreference,
  readTeacherPblPreference,
  saveTeacherClassPreference,
  saveTeacherInsightsPreference,
  saveTeacherPblPreference,
} from '@/platform/navigation/teacherPreferences'

const lifecycle = vi.hoisted(() => ({
  loads: [] as Array<(query?: Record<string, string>) => void>,
  shows: [] as Array<() => unknown>,
}))
const auth = vi.hoisted(() => ({
  session: null as null | { openid: string; role: 'teacher' | 'student' },
}))
const api = vi.hoisted(() => ({
  getTeacherClasses: vi.fn(),
  getTeacherPblSessionPage: vi.fn(),
  requireRole: vi.fn(),
  workspaceRefresh: vi.fn(),
  workspaceMounts: 0,
}))
const navigation = vi.hoisted(() => ({ relaunchToTeacherWorkspace: vi.fn(), prepareSwipeEntry: vi.fn() }))
const wrappers: Array<ReturnType<typeof mount>> = []

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query?: Record<string, string>) => void) => lifecycle.loads.push(hook),
  onShow: (hook: () => unknown) => lifecycle.shows.push(hook),
}))
vi.mock('@/features/classroom/public', () => ({ getTeacherClasses: api.getTeacherClasses }))
vi.mock('@/features/pbl/public', () => ({ getTeacherPblSessionPage: api.getTeacherPblSessionPage }))
vi.mock('@/features/identity/public', () => ({
  getSession: () => auth.session,
  requireRole: api.requireRole,
}))
vi.mock('@/features/analytics/presentation/TeacherInsightsReadWorkspace.vue', () => ({
  default: {
    name: 'InsightsWorkspaceProbe',
    props: ['panel', 'filters', 'classes'],
    setup(_props: unknown, { expose }: { expose: (value: unknown) => void }) {
      api.workspaceMounts += 1
      expose({ refresh: api.workspaceRefresh })
      return () => null
    },
  },
}))
vi.mock('@/components/teacher/TeacherPageFrame.vue', () => ({
  default: {
    name: 'InsightsPageFrameProbe',
    props: { fixedContent: Boolean, panelSwipes: Boolean, swipeContext: String, swipeDisabled: Boolean },
    emits: ['horizontalSwipe', 'swipeProgress'],
    template: '<main><slot /></main>',
  },
}))
vi.mock('@/components/teacher/TeacherPager.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/teacher/topicLabel', () => ({ displayTopicCode: (value: string) => value }))
vi.mock('@/components/ui/MedState.vue', () => ({
  default: {
    props: ['title', 'description', 'actionLabel'],
    emits: ['action'],
    template:
      '<section class="med-state"><span>{{ title }}</span><span>{{ description }}</span><button v-if="actionLabel" @click="$emit(\'action\')">{{ actionLabel }}</button></section>',
  },
}))
vi.mock('@/platform/navigation', () => ({
  goDetail: vi.fn(),
  backOrRoute: vi.fn(),
  relaunchTo: vi.fn(),
  ROUTES: {
    teacherInsights: '/pages/teacher/insights/index',
    teacherInsightsStudentDetail: '/pages/teacher/insights/student-detail',
    teacherPbl: '/pages/teacher/pbl/index',
    teacherPblDiagnosticDetail: '/pages/teacher/pbl-diagnostic-detail/pbl-diagnostic-detail',
    teacherLearningFinalTest: '/pages/teacher/learning/final-test',
    teacherContent: '/pages/teacher/content/index',
  },
}))
vi.mock('@/platform/navigation/teacher', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/platform/navigation/teacher')>()),
  relaunchToTeacherWorkspace: navigation.relaunchToTeacherWorkspace,
}))
vi.mock('@/platform/navigation/teacherSwipeMotion', () => ({
  prepareTeacherSwipeEntry: navigation.prepareSwipeEntry,
}))

const classes = [
  { id: 1, name: '炎症班' },
  { id: 2, name: '肿瘤班' },
  { id: 3, name: '循环班' },
]
const sessions = [
  { id: 'demo-11', classId: '1', className: '炎症班', topicCode: 'INFLAMMATION', status: 'active' },
  { id: 'demo-14', classId: '1', className: '炎症班', topicCode: 'CELL_INJURY', status: 'closed' },
  { id: 'demo-21', classId: '2', className: '肿瘤班', topicCode: 'TUMOR', status: 'active' },
  { id: 'demo-16', classId: '3', className: '循环班', topicCode: 'CIRCULATION', status: 'active' },
]

function sessionPage(items: typeof sessions) {
  return { items, total: items.length, limit: 20, offset: 0 }
}

const pickerStub = {
  name: 'PickerProbe',
  props: ['range', 'rangeKey', 'mode', 'value'],
  emits: ['change'],
  template: '<div class="picker-probe" @change="$emit(\'change\', $event)"><slot /></div>',
}

function mountRoot(context?: TeacherScreenContext) {
  const wrapper = mount(InsightsRoot, {
    global: {
      stubs: { picker: pickerStub },
      provide: context ? { [teacherScreenKey as symbol]: context } : {},
    },
  })
  wrappers.push(wrapper)
  return wrapper
}

function paneContext(
  panel: 'overview' | 'knowledge' | 'students',
  active: Ref<boolean>,
  show: Ref<number>,
  insights: Ref<InsightsSelection | undefined>,
): TeacherScreenContext {
  return {
    active,
    show,
    query: { classId: '1', sessionId: 'demo-11', dateFrom: '2026-09-01', dateTo: '2026-09-30', panel },
    panel,
    insights,
    position: computed(() => (panel === 'overview' ? 1 : panel === 'knowledge' ? 2 : 3)),
    selectPanel: vi.fn(),
    block: vi.fn(),
    ready: vi.fn(),
  }
}

function currentShow() {
  return lifecycle.shows[lifecycle.shows.length - 1]
}

function workspaceProbe(wrapper: ReturnType<typeof mount>) {
  const probes = wrapper.findAllComponents({ name: 'InsightsWorkspaceProbe' })
  return probes[probes.length - 1]!
}

async function openRoot(query: Record<string, string> = {}) {
  const wrapper = mountRoot()
  lifecycle.loads[lifecycle.loads.length - 1]?.(query)
  await currentShow()?.()
  await flushPromises()
  await nextTick()
  await flushPromises()
  return wrapper
}

async function updateDate(wrapper: ReturnType<typeof mount>, index: number, value: string) {
  if (!wrapper.find('.range-sheet').exists()) await wrapper.get('.insights-hero__description').trigger('click')
  await wrapper.findAll('.picker-probe')[index].trigger('change', { detail: { value } })
  await nextTick()
}

describe('T53 teacher insights root state and scope', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    lifecycle.loads.length = 0
    lifecycle.shows.length = 0
    api.workspaceMounts = 0
    navigation.relaunchToTeacherWorkspace.mockReset()
    navigation.prepareSwipeEntry.mockReset()
    vi.mocked(relaunchTo).mockReset()
    api.workspaceRefresh.mockReset().mockResolvedValue(undefined)
    api.requireRole.mockImplementation(() => auth.session?.role === 'teacher')
    auth.session = { openid: 'teacher-a', role: 'teacher' }
    api.getTeacherClasses.mockResolvedValue(classes)
    api.getTeacherPblSessionPage.mockImplementation(async ({ classId }: { classId?: string }) =>
      sessionPage(sessions.filter((item) => classId === undefined || item.classId === classId)),
    )
  })

  afterEach(() => {
    for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  })

  it('contains scrolling only for students and resets the native list when its classroom scope changes', async () => {
    const wrapper = await openRoot({ panel: 'students' })
    const frame = wrapper.findComponent({ name: 'InsightsPageFrameProbe' })
    expect(frame.props('fixedContent')).toBe(true)
    expect(wrapper.get('.student-records-heading').text()).toBe('学生学习记录')
    const previousScroll = wrapper.get('.student-records-scroll').element

    await wrapper.findAll('.picker-probe')[0]!.trigger('change', { detail: { value: '2' } })
    await flushPromises()
    expect(workspaceProbe(wrapper).props('filters').classId).toBe(2)
    expect(wrapper.get('.student-records-scroll').element).not.toBe(previousScroll)

    await wrapper.get('.insights-panel--knowledge').trigger('click')
    await flushPromises()
    expect(frame.props('fixedContent')).toBe(false)
    expect(wrapper.find('.student-records-scroll').exists()).toBe(false)
    expect(workspaceProbe(wrapper).props('panel')).toBe('knowledge')
    expect(workspaceProbe(wrapper).props('filters').classId).toBe(2)
  })

  it('isolates insight filters by teacher and leaves PBL class and queue preferences untouched', async () => {
    saveTeacherClassPreference('teacher-a', 'insights', 1)
    saveTeacherClassPreference('teacher-a', 'pbl', 2)
    saveTeacherInsightsPreference('teacher-a', {
      panel: 'progress',
      sessionId: 'demo-11',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
    saveTeacherPblPreference('teacher-a', {
      section: 'diagnostics',
      reviewKind: 'needs_changes',
      sessionId: 'demo-pbl-1',
    })
    saveTeacherClassPreference('teacher-b', 'insights', 3)
    saveTeacherClassPreference('teacher-b', 'pbl', 1)
    saveTeacherInsightsPreference('teacher-b', {
      panel: 'students',
      sessionId: 'demo-16',
      dateFrom: '2026-10-01',
      dateTo: '2026-10-31',
    })
    saveTeacherPblPreference('teacher-b', { section: 'classrooms', sessionId: 'demo-pbl-2' })

    const wrapper = await openRoot()
    expect(workspaceProbe(wrapper).props('panel')).toBe('students')
    expect(workspaceProbe(wrapper).props('filters')).toEqual({
      classId: 1,
      sessionId: 'demo-11',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })

    await wrapper
      .findAll('button')
      .find((button) => button.text() === '知识与推理')!
      .trigger('click')
    const pickers = wrapper.findAll('.picker-probe')
    await pickers[1].trigger('change', { detail: { value: '2' } })
    await updateDate(wrapper, 2, '2026-10-03')
    await updateDate(wrapper, 3, '2026-10-10')
    await nextTick()

    expect(readTeacherInsightsPreference('teacher-a')).toEqual({
      panel: 'knowledge',
      sessionId: 'demo-14',
      dateFrom: '2026-10-03',
      dateTo: '2026-10-10',
    })
    expect(readTeacherPblPreference('teacher-a')).toEqual({
      section: 'diagnostics',
      reviewKind: 'needs_changes',
      sessionId: 'demo-pbl-1',
    })
    expect(readTeacherClassPreference('teacher-a', 'pbl')).toBe(2)

    auth.session = { openid: 'teacher-b', role: 'teacher' }
    await currentShow()?.()
    await flushPromises()
    await nextTick()

    expect(workspaceProbe(wrapper).props('panel')).toBe('students')
    expect(workspaceProbe(wrapper).props('filters')).toEqual({
      classId: 3,
      sessionId: 'demo-16',
      dateFrom: '2026-10-01',
      dateTo: '2026-10-31',
    })
    expect(readTeacherClassPreference('teacher-b', 'pbl')).toBe(1)
    expect(readTeacherPblPreference('teacher-b')).toEqual({ section: 'classrooms', sessionId: 'demo-pbl-2' })
  })

  it('shares insight filters between mounted panels and lets only the active panel save its preference', async () => {
    saveTeacherInsightsPreference('teacher-a', {
      panel: 'overview',
      sessionId: 'demo-11',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
    const show = ref(0)
    const shared = ref<InsightsSelection>()
    const overviewActive = ref(true)
    const studentsActive = ref(false)
    const overview = mountRoot(paneContext('overview', overviewActive, show, shared))
    const students = mountRoot(paneContext('students', studentsActive, show, shared))
    await flushPromises()
    await nextTick()
    await flushPromises()

    expect(workspaceProbe(overview).props('filters')).toMatchObject({ classId: 1, sessionId: 'demo-11' })
    expect(workspaceProbe(students).props('filters')).toMatchObject({ classId: 1, sessionId: 'demo-11' })

    await overview.findAll('.picker-probe')[0]!.trigger('change', { detail: { value: '2' } })
    await flushPromises()
    await nextTick()
    expect(shared.value).toMatchObject({ classId: 2, dateFrom: '2026-09-01', dateTo: '2026-09-30' })
    expect(shared.value?.sessionId).toBeUndefined()
    expect(workspaceProbe(students).props('filters')).toMatchObject({ classId: 2, sessionId: undefined })

    const savedByActivePane = readTeacherInsightsPreference('teacher-a')
    expect(savedByActivePane).toMatchObject({ panel: 'overview', sessionId: undefined })
    await updateDate(students, 2, '2026-09-15')
    expect(readTeacherInsightsPreference('teacher-a')).toEqual(savedByActivePane)
    expect(shared.value?.dateFrom).toBe('2026-09-01')

    overviewActive.value = false
    studentsActive.value = true
    await flushPromises()
    expect(readTeacherInsightsPreference('teacher-a')).toMatchObject({ panel: 'students', dateFrom: '2026-09-15' })
  })

  it('passes an explicit validated class, session, date range and panel to the read workspace', async () => {
    saveTeacherClassPreference('teacher-a', 'insights', 1)
    saveTeacherInsightsPreference('teacher-a', {
      panel: 'overview',
      sessionId: 'demo-11',
      dateFrom: '2026-08-01',
      dateTo: '2026-08-31',
    })
    const wrapper = await openRoot({
      classId: '2',
      sessionId: 'demo-21',
      dateFrom: '2026-09-10',
      dateTo: '2026-09-20',
      panel: 'knowledge',
    })

    expect(workspaceProbe(wrapper).props('panel')).toBe('knowledge')
    expect(workspaceProbe(wrapper).props('filters')).toEqual({
      classId: 2,
      sessionId: 'demo-21',
      dateFrom: '2026-09-10',
      dateTo: '2026-09-20',
    })
    expect(api.getTeacherPblSessionPage).toHaveBeenCalledWith({ classId: '2', offset: 0 })
    expect(api.workspaceRefresh).toHaveBeenCalledTimes(1)
  })

  it('unmounts the read workspace for an invalid date range without refreshing or overwriting saved dates', async () => {
    saveTeacherInsightsPreference('teacher-a', {
      panel: 'progress',
      sessionId: 'demo-11',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
    const wrapper = await openRoot()
    expect(workspaceProbe(wrapper).exists()).toBe(true)
    expect(api.workspaceRefresh).toHaveBeenCalledTimes(1)

    await updateDate(wrapper, 2, '2026-10-01')

    expect(wrapper.text()).toContain('日期范围无效')
    expect(wrapper.findAllComponents({ name: 'InsightsWorkspaceProbe' })).toHaveLength(0)
    expect(api.workspaceRefresh).toHaveBeenCalledTimes(1)
    expect(readTeacherInsightsPreference('teacher-a')).toEqual({
      panel: 'students',
      sessionId: 'demo-11',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
  })

  it('clears session selection on class change and ignores an older session directory response', async () => {
    saveTeacherClassPreference('teacher-a', 'insights', 1)
    saveTeacherInsightsPreference('teacher-a', { panel: 'progress', sessionId: 'demo-11' })
    const delayed: Array<(value: ReturnType<typeof sessionPage>) => void> = []
    api.getTeacherPblSessionPage.mockImplementation(({ classId }: { classId?: string }) => {
      if (classId === '1') {
        return new Promise((resolve) => delayed.push(resolve))
      }
      return Promise.resolve(sessionPage(sessions.filter((item) => item.classId === classId)))
    })
    const wrapper = await openRoot()
    expect(delayed.length).toBeGreaterThan(0)
    expect(workspaceProbe(wrapper).props('filters')).toMatchObject({ classId: 1, sessionId: 'demo-11' })

    await wrapper.findAll('.picker-probe')[0].trigger('change', { detail: { value: '2' } })
    await flushPromises()
    await nextTick()

    expect(workspaceProbe(wrapper).props('filters')).toMatchObject({ classId: 2, sessionId: undefined })
    expect(readTeacherClassPreference('teacher-a', 'insights')).toBe(2)
    expect(readTeacherInsightsPreference('teacher-a')?.sessionId).toBeUndefined()
    expect(api.getTeacherPblSessionPage).toHaveBeenCalledWith({ classId: '2', offset: 0 })

    delayed.forEach((resolve) => resolve(sessionPage([sessions[0]!])))
    await flushPromises()

    const currentSessionPicker = wrapper.findAllComponents({ name: 'PickerProbe' })[1]
    expect(currentSessionPicker.props('range').map((item: { id?: string }) => item.id)).toEqual([undefined, 'demo-21'])
  })

  it('does not mount the read workspace when teacher role is lost', async () => {
    const wrapper = mountRoot()
    lifecycle.loads[lifecycle.loads.length - 1]?.({})
    auth.session = { openid: 'teacher-a', role: 'student' }
    await currentShow()?.()
    await flushPromises()

    expect(wrapper.text()).toContain('教师身份已变化')
    expect(api.getTeacherClasses).not.toHaveBeenCalled()
    expect(api.getTeacherPblSessionPage).not.toHaveBeenCalled()
    expect(api.workspaceMounts).toBe(0)
  })

  it('discards the previous teacher class response after the account changes', async () => {
    let resolvePrevious!: (value: typeof classes) => void
    api.getTeacherClasses
      .mockReturnValueOnce(new Promise((resolve) => (resolvePrevious = resolve)))
      .mockResolvedValueOnce([classes[2]!])
    saveTeacherClassPreference('teacher-b', 'insights', 3)

    const wrapper = mountRoot()
    lifecycle.loads[lifecycle.loads.length - 1]?.({})
    const previousUserRequest = Promise.resolve(currentShow()?.())
    await Promise.resolve()

    auth.session = { openid: 'teacher-b', role: 'teacher' }
    await currentShow()?.()
    await flushPromises()
    expect(workspaceProbe(wrapper).props('classes')).toEqual([classes[2]])
    expect(workspaceProbe(wrapper).props('filters').classId).toBe(3)

    resolvePrevious([classes[0]!])
    await previousUserRequest
    await flushPromises()

    expect(workspaceProbe(wrapper).props('classes')).toEqual([classes[2]])
    expect(workspaceProbe(wrapper).props('filters').classId).toBe(3)
    expect(api.getTeacherClasses).toHaveBeenCalledTimes(2)
  })
  it('maps the old progress entry to students and keeps scope when preview opens another panel', async () => {
    const wrapper = await openRoot({
      classId: '1',
      sessionId: 'demo-11',
      panel: 'progress',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
    expect(wrapper.findAll('.panels button').map((item) => item.text())).toEqual(['总览', '知识与推理', '学生'])
    expect(workspaceProbe(wrapper).props('panel')).toBe('students')
    expect(wrapper.find('.date-filters').exists()).toBe(false)
    const before = workspaceProbe(wrapper).props('filters')
    workspaceProbe(wrapper).vm.$emit('selectPanel', 'knowledge')
    await nextTick()
    expect(workspaceProbe(wrapper).props('panel')).toBe('knowledge')
    expect(workspaceProbe(wrapper).props('filters')).toEqual(before)
    expect(wrapper.get('.insights-hero__title').text()).toBe('知识与推理')
  })

  it('handles frame swipes for insight panels, retains scope, and guards the date overlay', async () => {
    const wrapper = await openRoot({
      classId: '2',
      sessionId: 'demo-21',
      dateFrom: '2026-09-10',
      dateTo: '2026-09-20',
      panel: 'overview',
    })
    const frame = wrapper.findComponent({ name: 'InsightsPageFrameProbe' })
    expect(frame.props('panelSwipes')).toBe(true)
    expect(frame.props('swipeContext')).toBe('overview')
    expect(frame.props('swipeDisabled')).toBe(false)
    const before = workspaceProbe(wrapper).props('filters')

    frame.vm.$emit('swipeProgress', { direction: 'left', progress: 0.5 })
    await nextTick()
    expect((wrapper.get('.panels__indicator').element as HTMLElement).style.transform).toBe('translate3d(50%, 0, 0)')
    expect(wrapper.get('.insights-panel--knowledge').classes()).toContain('selected')
    frame.vm.$emit('swipeProgress', undefined)
    await nextTick()
    expect((wrapper.get('.panels__indicator').element as HTMLElement).style.transform).toBe('translate3d(0%, 0, 0)')

    frame.vm.$emit('horizontalSwipe', 'left')
    await nextTick()
    expect(workspaceProbe(wrapper).props('panel')).toBe('knowledge')
    expect(frame.props('swipeContext')).toBe('knowledge')
    expect(workspaceProbe(wrapper).props('filters')).toEqual(before)

    await wrapper.get('.insights-hero__description').trigger('click')
    expect(frame.props('swipeDisabled')).toBe(true)
    frame.vm.$emit('horizontalSwipe', 'left')
    await nextTick()
    expect(wrapper.find('.range-sheet').exists()).toBe(true)
    expect(workspaceProbe(wrapper).props('panel')).toBe('knowledge')
    expect(workspaceProbe(wrapper).props('filters')).toEqual(before)
  })

  it('connects the insights panel endpoints to PBL and content navigation', async () => {
    const overview = await openRoot({ panel: 'overview' })
    overview.findComponent({ name: 'InsightsPageFrameProbe' }).vm.$emit('horizontalSwipe', 'right')
    expect(navigation.relaunchToTeacherWorkspace).toHaveBeenCalledWith({ workspace: 'pbl' })
    expect(navigation.prepareSwipeEntry).toHaveBeenCalledWith('pbl', 'right')

    navigation.relaunchToTeacherWorkspace.mockReset()
    navigation.prepareSwipeEntry.mockReset()
    const students = await openRoot({
      classId: '2',
      sessionId: 'demo-21',
      dateFrom: '2026-09-10',
      dateTo: '2026-09-20',
      panel: 'students',
    })
    const before = workspaceProbe(students).props('filters')
    students.findComponent({ name: 'InsightsPageFrameProbe' }).vm.$emit('horizontalSwipe', 'left')
    expect(navigation.relaunchToTeacherWorkspace).toHaveBeenCalledWith({ workspace: 'content' })
    expect(navigation.prepareSwipeEntry).toHaveBeenCalledWith('content', 'left')
    expect(workspaceProbe(students).props('filters')).toEqual(before)
  })
})
