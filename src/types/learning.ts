export type LearningTaskType = 'focused_retry' | 'micro_drill' | 'cross_case_transfer'
export type LearningTaskStatus = 'pending' | 'in_progress' | 'completed'

export interface LearningTask {
  id: number
  position: number
  taskType: LearningTaskType
  dimensionId: string
  stageId?: string
  problemId?: number
  status: LearningTaskStatus
  publicDefinition: {
    title?: string
    context?: string
    instruction?: string
    answerSchema?: 'short_text' | 'evidence_grid' | 'decision_cards'
    displayHints?: string[]
    reason?: string
  }
  startedAt?: string
  completedAt?: string
}

export interface LearningPlan {
  id: number
  status: 'active' | 'completed' | 'superseded'
  sourceAssessmentId: number | null
  sourceType: 'case_assessment' | 'pbl_suggestion'
  sourceId: number | null
  targetDimensionIds: string[]
  dueAt: string
  generationMode: string
  modelName: string
  promptVersion: string
  fallbackUsed: boolean
  failureReason?: string
  createdAt: string
  completedAt?: string
  supersededAt?: string
  tasks: LearningTask[]
}

export interface LearningTaskAttempt {
  id: number
  taskId: number
  status: 'in_progress' | 'assessed'
  answer: Record<string, unknown>
  publicDefinition: LearningTask['publicDefinition']
  score?: number
  evidence: string[]
  feedback: string
  nextStep: string
  createdAt: string
  assessedAt?: string
}

export interface LearningNotification {
  id: number
  type: 'learning_plan_ready' | 'learning_plan_due' | 'learning_plan_completed'
  entityType: 'learning_plan'
  entityId: number
  title: string
  body: string
  readAt?: string
  createdAt: string
}

export interface LearningProfile {
  formalDimensions: Array<Record<string, unknown>>
  recentAssessments: Array<Record<string, unknown>>
  practiceMastery: Record<string, { averageScore: number; attemptCount: number }>
  activePlan?: LearningPlan
  unreadCount: number
}
