import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LearningHome from './index.vue'

const api = vi.hoisted(() => ({
  show: undefined as undefined | (() => void),
  allowed: true,
  session: { role: 'student', openid: 'student-a' } as { role: string; openid: string },
  getKnowledgeMap: vi.fn(),
  getLearningRoutes: vi.fn(),
  learningGoalLabel: vi.fn((code: string) => `目标 ${code}`),
  goDetail: vi.fn(),
}))

vi.mock('@dcloudio/uni-app', () => ({
  onShow: (hook: () => void) => {
    api.show = hook
  },
}))
vi.mock('@/features/identity/public', () => ({
  getSession: () => api.session,
  requireRole: () => api.allowed,
}))
vi.mock('@/features/learning/public', () => ({
  getKnowledgeMap: api.getKnowledgeMap,
  getLearningRoutes: api.getLearningRoutes,
  learningGoalLabel: api.learningGoalLabel,
}))
vi.mock('@/platform/navigation', () => ({
  goDetail: api.goDetail,
  ROUTES: {
    studentCases: '/question',
    studentKnowledgeNode: '/knowledge-node',
    studentLearningPlans: '/plans',
    studentLearningPlanDetail: '/plan-detail',
    studentPbl: '/pbl',
  },
}))

const point = (code: string, systemCode: string, systemLabel: string, status: string) => ({
  code,
  systemCode,
  systemLabel,
  topic: code,
  title: `知识点 ${code}`,
  objective: '理解本知识点',
  learningObjectives: ['理解本知识点'],
  reference: '课程资料',
  cardCount: 2,
  catalogVersion: 'test-v1',
  catalogEvidenceStatus: 'source_supported',
  catalogMedicalReviewStatus: 'pending_expert_review',
  evidenceStatus: 'source_supported',
  medicalReviewStatus: 'pending_expert_review',
  relationshipNote: '',
  sources: [],
  dependencies: [],
  status,
})

const route = (id: string, options: Record<string, unknown> = {}) => ({
  id,
  title: `学习计划 ${id}`,
  sourceKind: 'classroom',
  sessionLocator: '炎症研讨',
  updatedAt: '2026-09-26T00:00:00Z',
  nextAction: 'reading',
  goalPointCodes: ['inflammation'],
  progress: { completedSteps: 1, totalSteps: 3 },
  ...options,
})

const routePage = (...items: ReturnType<typeof route>[]) => ({ items, total: items.length, limit: 4, offset: 0 })

const mountPage = () =>
  mount(LearningHome, {
    global: {
      stubs: {
        MedIcon: true,
        StudentPrimaryNav: true,
        'scroll-view': { template: '<view><slot /></view>' },
        MedState: {
          props: ['title', 'description'],
          template: '<view class="med-state-stub"><text>{{ title }}</text><text>{{ description }}</text></view>',
        },
      },
    },
  })

const showPage = async () => {
  api.show?.()
  await flushPromises()
}

describe('T44 student learning home behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.show = undefined
    api.allowed = true
    api.session = { role: 'student', openid: 'student-a' }
    api.getKnowledgeMap.mockResolvedValue([
      point('inflammation', 'pathology.inflammation', '炎症', 'weak'),
      point('cell', 'pathology.cell', '细胞损伤', 'stable'),
    ])
    api.getLearningRoutes.mockResolvedValue(routePage())
    api.learningGoalLabel.mockImplementation((code: string) => `目标 ${code}`)
  })

  it('denies a changed or non-student session without reading student learning data', async () => {
    api.allowed = false
    const wrapper = mountPage()

    await showPage()

    expect(wrapper.text()).toContain('学生身份已变化')
    expect(api.getKnowledgeMap).not.toHaveBeenCalled()
    expect(api.getLearningRoutes).not.toHaveBeenCalled()
  })

  it('renders the empty route action and links current plans, knowledge map and retained case entry', async () => {
    const wrapper = mountPage()
    await showPage()

    expect(api.getLearningRoutes).toHaveBeenCalledWith('active', 4, 0)
    expect(wrapper.text()).toContain('完成一次研讨后，学习计划会自动出现在这里')
    await wrapper.get('.routes-empty button').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/pbl')

    await wrapper.get('.routes-section .module-link').trigger('click')
    await wrapper.get('.knowledge-section .module-link').trigger('click')
    await wrapper.get('.practice-card--cases').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/plans')
    expect(api.goDetail).toHaveBeenCalledWith('/question', { view: 'knowledge' })
    expect(api.goDetail).toHaveBeenCalledWith('/question', { view: 'cases' })
    expect(wrapper.findAll('.practice-card')).toHaveLength(2)
    expect(wrapper.text()).toContain('知识点学习')
    expect(wrapper.text()).not.toContain('知识巩固')
    expect(wrapper.text()).not.toContain('三题复习')
    expect(wrapper.text()).not.toContain('教师发布')
    expect(wrapper.find('.practice-card--questions').exists()).toBe(false)
    wrapper.unmount()
  })

  it('recovers an initial route error and opens a route card at its own detail page', async () => {
    const current = route('route-a', {
      nextAction: 'test',
      goalPointCodes: ['inflammation'],
      progress: { completedSteps: 2, totalSteps: 2 },
    })
    api.getLearningRoutes.mockRejectedValueOnce(new Error('计划读取失败')).mockResolvedValueOnce(routePage(current))
    const wrapper = mountPage()
    await showPage()

    expect(wrapper.get('[role="alert"]').text()).toContain('计划读取失败')
    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('学习计划 route-a')
    expect(wrapper.text()).toContain('目标 inflammation')
    expect(wrapper.text()).toContain('已完成 2/2 步')
    expect(wrapper.text()).toContain('开始最终测试')
    await wrapper.get('.route-card').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/plan-detail', { routeId: 'route-a' })
    wrapper.unmount()
  })

  it('keeps loaded routes visible through refresh failures and clears the error after recovery', async () => {
    api.getLearningRoutes
      .mockResolvedValueOnce(routePage(route('route-kept', { sourceKind: 'autonomous', nextAction: 'wait_teacher' })))
      .mockRejectedValueOnce(new Error('暂时无法刷新'))
      .mockResolvedValueOnce(routePage(route('route-kept', { sourceKind: 'autonomous', nextAction: 'wait_teacher' })))
    const wrapper = mountPage()
    await showPage()
    api.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('学习计划 route-kept')
    expect(wrapper.text()).toContain('等待教师开放')
    expect(wrapper.text()).toContain('自主研讨')
    expect(wrapper.get('[role="alert"]').text()).toContain('暂时无法刷新')
    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(api.getLearningRoutes).toHaveBeenCalledTimes(3)
    wrapper.unmount()
  })

  it('sorts knowledge by review status, filters by system and navigates to the selected topic', async () => {
    api.getKnowledgeMap.mockResolvedValue([
      point('stable', 'pathology.cell', '细胞损伤', 'stable'),
      point('not-started', 'pathology.inflammation', '炎症', 'not_started'),
      point('due', 'pathology.cell', '细胞损伤', 'due'),
      point('weak', 'pathology.inflammation', '炎症', 'weak'),
      point('learning', 'pathology.cell', '细胞损伤', 'learning'),
    ])
    const wrapper = mountPage()
    await showPage()

    const rows = wrapper.findAll('.knowledge-row')
    expect(rows.map((row) => row.text())).toEqual([
      expect.stringContaining('知识点 weak'),
      expect.stringContaining('知识点 due'),
      expect.stringContaining('知识点 learning'),
      expect.stringContaining('知识点 not-started'),
      expect.stringContaining('知识点 stable'),
    ])
    expect(rows[0].attributes('aria-label')).toContain('需巩固')
    expect(rows[1].attributes('aria-label')).toContain('待复习')
    expect(rows[4].attributes('aria-label')).toContain('相对稳定')
    await rows[0].trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/knowledge-node', { topicCode: 'weak' })

    const inflammationTab = wrapper.findAll('.category-tab').find((tab) => tab.text() === '炎症')
    expect(inflammationTab).toBeDefined()
    await inflammationTab?.trigger('click')
    expect(wrapper.findAll('.knowledge-row').map((row) => row.text())).toHaveLength(2)
    expect(wrapper.text()).toContain('知识点 weak')
    expect(wrapper.text()).not.toContain('知识点 due')
    await wrapper.get('.practice-card--knowledge').trigger('click')
    expect(api.goDetail).toHaveBeenLastCalledWith('/knowledge-node', { topicCode: 'weak' })
    wrapper.unmount()
  })

  it('retries knowledge loading and sends an empty knowledge learning entry to the complete map', async () => {
    api.getKnowledgeMap.mockRejectedValueOnce(new Error('知识目录暂不可用')).mockResolvedValueOnce([])
    const wrapper = mountPage()
    await showPage()

    expect(wrapper.get('[role="alert"]').text()).toContain('知识目录暂不可用')
    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('当前分类暂无可用知识点')
    await wrapper.get('.knowledge-section .inline-state button').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/question', { view: 'knowledge' })
    await wrapper.get('.practice-card--knowledge').trigger('click')
    expect(api.goDetail).toHaveBeenLastCalledWith('/question', { view: 'knowledge' })
    expect(api.getKnowledgeMap).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })

  it('discards prior student content when the signed-in student changes', async () => {
    api.getLearningRoutes
      .mockResolvedValueOnce(routePage(route('student-a-route')))
      .mockResolvedValueOnce(routePage(route('student-b-route')))
    const wrapper = mountPage()
    await showPage()
    expect(wrapper.text()).toContain('student-a-route')

    api.session = { role: 'student', openid: 'student-b' }
    api.getKnowledgeMap.mockResolvedValueOnce([point('student-b-topic', 'pathology.cell', '细胞损伤', 'learning')])
    api.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('student-b-route')
    expect(wrapper.text()).toContain('知识点 student-b-topic')
    expect(wrapper.text()).not.toContain('student-a-route')
    wrapper.unmount()
  })
})
