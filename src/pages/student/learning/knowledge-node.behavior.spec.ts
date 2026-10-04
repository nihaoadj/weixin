import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import KnowledgeNode from './knowledge-node.vue'
import type { KnowledgeMapPoint } from '@/types/knowledge'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((options?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
  back: undefined as undefined | ((event: { from: 'backbutton' }) => boolean),
}))
const getKnowledgeMap = vi.hoisted(() => vi.fn())
const getStudyPath = vi.hoisted(() => vi.fn())
const startStudyPath = vi.hoisted(() => vi.fn())
const createPblMessageId = vi.hoisted(() => vi.fn(() => 'pbl-client'))
const goDetail = vi.hoisted(() => vi.fn())
const goReplace = vi.hoisted(() => vi.fn())

const point = (
  code: string,
  status: KnowledgeMapPoint['status'],
  prerequisiteCodes: string[] = [],
): KnowledgeMapPoint => ({
  code,
  systemCode: 'pathology.cell-injury',
  systemLabel: '细胞损伤与适应',
  topic: code,
  title: code === 'base' ? '细胞适应' : '可逆性损伤',
  objective: '理解细胞损伤机制',
  learningObjectives: ['理解细胞损伤机制', '结合形态线索说明判断依据'],
  description: '通过形态变化与机制解释判断损伤是否可逆。',
  reference: '合成病理学总论教学材料',
  cardCount: 2,
  catalogVersion: 'test',
  catalogEvidenceStatus: 'source_supported',
  catalogMedicalReviewStatus: 'pending_expert_review',
  evidenceStatus: 'source_supported',
  medicalReviewStatus: 'pending_expert_review',
  relationshipNote: '测试关系说明',
  sources: [],
  dependencies: prerequisiteCodes.map((prerequisiteCode, index) => ({
    id: index + 1,
    prerequisiteCode,
    dependentCode: code,
    relationKind: 'mechanistic_basis',
    rationale: '仅用于测试的前置关系',
    limitation: '测试数据',
    confidence: 'moderate',
    evidenceStatus: 'source_supported',
    medicalReviewStatus: 'pending_expert_review',
    sources: [],
  })),
  prerequisiteCodes,
  relatedCodes: code === 'current' ? ['base'] : [],
  status,
})

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (options?: Record<string, string>) => void) => {
    hooks.load = hook
  },
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onBackPress: (hook: (event: { from: 'backbutton' }) => boolean) => {
    hooks.back = hook
  },
}))
vi.mock('@/features/learning/public', () => ({
  getKnowledgeMap,
  getStudyPath,
  startStudyPath,
  getStudyPractices: vi.fn(),
  generateStudyPractice: vi.fn(),
  answerPrivatePractice: vi.fn(),
  getPrivatePractice: vi.fn(),
}))
vi.mock('@/features/pbl/public', () => ({ createPblMessageId }))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true }))
vi.mock('@/platform/navigation', () => ({
  goDetail,
  goReplace,
  handleBackPress: vi.fn(),
  ROUTES: {
    studentCases: '/pages/student/question/question',
    studentKnowledgeNode: '/pages/student/learning/knowledge-node',
    studentKnowledgeLoop: '/pages/student/learning/knowledge-loop',
    studentLearningPlanDetail: '/pages/student/learning/plan-detail',
    studentSourceView: '/pages/student/learning/source-view',
    studentPbl: '/pages/student/pbl/pbl',
  },
}))

describe('knowledge node page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
    hooks.load = undefined
    hooks.show = undefined
    hooks.back = undefined
  })

  it('shows status and relationships without making learning evidence, then uses existing learning entries', async () => {
    getKnowledgeMap.mockResolvedValue([point('base', 'learning'), point('current', 'not_started', ['base'])])
    getStudyPath.mockResolvedValue({
      material: {
        version: 'test-v1',
        pointCode: 'current',
        title: '可逆性损伤',
        objective: '理解细胞损伤机制',
        learningObjectives: ['理解细胞损伤机制', '结合形态线索说明判断依据'],
        scenario: '观察改变。',
        background: [],
        example: { title: '示例', text: '先区分观察与推断。' },
        remediation: [],
        reference: '合成材料',
        evidenceStatus: 'source_supported',
        medicalReviewStatus: 'pending_expert_review',
      },
      phase: 'not_started',
      practiceUnlocked: false,
      reviewUnlocked: false,
      legacyAccess: false,
      summary: '',
      lockReason: '完成研讨后开放练习。',
      history: [],
    })
    startStudyPath.mockResolvedValue({
      material: {
        version: 'test-v1',
        pointCode: 'current',
        title: '可逆性损伤',
        objective: '理解细胞损伤机制',
        learningObjectives: ['理解细胞损伤机制', '结合形态线索说明判断依据'],
        scenario: '观察改变。',
        background: [],
        example: { title: '示例', text: '先区分观察与推断。' },
        remediation: [],
        reference: '合成材料',
        evidenceStatus: 'source_supported',
        medicalReviewStatus: 'pending_expert_review',
      },
      sessions: [{ sessionId: '88', pointCode: 'current', phase: 'problem_framing' }],
      activeSession: { sessionId: '88', pointCode: 'current', phase: 'problem_framing' },
      phase: 'problem_framing',
      practiceUnlocked: false,
      reviewUnlocked: false,
      legacyAccess: false,
      summary: '',
      lockReason: '完成研讨后开放练习。',
      history: [],
    })
    const wrapper = mount(KnowledgeNode)
    hooks.load?.({ topicCode: 'current' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('可逆性损伤')
    expect(wrapper.text()).toContain('建议先回顾：细胞适应')
    expect(wrapper.text()).toContain('仅用于测试的前置关系')
    expect(wrapper.text()).not.toContain('待医学专家审核')
    expect(wrapper.text()).toContain('关联知识')
    expect(wrapper.text()).toContain('研讨准备')
    expect(wrapper.text()).not.toContain('自测与巩固')

    await wrapper.get('.relation-row').trigger('click')
    expect(goReplace).toHaveBeenCalledWith('/pages/student/learning/knowledge-node', { topicCode: 'base' })
    await wrapper.get('.primary-action').trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/pages/student/pbl/pbl', { topicCode: 'current', dialogueId: '88' })
  })

  it('handles an unknown node with a recoverable return action', async () => {
    getKnowledgeMap.mockResolvedValue([point('base', 'stable')])
    const wrapper = mount(KnowledgeNode)
    hooks.load?.({ topicCode: 'missing' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('未找到这个知识节点')
    await wrapper.get('.text-action').trigger('click')
    expect(goReplace).toHaveBeenCalledWith('/pages/student/question/question', { view: 'knowledge' })
  })

  it('renders a concise catalog source and opens the persisted source by identity', async () => {
    const current = point('current', 'not_started')
    current.objective = '按真实目录说明学习目标'
    current.learningObjectives = ['按真实目录说明学习目标', '结合情境线索解释判断依据']
    current.sources = [
      {
        sourceKey: 'S01',
        title: 'Cellular Injury and Adaptation',
        publisher: 'NCBI/PMC',
        url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC7171462/',
        sourceType: 'peer_reviewed',
        accessedOn: '2026-09-16',
      },
    ]
    getKnowledgeMap.mockResolvedValue([current])
    getStudyPath.mockResolvedValue({
      material: {
        version: 'catalog-v4',
        pointCode: 'current',
        title: '可逆性损伤',
        objective: '按入库材料辨认形态，并给出依据。',
        learningObjectives: ['按入库材料辨认形态，并给出依据。', '结合情境线索解释判断依据。'],
        scenario: '观察细胞肿胀与情境线索。',
        background: [{ title: '观察与解释', text: '区分形态和推断。' }],
        example: { title: '引导实例', text: '结合题目情境解释。' },
        remediation: [],
        reference: '公开来源支持，待医学专家审核。',
        evidenceStatus: 'source_supported',
        medicalReviewStatus: 'pending_expert_review',
      },
      phase: 'not_started',
      learningRouteId: 'route-123',
      practiceUnlocked: false,
      reviewUnlocked: false,
      legacyAccess: false,
      summary: '',
      lockReason: '完成研讨后开放练习。',
      history: [],
    })
    const wrapper = mount(KnowledgeNode)
    hooks.load?.({ topicCode: 'current' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('按入库材料辨认形态，并给出依据。')
    expect(wrapper.text()).not.toContain('观察细胞肿胀与情境线索。')
    expect(wrapper.text()).toContain('同行评议文献')
    expect(wrapper.text()).toContain('通过形态变化与机制解释判断损伤是否可逆。')
    expect(wrapper.text()).not.toContain('访问于')
    expect(wrapper.text()).not.toContain('待医学专家审核')
    expect(wrapper.findAll('.goal-row')).toHaveLength(2)
    expect(wrapper.get('.goals-panel').text()).toContain('结合情境线索解释判断依据。')
    expect(wrapper.get('.review-action').text()).toContain('查看研讨学习计划')
    await wrapper.get('.review-action').trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/pages/student/learning/plan-detail', { routeId: 'route-123' })

    await wrapper.get('.source-open').trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/pages/student/learning/source-view', {
      pointCode: 'current',
      sourceKey: 'S01',
    })
  })

  it('keeps the node visible when starting discussion fails, so the action can be retried', async () => {
    getKnowledgeMap.mockResolvedValue([point('base', 'not_started')])
    getStudyPath.mockResolvedValue({
      material: {
        version: 'test',
        pointCode: 'base',
        title: '细胞适应',
        objective: '理解细胞适应。',
        learningObjectives: ['理解细胞适应。', '结合典型形态说明适应类型。'],
        scenario: '观察细胞形态。',
        background: [],
        example: { title: '实例', text: '区分观察和判断。' },
        remediation: [],
        reference: '测试来源',
        evidenceStatus: 'source_supported',
        medicalReviewStatus: 'pending_expert_review',
      },
      phase: 'not_started',
      practiceUnlocked: false,
      reviewUnlocked: false,
      legacyAccess: false,
      summary: '',
      lockReason: '完成研讨后开放练习。',
      history: [],
    })
    startStudyPath.mockRejectedValueOnce(new Error('研讨暂不可用'))
    const wrapper = mount(KnowledgeNode)
    hooks.load?.({ topicCode: 'base' })
    hooks.show?.()
    await flushPromises()

    await wrapper.get('.primary-action').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('细胞适应')
    expect(wrapper.get('.action-error').text()).toBe('研讨暂不可用')
    expect(wrapper.get('.primary-action').attributes('disabled')).toBeUndefined()
  })
})
