import { describe, expect, it } from 'vitest'
import { buildKnowledgeGraph } from './knowledgeGraph'
import type { KnowledgeMapPoint } from '@/types/knowledge'

const point = (
  code: string,
  systemCode: string,
  status: KnowledgeMapPoint['status'],
  prerequisiteCodes: string[] = [],
): KnowledgeMapPoint => ({
  code,
  systemCode,
  systemLabel: systemCode === 'a' ? '模块 A' : '模块 B',
  topic: code,
  title: code.toUpperCase(),
  objective: '',
  reference: '',
  cardCount: 2,
  catalogVersion: 'test',
  prerequisiteCodes,
  status,
})

describe('knowledge graph', () => {
  it('keeps each point once and preserves multi-parent and cross-module dependencies', () => {
    const graph = buildKnowledgeGraph([
      point('a.1', 'a', 'stable'),
      point('a.2', 'a', 'learning', ['a.1']),
      point('b.1', 'b', 'stable'),
      point('b.2', 'b', 'not_started', ['a.2', 'b.1']),
    ])

    expect(graph.nodes.filter((node) => node.kind === 'point')).toHaveLength(4)
    expect(graph.nodes.find((node) => node.id === 'b.2')?.depth).toBe(2)
    expect(graph.edges.filter((edge) => edge.to === 'b.2' && edge.kind === 'prerequisite')).toHaveLength(2)
    expect(graph.edges.find((edge) => edge.id === 'a.2->b.2')?.crossModule).toBe(true)
    expect(graph.modules.map((module) => module.pointCodes)).toEqual([
      ['a.1', 'a.2'],
      ['b.1', 'b.2'],
    ])
  })

  it('uses evidence and prerequisite readiness to select the next point deterministically', () => {
    expect(
      buildKnowledgeGraph([
        point('a.1', 'a', 'stable'),
        point('a.2', 'a', 'not_started', ['a.1']),
        point('b.1', 'b', 'due'),
        point('b.2', 'b', 'weak'),
      ]).recommendedPointCode,
    ).toBe('b.2')

    expect(
      buildKnowledgeGraph([
        point('a.1', 'a', 'stable'),
        point('a.2', 'a', 'not_started', ['a.1']),
        point('b.1', 'b', 'not_started', ['missing']),
      ]).recommendedPointCode,
    ).toBe('a.2')
  })

  it('degrades duplicate, missing and cyclic relationships without dropping usable nodes', () => {
    const graph = buildKnowledgeGraph([
      point('a.1', 'a', 'not_started', ['a.2', 'missing']),
      point('a.2', 'a', 'not_started', ['a.1']),
      point('a.2', 'a', 'weak'),
      point('b.1', 'b', 'stable'),
    ])

    expect(graph.nodes.filter((node) => node.kind === 'point')).toHaveLength(3)
    expect(graph.nodes.find((node) => node.id === 'b.1')).toBeDefined()
    expect(graph.issues.map((issue) => issue.type)).toEqual(
      expect.arrayContaining(['duplicate_point', 'missing_prerequisite', 'cyclic_prerequisite']),
    )
  })
})
