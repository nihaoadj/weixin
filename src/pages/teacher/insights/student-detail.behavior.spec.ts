import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentAnalyticsDetailPage from './student-detail.vue'
import type { TeacherInsightsStudentDetail } from '@/features/analytics/public'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
  backPress: undefined as undefined | ((event: { from: 'navigateBack' | 'backbutton' }) => boolean),
}))
const identity = vi.hoisted(() => ({
  current: null as null | { openid: string; role: 'teacher' | 'student' },
}))
const api = vi.hoisted(() => ({
  getDetail: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
  goDetail: vi.fn(),
  relaunchTo: vi.fn(),
}))

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query?: Record<string, string>) => void) => {
    hooks.load = hook
  },
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onBackPress: (hook: (event: { from: 'navigateBack' | 'backbutton' }) => boolean) => {
    hooks.backPress = hook
  },
}))
vi.mock('@/features/identity/public', () => ({
  requireRole: () => identity.current?.role === 'teacher',
  getSession: () => identity.current,
}))
vi.mock('@/features/analytics/public', () => ({ getTeacherInsightsStudent: api.getDetail }))
vi.mock('@/platform/navigation', () => ({
  backOrRoute: api.backOrRoute,
  handleBackPress: api.handleBackPress,
  goDetail: api.goDetail,
  relaunchTo: api.relaunchTo,
  ROUTES: {
    teacherPbl: '/pages/teacher/pbl/index',
    teacherTestQueue: '/pages/teacher/pbl/test-queue',
    teacherInsights: '/pages/teacher/insights/index',
    teacherInsightsStudentDetail: '/pages/teacher/insights/student-detail',
    teacherInsightsResult: '/pages/teacher/insights/result',
  },
}))

const route = (id: string, overrides: Record<string, unknown> = {}) => ({
  routeId: id,
  studentId: 41,
  classId: 8,
  sessionId: 'demo-3',
  publishedAt: '2026-09-01T00:00:00Z',
  resultId: null,
  testGenerationState: null,
  testReviewState: null,
  attemptStatus: null,
  completedSteps: 0,
  totalSteps: 4,
  readingSeconds: 0,
  ...overrides,
})
const result = (id: string, version: 'single_choice_v1' | 'mixed_v2', overrides: Record<string, unknown> = {}) => ({
  resultId: id,
  routeId: `${id}-route`,
  classId: 8,
  sessionId: 'demo-3',
  studentId: 41,
  score: 0,
  completedAt: '2026-09-18T08:30:00Z',
  formatVersion: version,
  ...overrides,
})

const studentDetail = (overrides: Partial<TeacherInsightsStudentDetail> = {}): TeacherInsightsStudentDetail => ({
  scope: {
    classId: 8,
    className: '甲班',
    classIds: [8],
    sessionId: 'demo-3',
    dateFrom: '2026-09-01',
    dateTo: '2026-09-30',
    timezone: 'Asia/Shanghai',
    asOf: '2026-09-30T00:00:00Z',
    metricBasis: {
      progress: 'published_route_cohort',
      results: 'completed_test_window',
      diagnoses: 'completed_diagnosis_window',
    },
  },
  summary: {
    studentId: 41,
    studentName: '学生甲',
    classIds: [8],
    cohort: { publishedRoutes: 2, completedTests: 2, completionRate: 100, gradingTests: 0 },
    periodResults: {
      completedTests: 2,
      averageScore: 0,
      formatCounts: { single_choice_v1: 1, mixed_v2: 1 },
    },
    diagnosisCount: 1,
    lastCompletedAt: '2026-09-18T08:30:00Z',
  },
  routes: [
    route('11111111-2222-4222-8222-333333333333', {
      resultId: 'mixed-result',
      testGenerationState: 'ready',
      testReviewState: 'released',
      attemptStatus: 'submitted',
      completedSteps: 0,
      totalSteps: 4,
      readingSeconds: 0,
    }),
    route('44444444-2222-4222-8222-333333333333', {
      testGenerationState: 'generation_failed',
      testReviewState: 'needs_changes',
      attemptStatus: 'in_progress',
      completedSteps: 2,
      totalSteps: 5,
      readingSeconds: 125,
    }),
  ],
  results: [result('mixed-result', 'mixed_v2'), result('old-result', 'single_choice_v1')],
  diagnoses: [
    {
      participationId: 'demo-3',
      sessionId: 'demo-3',
      classId: 8,
      className: '甲班',
      studentId: 41,
      studentName: '学生甲',
      completedAt: '2026-09-19T08:30:00Z',
      knowledgeGapCodes: ['CELL_INJURY'],
      reasoningIssueCodes: ['EVIDENCE_LINK'],
      knowledgeGaps: [{ code: 'CELL_INJURY', summary: '细胞损伤机制需要复习' }],
      reasoningIssues: [{ code: 'EVIDENCE_LINK', summary: '需要补充证据与结论的联系' }],
    },
  ],
  knowledge: [
    {
      pointCode: 'CELL_INJURY',
      correctCount: 0,
      objectiveCount: 1,
      invalidObjectiveCount: 0,
      shortAnswerCount: 1,
      invalidShortAnswerCount: 0,
      pointsAwarded: 0,
      pointsPossible: 2,
      accuracyRate: 0,
      shortAnswerScoreRate: 0,
    },
  ],
  ...overrides,
})

const mountPage = () =>
  mount(StudentAnalyticsDetailPage, {
    global: {
      stubs: {
        picker: {
          props: ['value'],
          emits: ['change'],
          template: '<div class="date-picker" @change="$emit(\'change\', $event)"><slot /></div>',
        },
      },
    },
  })

async function openPage(query: Record<string, string> = { classId: '8', studentId: '41' }) {
  const wrapper = mountPage()
  hooks.load?.(query)
  hooks.show?.()
  await flushPromises()
  return wrapper
}

describe('T53 teacher student insights detail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    hooks.load = undefined
    hooks.show = undefined
    hooks.backPress = undefined
    identity.current = { openid: 'teacher-1', role: 'teacher' }
    api.getDetail.mockResolvedValue(studentDetail())
  })

  it('loads only the scoped summary projection and separates route learning and test states', async () => {
    const wrapper = await openPage({
      classId: '8',
      studentId: '41',
      sessionId: 'demo-3',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
      panel: 'knowledge',
    })

    expect(api.getDetail).toHaveBeenCalledWith(41, {
      classId: 8,
      sessionId: 'demo-3',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
    expect(wrapper.text()).toContain('0 / 4 步')
    expect(wrapper.text()).toContain('实际阅读：0 秒')
    expect(wrapper.text()).toContain('生成：已生成')
    expect(wrapper.text()).toContain('审核：已发布')
    expect(wrapper.text()).toContain('作答：已提交')
    expect(wrapper.text()).toContain('生成：生成失败')
    expect(wrapper.text()).toContain('审核：退回修改')
    expect(wrapper.text()).toContain('作答：作答中')
    expect(wrapper.text()).toContain('单选旧版 1 份 · 混合题型 1 份')
    expect(wrapper.text()).toContain('历史单选题')
    expect(wrapper.text()).toContain('混合题型')
    expect(wrapper.text()).toContain('0 分')
    expect(wrapper.text()).toContain('细胞损伤机制需要复习')
    expect(wrapper.text()).toContain('需要补充证据与结论的联系')

    await wrapper.findAll('.result-row')[0].get('button').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/pages/teacher/insights/result', {
      resultId: 'mixed-result',
      studentId: 41,
      tab: 'insights',
      panel: 'knowledge',
      classId: 8,
      sessionId: 'demo-3',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
  })

  it('navigates unreleased tests to the scoped PBL queue without writing from insights', async () => {
    api.getDetail.mockResolvedValue(
      studentDetail({
        routes: [
          route('pending', { testGenerationState: 'ready', testReviewState: 'pending_review' }),
          route('changes', { testGenerationState: 'ready', testReviewState: 'needs_changes' }),
          route('failed', { testGenerationState: 'generation_failed', testReviewState: 'needs_changes' }),
          route('released', { testGenerationState: 'ready', testReviewState: 'released' }),
          route('generating', { testGenerationState: 'generating', testReviewState: 'pending_review' }),
        ],
      }),
    )
    const wrapper = await openPage()
    const buttons = wrapper.findAll('.pbl-review-action')
    expect(buttons).toHaveLength(3)
    for (const [index, reviewKind] of ['pending_review', 'needs_changes', 'generation_failed'].entries()) {
      await buttons[index].trigger('click')
      expect(api.relaunchTo).toHaveBeenLastCalledWith('/pages/teacher/pbl/test-queue', {
        section: 'diagnostics',
        classId: 8,
        sessionId: 'demo-3',
        reviewKind,
      })
    }
    identity.current = { openid: 'teacher-2', role: 'teacher' }
    await buttons[0].trigger('click')
    expect(api.relaunchTo).toHaveBeenCalledTimes(3)
  })

  it('shows unfinished classroom discussions even when no route has been published', async () => {
    api.getDetail.mockResolvedValue(
      studentDetail({
        routes: [],
        results: [],
        discussions: [
          {
            participationId: 'participation-1',
            sessionId: 'demo-3',
            classId: 8,
            studentId: 41,
            phase: 'hypothesis',
            status: 'active',
            startedAt: '2026-09-20T07:00:00Z',
            completedAt: null,
          },
        ],
      }),
    )
    const wrapper = await openPage()
    expect(wrapper.text()).toContain('课堂研讨进度')
    expect(wrapper.text()).toContain('阶段：形成假设')
    expect(wrapper.text()).toContain('状态：进行中')
    expect(wrapper.text()).toContain('当前授权范围内没有已发布路线')
    expect(wrapper.text()).not.toContain('完成于')
    expect(wrapper.findAll('.pbl-review-action')).toHaveLength(0)
    expect(api.getDetail).toHaveBeenCalledTimes(1)
  })

  it('keeps genuine zeros distinct from missing result summaries', async () => {
    api.getDetail.mockResolvedValue(
      studentDetail({
        summary: {
          ...studentDetail().summary,
          cohort: { publishedRoutes: 0, completedTests: 0, completionRate: null, gradingTests: 0 },
          periodResults: {
            completedTests: 0,
            averageScore: null,
            formatCounts: { single_choice_v1: 0, mixed_v2: 0 },
          },
          diagnosisCount: 0,
          lastCompletedAt: null,
        },
        routes: [],
        results: [],
        diagnoses: [],
        knowledge: [],
      }),
    )
    const wrapper = await openPage()

    expect(wrapper.text()).toContain('0 条')
    expect(wrapper.text()).toContain('0 份')
    expect(wrapper.text()).toContain('暂无数据')
    expect(wrapper.text()).toContain('暂无已完成测试评分')
    expect(wrapper.text()).toContain('当前范围没有已完成测试结果')
    expect(wrapper.text()).not.toContain('0 分')
    expect(wrapper.findAll('.result-row')).toHaveLength(0)
  })

  it('retries a failed scoped projection through the visible action', async () => {
    api.getDetail.mockRejectedValueOnce(new Error('学情暂不可用')).mockResolvedValueOnce(studentDetail())
    const wrapper = mountPage()
    hooks.load?.({ classId: '8', studentId: '41', sessionId: 'demo-3' })
    hooks.show?.()
    await flushPromises()
    expect(wrapper.text()).toContain('学情暂不可用')
    await wrapper.get('.med-state__action').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('学生甲')
    expect(api.getDetail).toHaveBeenCalledTimes(2)
  })

  it('rejects unsafe class or student identifiers without querying', async () => {
    const wrapper = await openPage({ classId: '8', studentId: '9007199254740992' })
    expect(api.getDetail).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('学生学情链接无效')

    const invalidClass = mountPage()
    hooks.load?.({ classId: '0', studentId: '41' })
    hooks.show?.()
    expect(api.getDetail).not.toHaveBeenCalled()
    expect(invalidClass.text()).toContain('学生学情链接无效')
  })

  it('uses validated insights parameters for no-stack fallback and native back', async () => {
    const wrapper = await openPage({
      classId: '8',
      studentId: 'bad',
      sessionId: 'unsupported-session',
      dateFrom: '2026-13-40',
      dateTo: '2026-09-30',
      panel: 'admin',
    })
    await wrapper.get('.med-state__action').trigger('click')
    expect(api.backOrRoute).toHaveBeenCalledWith(
      '/pages/teacher/insights/index',
      {
        panel: 'students',
        classId: 8,
        dateTo: '2026-09-30',
      },
      1,
    )

    api.backOrRoute.mockReset()
    const loaded = await openPage({ classId: '8', studentId: '41', panel: 'progress' })
    expect(loaded.text()).toContain('学生甲')
    hooks.backPress?.({ from: 'backbutton' })
    expect(api.handleBackPress).toHaveBeenCalledWith('backbutton', '/pages/teacher/insights/index', {
      tab: 'insights',
      panel: 'progress',
      classId: 8,
      sessionId: 'demo-3',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
  })

  it('discards a stale projection after the teacher identity changes', async () => {
    let resolveRequest!: (value: TeacherInsightsStudentDetail) => void
    api.getDetail.mockReturnValueOnce(
      new Promise<TeacherInsightsStudentDetail>((resolve) => {
        resolveRequest = resolve
      }),
    )
    const wrapper = mountPage()
    hooks.load?.({ classId: '8', studentId: '41' })
    hooks.show?.()

    identity.current = { openid: 'teacher-2', role: 'teacher' }
    hooks.show?.()
    resolveRequest(studentDetail())
    await flushPromises()

    expect(wrapper.text()).not.toContain('学生甲')
    expect(wrapper.text()).toContain('教师账号已变更')
    expect(api.getDetail).toHaveBeenCalledTimes(1)
  })
})
