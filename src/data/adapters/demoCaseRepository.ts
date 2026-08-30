import { fromProblemView, optional } from '@/data/mappers/presentation'
import type { CaseDraftGenerateInput, CaseDraftGenerateResult, StageAnswer } from '@/types/case'
import type { CaseRepository } from '@/data/repositories/case'

const local = () => import('@/services/caseRepository')

export class DemoCaseRepository implements CaseRepository {
  async getCaseAttemptsAsync() {
    return (await local()).demoAttempts()
  }
  async getDemoCaseProblemsAsync() {
    return (await local()).demoCaseProblems().map(fromProblemView)
  }
  async getGuidedCasesAsync() {
    return (await local()).demoGuidedCases().map(fromProblemView)
  }
  async getCaseAuthoringAsync(id: string) {
    return (await local()).demoAuthoring(id)
  }
  async cloneCaseVersionAsync(id: string) {
    const repo = await local()
    const problem = repo.demoCloneCase(id)
    return { id: problem?.id || id, slug: problem?.slug, draft: problem ? repo.demoAuthoring(problem.id) : undefined }
  }
  async publishGuidedCaseAsync(id: string) {
    return optional((await local()).demoPublishCase(id), fromProblemView)
  }
  async submitGuidedCaseForReviewAsync(id: string) {
    return optional((await local()).demoSubmitCaseForReview(id), fromProblemView)
  }
  async getMedicalReviewQueueAsync(status = 'pending') {
    return (await local()).demoReviewQueue(status).map(fromProblemView)
  }
  async getMedicalReviewViewAsync(id: string) {
    return optional((await local()).demoReviewView(id), fromProblemView)
  }
  async decideGuidedCaseReviewAsync(id: string, decision: 'approved' | 'rejected', comment: string) {
    return optional((await local()).demoDecideCaseReview(id, decision, comment), fromProblemView)
  }
  async getCaseAttemptAsync(id: string) {
    return (await local()).demoFind(id)
  }
  async startCaseAttemptAsync(problemId: string, retryOfId?: string) {
    return (await local()).demoStart(problemId, retryOfId)
  }
  async sendPatientMessageAsync(id: string, content: string) {
    const attempt = (await local()).demoMessage(id, content)
    return attempt.messages[attempt.messages.length - 1]
  }
  async submitCaseStageAsync(id: string, answer: StageAnswer) {
    ;(await local()).demoSubmit(id, answer)
  }
  async completeCaseAttemptAsync(id: string) {
    return (await local()).demoComplete(id)
  }
  async getCaseAssessmentAsync(id: string) {
    return (await local()).demoAssessments().find((item) => item.attemptId === id)
  }
  async generateCaseDraftAsync(input: CaseDraftGenerateInput) {
    return (await local()).demoDraft(input.topic)
  }
  async saveGuidedCaseAsync(draft: CaseDraftGenerateResult, id?: string, _metadata?: { slug?: string }) {
    const problem = fromProblemView((await local()).demoSaveCaseDraft(draft, id))
    return {
      id: problem.id,
      slug: problem.slug,
      status: problem.status,
      medicalReviewStatus: problem.medicalReviewStatus,
    }
  }
}
