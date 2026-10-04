export type StudyMaterial = {
  version: string
  pointCode: string
  title: string
  objective: string
  learningObjectives: string[]
  scenario: string
  background: Array<{ title: string; text: string }>
  example: { title: string; text: string }
  remediation: Array<{ title: string; text: string }>
  reference: string
  evidenceStatus: string
  medicalReviewStatus: string
}

export type StudySession = {
  sessionId: string
  pointCode: string
  phase: string
  learningRouteId?: string
}

export type StudyPathState = {
  material: StudyMaterial
  sessions: StudySession[]
  activeSession?: StudySession
  phase: string
  learningRouteId?: string
}
