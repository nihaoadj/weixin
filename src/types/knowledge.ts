export interface KnowledgePoint {
  code: string
  systemCode: string
  systemLabel: string
  topic: string
  title: string
  objective: string
  reference: string
  cardCount: number
  description?: string
  prerequisiteCodes?: string[]
  relatedCodes?: string[]
  caseSlug?: string
  catalogVersion: string
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

export interface ReviewCard {
  cardCode: string
  pointCode: string
  prompt: string
  options: string[]
  dueAt?: string
}

export interface ReviewItem {
  id: number
  pointCode: string
  cardCode?: string
  sourceType: string
  sourceId: string
  note: string
  active: boolean
  createdAt: string
  updatedAt: string
}

export interface ReviewDashboard {
  dueCount: number
  weakPointCodes: string[]
  items: ReviewItem[]
}

export interface ReviewGrade {
  cardCode: string
  correct: boolean
  rating: 'again' | 'hard' | 'good' | 'easy'
  explanation: string
  dueAt: string
}

export interface RecallReveal {
  cardCode: string
  pointCode: string
  prompt: string
  explanation: string
}

export type KnowledgeCardContributionStatus = 'draft' | 'pending' | 'approved' | 'rejected' | 'disabled'

export interface KnowledgeCardContribution {
  id: number
  pointCode: string
  classCode?: string
  version: number
  cardType: 'single_choice' | 'recall'
  prompt: string
  options: string[]
  correctOption?: number
  explanation: string
  reference: string
  status: KnowledgeCardContributionStatus
  reviewerId?: number
  reviewComment: string
  reviewedAt?: string
  createdAt: string
  updatedAt: string
}

export interface KnowledgeCardContributionInput {
  pointCode: string
  classCode?: string
  cardType: 'single_choice' | 'recall'
  prompt: string
  options: string[]
  correctOption?: number
  explanation: string
  reference: string
}
