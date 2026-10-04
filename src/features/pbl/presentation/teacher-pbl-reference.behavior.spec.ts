import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherPblClassrooms from './TeacherPblClassrooms.vue'

const pickerStub = {
  name: 'PickerStub',
  props: ['range', 'rangeKey', 'value', 'disabled'],
  emits: ['change'],
  template: '<div><slot /></div>',
}

const uniComponents = {
  stubs: {
    picker: pickerStub,
    checkbox: true,
    'radio-group': { name: 'RadioGroupStub', emits: ['change'], template: '<div><slot /></div>' },
    radio: { name: 'RadioStub', props: ['checked', 'value'], template: '<span />' },
  },
}

const mocks = vi.hoisted(() => ({
  getSessionPage: vi.fn(),
  getDashboard: vi.fn(),
  createSession: vi.fn(),
  closeSession: vi.fn(),
  getCases: vi.fn(),
  getKnowledgeCatalog: vi.fn(),
  goDetail: vi.fn(),
}))

type SelectorRect = { height?: number } | null | undefined | Array<{ height?: number } | null | undefined>
type SelectorRectHandler = (result: SelectorRect) => void

const selectorCallbacks: SelectorRectHandler[] = []
const resizeCallbacks: Array<() => void> = []

function mockSelectorQuery() {
  let callback: SelectorRectHandler | undefined
  const query = {
    in: vi.fn(),
    select: vi.fn(),
    boundingClientRect: vi.fn(),
    exec: vi.fn(),
  }
  query.in.mockImplementation(() => query)
  query.select.mockImplementation(() => query)
  query.boundingClientRect.mockImplementation((handler: SelectorRectHandler) => {
    callback = handler
    return query
  })
  query.exec.mockImplementation(() => {
    if (callback) selectorCallbacks.push(callback)
    return query
  })
  return query
}

const createSelectorQuery = vi.fn(mockSelectorQuery)
const onWindowResize = vi.fn((callback: () => void) => resizeCallbacks.push(callback))
const offWindowResize = vi.fn()

vi.mock('@/platform/navigation', () => ({
  ROUTES: { teacherPblDiagnosticDetail: '/teacher/pbl-diagnostic-detail' },
  goDetail: mocks.goDetail,
}))
vi.mock('@/features/pbl/public', () => ({
  getTeacherPblSessionPage: mocks.getSessionPage,
  getTeacherPblDashboard: mocks.getDashboard,
  createPblSession: mocks.createSession,
  closePblSession: mocks.closeSession,
}))
vi.mock('@/features/content/public', () => ({ getGuidedCasesAsync: mocks.getCases }))
vi.mock('@/features/learning/public', () => ({ getKnowledgeCatalog: mocks.getKnowledgeCatalog }))

const sessions = [
  { id: 'session-1', classId: '1', className: '病理班', topicCode: '炎症研讨', status: 'active' },
  { id: 'session-2', classId: '1', className: '病理班', topicCode: '肿瘤研讨', status: 'active' },
  { id: 'session-3', classId: '1', className: '病理班', topicCode: '循环研讨', status: 'active' },
]

function dashboard(sessionId: string, classId = '1', extra: Record<string, unknown> = {}) {
  return {
    session: { id: sessionId, classId, status: 'active' },
    summary: { participants: 0, phaseCounts: {}, completedRoutes: 0 },
    students: [],
    ...extra,
  }
}

function completedStudents(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    studentId: `done-${index + 1}`,
    studentName: `完成学生${index + 1}`,
    currentPhase: 'completed',
    phaseStatus: 'completed',
    taskProgress: { completed: 1, total: 1 },
  }))
}

function mountReference(props: Record<string, unknown> = {}) {
  return mount(TeacherPblClassrooms, {
    props: {
      classes: [{ id: 1, name: '病理班' }],
      referenceLayout: true,
      ...props,
    },
    global: uniComponents,
  })
}

async function settleMeasurements(wrapper: ReturnType<typeof mountReference>) {
  await flushPromises()
  await wrapper.vm.$nextTick()
  await flushPromises()
}

function latestSelectorCallback() {
  const callback = selectorCallbacks.at(-1)
  if (!callback) throw new Error('Expected a records selector query callback')
  return callback
}

function classroomPicker(wrapper: ReturnType<typeof mountReference>) {
  return wrapper.find('.classroom-picker').findComponent(pickerStub)
}

function selectClassroomAction(wrapper: ReturnType<typeof mountReference>, action: string) {
  const picker = classroomPicker(wrapper)
  const options = picker.props('range') as Array<{ action: string }>
  const index = options.findIndex((option) => option.action === action)
  if (index < 0) throw new Error(`Missing classroom picker action: ${action}`)
  picker.vm.$emit('change', { detail: { value: String(index) } })
}

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset()
  selectorCallbacks.length = 0
  resizeCallbacks.length = 0
  createSelectorQuery.mockClear()
  onWindowResize.mockClear()
  offWindowResize.mockClear()
  const baseUni = uni as unknown as Record<string, unknown>
  vi.stubGlobal('uni', { ...baseUni, createSelectorQuery, onWindowResize, offWindowResize })
  mocks.getSessionPage.mockResolvedValue({ items: sessions, total: sessions.length })
  mocks.getDashboard.mockImplementation(async (_classId: string, sessionId: string) => dashboard(sessionId))
  mocks.getCases.mockResolvedValue([])
  mocks.getKnowledgeCatalog.mockResolvedValue([])
})

describe('teacher PBL reference layout behavior', () => {
  it('opens the first classroom when no session is explicitly requested', async () => {
    const wrapper = mountReference()
    await flushPromises()

    expect(mocks.getDashboard).toHaveBeenCalledWith('1', 'session-1')
    expect(wrapper.find('.dashboard').exists()).toBe(true)
    expect(wrapper.emitted('sessionChange')).toEqual([['session-1']])
  })

  it('opens the explicitly requested session instead of the first classroom', async () => {
    const wrapper = mountReference({ sessionId: 'session-2' })
    await flushPromises()

    expect(mocks.getDashboard).toHaveBeenCalledTimes(1)
    expect(mocks.getDashboard).toHaveBeenCalledWith('1', 'session-2')
    expect(wrapper.emitted('sessionChange')).toEqual([['session-2']])
  })

  it('places classroom creation in the classroom picker', async () => {
    const wrapper = mountReference()
    await flushPromises()

    expect(wrapper.find('.create-toggle').exists()).toBe(false)
    expect(classroomPicker(wrapper).props('range')).toEqual(
      expect.arrayContaining([expect.objectContaining({ label: '+ 新建课堂', action: 'create' })]),
    )

    selectClassroomAction(wrapper, 'create')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.create-form').exists()).toBe(true)
  })

  it('shows completed students only while retaining ongoing phase counts', async () => {
    mocks.getDashboard.mockResolvedValue(
      dashboard('session-1', '1', {
        summary: {
          participants: 10,
          phaseCounts: { problem_framing: 1, hypothesis: 2, evidence: 2, synthesis: 1, completed: 4 },
          completedRoutes: 7,
        },
        students: [
          {
            studentId: 'done-1',
            studentName: '已完成甲',
            currentPhase: 'completed',
            phaseStatus: 'completed',
            taskProgress: { completed: 2, total: 3 },
          },
          {
            studentId: 'done-2',
            studentName: '已完成乙',
            currentPhase: 'completed',
            phaseStatus: 'completed',
            taskProgress: { completed: 1, total: 2 },
          },
          {
            studentId: 'active-1',
            studentName: '进行中甲',
            currentPhase: 'evidence',
            phaseStatus: 'active',
            taskProgress: { completed: 0, total: 0 },
          },
          {
            studentId: 'active-2',
            studentName: '进行中乙',
            currentPhase: 'hypothesis',
            phaseStatus: 'active',
            taskProgress: { completed: 0, total: 0 },
          },
        ],
      }),
    )
    const wrapper = mountReference()
    await flushPromises()

    const groups = wrapper.findAll('.reference-group')
    expect(groups).toHaveLength(1)
    expect(groups[0].text()).toContain('研讨完成学生')
    expect(groups[0].text()).toContain('已完成甲')
    expect(groups[0].text()).toContain('已完成乙')
    expect(wrapper.find('.reference-students').text()).not.toContain('进行中甲')
    expect(wrapper.find('.reference-students').text()).not.toContain('进行中乙')

    const metrics = wrapper.findAll('.reference-metric')
    expect(metrics).toHaveLength(4)
    expect(
      metrics.map(
        (metric) =>
          `${metric.get('.reference-metric__label').text()} ${metric.get('.reference-metric__number').text()}`,
      ),
    ).toEqual(['参与学生 10人', '研讨进行中 6人', '研讨完成 4人', '测试完成 7人'])
  })

  it('keeps metrics and the student heading outside the fixed records scroll while more stays inside', async () => {
    mocks.getDashboard.mockResolvedValue(
      dashboard('session-1', '1', {
        summary: { participants: 10, phaseCounts: { completed: 10 }, completedRoutes: 0 },
        students: Array.from({ length: 10 }, (_, index) => ({
          studentId: `done-${index + 1}`,
          studentName: `完成学生${index + 1}`,
          currentPhase: 'completed',
          phaseStatus: 'completed',
          taskProgress: { completed: 1, total: 1 },
        })),
      }),
    )
    const wrapper = mountReference({ fixedRecords: true })
    await flushPromises()

    const records = wrapper.get('.reference-records-scroll')
    expect(wrapper.get('.classrooms').classes()).toContain('classrooms--fixed-records')
    expect(records.attributes('scroll-y')).toBeDefined()
    expect(records.element.contains(wrapper.get('.reference-students').element)).toBe(true)
    expect(records.element.contains(wrapper.get('.reference-metrics').element)).toBe(false)
    expect(records.element.contains(wrapper.get('.reference-group__heading').element)).toBe(false)
    expect(records.element.contains(wrapper.get('.reference-more').element)).toBe(true)
    expect(wrapper.findAll('.reference-student')).toHaveLength(8)

    await wrapper.get('.reference-more').trigger('click')
    expect(wrapper.findAll('.reference-student')).toHaveLength(10)
  })

  it('distributes the measured fixed region across eight visible student cards', async () => {
    mocks.getDashboard.mockResolvedValue(dashboard('session-1', '1', { students: completedStudents(8) }))
    const wrapper = mountReference({ fixedRecords: true })
    await settleMeasurements(wrapper)
    expect(selectorCallbacks.length).toBeGreaterThan(0)

    latestSelectorCallback()([{ height: 440 }])
    await wrapper.vm.$nextTick()

    const students = wrapper.get('.reference-students')
    expect(students.classes()).toContain('reference-students--balanced')
    expect((students.element as HTMLElement).style.minHeight).toBe('438px')
    expect(wrapper.find('.reference-more').exists()).toBe(false)
  })

  it('reserves the more action for ten students and clears the measured height after expansion', async () => {
    mocks.getDashboard.mockResolvedValue(dashboard('session-1', '1', { students: completedStudents(10) }))
    const wrapper = mountReference({ fixedRecords: true })
    await settleMeasurements(wrapper)
    latestSelectorCallback()({ height: 500 })
    await wrapper.vm.$nextTick()

    const students = wrapper.get('.reference-students')
    expect((students.element as HTMLElement).style.minHeight).toBe('454px')
    expect(wrapper.findAll('.reference-student')).toHaveLength(8)
    expect(wrapper.find('.reference-more').exists()).toBe(true)

    await wrapper.get('.reference-more').trigger('click')

    expect(students.classes()).not.toContain('reference-students--balanced')
    expect((students.element as HTMLElement).style.minHeight).toBe('')
    expect(wrapper.findAll('.reference-student')).toHaveLength(10)
  })

  it('ignores a non-positive selector measurement', async () => {
    mocks.getDashboard.mockResolvedValue(dashboard('session-1', '1', { students: completedStudents(8) }))
    const wrapper = mountReference({ fixedRecords: true })
    await settleMeasurements(wrapper)
    latestSelectorCallback()({ height: 0 })
    await wrapper.vm.$nextTick()

    const students = wrapper.get('.reference-students')
    expect(students.classes()).not.toContain('reference-students--balanced')
    expect((students.element as HTMLElement).style.minHeight).toBe('')
  })

  it('discards an older resize measurement and unregisters the resize listener on unmount', async () => {
    mocks.getDashboard.mockResolvedValue(dashboard('session-1', '1', { students: completedStudents(8) }))
    const wrapper = mountReference({ fixedRecords: true })
    await settleMeasurements(wrapper)
    const oldMeasurement = latestSelectorCallback()
    expect(resizeCallbacks).toHaveLength(1)
    expect(onWindowResize).toHaveBeenCalledTimes(1)

    const resize = resizeCallbacks[0]!
    resize()
    await settleMeasurements(wrapper)
    const currentMeasurement = latestSelectorCallback()
    expect(selectorCallbacks).toHaveLength(2)

    oldMeasurement({ height: 520 })
    await wrapper.vm.$nextTick()
    const students = wrapper.get('.reference-students')
    expect((students.element as HTMLElement).style.minHeight).toBe('')

    currentMeasurement({ height: 360 })
    await wrapper.vm.$nextTick()
    expect((students.element as HTMLElement).style.minHeight).toBe('358px')

    wrapper.unmount()
    expect(offWindowResize).toHaveBeenCalledWith(resize)
  })

  it('uses route status for the publish marker and disables actions without linked records', async () => {
    mocks.getDashboard.mockResolvedValue(
      dashboard('session-1', '1', {
        students: [
          {
            studentId: 'published',
            studentName: '已发布路线',
            currentPhase: 'completed',
            phaseStatus: 'completed',
            learningRouteId: 'route-1',
            routeStatus: 'learning',
            snapshotId: 'snapshot-1',
            finalTestId: 'test-1',
            taskProgress: { completed: 1, total: 1 },
          },
          {
            studentId: 'unpublished',
            studentName: '未发布路线',
            currentPhase: 'completed',
            phaseStatus: 'completed',
            learningRouteId: 'route-2',
            routeStatus: 'generation_failed',
            taskProgress: { completed: 0, total: 0 },
          },
          {
            studentId: 'unlinked',
            studentName: '没有关联记录',
            currentPhase: 'completed',
            phaseStatus: 'completed',
            taskProgress: { completed: 0, total: 0 },
          },
        ],
      }),
    )
    const wrapper = mountReference()
    await flushPromises()

    const published = wrapper.findAll('.reference-student').find((student) => student.text().includes('已发布路线'))
    const unpublished = wrapper.findAll('.reference-student').find((student) => student.text().includes('未发布路线'))
    const unlinked = wrapper.findAll('.reference-student').find((student) => student.text().includes('没有关联记录'))
    expect(published?.text()).toContain('已发布')
    expect(unpublished?.text()).toContain('未发布')
    expect(unlinked).toBeDefined()
    expect(unlinked?.findAll('button')).toHaveLength(2)
    expect(unlinked?.findAll('button').every((button) => button.attributes('disabled') !== undefined)).toBe(true)
  })

  it('emits the cross-class test queue action from the classroom picker', async () => {
    const wrapper = mountReference()
    await flushPromises()

    selectClassroomAction(wrapper, 'queue')
    expect(wrapper.emitted('openTestQueue')).toEqual([[]])
  })

  it('keeps the latest selected classroom when an older dashboard request finishes later', async () => {
    let resolveSecond!: (value: ReturnType<typeof dashboard>) => void
    mocks.getDashboard.mockImplementation((_classId: string, sessionId: string) => {
      if (sessionId === 'session-2') return new Promise((resolve) => (resolveSecond = resolve))
      return Promise.resolve(dashboard(sessionId))
    })
    const wrapper = mountReference()
    await flushPromises()

    selectClassroomAction(wrapper, 'session-2')
    await wrapper.vm.$nextTick()
    selectClassroomAction(wrapper, 'session-3')
    await flushPromises()
    resolveSecond(dashboard('session-2'))
    await flushPromises()

    expect(wrapper.emitted('sessionChange')).toEqual([['session-1'], ['session-3']])
    expect(wrapper.find('.dashboard').exists()).toBe(true)
    expect(wrapper.get('.classroom-picker').text()).toContain('循环研讨')
  })

  it('keeps the new class dashboard when a previous class request finishes later', async () => {
    let resolveOldClass!: (value: ReturnType<typeof dashboard>) => void
    mocks.getDashboard.mockImplementation((classId: string, sessionId: string) => {
      if (classId === '1') return new Promise((resolve) => (resolveOldClass = resolve))
      return Promise.resolve(dashboard(sessionId, classId))
    })
    mocks.getSessionPage.mockImplementation(async ({ classId }: { classId?: string }) => ({
      items: classId === '2' ? [{ ...sessions[0], id: 'class-2-session', classId: '2' }] : sessions,
      total: 1,
    }))
    const wrapper = mountReference({
      classes: [
        { id: 1, name: '旧班' },
        { id: 2, name: '新班' },
      ],
    })
    await flushPromises()
    await wrapper.setProps({ classId: '2' })
    await flushPromises()
    resolveOldClass(dashboard('session-1', '1'))
    await flushPromises()

    expect(mocks.getDashboard).toHaveBeenCalledWith('2', 'class-2-session')
    expect(wrapper.emitted('sessionChange')).toEqual([['class-2-session']])
    expect(wrapper.find('.dashboard').exists()).toBe(true)
  })
})
