import type { CaseRepository } from '@/data/repositories/case'
import { apiRequest, encodePathSegment as segment } from '@/services/apiClient'
import { apiProblemSchema, apiProblemListSchema } from '@/data/contracts/core'
import {
  apiCaseAttemptSchema,
  apiCaseAttemptListSchema,
  apiCaseDraftSchema,
  apiCaseAuthoringSchema,
  apiCaseAssessmentSchema,
  apiMedicalReviewViewSchema,
  apiPatientMessageSchema,
  apiStageSubmissionSchema,
} from '@/data/contracts/case'
import {
  toCaseAttempt,
  toCaseAttemptSummary,
  toAuthoring,
  toCaseDraft,
  toCaseAssessment,
  toCaseMessage,
  toApiAnswer,
  toApiDefinition,
  toApiRubric,
} from '@/data/mappers/case'
import { toProblem, undefinedOnNotFound } from '@/data/mappers/core'
import type { CaseDraftGenerateInput, CaseDraftGenerateResult, StageAnswer } from '@/types/case'
import type { MedicalReviewRecord as MedicalReviewView } from '@/types/review'
import type { Problem } from '@/types/records'

const invalidates = ['/attempts', '/learning', '/notifications', '/analytics', '/problems', '/student/questions']
const ttl = 15_000

export class ApiCaseRepository implements CaseRepository {
  async getCaseAttemptsAsync() {
    return (await apiRequest({ path: '/attempts', schema: apiCaseAttemptListSchema, cacheTtlMs: ttl })).map(
      toCaseAttemptSummary,
    )
  }
  async getDemoCaseProblemsAsync(): Promise<Problem[]> {
    return []
  }
  async getGuidedCasesAsync() {
    return (await apiRequest({ path: '/problems', schema: apiProblemListSchema, cacheTtlMs: 30_000 }))
      .map(toProblem)
      .filter((item) => item.contentType === 'guided_case')
  }
  async getCaseAuthoringAsync(id: string) {
    return apiRequest({
      path: `/problems/${segment(id)}/authoring`,
      schema: apiCaseAuthoringSchema,
      cacheTtlMs: 30_000,
    })
      .then(toAuthoring)
      .catch(undefinedOnNotFound<CaseDraftGenerateResult>)
  }
  async cloneCaseVersionAsync(id: string) {
    const value = await apiRequest({
      path: `/problems/${segment(id)}/clone-version`,
      method: 'POST',
      schema: apiCaseAuthoringSchema,
      invalidateCache: invalidates,
    })
    return { id: String(value.id), slug: value.slug ?? undefined, draft: toAuthoring(value) }
  }
  async publishGuidedCaseAsync(id: string) {
    return apiRequest({
      path: `/problems/${segment(id)}/publish`,
      method: 'POST',
      schema: apiProblemSchema,
      invalidateCache: invalidates,
    })
      .then(toProblem)
      .catch(undefinedOnNotFound<Problem>)
  }
  async submitGuidedCaseForReviewAsync(id: string) {
    return apiRequest({
      path: `/problems/${segment(id)}/medical-review/submit`,
      method: 'POST',
      schema: apiProblemSchema,
      invalidateCache: invalidates,
    })
      .then(toProblem)
      .catch(undefinedOnNotFound<Problem>)
  }
  async getMedicalReviewQueueAsync(status = 'pending') {
    return (
      await apiRequest({
        path: '/problems/review-queue',
        query: { status },
        schema: apiProblemListSchema,
        cacheTtlMs: 30_000,
      })
    ).map(toProblem)
  }
  async getMedicalReviewViewAsync(id: string): Promise<MedicalReviewView | undefined> {
    try {
      const value = await apiRequest({
        path: `/problems/${segment(id)}/medical-review-view`,
        schema: apiMedicalReviewViewSchema,
        cacheTtlMs: 30_000,
      })
      const draft = toAuthoring(value)
      return {
        ...toProblem(value),
        caseDefinition: draft.caseDefinition,
        rubric: draft.rubric,
        currentDigest: value.current_digest,
        authorNickname: value.author_nickname ?? undefined,
        reviews: value.reviews.map((item) => ({
          id: item.id,
          problemId: item.problem_id,
          reviewerId: item.reviewer_id,
          decision: item.decision,
          comment: item.comment,
          problemVersion: item.problem_version,
          caseDigest: item.case_digest,
          createdAt: item.created_at,
        })),
      }
    } catch (error) {
      return undefinedOnNotFound<MedicalReviewView>(error)
    }
  }
  async decideGuidedCaseReviewAsync(id: string, decision: 'approved' | 'rejected', comment: string) {
    return apiRequest({
      path: `/problems/${segment(id)}/medical-review`,
      method: 'POST',
      body: { decision, comment },
      schema: apiProblemSchema,
      invalidateCache: invalidates,
    })
      .then(toProblem)
      .catch(undefinedOnNotFound<Problem>)
  }
  async getCaseAttemptAsync(id: string) {
    return apiRequest({ path: `/attempts/${segment(id)}`, schema: apiCaseAttemptSchema, cacheTtlMs: ttl })
      .then(toCaseAttempt)
      .catch(undefinedOnNotFound<ReturnType<typeof toCaseAttempt>>)
  }
  async startCaseAttemptAsync(problemId: string, retryOfId?: string) {
    return toCaseAttempt(
      await apiRequest({
        path: `/problems/${segment(problemId)}/attempts`,
        method: 'POST',
        body: { retry_of_id: retryOfId ? Number(retryOfId) : null },
        schema: apiCaseAttemptSchema,
        invalidateCache: invalidates,
      }),
    )
  }
  async sendPatientMessageAsync(id: string, content: string) {
    return toCaseMessage(
      await apiRequest({
        path: `/attempts/${segment(id)}/messages`,
        method: 'POST',
        body: { content },
        schema: apiPatientMessageSchema,
        invalidateCache: invalidates,
      }),
    )
  }
  async submitCaseStageAsync(id: string, answer: StageAnswer) {
    await apiRequest({
      path: `/attempts/${segment(id)}/stages/${segment(answer.stageId)}/submit`,
      method: 'POST',
      body: { answer: toApiAnswer(answer) },
      schema: apiStageSubmissionSchema,
      invalidateCache: invalidates,
    })
  }
  async completeCaseAttemptAsync(id: string) {
    return toCaseAssessment(
      await apiRequest({
        path: `/attempts/${segment(id)}/complete`,
        method: 'POST',
        schema: apiCaseAssessmentSchema,
        invalidateCache: invalidates,
      }),
    )
  }
  async getCaseAssessmentAsync(id: string) {
    return apiRequest({
      path: `/attempts/${segment(id)}/assessment`,
      schema: apiCaseAssessmentSchema,
      cacheTtlMs: 30_000,
    })
      .then(toCaseAssessment)
      .catch(undefinedOnNotFound<ReturnType<typeof toCaseAssessment>>)
  }
  async generateCaseDraftAsync(input: CaseDraftGenerateInput) {
    return toCaseDraft(
      await apiRequest({
        path: '/problems/case-drafts/generate',
        method: 'POST',
        schema: apiCaseDraftSchema,
        body: { topic: input.topic, learner_level: input.learnerLevel, learning_objectives: input.learningObjectives },
      }),
    )
  }
  async saveGuidedCaseAsync(draft: CaseDraftGenerateResult, id?: string, metadata?: { slug?: string }) {
    const body = {
      type: '病例分析',
      title: draft.title,
      description: draft.description,
      target: 'all',
      target_label: '全体学生',
      target_ids: [],
      content_type: 'guided_case',
      slug: metadata?.slug || (id ? undefined : `case-${Date.now()}`),
      specialty: draft.specialty,
      difficulty: draft.difficulty,
      estimated_minutes: draft.estimatedMinutes,
      version: 1,
      case_definition: toApiDefinition(draft.caseDefinition),
      rubric: toApiRubric(draft.rubric),
      capability_tags: [...new Set((draft.caseDefinition.practiceBlueprints || []).map((item) => item.dimensionId))],
    }
    const saved = toProblem(
      await apiRequest({
        path: id ? `/problems/${segment(id)}` : '/problems',
        method: id ? 'PUT' : 'POST',
        body,
        schema: apiProblemSchema,
        invalidateCache: invalidates,
      }),
    )
    return { id: saved.id, slug: saved.slug, status: saved.status, medicalReviewStatus: saved.medicalReviewStatus }
  }
}
