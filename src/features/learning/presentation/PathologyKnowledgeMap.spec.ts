import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import PathologyKnowledgeMap from './PathologyKnowledgeMap.vue'
import type { KnowledgeMapPoint } from '@/types/knowledge'

const getKnowledgeMap = vi.hoisted(() => vi.fn())
const goDetail = vi.hoisted(() => vi.fn())

const point = (code: string, systemCode: string, status: KnowledgeMapPoint['status']): KnowledgeMapPoint => ({
  code,
  systemCode,
  systemLabel: systemCode === 'a' ? '模块 A' : '模块 B',
  topic: code,
  title: code === 'a.1' ? '细胞适应' : code === 'a.2' ? '肉芽组织' : '血管反应',
  objective: '理解机制',
  learningObjectives: ['理解机制', '说明判断依据'],
  reference: '合成教学材料',
  cardCount: 2,
  catalogVersion: 'test',
  catalogEvidenceStatus: 'source_supported',
  catalogMedicalReviewStatus: 'pending_expert_review',
  evidenceStatus: 'source_supported',
  medicalReviewStatus: 'pending_expert_review',
  relationshipNote: '测试关系说明',
  sources: [],
  dependencies:
    code === 'b.1'
      ? [
          {
            id: 1,
            prerequisiteCode: 'a.1',
            dependentCode: 'b.1',
            relationKind: 'mechanistic_basis',
            rationale: '跨主题测试关系',
            limitation: '仅用于组件测试',
            confidence: 'high',
            evidenceStatus: 'source_supported',
            medicalReviewStatus: 'pending_expert_review',
            sources: [],
          },
        ]
      : [],
  status,
})

vi.mock('@/features/learning/public', () => ({
  getKnowledgeMap,
  crossModuleDependenciesForModule: (points: KnowledgeMapPoint[], moduleCode: string) => {
    const byCode = new Map(points.map((item) => [item.code, item]))
    return points.flatMap((dependent) =>
      dependent.dependencies.flatMap((dependency) => {
        const prerequisite = byCode.get(dependency.prerequisiteCode)
        if (
          !prerequisite ||
          prerequisite.systemCode === dependent.systemCode ||
          (prerequisite.systemCode !== moduleCode && dependent.systemCode !== moduleCode)
        )
          return []
        return [{ dependency, prerequisite, dependent }]
      }),
    )
  },
  buildKnowledgeGraph: (points: KnowledgeMapPoint[]) => {
    const modulePoints = (code: string) => points.filter((item) => item.systemCode === code)
    return {
      rootId: 'pathology',
      nodes: [
        { id: 'pathology', kind: 'root', title: '病理学总论', order: 0, depth: -2 },
        { id: 'a', kind: 'module', title: '模块 A', order: 0, depth: -1, moduleCode: 'a' },
        { id: 'b', kind: 'module', title: '模块 B', order: 1, depth: -1, moduleCode: 'b' },
        ...points.map((item, order) => ({
          id: item.code,
          kind: 'point' as const,
          title: item.title,
          order,
          depth: item.code === 'a.2' || item.code === 'a.3' ? 3 : 0,
          moduleCode: item.systemCode,
          point: item,
        })),
      ],
      edges: [
        { id: 'pathology->a', from: 'pathology', to: 'a', kind: 'contains', crossModule: false },
        { id: 'pathology->b', from: 'pathology', to: 'b', kind: 'contains', crossModule: false },
        { id: 'a.1->a.2', from: 'a.1', to: 'a.2', kind: 'prerequisite', crossModule: false },
        ...(points.some((item) => item.code === 'a.3')
          ? [{ id: 'a.1->a.3', from: 'a.1', to: 'a.3', kind: 'prerequisite', crossModule: false }]
          : []),
        { id: 'a.1->b.1', from: 'a.1', to: 'b.1', kind: 'prerequisite', crossModule: true },
      ],
      modules: [
        {
          code: 'a',
          title: '模块 A',
          order: 0,
          pointCodes: modulePoints('a').map((item) => item.code),
          stableCount: modulePoints('a').filter((item) => item.status === 'stable').length,
          attentionCount: modulePoints('a').filter((item) => item.status !== 'stable').length,
        },
        {
          code: 'b',
          title: '模块 B',
          order: 1,
          pointCodes: modulePoints('b').map((item) => item.code),
          stableCount: modulePoints('b').filter((item) => item.status === 'stable').length,
          attentionCount: modulePoints('b').filter((item) => item.status !== 'stable').length,
        },
      ],
      issues: [],
      recommendedPointCode: 'a.1',
      recommendedModuleCode: 'a',
    }
  },
}))
vi.mock('@/platform/navigation', () => ({
  goDetail,
  ROUTES: { studentKnowledgeNode: '/pages/student/learning/knowledge-node' },
}))

const mountMap = () =>
  mount(PathologyKnowledgeMap, {
    global: {
      stubs: {
        'scroll-view': { template: '<div><slot /></div>' },
      },
    },
  })

describe('PathologyKnowledgeMap', () => {
  it('renders the recommended branch, exposes the complete tree and opens a point without changing evidence', async () => {
    getKnowledgeMap.mockResolvedValue([point('a.1', 'a', 'weak'), point('b.1', 'b', 'stable')])
    const wrapper = mountMap()
    await flushPromises()

    expect(wrapper.text()).toContain('建议下一步')
    expect(wrapper.get('.title').text()).toBe('从概念主干，走到病理机制')
    expect(wrapper.find('.tree-hero').exists()).toBe(true)
    expect(wrapper.find('.next-book').exists()).toBe(true)
    expect(wrapper.findAll('.module-tab-icon')).toHaveLength(2)
    expect(wrapper.find('.tree-toolbar').exists()).toBe(true)
    expect(wrapper.text()).toContain('薄弱')
    expect(wrapper.text()).toContain('第 1 层')
    expect(wrapper.findAll('.tree-node')).toHaveLength(3)
    expect(wrapper.findAll('.tree-node.node-module')).toHaveLength(1)
    expect(wrapper.get('.tree-node.is-focused-module').attributes('style')).toContain('left: 511px')
    expect(wrapper.get('button.tree-node.status-weak').attributes('style')).toContain('left: 511px')
    expect(wrapper.get('.cross-dependency-strip').text()).toContain('细胞适应→血管反应')

    await wrapper.get('button.tree-node.status-weak').trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/pages/student/learning/knowledge-node', { topicCode: 'a.1' })

    await wrapper.findAll('.module-tab')[1].trigger('click')
    expect(wrapper.get('.cross-dependency-strip').text()).toContain('细胞适应→血管反应')
    await wrapper.get('.mode-button:nth-child(1)').trigger('click')
    await wrapper.get('.mode-button:nth-child(2)').trigger('click')
    expect(wrapper.findAll('.tree-node')).toHaveLength(5)
    expect(wrapper.text()).toContain('20%')
    await wrapper.get('.mode-button:nth-child(1)').trigger('click')
    expect(wrapper.text()).toContain('60%')
    expect(getKnowledgeMap).toHaveBeenCalledTimes(1)
  })

  it('shows a recoverable retry state when the map cannot be loaded', async () => {
    getKnowledgeMap.mockRejectedValueOnce(new Error('网络不可用'))
    const wrapper = mountMap()
    await flushPromises()
    expect(wrapper.text()).toContain('网络不可用')
    expect(wrapper.text()).toContain('重新加载')
  })

  it('keeps zoom controls inside the documented range and restores the focused view', async () => {
    getKnowledgeMap.mockResolvedValue([point('a.1', 'a', 'weak'), point('b.1', 'b', 'stable')])
    const wrapper = mountMap()
    await flushPromises()
    const [shrink, enlarge, reset] = wrapper.findAll('.zoom-controls button')

    for (let index = 0; index < 12; index += 1) await enlarge.trigger('click')
    expect(wrapper.text()).toContain('180%')
    for (let index = 0; index < 14; index += 1) await shrink.trigger('click')
    expect(wrapper.text()).toContain('20%')
    await reset.trigger('click')
    expect(wrapper.text()).toContain('60%')
  })

  it('compacts missing source depths into consistent focused-level spacing', async () => {
    getKnowledgeMap.mockResolvedValue([
      point('a.1', 'a', 'weak'),
      point('a.2', 'a', 'not_started'),
      point('b.1', 'b', 'stable'),
    ])
    const wrapper = mountMap()
    await flushPromises()

    const focusedPoints = wrapper.findAll('.tree-node.node-point')
    expect(focusedPoints).toHaveLength(2)
    expect(focusedPoints[0].attributes('style')).toContain('top: 332px')
    expect(focusedPoints[1].attributes('style')).toContain('top: 474px')
  })

  it('keeps every enlarged-tree edge reachable through bounded panning', async () => {
    getKnowledgeMap.mockResolvedValue([point('a.1', 'a', 'weak'), point('b.1', 'b', 'stable')])
    const wrapper = mountMap()
    await flushPromises()
    await wrapper.get('.mode-button:nth-child(2)').trigger('click')
    const enlarge = wrapper.findAll('.zoom-controls button')[1]
    await enlarge.trigger('click')
    await enlarge.trigger('click')
    expect(wrapper.text()).toContain('50%')

    const viewport = wrapper.get('.tree-viewport')
    await viewport.trigger('touchstart', { touches: [{ clientX: 200, clientY: 200 }] })
    await viewport.trigger('touchmove', { touches: [{ clientX: 600, clientY: 200 }] })
    const rightwardTransform = wrapper.get('.tree-plane').attributes('style') || ''
    const rightwardOffset = Number(rightwardTransform.match(/translate\(([-\d.]+)px/)?.[1])
    expect(rightwardOffset).toBeGreaterThan(100)

    await viewport.trigger('touchstart', { touches: [{ clientX: 200, clientY: 200 }] })
    await viewport.trigger('touchmove', { touches: [{ clientX: -600, clientY: 200 }] })
    const leftwardTransform = wrapper.get('.tree-plane').attributes('style') || ''
    const leftwardOffset = Number(leftwardTransform.match(/translate\(([-\d.]+)px/)?.[1])
    expect(leftwardOffset).toBeLessThan(-100)
  })

  it('reuses the focused-tree sibling topology in the overview and preserves cross-module prerequisites', async () => {
    getKnowledgeMap.mockResolvedValue([
      point('a.1', 'a', 'weak'),
      point('a.2', 'a', 'not_started'),
      point('a.3', 'a', 'not_started'),
      point('b.1', 'b', 'stable'),
    ])
    const wrapper = mountMap()
    await flushPromises()
    await wrapper.get('.mode-button:nth-child(2)').trigger('click')

    const allTreePoints = wrapper.findAll('.tree-node.node-point')
    expect(allTreePoints).toHaveLength(4)
    expect(allTreePoints[0].attributes('style')).toContain('top: 332px')
    expect(allTreePoints[1].attributes('style')).toContain('top: 474px')
    expect(allTreePoints[2].attributes('style')).toContain('top: 474px')
    expect(allTreePoints[1].attributes('style')).not.toBe(allTreePoints[2].attributes('style'))
    expect(allTreePoints[1].attributes('style')).toContain('width: 140px')
    const crossSegments = wrapper.findAll('.tree-edge.cross')
    expect(crossSegments).toHaveLength(1)
    expect(wrapper.find('.tree-edge.cross.edge-direct.is-terminal').exists()).toBe(true)
    expect(crossSegments[0].attributes('data-edge-from')).toBe('a.1')
    expect(crossSegments[0].attributes('data-edge-to')).toBe('b.1')
    expect(crossSegments[0].attributes('style')).toContain('transform: rotate(')
    expect(wrapper.text()).toContain('跨主题学习前置（圆点指向后学）')
    expect(wrapper.text()).toContain('依赖来自 test 持久化目录；公开来源支持，当前仍待医学专家审核。')
    expect(wrapper.text()).toContain('测试关系说明')
  })
})
