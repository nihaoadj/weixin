import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DiagnosticDetailPage from './pbl-diagnostic-detail.vue'
import type { PblDiagnostic, PblWorkItem } from '@/features/pbl/public'
import { getRuntimeMode } from '@/platform/runtime'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
  backPress: undefined as undefined | ((event: { from: 'backbutton' | 'navigateBack' }) => boolean),
}))
const api = vi.hoisted(() => ({
  getWorkItem: vi.fn(),
  goDetail: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
}))
const auth = vi.hoisted(() => ({
  allowed: true,
  session: null as null | { openid: string; role: 'teacher' | 'student' },
}))

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query?: Record<string, string>) => void) => {
    hooks.load = hook
  },
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onBackPress: (handler: (event: { from: 'backbutton' | 'navigateBack' }) => boolean) => {
    hooks.backPress = handler
  },
}))
vi.mock('@/features/identity/public', () => ({
  requireRole: () => auth.allowed && auth.session?.role === 'teacher',
  getSession: () => auth.session,
}))
vi.mock('@/features/pbl/public', () => ({
  getTeacherPblWorkItem: api.getWorkItem,
}))
vi.mock('@/platform/navigation', () => ({
  backOrRoute: api.backOrRoute,
  goDetail: api.goDetail,
  handleBackPress: api.handleBackPress,
  ROUTES: {
    teacherPbl: '/pages/teacher/pbl/index',
    teacherLearningFinalTest: '/pages/teacher/learning/final-test',
  },
}))

const finalTestId = '4f7d3b12-a213-4df8-9f7d-016e8c90bd11'
const sourceSessionQuery = getRuntimeMode() === 'demo' ? 'demo-pbl-1' : '9'
const sourceSessionValue = sourceSessionQuery === '9' ? 9 : sourceSessionQuery

const workItem: PblWorkItem = {
  snapshotId: '42',
  sessionId: '9',
  source: 'classroom_diagnostic',
  status: 'pending',
  student: { id: '2', name: '林同学' },
  class: { id: '3', name: '病理学课堂' },
  topic: 'pathology.inflammation',
  knowledgeGapCount: 0,
  reasoningIssueCount: 0,
  nextAction: '整包审阅',
}
const diagnostic = (schemaVersion: number, sessionKind: 'classroom' | 'student_initiated'): PblDiagnostic => ({
  diagnosticStatus: 'completed',
  assistantReply: '课堂讨论摘要。',
  knowledgeGaps: [],
  reasoningIssues: [],
  schemaVersion,
  sessionKind,
  topicCode: 'pathology.inflammation',
})
const detail = (
  schemaVersion: number,
  sessionKind: 'classroom' | 'student_initiated',
  studentName = '林同学',
  sessionId = workItem.sessionId,
) => ({
  workItem: {
    ...workItem,
    sessionId,
    student: { ...workItem.student, name: studentName },
    finalTestId: schemaVersion >= 7 ? finalTestId : undefined,
  },
  diagnostic: diagnostic(schemaVersion, sessionKind),
  feedbacks: [],
})

function mountPage() {
  return mount(DiagnosticDetailPage, {
    global: {
      stubs: {
        MedState: {
          props: ['title', 'description', 'actionLabel', 'secondaryActionLabel'],
          emits: ['action', 'secondary-action'],
          template:
            '<div class="med-state"><span>{{ title }}</span><span>{{ description }}</span><button class="primary-action" @click="$emit(\'action\')">{{ actionLabel }}</button><button class="secondary-action" @click="$emit(\'secondary-action\')">{{ secondaryActionLabel }}</button></div>',
        },
        TeacherPblWorkItemDetail: {
          props: ['selected'],
          template: '<div class="work-item-detail-stub">{{ selected?.student.name }}</div>',
        },
        TeacherModuleSection: {
          props: ['title', 'description'],
          template: '<section><h2>{{ title }}</h2><p>{{ description }}</p><slot /></section>',
        },
      },
    },
  })
}

describe('teacher fixed diagnostic detail route', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    hooks.load = undefined
    hooks.show = undefined
    hooks.backPress = undefined
    auth.allowed = true
    auth.session = { openid: 'teacher-1', role: 'teacher' }
  })

  it('presents fixed diagnostic and discussion analysis, then carries their PBL context to the final test', async () => {
    api.getWorkItem.mockResolvedValue(detail(7, 'classroom', '林同学', sourceSessionQuery))
    const wrapper = mountPage()
    hooks.load?.({ snapshotId: '42', returnSection: 'diagnostics', classId: '3', sessionId: sourceSessionQuery })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.find('.work-item-detail-stub').exists()).toBe(true)
    expect(wrapper.text()).toContain('研讨分析')
    expect(wrapper.text()).not.toMatch(/返回诊断审阅|独立诊断审批|查看并审阅测试|可检查并编辑/)
    expect(wrapper.get('.route-test-action').text()).toBe('查看最终测试')
    expect(api.getWorkItem).toHaveBeenCalledWith('42')
    await wrapper.get('.route-test-action').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/pages/teacher/learning/final-test', {
      finalTestId,
      returnSection: 'diagnostics',
      classId: 3,
      sessionId: sourceSessionValue,
    })
  })

  it('keeps older fixed diagnostics available without a final-test entry', async () => {
    api.getWorkItem.mockResolvedValue(detail(6, 'classroom'))
    const wrapper = mountPage()
    hooks.load?.({ snapshotId: '42', classId: '3' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.find('.work-item-detail-stub').exists()).toBe(true)
    expect(wrapper.find('.route-test-action').exists()).toBe(false)
  })

  it('uses only validated PBL return context for navigation and native back fallback', async () => {
    const wrapper = mountPage()
    hooks.load?.({ snapshotId: 'invalid', returnSection: 'diagnostics', classId: '3', sessionId: sourceSessionQuery })
    hooks.show?.()
    await flushPromises()

    expect(api.getWorkItem).not.toHaveBeenCalled()
    hooks.backPress?.({ from: 'backbutton' })
    expect(api.handleBackPress).toHaveBeenCalledWith('backbutton', '/pages/teacher/pbl/index', {
      section: 'diagnostics',
      classId: 3,
      sessionId: sourceSessionValue,
    })
    await wrapper.get('.primary-action').trigger('click')
    expect(api.backOrRoute).toHaveBeenCalledWith('/pages/teacher/pbl/index', {
      section: 'diagnostics',
      classId: 3,
      sessionId: sourceSessionValue,
    })
  })

  it('defaults malformed return context to classrooms and drops invalid class and session ids', async () => {
    const wrapper = mountPage()
    hooks.load?.({ snapshotId: '9007199254740992', returnSection: 'approval', classId: '-2', sessionId: 'other' })
    hooks.show?.()
    await flushPromises()
    await wrapper.get('.primary-action').trigger('click')

    expect(api.getWorkItem).not.toHaveBeenCalled()
    expect(api.backOrRoute).toHaveBeenCalledWith('/pages/teacher/pbl/index', { section: 'classrooms' })
  })

  it('requires a safe numeric snapshot id and retries a recoverable work-item read', async () => {
    api.getWorkItem.mockRejectedValueOnce(new Error('暂时无法连接')).mockResolvedValueOnce(detail(7, 'classroom'))
    const wrapper = mountPage()
    hooks.load?.({ snapshotId: '42' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('暂时无法连接')
    await wrapper.get('.primary-action').trigger('click')
    await flushPromises()

    expect(api.getWorkItem).toHaveBeenNthCalledWith(1, '42')
    expect(api.getWorkItem).toHaveBeenNthCalledWith(2, '42')
    expect(wrapper.find('.work-item-detail-stub').exists()).toBe(true)
  })

  it('clears the prior teacher details on identity change and ignores late responses from both teachers', async () => {
    let resolveOldTeacher!: (value: ReturnType<typeof detail>) => void
    let resolveNewTeacher!: (value: ReturnType<typeof detail>) => void
    api.getWorkItem
      .mockResolvedValueOnce(detail(7, 'classroom', '教师甲内容'))
      .mockReturnValueOnce(new Promise((resolve) => (resolveOldTeacher = resolve)))
      .mockReturnValueOnce(new Promise((resolve) => (resolveNewTeacher = resolve)))
    const wrapper = mountPage()
    hooks.load?.({ snapshotId: '42' })
    hooks.show?.()
    await flushPromises()
    expect(wrapper.text()).toContain('教师甲内容')

    hooks.show?.()
    await flushPromises()
    auth.session = { openid: 'teacher-2', role: 'teacher' }
    hooks.show?.()
    await flushPromises()
    expect(wrapper.text()).not.toContain('教师甲内容')

    resolveOldTeacher(detail(7, 'classroom', '旧教师迟到内容'))
    await flushPromises()
    expect(wrapper.text()).not.toContain('旧教师迟到内容')

    resolveNewTeacher(detail(7, 'classroom', '教师乙内容'))
    await flushPromises()

    expect(wrapper.text()).toContain('教师乙内容')
    expect(wrapper.text()).not.toContain('旧教师迟到内容')
  })

  it('clears details after teacher-role loss and ignores a late request result', async () => {
    let resolveReload!: (value: ReturnType<typeof detail>) => void
    api.getWorkItem
      .mockResolvedValueOnce(detail(7, 'classroom', '当前教师内容'))
      .mockReturnValueOnce(new Promise((resolve) => (resolveReload = resolve)))
    const wrapper = mountPage()
    hooks.load?.({ snapshotId: '42' })
    hooks.show?.()
    await flushPromises()
    expect(wrapper.text()).toContain('当前教师内容')

    hooks.show?.()
    auth.allowed = false
    auth.session = { openid: 'teacher-1', role: 'student' }
    hooks.show?.()
    resolveReload(detail(7, 'classroom', '失权后的迟到内容'))
    await flushPromises()

    expect(wrapper.text()).toContain('教师身份已变化')
    expect(wrapper.text()).not.toContain('当前教师内容')
    expect(wrapper.text()).not.toContain('失权后的迟到内容')
    expect(wrapper.find('.route-test-action').exists()).toBe(false)
    expect(api.getWorkItem).toHaveBeenCalledTimes(2)
  })
})
