import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentCaseReportPage from './case-report.vue'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
}))
const auth = vi.hoisted(() => ({
  user: { openid: 'student-1', role: 'student' } as { openid: string; role: string } | null,
}))
const api = vi.hoisted(() => ({
  getAssessment: vi.fn(),
  getAttempt: vi.fn(),
  startAttempt: vi.fn(),
  getContext: vi.fn(),
  getPackage: vi.fn(),
}))

vi.mock('@dcloudio/uni-app', () => ({
  onBackPress: vi.fn(),
  onLoad: (hook: (query?: Record<string, string>) => void) => (hooks.load = hook),
  onShow: (hook: () => void) => (hooks.show = hook),
}))
vi.mock('@/features/identity/public', () => ({
  getSession: () => auth.user,
  requireRole: () => auth.user?.role === 'student',
}))
vi.mock('@/features/training/public', () => ({
  getCaseAssessmentAsync: api.getAssessment,
  getCaseAttemptAsync: api.getAttempt,
  startCaseAttemptAsync: api.startAttempt,
}))
vi.mock('@/features/learning/public', () => ({
  getStudentClassroomCaseAttemptContext: api.getContext,
  getStudentClassroomPackage: api.getPackage,
}))
vi.mock('@/platform/navigation', () => ({
  backOrRoute: vi.fn(),
  goPrimary: vi.fn(),
  goReplace: vi.fn(),
  handleBackPress: vi.fn(),
  ROUTES: {
    studentCases: '/student/cases',
    studentCaseTraining: '/student/training',
    studentLearning: '/student/learning',
  },
}))

describe('T43 student case analysis identity scope', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.user = { openid: 'student-1', role: 'student' }
    hooks.load = undefined
    hooks.show = undefined
  })

  it('clears and ignores a private assessment read after the student identity changes', async () => {
    let resolveAssessment!: (value: { summary: string }) => void
    api.getAssessment.mockImplementationOnce(
      () => new Promise<{ summary: string }>((resolve) => (resolveAssessment = resolve)),
    )
    const wrapper = mount(StudentCaseReportPage)
    hooks.load?.({ attemptId: 'private-attempt' })

    auth.user = { openid: 'student-2', role: 'student' }
    hooks.show?.()
    await flushPromises()
    expect(wrapper.text()).toContain('学生身份已变化')

    resolveAssessment({ summary: '学生一的私人病例分析' })
    await flushPromises()
    expect(wrapper.text()).toContain('学生身份已变化')
    expect(wrapper.text()).not.toContain('学生一的私人病例分析')
    expect(api.getContext).not.toHaveBeenCalled()
  })
})
