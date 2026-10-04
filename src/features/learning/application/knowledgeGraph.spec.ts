import { describe, expect, it } from 'vitest'
import { buildKnowledgeGraph, crossModuleDependenciesForModule } from './knowledgeGraph'
import { pathologyCatalogSnapshot as pathologyCatalog } from '@/features/content/public'
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
  learningObjectives: ['目标一', '目标二'],
  reference: '',
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
    rationale: '组件测试关系',
    limitation: '仅用于测试',
    confidence: 'moderate',
    evidenceStatus: 'source_supported',
    medicalReviewStatus: 'pending_expert_review',
    sources: [],
  })),
  prerequisiteCodes,
  status,
})

const persistedCatalogPoints = (): KnowledgeMapPoint[] =>
  pathologyCatalog.map((item) => ({
    code: item.code,
    systemCode: item.system_code,
    systemLabel: item.system_label,
    topic: item.topic,
    title: item.title,
    objective: item.objective,
    learningObjectives: item.learning_objectives,
    reference: item.reference,
    cardCount: item.card_count,
    catalogVersion: item.catalog_version,
    catalogEvidenceStatus: item.catalog_evidence_status,
    catalogMedicalReviewStatus: item.catalog_medical_review_status,
    evidenceStatus: item.evidence_status,
    medicalReviewStatus: item.medical_review_status,
    relationshipNote: item.relationship_note,
    sources: [],
    dependencies: item.dependencies.map((dependency) => ({
      id: dependency.id,
      prerequisiteCode: dependency.prerequisite_code,
      dependentCode: dependency.dependent_code,
      relationKind: dependency.relation_kind,
      rationale: dependency.rationale,
      limitation: dependency.limitation,
      confidence: dependency.confidence,
      evidenceStatus: dependency.evidence_status,
      medicalReviewStatus: dependency.medical_review_status,
      sources: [],
    })),
    prerequisiteCodes: item.prerequisite_codes,
    status: 'not_started',
  }))

describe('knowledge graph', () => {
  it('renders every catalog prerequisite exactly once without inventing relationships', () => {
    const catalogPoints: KnowledgeMapPoint[] = pathologyCatalog.map((item) => ({
      code: item.code,
      systemCode: item.system_code,
      systemLabel: item.system_label,
      topic: item.topic,
      title: item.title,
      objective: item.objective,
      learningObjectives: item.learning_objectives,
      reference: item.reference,
      cardCount: item.card_count,
      catalogVersion: item.catalog_version,
      catalogEvidenceStatus: item.catalog_evidence_status,
      catalogMedicalReviewStatus: item.catalog_medical_review_status,
      evidenceStatus: item.evidence_status,
      medicalReviewStatus: item.medical_review_status,
      relationshipNote: item.relationship_note,
      sources: [],
      dependencies: item.dependencies.map((dependency) => ({
        id: dependency.id,
        prerequisiteCode: dependency.prerequisite_code,
        dependentCode: dependency.dependent_code,
        relationKind: dependency.relation_kind,
        rationale: dependency.rationale,
        limitation: dependency.limitation,
        confidence: dependency.confidence,
        evidenceStatus: dependency.evidence_status,
        medicalReviewStatus: dependency.medical_review_status,
        sources: dependency.sources.map((source) => ({
          sourceKey: source.source_key,
          title: source.title,
          publisher: source.publisher,
          url: source.url,
          sourceType: source.source_type,
          accessedOn: source.accessed_on,
        })),
      })),
      prerequisiteCodes: item.prerequisite_codes,
      status: 'not_started',
    }))
    const moduleByPoint = new Map(catalogPoints.map((item) => [item.code, item.systemCode]))
    const expectedPrerequisites = catalogPoints.flatMap((item) =>
      item.dependencies.map((dependency) => `${dependency.prerequisiteCode}->${dependency.dependentCode}`),
    )
    const expectedCrossModule = catalogPoints.flatMap((item) =>
      item.dependencies
        .filter((dependency) => moduleByPoint.get(dependency.prerequisiteCode) !== item.systemCode)
        .map((dependency) => `${dependency.prerequisiteCode}->${dependency.dependentCode}`),
    )
    const graph = buildKnowledgeGraph(catalogPoints)

    expect(graph.edges.filter((edge) => edge.kind === 'prerequisite').map((edge) => edge.id)).toEqual(
      expectedPrerequisites,
    )
    expect(graph.edges.filter((edge) => edge.crossModule).map((edge) => edge.id)).toEqual(expectedCrossModule)
    expect(expectedCrossModule).toEqual([
      'pathology.cell-injury.necrosis->pathology.inflammation.acute',
      'pathology.inflammation.acute->pathology.repair.granulation',
      'pathology.inflammation.chronic->pathology.repair.fibrosis',
      'pathology.inflammation.vascular->pathology.circulatory.edema',
      'pathology.cell-injury.necrosis->pathology.circulatory.infarction',
    ])
  })

  it('exposes every persisted cross-module edge from either incident focused module without changing direction', () => {
    const edgesFor = (moduleCode: string) =>
      crossModuleDependenciesForModule(persistedCatalogPoints(), moduleCode).map(
        ({ dependency }) => `${dependency.prerequisiteCode}->${dependency.dependentCode}`,
      )

    expect(edgesFor('pathology.cell-injury')).toEqual([
      'pathology.cell-injury.necrosis->pathology.inflammation.acute',
      'pathology.cell-injury.necrosis->pathology.circulatory.infarction',
    ])
    expect(edgesFor('pathology.inflammation')).toEqual([
      'pathology.cell-injury.necrosis->pathology.inflammation.acute',
      'pathology.inflammation.acute->pathology.repair.granulation',
      'pathology.inflammation.chronic->pathology.repair.fibrosis',
      'pathology.inflammation.vascular->pathology.circulatory.edema',
    ])
    expect(edgesFor('pathology.repair')).toEqual([
      'pathology.inflammation.acute->pathology.repair.granulation',
      'pathology.inflammation.chronic->pathology.repair.fibrosis',
    ])
    expect(edgesFor('pathology.circulatory')).toEqual([
      'pathology.inflammation.vascular->pathology.circulatory.edema',
      'pathology.cell-injury.necrosis->pathology.circulatory.infarction',
    ])
    expect(edgesFor('pathology.neoplasm')).toEqual([])
  })

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

  it('rejects a compatibility projection that disagrees with persisted dependencies', () => {
    expect(() =>
      buildKnowledgeGraph([{ ...point('a.1', 'a', 'not_started', ['a.2']), prerequisiteCodes: ['missing'] }]),
    ).toThrow('前置投影与依赖记录不一致')
    expect(() =>
      buildKnowledgeGraph([
        {
          ...point('a.1', 'a', 'not_started', ['a.2']),
          dependencies: [{ ...point('a.1', 'a', 'not_started', ['a.2']).dependencies[0], dependentCode: 'a.2' }],
        },
      ]),
    ).toThrow('依赖目标与节点不一致')
  })

  it('rejects duplicate persisted edges instead of silently dropping a relationship', () => {
    const dependent = point('b.1', 'b', 'not_started', ['a.1'])
    expect(() =>
      buildKnowledgeGraph([
        point('a.1', 'a', 'stable'),
        {
          ...dependent,
          dependencies: [...dependent.dependencies, dependent.dependencies[0]],
          prerequisiteCodes: ['a.1', 'a.1'],
        },
      ]),
    ).toThrow('重复依赖记录')
  })
})
