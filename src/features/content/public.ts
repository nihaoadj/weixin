import { getApplicationServices } from '@/bootstrap/wiring'
import { fromProblemView, nullable, toMedicalReviewView, toProblemView, optional } from '@/shared/mappers/presentation'
import type { CaseDraftGenerateInput, CaseDraftGenerateResult } from '@/types/case'
import type { ProblemTarget, ProblemType } from '@/types/domain'
import type { MedicalReviewView } from '@/types/review'
import type { KnowledgeCardContributionInput } from '@/types/knowledge'

const content = () => getApplicationServices().content

export const getProblemsAsync = async () => (await content().getProblems()).map(toProblemView)
export const findProblemAsync = async (id: string) => optional(await content().findProblem(id), toProblemView)
export const saveProblemsAsync = (problems: import('@/types/domain').Problem[]) =>
  content().saveProblems(problems.map(fromProblemView))
export const upsertProblemAsync = async (problem: import('@/types/domain').Problem) =>
  toProblemView(await content().upsertProblem(fromProblemView(problem)))
export const publishProblemAsync = async (id: string) => nullable(await content().publishProblem(id), toProblemView)
export const rejectProblemAsync = async (id: string) => nullable(await content().rejectProblem(id), toProblemView)
export const resetProblemsAsync = async () => (await content().resetProblems()).map(toProblemView)

export const getDemoCaseProblemsAsync = async () => (await content().getDemoCaseProblemsAsync()).map(toProblemView)
export const getGuidedCasesAsync = async () => (await content().getGuidedCasesAsync()).map(toProblemView)
export const getCaseAuthoringAsync = (id: string) => content().getCaseAuthoringAsync(id)
export const cloneCaseVersionAsync = (id: string) => content().cloneCaseVersionAsync(id)
export async function publishGuidedCaseAsync(id: string) {
  return optional(await content().publishGuidedCaseAsync(id), toProblemView)
}

export async function submitGuidedCaseForReviewAsync(id: string) {
  return optional(await content().submitGuidedCaseForReviewAsync(id), toProblemView)
}

export async function getMedicalReviewQueueAsync(status = 'pending') {
  return (await content().getMedicalReviewQueueAsync(status)).map(toProblemView)
}

export async function getMedicalReviewViewAsync(id: string): Promise<MedicalReviewView | undefined> {
  return optional(await content().getMedicalReviewViewAsync(id), toMedicalReviewView)
}

export async function decideGuidedCaseReviewAsync(id: string, decision: 'approved' | 'rejected', comment: string) {
  return optional(await content().decideGuidedCaseReviewAsync(id, decision, comment), toProblemView)
}

export const generateCaseDraftAsync = (input: CaseDraftGenerateInput) => content().generateCaseDraftAsync(input)
export const saveGuidedCaseAsync = async (draft: CaseDraftGenerateResult, id?: string, metadata?: { slug?: string }) =>
  toProblemView(await content().saveGuidedCaseAsync(draft, id, metadata))

export const getReviewQueue = getMedicalReviewQueueAsync
export const getReviewView = getMedicalReviewViewAsync
export const getMedicalReviewView = getMedicalReviewViewAsync
export async function submitMedicalReview(id: string, decision: 'approved' | 'rejected', comment: string) {
  const result = await decideGuidedCaseReviewAsync(id, decision, comment)
  if (!result) throw new Error('病例不存在')
  return result
}
export async function submitCaseForMedicalReview(id: string) {
  const result = await submitGuidedCaseForReviewAsync(id)
  if (!result) throw new Error('病例不存在')
  return result
}

export const getKnowledgeCardContributions = (pointCode?: string) => content().getKnowledgeCardContributions(pointCode)
export const getKnowledgeCardReviewQueue = () => content().getKnowledgeCardReviewQueue()
export const createKnowledgeCardContribution = (input: KnowledgeCardContributionInput) =>
  content().createKnowledgeCardContribution(input)
export const updateKnowledgeCardContribution = (id: number, input: KnowledgeCardContributionInput) =>
  content().updateKnowledgeCardContribution(id, input)
export const submitKnowledgeCardContribution = (id: number) => content().submitKnowledgeCardContribution(id)
export const reviewKnowledgeCardContribution = (id: number, decision: 'approved' | 'rejected', comment: string) =>
  content().reviewKnowledgeCardContribution(id, decision, comment)
export const disableKnowledgeCardContribution = (id: number) => content().disableKnowledgeCardContribution(id)

export type { ProblemTarget, ProblemType }
