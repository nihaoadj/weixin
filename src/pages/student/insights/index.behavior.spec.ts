import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './index.vue'
import type { StudentLearningInsightsAction, StudentLearningInsightsPage } from '@/features/learning/public'

const state = vi.hoisted(() => ({
  show: undefined as undefined | (() => void),
  student: 'student-a',
  allowed: true,
  list: vi.fn(),
  detail: vi.fn(),
}))
vi.mock('@dcloudio/uni-app', () => ({ onShow: (hook: () => void) => (state.show = hook) }))
vi.mock('@/features/identity/public', () => ({
  getSession: () => ({ role: 'student', openid: state.student }),
  requireRole: () => state.allowed,
}))
vi.mock('@/features/learning/public', () => ({ getStudentLearningInsights: state.list }))
vi.mock('@/platform/navigation', () => ({
  goDetail: state.detail,
  goPrimary: vi.fn(),
  ROUTES: {
    studentPbl: '/pbl',
    studentLearning: '/learning',
    studentLearningPlanDetail: '/plan',
    studentLearningResult: '/result',
  },
}))
const record = (id: string, kind: StudentLearningInsightsAction['kind'] = 'discussion') => ({
  id,
  session: { id, topicLabel: '病理学研讨', caseTitle: `研讨病例 ${id}` },
  summaryText: kind === 'result' ? '最终测试已完成 · 75 分' : '病例学习进行中',
  updatedAt: '2026-09-30T09:30:00Z',
  action: { kind, sessionId: id, ...(kind !== 'discussion' ? { routeId: `route-${id}` } : {}), label: '继续学习' },
})
const page = (items = [record('mine')], offset = 0, total = items.length): StudentLearningInsightsPage => ({
  summary: {
    dashboard: {
      dataBasis: 'learning_route_results',
      periodStart: '2026-09-28',
      periodEnd: '2026-10-04',
      masteryScore: 75,
      masteryDelta: -5,
      masterySampleCount: 2,
      studyMinutes: 120,
      studyDurationBasis: 'recorded_reading',
      planCompletionRate: 50,
      testedKnowledgeCount: 3,
      aiDiagnosticCount: 4,
      statusLabel: '持续学习',
      trend: [
        { periodStart: '2026-09-21', periodEnd: '2026-09-27', score: 80, sampleCount: 1 },
        { periodStart: '2026-09-28', periodEnd: '2026-10-04', score: 75, sampleCount: 2 },
      ],
      weaknesses: [
        {
          targetType: 'knowledge',
          targetCode: 'inflammation',
          label: '炎症反应',
          occurrences: 2,
          masteryPercentage: 75,
        },
      ],
      aiSummary: '已完成研讨诊断；最新测试提示继续巩固炎症反应。',
    },
  },
  items,
  total,
  limit: 20,
  offset,
})
const mountPage = () =>
  mount(Page, {
    global: {
      stubs: {
        StudentPrimaryNav: true,
        'scroll-view': { template: '<view><slot /></view>' },
        MedState: { props: ['title', 'description'], template: '<view>{{ title }}{{ description }}</view>' },
      },
    },
  })
const show = async () => {
  state.show?.()
  await flushPromises()
}

describe('student insights current workflow in the original layout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    state.show = undefined
    state.student = 'student-a'
    state.allowed = true
    state.list.mockReset()
    state.list.mockResolvedValue(page([]))
  })

  it('preserves all sections and renders persisted dashboard metrics without fake growth', async () => {
    state.list.mockResolvedValue(page())
    const wrapper = mountPage()
    await show()
    for (const section of [
      'profile-strip',
      'weekly-section',
      'trend-section',
      'focus-points-section',
      'diagnosis-section',
      'recent-section',
    ]) {
      expect(wrapper.find(`.${section}`).exists()).toBe(true)
    }
    expect(wrapper.findAll('.metric-card')).toHaveLength(4)
    expect(wrapper.get('.mastery-value').text()).toBe('75')
    expect(wrapper.get('.delta-value').text()).toBe('-5分')
    expect(wrapper.get('.trend-arrow').text()).toBe('↘')
    expect(wrapper.get('.weekly-copy').text()).toContain('共 2 份结果')
    expect(wrapper.text()).toContain('累计阅读时长')
    expect(wrapper.text()).toContain('已测知识点')
    expect(wrapper.text()).toContain('炎症反应')
    expect(wrapper.text()).not.toContain('+28%')
    expect(wrapper.text()).not.toContain('正式评价已通过')
    await wrapper.get('.report-row').trigger('click')
    expect(state.detail).toHaveBeenCalledWith('/pbl', { dialogueId: 'mine' })
    wrapper.unmount()
  })

  it('opens the current plan or completed result rather than the retired report', async () => {
    const response = page([record('active', 'route'), record('done', 'result')])
    response.summary.nextAction = response.items[0]!.action
    state.list.mockResolvedValue(response)
    const wrapper = mountPage()
    await show()
    await wrapper.findAll('.report-row')[0]!.trigger('click')
    expect(state.detail).toHaveBeenCalledWith('/plan', { routeId: 'route-active' })
    await wrapper.findAll('.report-row')[1]!.trigger('click')
    expect(state.detail).toHaveBeenCalledWith('/result', { routeId: 'route-done' })
    await wrapper.get('.diagnosis-action').trigger('click')
    expect(state.detail).toHaveBeenLastCalledWith('/plan', { routeId: 'route-active' })
    wrapper.unmount()
  })

  it('paginates records without replacing the initial dashboard', async () => {
    const later = page([record('last')], 1, 2)
    later.summary.dashboard.masteryScore = 0
    state.list.mockResolvedValueOnce(page([record('first')], 0, 2)).mockResolvedValueOnce(later)
    const wrapper = mountPage()
    await show()
    await wrapper.get('.secondary').trigger('click')
    await flushPromises()
    expect(state.list).toHaveBeenNthCalledWith(2, 20, 1)
    expect(wrapper.findAll('.report-row')).toHaveLength(2)
    expect(wrapper.get('.mastery-value').text()).toBe('75')
    wrapper.unmount()
  })

  it('uses the original more link to expose every evidence-backed weakness', async () => {
    const response = page()
    response.summary.dashboard.weaknesses = Array.from({ length: 4 }, (_, index) => ({
      targetType: 'knowledge',
      targetCode: `point-${index}`,
      label: `知识重点 ${index}`,
      occurrences: 1,
      masteryPercentage: null,
    }))
    state.list.mockResolvedValue(response)
    const wrapper = mountPage()
    await show()
    expect(wrapper.findAll('.focus-card')).toHaveLength(3)
    await wrapper.get('.focus-points-section .section-link').trigger('click')
    expect(wrapper.findAll('.focus-card')).toHaveLength(4)
    await wrapper.get('.focus-points-section .section-link').trigger('click')
    expect(wrapper.findAll('.focus-card')).toHaveLength(3)
    wrapper.unmount()
  })

  it('refreshes on return and distinguishes a completed zero score from no sample', async () => {
    const zero = page()
    zero.summary.dashboard.masteryScore = 0
    zero.summary.dashboard.masteryDelta = null
    const empty = page()
    empty.summary.dashboard.masteryScore = null
    empty.summary.dashboard.masteryDelta = null
    empty.summary.dashboard.masterySampleCount = 0
    state.list.mockResolvedValueOnce(zero).mockResolvedValueOnce(empty)
    const wrapper = mountPage()
    await show()
    expect(wrapper.get('.mastery-value').text()).toBe('0')
    expect(wrapper.get('.weekly-copy').text()).toContain('平均 0 分')
    await show()
    expect(state.list).toHaveBeenCalledTimes(2)
    expect(wrapper.get('.mastery-value').text()).toBe('--')
    expect(wrapper.get('.weekly-copy').text()).toContain('本周尚无')
    wrapper.unmount()
  })

  it('discards a late response after the student changes', async () => {
    let resolveFirst!: (value: StudentLearningInsightsPage) => void
    state.list
      .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce(page([record('new')]))
    const wrapper = mountPage()
    state.show?.()
    state.student = 'student-b'
    await show()
    resolveFirst(page([record('old')]))
    await flushPromises()
    expect(wrapper.text()).toContain('研讨病例 new')
    expect(wrapper.text()).not.toContain('研讨病例 old')
    wrapper.unmount()
  })

  it('discards data if identity changes without another onShow', async () => {
    let resolve!: (value: StudentLearningInsightsPage) => void
    state.list.mockReturnValueOnce(new Promise((done) => (resolve = done)))
    const wrapper = mountPage()
    state.show?.()
    state.student = 'student-b'
    resolve(page([record('private-record')]))
    await flushPromises()
    expect(wrapper.text()).not.toContain('private-record')
    wrapper.unmount()
  })

  it('clears visible records when the student role is no longer valid', async () => {
    state.list.mockResolvedValue(page([record('private-record')]))
    const wrapper = mountPage()
    await show()
    expect(wrapper.text()).toContain('private-record')
    state.allowed = false
    await show()
    expect(wrapper.text()).not.toContain('private-record')
    expect(wrapper.text()).toContain('学生身份已变化')
    wrapper.unmount()
  })

  it('shows API failure instead of stale metrics', async () => {
    state.list.mockResolvedValueOnce(page()).mockRejectedValueOnce(new Error('服务暂不可用'))
    const wrapper = mountPage()
    await show()
    await show()
    expect(wrapper.text()).toContain('服务暂不可用')
    expect(wrapper.find('.weekly-section').exists()).toBe(false)
    wrapper.unmount()
  })
})
