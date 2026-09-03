import * as problems from './demoProblemStore'
import * as cases from './demoCaseContentStore'
import { fromProblemView, optional, toProblemView } from '@/shared/mappers/presentation'
import { getSessionContext } from '@/platform/session/context'
import type { ContentRepository } from '@/features/content/domain/ports'
import type { CaseDraftGenerateInput, CaseDraftGenerateResult } from '@/types/case'
import type { UserRole } from '@/types/domain'
import type { Problem } from '@/types/records'
import { AppError } from '@/types/errors'
import type { KnowledgeCardContribution, KnowledgeCardContributionInput } from '@/types/knowledge'

let demoKnowledgeCards: KnowledgeCardContribution[] = []
let nextKnowledgeCardId = 1

function makeKnowledgeCard(input: KnowledgeCardContributionInput): KnowledgeCardContribution {
  const timestamp = new Date().toISOString()
  return {
    id: nextKnowledgeCardId++,
    pointCode: input.pointCode,
    classCode: input.classCode,
    version: 1,
    cardType: input.cardType,
    prompt: input.prompt,
    options: input.options,
    correctOption: input.correctOption,
    explanation: input.explanation,
    reference: input.reference,
    status: 'draft',
    reviewComment: '',
    createdAt: timestamp,
    updatedAt: timestamp,
  }
}

function requireUser(role?: UserRole) {
  const user = getSessionContext()
  if (!user) throw new AppError('请先登录', { code: 'AUTH_REQUIRED', statusCode: 401 })
  if (role && user.role !== role) throw new AppError('无权执行此操作', { code: 'FORBIDDEN', statusCode: 403 })
  return user
}

export class DemoContentRepository implements ContentRepository {
  async getKnowledgeCardContributions(pointCode?: string): Promise<KnowledgeCardContribution[]> {
    const user = requireUser()
    const matched = demoKnowledgeCards.filter((card) => !pointCode || card.pointCode === pointCode)
    if (user.role === 'teacher') return matched
    return matched
      .filter((card) => card.status === 'approved')
      .map((card) => ({ ...card, correctOption: undefined, explanation: '', reviewerId: undefined, reviewComment: '' }))
  }

  async getKnowledgeCardReviewQueue(): Promise<KnowledgeCardContribution[]> {
    const user = requireUser('teacher')
    if (!user.permissions?.includes('medical_review')) throw new AppError('无医学审核权限', { code: 'FORBIDDEN' })
    return demoKnowledgeCards.filter((card) => card.status === 'pending')
  }

  async createKnowledgeCardContribution(input: KnowledgeCardContributionInput): Promise<KnowledgeCardContribution> {
    requireUser('teacher')
    const card = makeKnowledgeCard(input)
    demoKnowledgeCards = [card, ...demoKnowledgeCards]
    return card
  }

  async updateKnowledgeCardContribution(
    id: number,
    input: KnowledgeCardContributionInput,
  ): Promise<KnowledgeCardContribution> {
    requireUser('teacher')
    const current = this.card(id)
    if (!['draft', 'rejected'].includes(current.status))
      throw new AppError('补充卡不能编辑', { code: 'STATE_CONFLICT' })
    const next = { ...current, ...input, updatedAt: new Date().toISOString(), status: 'draft' as const }
    demoKnowledgeCards = demoKnowledgeCards.map((card) => (card.id === id ? next : card))
    return next
  }

  async submitKnowledgeCardContribution(id: number): Promise<KnowledgeCardContribution> {
    requireUser('teacher')
    return this.changeCard(id, { status: 'pending' })
  }

  async reviewKnowledgeCardContribution(
    id: number,
    decision: 'approved' | 'rejected',
    comment: string,
  ): Promise<KnowledgeCardContribution> {
    const user = requireUser('teacher')
    if (!user.permissions?.includes('medical_review')) throw new AppError('无医学审核权限', { code: 'FORBIDDEN' })
    return this.changeCard(id, { status: decision, reviewComment: comment, reviewedAt: new Date().toISOString() })
  }

  async disableKnowledgeCardContribution(id: number): Promise<KnowledgeCardContribution> {
    const user = requireUser('teacher')
    if (!user.permissions?.includes('medical_review')) throw new AppError('无医学审核权限', { code: 'FORBIDDEN' })
    return this.changeCard(id, { status: 'disabled' })
  }

  private card(id: number): KnowledgeCardContribution {
    const current = demoKnowledgeCards.find((card) => card.id === id)
    if (!current) throw new AppError('补充卡不存在', { code: 'RESOURCE_NOT_FOUND' })
    return current
  }

  private changeCard(id: number, patch: Partial<KnowledgeCardContribution>): KnowledgeCardContribution {
    const next = { ...this.card(id), ...patch, updatedAt: new Date().toISOString() }
    demoKnowledgeCards = demoKnowledgeCards.map((card) => (card.id === id ? next : card))
    return next
  }

  async getProblems(): Promise<Problem[]> {
    const user = requireUser()
    const all = problems.getProblems().map(fromProblemView)
    if (user?.role === 'teacher') return all
    return all.filter(
      (problem) =>
        problem.status === 'published' &&
        (problem.target === 'all' ||
          (problem.target === 'individual'
            ? problem.targetIds?.includes(user?.openid || '')
            : user?.classIds?.some((id) => problem.targetIds?.includes(id)))),
    )
  }

  async findProblem(id: string): Promise<Problem | undefined> {
    return (await this.getProblems()).find((problem) => problem.id === id)
  }

  async saveProblems(values: Problem[]): Promise<void> {
    requireUser('teacher')
    problems.saveProblems(values.map(toProblemView))
  }

  async upsertProblem(problem: Problem): Promise<Problem> {
    requireUser('teacher')
    problems.upsertProblem(toProblemView(problem))
    return problem
  }

  async publishProblem(id: string): Promise<Problem | null> {
    requireUser('teacher')
    const problem = await this.findProblem(id)
    return problem
      ? this.upsertProblem({ ...problem, status: 'published', publishTime: new Date().toISOString() })
      : null
  }

  async rejectProblem(id: string): Promise<Problem | null> {
    requireUser('teacher')
    const problem = await this.findProblem(id)
    return problem ? this.upsertProblem({ ...problem, status: 'rejected' }) : null
  }

  async resetProblems(): Promise<Problem[]> {
    requireUser('teacher')
    return problems.resetProblems().map(fromProblemView)
  }

  async getDemoCaseProblemsAsync(): Promise<Problem[]> {
    return cases.demoCaseProblems().map(fromProblemView)
  }

  async getGuidedCasesAsync(): Promise<Problem[]> {
    return cases.demoGuidedCases().map(fromProblemView)
  }

  async getCaseAuthoringAsync(id: string): Promise<CaseDraftGenerateResult | undefined> {
    return cases.demoAuthoring(id)
  }

  async cloneCaseVersionAsync(id: string) {
    const problem = cases.demoCloneCase(id)
    return { id: problem?.id || id, slug: problem?.slug, draft: problem ? cases.demoAuthoring(problem.id) : undefined }
  }

  async publishGuidedCaseAsync(id: string) {
    return optional(cases.demoPublishCase(id), fromProblemView)
  }

  async submitGuidedCaseForReviewAsync(id: string) {
    return optional(cases.demoSubmitCaseForReview(id), fromProblemView)
  }

  async getMedicalReviewQueueAsync(status = 'pending') {
    return cases.demoReviewQueue(status).map(fromProblemView)
  }

  async getMedicalReviewViewAsync(id: string) {
    return optional(cases.demoReviewView(id), fromProblemView)
  }

  async decideGuidedCaseReviewAsync(id: string, decision: 'approved' | 'rejected', comment: string) {
    return optional(cases.demoDecideCaseReview(id, decision, comment), fromProblemView)
  }

  async generateCaseDraftAsync(input: CaseDraftGenerateInput) {
    return cases.demoDraft(input.topic)
  }

  async saveGuidedCaseAsync(draft: CaseDraftGenerateResult, id?: string, _metadata?: { slug?: string }) {
    const problem = fromProblemView(cases.demoSaveCaseDraft(draft, id))
    return {
      id: problem.id,
      slug: problem.slug,
      status: problem.status,
      medicalReviewStatus: problem.medicalReviewStatus,
    }
  }
}
