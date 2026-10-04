export interface KnowledgeSource {
  sourceKey: string
  title: string
  publisher: string
  url: string
  sourceType: string
  accessedOn: string
}

export interface KnowledgeDependency {
  id: number
  prerequisiteCode: string
  dependentCode: string
  relationKind: string
  rationale: string
  limitation: string
  confidence: string
  evidenceStatus: string
  medicalReviewStatus: string
  sources: KnowledgeSource[]
}

export interface KnowledgePoint {
  code: string
  systemCode: string
  systemLabel: string
  topic: string
  title: string
  objective: string
  learningObjectives: string[]
  reference: string
  cardCount: number
  description?: string
  prerequisiteCodes?: string[]
  relatedCodes?: string[]
  caseSlug?: string
  catalogVersion: string
  catalogEvidenceStatus: string
  catalogMedicalReviewStatus: string
  evidenceStatus: string
  medicalReviewStatus: string
  relationshipNote: string
  sources: KnowledgeSource[]
  dependencies: KnowledgeDependency[]
}

export type KnowledgeStatus = 'not_started' | 'weak' | 'learning' | 'due' | 'stable'

export interface KnowledgeMapPoint extends KnowledgePoint {
  status: KnowledgeStatus
}

export type KnowledgeGraphNodeKind = 'root' | 'module' | 'point'
export type KnowledgeGraphEdgeKind = 'contains' | 'prerequisite'

export interface KnowledgeGraphNode {
  id: string
  kind: KnowledgeGraphNodeKind
  title: string
  order: number
  depth: number
  moduleCode?: string
  point?: KnowledgeMapPoint
}

export interface KnowledgeGraphEdge {
  id: string
  from: string
  to: string
  kind: KnowledgeGraphEdgeKind
  crossModule: boolean
}

export interface KnowledgeGraphModule {
  code: string
  title: string
  order: number
  pointCodes: string[]
  stableCount: number
  attentionCount: number
}

export interface KnowledgeGraphIssue {
  type: 'duplicate_point' | 'missing_prerequisite' | 'cyclic_prerequisite'
  pointCode: string
  relatedCode?: string
}

export interface KnowledgeGraph {
  rootId: string
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
  modules: KnowledgeGraphModule[]
  issues: KnowledgeGraphIssue[]
  recommendedPointCode?: string
  recommendedModuleCode?: string
}
