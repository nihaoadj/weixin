export type StudyMaterial = {
  version: string
  pointCode: string
  title: string
  objective: string
  scenario: string
  background: Array<{ title: string; text: string }>
  example: { title: string; text: string }
  remediation: Array<{ title: string; text: string }>
  reference: string
  reviewStatus: 'unreviewed'
}

export type StudyPath = { id: number; pointCode: string; sessionId: string; materialVersion: string }
export type StudyPathState = {
  material: StudyMaterial
  path?: StudyPath
  phase: string
  practiceUnlocked: boolean
  reviewUnlocked: boolean
  legacyAccess: boolean
  summary: string
  lockReason: string
  history: StudyPath[]
}

export type PrivatePracticeQuestion = { index: number; pointCode: string; prompt: string; options: string[] }
export type PrivatePracticeAttempt = {
  id: number
  questionIndex: number
  selectedOption: number
  correct: boolean
  dueAt: string
  createdAt: string
}
export type PrivatePracticeGroup = {
  id: number
  pathId: number
  cycle: 1 | 2
  status: 'generating' | 'ready' | 'failed'
  failure?: string
  questions: PrivatePracticeQuestion[]
  attempts: PrivatePracticeAttempt[]
  dueIndexes: number[]
  canRetest: boolean
  exhausted: boolean
}
export type PrivatePracticeFeedback = PrivatePracticeAttempt & {
  explanation: string
  referenceOption: number
}
