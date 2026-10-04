export const ROUTE_CASE_STAGES = [
  {
    phase: 'pathology_recognition',
    label: '病理识别',
  },
  {
    phase: 'mechanism_explanation',
    label: '机制解释',
  },
  {
    phase: 'evidence_judgment',
    label: '证据判断',
  },
  {
    phase: 'summary_reflection',
    label: '总结反思',
  },
] as const
export type RouteCasePhase = (typeof ROUTE_CASE_STAGES)[number]['phase']
export type RouteCaseStage = {
  phase: RouteCasePhase
  goals: Array<{ goalId: string; objective: string }>
  prompt: string
}

export type RouteCaseMessage = {
  id: string
  role: 'student' | 'assistant'
  content: string
  revision: number
  phase?: RouteCasePhase
}
export type RouteCasePendingMessage = {
  clientMessageId: string
  requestRevision: number
  processingState: string
  retryAllowed: boolean
  claimExpiresAt?: string
}
export type RouteCaseRead = {
  id: string
  routeId: string
  stepId: string
  syntheticCase: { title: string; publicScenario: string; caseFacts: string[]; targetPointCodes: string[] }
  phase: string
  revision: number
  status: string
  goals: Array<{ goalId: string; objective: string }>
  stages: RouteCaseStage[]
  messages: RouteCaseMessage[]
  nextPrompt: string
  safetyNotice: string
  pendingMessage?: RouteCasePendingMessage
}
export type RouteCaseMessageResult = {
  clientMessageId: string
  requestRevision: number
  processingState: string
  retryAllowed: boolean
  reply?: string
  phase: string
  revision: number
  decision?: string
  missingElements: string[]
  status: string
}
