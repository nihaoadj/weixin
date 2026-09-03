import { getApplicationServices } from '@/bootstrap/wiring'
import type { StageAnswer } from '@/types/case'

const training = () => getApplicationServices().training

export const getCaseAttemptsAsync = () => training().getCaseAttemptsAsync()
export const getCaseAttemptAsync = (id: string) => training().getCaseAttemptAsync(id)
export const startCaseAttemptAsync = (problemId: string, retryOfId?: string) =>
  training().startCaseAttemptAsync(problemId, retryOfId)
export const sendPatientMessageAsync = (id: string, content: string) => training().sendPatientMessageAsync(id, content)
export const submitCaseStageAsync = (id: string, answer: StageAnswer) => training().submitCaseStageAsync(id, answer)
export const completeCaseAttemptAsync = (id: string) => training().completeCaseAttemptAsync(id)
export const getCaseAssessmentAsync = (id: string) => training().getCaseAssessmentAsync(id)
export type { CaseAttempt, CaseAssessment, StageAnswer } from '@/types/case'
