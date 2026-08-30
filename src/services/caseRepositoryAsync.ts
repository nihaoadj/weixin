import { toProblemView, optional } from '@/data/mappers/presentation'
import { isApiMode } from '@/config/runtime'
import { ApiCaseRepository } from '@/data/adapters/apiCaseRepository'
import { DemoCaseRepository } from '@/data/adapters/demoCaseRepository'
import type { CaseRepository } from '@/data/repositories/case'
export type { MedicalReviewEntry, MedicalReviewView } from '@/types/review'

const repository: CaseRepository = isApiMode() ? new ApiCaseRepository() : new DemoCaseRepository()
export const getCaseAttemptsAsync = repository.getCaseAttemptsAsync.bind(repository)
export const getDemoCaseProblemsAsync = async (...args: Parameters<CaseRepository['getDemoCaseProblemsAsync']>) =>
  (await repository.getDemoCaseProblemsAsync(...args)).map(toProblemView)
export const getGuidedCasesAsync = async (...args: Parameters<CaseRepository['getGuidedCasesAsync']>) =>
  (await repository.getGuidedCasesAsync(...args)).map(toProblemView)
export const getCaseAuthoringAsync = repository.getCaseAuthoringAsync.bind(repository)
export const cloneCaseVersionAsync = repository.cloneCaseVersionAsync.bind(repository)
export const publishGuidedCaseAsync = async (...args: Parameters<CaseRepository['publishGuidedCaseAsync']>) =>
  optional(await repository.publishGuidedCaseAsync(...args), toProblemView)
export const submitGuidedCaseForReviewAsync = async (
  ...args: Parameters<CaseRepository['submitGuidedCaseForReviewAsync']>
) => optional(await repository.submitGuidedCaseForReviewAsync(...args), toProblemView)
export const getMedicalReviewQueueAsync = async (...args: Parameters<CaseRepository['getMedicalReviewQueueAsync']>) =>
  (await repository.getMedicalReviewQueueAsync(...args)).map(toProblemView)
export const getMedicalReviewViewAsync = async (...args: Parameters<CaseRepository['getMedicalReviewViewAsync']>) =>
  optional(await repository.getMedicalReviewViewAsync(...args), toProblemView)
export const decideGuidedCaseReviewAsync = async (...args: Parameters<CaseRepository['decideGuidedCaseReviewAsync']>) =>
  optional(await repository.decideGuidedCaseReviewAsync(...args), toProblemView)
export const getCaseAttemptAsync = repository.getCaseAttemptAsync.bind(repository)
export const startCaseAttemptAsync = repository.startCaseAttemptAsync.bind(repository)
export const sendPatientMessageAsync = repository.sendPatientMessageAsync.bind(repository)
export const submitCaseStageAsync = repository.submitCaseStageAsync.bind(repository)
export const completeCaseAttemptAsync = repository.completeCaseAttemptAsync.bind(repository)
export const getCaseAssessmentAsync = repository.getCaseAssessmentAsync.bind(repository)
export const generateCaseDraftAsync = repository.generateCaseDraftAsync.bind(repository)
export const saveGuidedCaseAsync = async (...args: Parameters<CaseRepository['saveGuidedCaseAsync']>) =>
  toProblemView(await repository.saveGuidedCaseAsync(...args))
