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
  description: '通过形态变化与机制解释判断损伤是否可逆。',
  reference: '合成病理学总论教学材料',
  cardCount: 2,
  catalogVersion: 'test',
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
    studentPbl: '/pages/student/pbl/pbl',
  },
}))

describe('knowledge node page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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
        scenario: '观察改变。',
        background: [],
        example: { title: '示例', text: '先区分观察与推断。' },
        remediation: [],
        reference: '合成材料',
        reviewStatus: 'unreviewed',
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
        scenario: '观察改变。',
        background: [],
        example: { title: '示例', text: '先区分观察与推断。' },
        remediation: [],
        reference: '合成材料',
        reviewStatus: 'unreviewed',
      },
      path: { id: 1, pointCode: 'current', sessionId: '88', materialVersion: 'test-v1' },
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
    expect(wrapper.text()).toContain('关联知识')
    expect(wrapper.text()).toContain('自测与巩固')

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
})
