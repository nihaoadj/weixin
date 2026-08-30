import type {
  CaseAssessment,
  CaseAttempt,
  CaseDraftGenerateInput,
  CaseDraftGenerateResult,
  CaseMessage,
  StageAnswer,
} from '@/types/case'
import type { Problem } from '@/types/records'
import type { MedicalReviewRecord as MedicalReviewView } from '@/types/review'

export interface CaseRepository {
  getCaseAttemptsAsync(): Promise<CaseAttempt[]>
  getDemoCaseProblemsAsync(): Promise<Problem[]>
  getGuidedCasesAsync(): Promise<Problem[]>
  getCaseAuthoringAsync(id: string): Promise<CaseDraftGenerateResult | undefined>
  cloneCaseVersionAsync(id: string): Promise<{ id: string; slug?: string; draft?: CaseDraftGenerateResult }>
  publishGuidedCaseAsync(id: string): Promise<Problem | undefined>
  submitGuidedCaseForReviewAsync(id: string): Promise<Problem | undefined>
  getMedicalReviewQueueAsync(status?: string): Promise<Problem[]>
  getMedicalReviewViewAsync(id: string): Promise<MedicalReviewView | undefined>
  decideGuidedCaseReviewAsync(
    id: string,
    decision: 'approved' | 'rejected',
    comment: string,
  ): Promise<Problem | undefined>
  getCaseAttemptAsync(id: string): Promise<CaseAttempt | undefined>
  startCaseAttemptAsync(problemId: string, retryOfId?: string): Promise<CaseAttempt>
  sendPatientMessageAsync(id: string, content: string): Promise<CaseMessage>
  submitCaseStageAsync(id: string, answer: StageAnswer): Promise<void>
  completeCaseAttemptAsync(id: string): Promise<CaseAssessment>
  getCaseAssessmentAsync(id: string): Promise<CaseAssessment | undefined>
  generateCaseDraftAsync(input: CaseDraftGenerateInput): Promise<CaseDraftGenerateResult>
  saveGuidedCaseAsync(
    draft: CaseDraftGenerateResult,
    id?: string,
    metadata?: { slug?: string },
  ): Promise<Pick<Problem, 'id' | 'slug' | 'status' | 'medicalReviewStatus'>>
}
