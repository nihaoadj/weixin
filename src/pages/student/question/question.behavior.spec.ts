import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuestionResources from './question.vue'
import type { CaseAttempt } from '@/types/case'
import type { Problem } from '@/types/domain'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((options?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
}))
const getProblemsAsync = vi.hoisted(() => vi.fn())
const getDemoCaseProblemsAsync = vi.hoisted(() => vi.fn())
const getStudentQuestionsAsync = vi.hoisted(() => vi.fn())
const getCaseAttemptsAsync = vi.hoisted(() => vi.fn())
const startCaseAttemptAsync = vi.hoisted(() => vi.fn())
const goDetail = vi.hoisted(() => vi.fn())

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (options?: Record<string, string>) => void) => {
    hooks.load = hook
  },
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onBackPress: vi.fn(),
}))
vi.mock('@/features/content/public', () => ({ getProblemsAsync, getDemoCaseProblemsAsync }))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true }))
vi.mock('@/features/qa/public', () => ({ getStudentQuestionsAsync }))
vi.mock('@/features/training/public', () => ({ getCaseAttemptsAsync, startCaseAttemptAsync }))
vi.mock('@/platform/navigation', () => ({
  goDetail,
  handleBackPress: vi.fn(),
  ROUTES: {
    studentCaseTraining: '/pages/student/case-training/case-training',
    studentCaseReport: '/pages/student/case-report/case-report',
    studentQuestionDetail: '/pages/student/question-detail/question-detail',
    studentLearning: '/pages/student/learning/index',
  },
}))

const problem = (id: string, title: string, difficulty: 'basic' | 'intermediate' = 'basic'): Problem => ({
  id,
  type: '病例分析',
  title,
  description: '结构化教学病例',
  target: 'all',
  status: '已发布',
  time: '2026-09-16',
  contentType: 'guided_case',
  specialty: '病理学',
  difficulty,
  estimatedMinutes: 15,
  version: 1,
})

const attempt = (id: string, problemId: string, status: CaseAttempt['status'], startedAt: string): CaseAttempt => ({
  id,
  problemId,
  problemVersion: 1,
  status,
  currentStage: status === 'in_progress' ? 'history' : 'completed',
  opening: { setting: '教学门诊', patientIntro: '合成患者', chiefComplaint: '教学病例' },
  messages: [],
  submissions: [],
  assessmentReady: status !== 'in_progress',
  startedAt,
})

const mountPage = () =>
  mount(QuestionResources, {
    global: {
      stubs: {
        PathologyKnowledgeMap: true,
        MedState: true,
        StudentPrimaryNav: true,
      },
    },
  })

describe('student case list reference UI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    hooks.load = undefined
    hooks.show = undefined
    Object.assign(uni, {
      setNavigationBarTitle: vi.fn(),
      showActionSheet: vi.fn(),
      showToast: vi.fn(),
    })
    getProblemsAsync.mockResolvedValue([
      problem('case-assessed', '细胞损伤与适应：病理证据讨论'),
      problem('case-progress', '炎症：病理证据讨论'),
      problem('case-new', '修复：病理证据讨论', 'intermediate'),
    ])
    getDemoCaseProblemsAsync.mockResolvedValue([problem('case-assessed', '细胞损伤与适应：病理证据讨论')])
    getStudentQuestionsAsync.mockResolvedValue([])
    getCaseAttemptsAsync.mockResolvedValue([
      attempt('attempt-assessed', 'case-assessed', 'assessed', '2026-09-15T08:00:00Z'),
      attempt('attempt-progress', 'case-progress', 'in_progress', '2026-09-16T08:00:00Z'),
    ])
    startCaseAttemptAsync.mockResolvedValue({ id: 'attempt-new' })
  })

  it('removes the in-page resource navigation and maps real attempt states into list actions', async () => {
    const wrapper = mountPage()
    hooks.load?.({ view: 'cases' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.find('.resource-tabs').exists()).toBe(false)
    expect(wrapper.get('.case-hero__title').text()).toBe('病例列表')
    expect(wrapper.findAll('.case-card')).toHaveLength(3)
    expect(wrapper.findAll('.case-card__action').map((item) => item.text())).toEqual(['复盘›', '继续›', '开始›'])
    expect(uni.setNavigationBarTitle).toHaveBeenCalledWith({ title: '病例学习' })

    await wrapper.findAll('.case-card')[0].trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/pages/student/case-report/case-report', {
      attemptId: 'attempt-assessed',
    })
    await wrapper.findAll('.case-card')[1].trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/pages/student/case-training/case-training', {
      id: 'attempt-progress',
    })
    await wrapper.findAll('.case-card')[2].trigger('click')
    await flushPromises()
    expect(startCaseAttemptAsync).toHaveBeenCalledWith('case-new')
    expect(goDetail).toHaveBeenCalledWith('/pages/student/case-training/case-training', { id: 'attempt-new' })
  })

  it('filters the list to studied cases while preserving the direct learning-page entry', async () => {
    const wrapper = mountPage()
    hooks.load?.({ view: 'cases' })
    hooks.show?.()
    await flushPromises()

    const studied = wrapper.findAll('.case-scope-tab').find((item) => item.text() === '已学')
    await studied?.trigger('click')
    expect(wrapper.findAll('.case-card')).toHaveLength(2)
    expect(wrapper.text()).not.toContain('修复：病理证据讨论')
  })

  it('keeps knowledge as a direct URL mode without restoring the page switcher', async () => {
    const wrapper = mountPage()
    hooks.load?.({ view: 'knowledge' })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.resource-tabs').exists()).toBe(false)
    expect(wrapper.find('.case-hero').exists()).toBe(false)
    expect(wrapper.classes()).toContain('page--knowledge')
    expect(wrapper.find('.direct-safety-note').exists()).toBe(false)
    expect(uni.setNavigationBarTitle).toHaveBeenCalledWith({ title: '知识点树' })
  })
  it('normalizes retired question URLs to cases and never reads old questions', async () => {
    getProblemsAsync.mockResolvedValue([
      problem('case-new', '保留病例'),
      { ...problem('retired', '旧讨论题'), contentType: 'question', type: 'open_discussion' },
    ])
    const wrapper = mountPage()
    hooks.load?.({ view: 'questions' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.get('.case-hero__title').text()).toBe('病例列表')
    expect(wrapper.text()).not.toContain('旧讨论题')
    expect(wrapper.text()).not.toContain('PBL 讨论题')
    expect(wrapper.text()).not.toContain('其他练习')
    expect(getStudentQuestionsAsync).not.toHaveBeenCalled()
    expect(wrapper.findAll('.case-card')).toHaveLength(2)
    wrapper.unmount()
  })

  it('opens the knowledge map without loading unrelated case or old question lists', async () => {
    const wrapper = mountPage()
    hooks.load?.({ view: 'knowledge' })
    hooks.show?.()
    await flushPromises()

    expect(getProblemsAsync).not.toHaveBeenCalled()
    expect(getDemoCaseProblemsAsync).not.toHaveBeenCalled()
    expect(getCaseAttemptsAsync).not.toHaveBeenCalled()
    expect(getStudentQuestionsAsync).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
