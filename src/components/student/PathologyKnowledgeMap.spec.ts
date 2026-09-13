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
  title: code === 'a.1' ? '细胞适应' : '血管反应',
  objective: '理解机制',
  reference: '合成教学材料',
  cardCount: 2,
  catalogVersion: 'test',
  status,
})

vi.mock('@/features/learning/public', () => ({
  getKnowledgeMap,
  buildKnowledgeGraph: (points: KnowledgeMapPoint[]) => ({
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
        depth: 0,
        moduleCode: item.systemCode,
        point: item,
      })),
    ],
    edges: [
      { id: 'pathology->a', from: 'pathology', to: 'a', kind: 'contains', crossModule: false },
      { id: 'pathology->b', from: 'pathology', to: 'b', kind: 'contains', crossModule: false },
    ],
    modules: [
      { code: 'a', title: '模块 A', order: 0, pointCodes: ['a.1'], stableCount: 0, attentionCount: 1 },
      { code: 'b', title: '模块 B', order: 1, pointCodes: ['b.1'], stableCount: 1, attentionCount: 0 },
    ],
    issues: [],
    recommendedPointCode: 'a.1',
    recommendedModuleCode: 'a',
  }),
}))
vi.mock('@/platform/navigation', () => ({
  goDetail,
  ROUTES: { studentKnowledgeNode: '/pages/student/learning/knowledge-node' },
}))

describe('PathologyKnowledgeMap', () => {
  it('renders the recommended branch, exposes the complete tree and opens a point without changing evidence', async () => {
    getKnowledgeMap.mockResolvedValue([point('a.1', 'a', 'weak'), point('b.1', 'b', 'stable')])
    const wrapper = mount(PathologyKnowledgeMap)
    await flushPromises()

    expect(wrapper.text()).toContain('建议下一步')
    expect(wrapper.text()).toContain('薄弱')
    expect(wrapper.text()).toContain('第 1 层')
    expect(wrapper.findAll('.tree-node')).toHaveLength(3)
    expect(wrapper.findAll('.tree-node.node-module')).toHaveLength(1)
    expect(wrapper.get('.tree-node.is-focused-module').attributes('style')).toContain('left: 511px')
    expect(wrapper.get('button.tree-node.status-weak').attributes('style')).toContain('left: 511px')

    await wrapper.get('button.tree-node.status-weak').trigger('click')
    expect(goDetail).toHaveBeenCalledWith('/pages/student/learning/knowledge-node', { topicCode: 'a.1' })

    await wrapper.get('.mode-button:nth-child(2)').trigger('click')
    expect(wrapper.findAll('.tree-node')).toHaveLength(5)
    await wrapper.get('.mode-button:nth-child(1)').trigger('click')
    expect(wrapper.text()).toContain('92%')
    expect(getKnowledgeMap).toHaveBeenCalledTimes(1)
  })

  it('shows a recoverable retry state when the map cannot be loaded', async () => {
    getKnowledgeMap.mockRejectedValueOnce(new Error('网络不可用'))
    const wrapper = mount(PathologyKnowledgeMap)
    await flushPromises()
    expect(wrapper.text()).toContain('网络不可用')
    expect(wrapper.text()).toContain('重新加载')
  })

  it('keeps zoom controls inside the documented range and restores the focused view', async () => {
    getKnowledgeMap.mockResolvedValue([point('a.1', 'a', 'weak'), point('b.1', 'b', 'stable')])
    const wrapper = mount(PathologyKnowledgeMap)
    await flushPromises()
    const [shrink, enlarge, reset] = wrapper.findAll('.zoom-controls button')

    for (let index = 0; index < 12; index += 1) await enlarge.trigger('click')
    expect(wrapper.text()).toContain('180%')
    for (let index = 0; index < 12; index += 1) await shrink.trigger('click')
    expect(wrapper.text()).toContain('60%')
    await reset.trigger('click')
    expect(wrapper.text()).toContain('92%')
  })
})
