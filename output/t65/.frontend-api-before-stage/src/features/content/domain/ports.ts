import type { CaseDraftGenerateInput, CaseDraftGenerateResult } from '@/types/case'
import type { Problem } from '@/types/records'
import type { MedicalReviewRecord } from '@/types/review'
import type { KnowledgeCardContribution, KnowledgeCardContributionInput } from '@/types/knowledge'
import type { TeacherContentActionSummary } from './teacherActionSummary'
import type {
  TeacherQuestionBankContent,
  TeacherQuestionBankFilters,
  TeacherQuestionBankImportInput,
  TeacherQuestionBankItem,
  TeacherQuestionBankPage,
  TeacherQuestionBankSource,
} from './questionBank'

export interface TeacherQuestionBankRepository {
  getTeacherQuestionBankSource(sourceId: string): Promise<TeacherQuestionBankSource>
  listTeacherQuestionBank(filters?: TeacherQuestionBankFilters): Promise<TeacherQuestionBankPage>
  getTeacherQuestionBankItem(id: number): Promise<TeacherQuestionBankItem>
  importTeacherQuestionBankItem(input: TeacherQuestionBankImportInput): Promise<TeacherQuestionBankItem>
  updateTeacherQuestionBankItem(
    id: number,
    version: number,
    content: TeacherQuestionBankContent,
  ): Promise<TeacherQuestionBankItem>
  archiveTeacherQuestionBankItem(id: number, version: number, clientRequestId: string): Promise<TeacherQuestionBankItem>
  deleteTeacherQuestionBankItem(id: number, version: number, clientRequestId: string): Promise<void>
}

export interface ProblemRepository {
  getProblems(): Promise<Problem[]>
  findProblem(id: string): Promise<Problem | undefined>
  saveProblems(problems: Problem[]): Promise<void>
  upsertProblem(problem: Problem): Promise<Problem>
  publishProblem(id: string): Promise<Problem | null>
  rejectProblem(id: string): Promise<Problem | null>
  resetProblems(): Promise<Problem[]>
}

export interface GuidedCaseRepository {
  deleteGuidedCaseAsync(id: string): Promise<void>
  getDemoCaseProblemsAsync(): Promise<Problem[]>
  getGuidedCasesAsync(): Promise<Problem[]>
  getCaseAuthoringAsync(id: string): Promise<CaseDraftGenerateResult | undefined>
  cloneCaseVersionAsync(id: string): Promise<{ id: string; slug?: string; draft?: CaseDraftGenerateResult }>
  publishGuidedCaseAsync(id: string): Promise<Problem | undefined>
  submitGuidedCaseForReviewAsync(id: string): Promise<Problem | undefined>
  getMedicalReviewQueueAsync(status?: string): Promise<Problem[]>
  getMedicalReviewViewAsync(id: string): Promise<MedicalReviewRecord | undefined>
  decideGuidedCaseReviewAsync(
    id: string,
    decision: 'approved' | 'rejected',
    comment: string,
  ): Promise<Problem | undefined>
  generateCaseDraftAsync(input: CaseDraftGenerateInput): Promise<CaseDraftGenerateResult>
  saveGuidedCaseAsync(
    draft: CaseDraftGenerateResult,
    id?: string,
    metadata?: { slug?: string; knowledgePointCodes?: string[] },
  ): Promise<Pick<Problem, 'id' | 'slug' | 'status' | 'medicalReviewStatus'>>
}

export interface KnowledgeCardContributionRepository {
  getKnowledgeCardContributions(pointCode?: string): Promise<KnowledgeCardContribution[]>
  getKnowledgeCardReviewQueue(): Promise<KnowledgeCardContribution[]>
  createKnowledgeCardContribution(input: KnowledgeCardContributionInput): Promise<KnowledgeCardContribution>
  updateKnowledgeCardContribution(id: number, input: KnowledgeCardContributionInput): Promise<KnowledgeCardContribution>
  submitKnowledgeCardContribution(id: number): Promise<KnowledgeCardContribution>
  reviewKnowledgeCardContribution(
    id: number,
    decision: 'approved' | 'rejected',
    comment: string,
  ): Promise<KnowledgeCardContribution>
  disableKnowledgeCardContribution(id: number): Promise<KnowledgeCardContribution>
}

export interface ContentRepository
  extends ProblemRepository, GuidedCaseRepository, KnowledgeCardContributionRepository, TeacherQuestionBankRepository {
  getTeacherContentActionSummary(): Promise<TeacherContentActionSummary>
}
