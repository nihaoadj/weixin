export type CaseStageId = 'history' | 'problem_representation' | 'differential' | 'tests' | 'management'
export type CaseDifficulty = 'basic' | 'intermediate' | 'advanced'
export type CaseContentType = 'question' | 'guided_case'

export interface CaseOpening {
  setting: string
  patientIntro: string
  chiefComplaint: string
}

export interface CaseFact {
  id: string
  category: 'history' | 'exam' | 'test'
  label: string
  value: string
  triggers: string[]
  revealStage: CaseStageId
}

export interface CaseDefinition {
  schemaVersion: 1 | 2
  opening: CaseOpening
  stageInstructions: Record<CaseStageId, string>
  facts: CaseFact[]
  referenceReasoning: Record<string, unknown>
  practiceBlueprints?: PracticeBlueprint[]
}

export interface PracticeBlueprint {
  id: string
  dimensionId: string
  stageId: CaseStageId
  learnerLevel: string
  publicInstruction: string
  allowedVariants: string[]
  fixedFacts: string[]
  fallbackPrompt: string
  answerSchema: 'short_text' | 'evidence_grid' | 'decision_cards'
  criteria: Array<{ id: string; weight: number; keywords: string[]; feedback: string; critical: boolean }>
}

export interface CaseRubricDimension {
  id: string
  label: string
  weight: number
  stageIds: CaseStageId[]
  criteria: Array<{ id: string; label: string; keywords: string[]; feedback: string; critical: boolean }>
}

export type StageAnswer =
  | { stageId: 'history'; summary: string; keyFindings: string[] }
  | { stageId: 'problem_representation'; summary: string }
  | {
      stageId: 'differential'
      items: Array<{ diagnosis: string; supportingEvidence: string[]; opposingEvidence: string[] }>
    }
  | {
      stageId: 'tests'
      items: Array<{ testName: string; rationale: string; priority: 'necessary' | 'optional' | 'avoid' }>
    }
  | { stageId: 'management'; items: Array<{ action: string; rationale: string }>; safetyConsiderations: string[] }

export interface CaseMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  revealedFactIds?: string[]
}
export interface StageSubmission {
  id: string
  stageId: CaseStageId
  answer: StageAnswer
  feedback: string
  inheritedFromId?: string
  createdAt: string
}
export interface CaseAttempt {
  id: string
  problemId: string
  problemVersion: number
  status: 'in_progress' | 'completed' | 'assessed'
  currentStage: CaseStageId | 'completed'
  focusStage?: CaseStageId
  retryOfId?: string
  opening: CaseOpening
  messages: CaseMessage[]
  submissions: StageSubmission[]
  assessmentReady: boolean
  startedAt: string
}
export interface AssessmentDimension {
  dimensionId: string
  label: string
  score: number
  weightedScore: number
  evidence: string[]
  feedback: string
  nextStep: string
}
export interface AssessmentComparison {
  totalDelta: number
  dimensions: Array<{ dimensionId: string; previousScore: number; currentScore: number; delta: number }>
}
export interface CaseAssessment {
  attemptId: string
  totalScore: number
  dimensions: AssessmentDimension[]
  strengths: string[]
  weaknesses: string[]
  nextSteps: string[]
  summary: string
  focusStage: CaseStageId
  modelName: string
  promptVersion: string
  fallbackUsed: boolean
  comparison?: AssessmentComparison
}
export interface CaseDraftGenerateInput {
  topic: string
  learnerLevel: string
  learningObjectives: string[]
}
export interface CaseDraftGenerateResult {
  title: string
  description: string
  specialty: string
  difficulty: CaseDifficulty
  estimatedMinutes: number
  caseDefinition: CaseDefinition
  rubric: { dimensions: CaseRubricDimension[] }
  generationMode: 'model' | 'fallback'
  safetyNotice: string
}

export const caseStages: Array<{ id: CaseStageId; label: string }> = [
  { id: 'history', label: '病史采集' },
  { id: 'problem_representation', label: '问题表征' },
  { id: 'differential', label: '鉴别诊断' },
  { id: 'tests', label: '检查决策' },
  { id: 'management', label: '初步处置' },
]
