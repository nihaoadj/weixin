import type { CaseAssessment, CaseAttempt, CaseDraftGenerateResult, CaseMessage, StageAnswer } from '@/types/case'
import type { Problem } from '@/types/records'

export interface CaseCatalogPort {
  findCaseDraft(problemId: string): { problem: Problem; draft: CaseDraftGenerateResult } | undefined
}

export interface CaseRepository {
  getCaseAttemptsAsync(): Promise<CaseAttempt[]>
  getCaseAttemptAsync(id: string): Promise<CaseAttempt | undefined>
  startCaseAttemptAsync(problemId: string, retryOfId?: string): Promise<CaseAttempt>
  sendPatientMessageAsync(id: string, content: string): Promise<CaseMessage>
  submitCaseStageAsync(id: string, answer: StageAnswer): Promise<void>
  completeCaseAttemptAsync(id: string): Promise<CaseAssessment>
  getCaseAssessmentAsync(id: string): Promise<CaseAssessment | undefined>
}
