import type { ContentRepository } from '@/features/content/domain/ports'
import type { TeacherContentActionSummary } from '@/features/content/domain/teacherActionSummary'
import { teacherContentActionSummarySchema } from '@/platform/contracts/contentActions'
import { apiRequest, encodePathSegment as segment, undefinedOnNotFound } from '@/platform/http/apiClient'
import { apiProblemListSchema, apiProblemSchema } from '@/platform/contracts/core'
import type { ApiProblem } from '@/platform/contracts/core'
import { apiCaseAuthoringSchema, apiCaseDraftSchema, apiMedicalReviewViewSchema } from '@/platform/contracts/case'
import { toApiDefinition, toApiRubric, toAuthoring, toCaseDraft } from './mappers/case'
import { problemPayload, toProblem } from './mappers/core'
import type { CaseDraftGenerateInput, CaseDraftGenerateResult } from '@/types/case'
import type { MedicalReviewRecord } from '@/types/review'
import type { Problem } from '@/types/records'
import { AppError } from '@/types/errors'
import {
  apiKnowledgeCardContributionListSchema,
  apiKnowledgeCardContributionSchema,
} from '@/platform/contracts/knowledge'
import type { KnowledgeCardContribution, KnowledgeCardContributionInput } from '@/types/knowledge'
import type {
  TeacherQuestionBankContent,
  TeacherQuestionBankFilters,
  TeacherQuestionBankImportInput,
  TeacherQuestionBankItem,
  TeacherQuestionBankPage,
  TeacherQuestionBankSource,
} from '@/features/content/domain/questionBank'
import {
  teacherQuestionBankItemSchema,
  teacherQuestionBankPageSchema,
  teacherQuestionBankContentSchema,
  teacherQuestionBankSourceSchema,
} from '@/platform/contracts/questionBank'

const invalidates = ['/analytics', '/problems', '/student/questions', '/learning']

function toKnowledgeCardContribution(
  value: ReturnType<typeof apiKnowledgeCardContributionSchema.parse>,
): KnowledgeCardContribution {
  return {
    id: value.id,
    pointCode: value.point_code,
    classCode: value.class_code || undefined,
    version: value.version,
    cardType: value.card_type,
    prompt: value.prompt,
    options: value.options,
    correctOption: value.correct_option ?? undefined,
    explanation: value.explanation,
    reference: value.reference,
    status: value.status,
    reviewerId: value.reviewer_id ?? undefined,
    reviewComment: value.review_comment,
    reviewedAt: value.reviewed_at || undefined,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
    aiTitle: value.ai_title || undefined,
    sourceType: value.source_type || undefined,
    sourceSnapshotId: value.source_snapshot_id ?? undefined,
    sourcePosition: value.source_position ?? undefined,
    sourceFindingIds: value.source_finding_ids,
    originStudentId: value.origin_student_id ?? undefined,
    originStudentName: value.origin_student_name || undefined,
    targetStudentIds: value.target_student_ids,
  }
}

function contributionPayload(input: KnowledgeCardContributionInput) {
  return {
    point_code: input.pointCode,
    class_code: input.classCode || null,
    card_type: input.cardType,
    prompt: input.prompt,
    options: input.options,
    correct_option: input.correctOption ?? null,
    explanation: input.explanation,
    reference: input.reference,
    target_student_ids: input.targetStudentIds || [],
  }
}

export class ApiContentRepository implements ContentRepository {
  async getTeacherContentActionSummary(): Promise<TeacherContentActionSummary> {
    const value = await apiRequest({
      path: '/problems/teacher-action-summary',
      schema: teacherContentActionSummarySchema,
      cacheTtlMs: 0,
    })
    return {
      casesDraft: value.cases_draft,
      casesRejected: value.cases_rejected,
      casesApproved: value.cases_approved,
      questionsDraft: value.questions_draft,
      questionsRejected: value.questions_rejected,
      cardsDraft: value.cards_draft,
      cardsRejected: value.cards_rejected,
      medicalCasesPending: value.medical_cases_pending,
      medicalCardsPending: value.medical_cards_pending,
      asOf: value.as_of,
    }
  }

  async getTeacherQuestionBankSource(sourceId: string): Promise<TeacherQuestionBankSource> {
    const value = await apiRequest({
      path: `/teacher/question-bank/sources/route-test-questions/${segment(sourceId)}`,
      schema: teacherQuestionBankSourceSchema,
      cacheTtlMs: 0,
    })
    return toQuestionBankSource(value)
  }

  async listTeacherQuestionBank(filters: TeacherQuestionBankFilters = {}): Promise<TeacherQuestionBankPage> {
    const value = await apiRequest({
      path: '/teacher/question-bank',
      query: {
        status: filters.status === 'archived' ? 'archived' : undefined,
        point_code: filters.pointCode,
        task_type: filters.taskType,
        q: filters.query,
        limit: filters.limit ?? 20,
        offset: filters.offset ?? 0,
      },
      schema: teacherQuestionBankPageSchema,
      cacheTtlMs: 0,
    })
    return {
      items: value.items.map(toQuestionBankItem),
      total: value.total,
      limit: value.limit,
      offset: value.offset,
    }
  }

  async getTeacherQuestionBankItem(id: number): Promise<TeacherQuestionBankItem> {
    return toQuestionBankItem(
      await apiRequest({
        path: `/teacher/question-bank/${segment(id)}`,
        schema: teacherQuestionBankItemSchema,
        cacheTtlMs: 0,
      }),
    )
  }

  async importTeacherQuestionBankItem(input: TeacherQuestionBankImportInput): Promise<TeacherQuestionBankItem> {
    const content = questionBankContentPayload(input)
    return toQuestionBankItem(
      await apiRequest({
        path: '/teacher/question-bank/import',
        method: 'POST',
        body: {
          ...content,
          source_type: input.sourceType,
          source_id: input.sourceId,
          source_digest: input.sourceDigest,
          client_request_id: input.clientRequestId,
          deidentified: input.deidentified,
        },
        schema: teacherQuestionBankItemSchema,
        invalidateCache: ['/teacher/question-bank'],
      }),
    )
  }

  async updateTeacherQuestionBankItem(
    id: number,
    version: number,
    content: TeacherQuestionBankContent,
  ): Promise<TeacherQuestionBankItem> {
    return toQuestionBankItem(
      await apiRequest({
        path: `/teacher/question-bank/${segment(id)}`,
        method: 'PUT',
        body: { ...questionBankContentPayload(content), version },
        schema: teacherQuestionBankItemSchema,
        invalidateCache: ['/teacher/question-bank'],
      }),
    )
  }

  async archiveTeacherQuestionBankItem(
    id: number,
    version: number,
    clientRequestId: string,
  ): Promise<TeacherQuestionBankItem> {
    return toQuestionBankItem(
      await apiRequest({
        path: `/teacher/question-bank/${segment(id)}/archive`,
        method: 'POST',
        body: { version, client_request_id: clientRequestId },
        schema: teacherQuestionBankItemSchema,
        invalidateCache: ['/teacher/question-bank'],
      }),
    )
  }

  async deleteTeacherQuestionBankItem(id: number, version: number, clientRequestId: string): Promise<void> {
    await apiRequest<void>({
      path: `/teacher/question-bank/${segment(id)}`,
      method: 'DELETE',
      body: { version, client_request_id: clientRequestId },
      invalidateCache: ['/teacher/question-bank'],
    })
  }

  async getKnowledgeCardContributions(pointCode?: string): Promise<KnowledgeCardContribution[]> {
    return (
      await apiRequest({
        path: '/knowledge/cards',
        query: pointCode ? { point_code: pointCode } : undefined,
        schema: apiKnowledgeCardContributionListSchema,
        cacheTtlMs: 15_000,
      })
    ).map(toKnowledgeCardContribution)
  }

  async getKnowledgeCardReviewQueue(): Promise<KnowledgeCardContribution[]> {
    return (
      await apiRequest({
        path: '/knowledge/review-queue',
        schema: apiKnowledgeCardContributionListSchema,
        cacheTtlMs: 15_000,
      })
    ).map(toKnowledgeCardContribution)
  }

  async createKnowledgeCardContribution(input: KnowledgeCardContributionInput): Promise<KnowledgeCardContribution> {
    return toKnowledgeCardContribution(
      await apiRequest({
        path: '/knowledge/teacher/cards',
        method: 'POST',
        body: contributionPayload(input),
        schema: apiKnowledgeCardContributionSchema,
        invalidateCache: ['/knowledge/cards', '/knowledge/review-queue'],
      }),
    )
  }

  async updateKnowledgeCardContribution(
    id: number,
    input: KnowledgeCardContributionInput,
  ): Promise<KnowledgeCardContribution> {
    return toKnowledgeCardContribution(
      await apiRequest({
        path: `/knowledge/teacher/cards/${segment(id)}`,
        method: 'PUT',
        body: contributionPayload(input),
        schema: apiKnowledgeCardContributionSchema,
        invalidateCache: ['/knowledge/cards', '/knowledge/review-queue'],
      }),
    )
  }

  async submitKnowledgeCardContribution(id: number): Promise<KnowledgeCardContribution> {
    return toKnowledgeCardContribution(
      await apiRequest({
        path: `/knowledge/teacher/cards/${segment(id)}/submit`,
        method: 'POST',
        schema: apiKnowledgeCardContributionSchema,
        invalidateCache: ['/knowledge/cards', '/knowledge/review-queue'],
      }),
    )
  }

  async reviewKnowledgeCardContribution(
    id: number,
    decision: 'approved' | 'rejected',
    comment: string,
  ): Promise<KnowledgeCardContribution> {
    return toKnowledgeCardContribution(
      await apiRequest({
        path: `/knowledge/teacher/cards/${segment(id)}/review`,
        method: 'POST',
        body: { decision, comment },
        schema: apiKnowledgeCardContributionSchema,
        invalidateCache: ['/knowledge/cards', '/knowledge/review-queue'],
      }),
    )
  }

  async disableKnowledgeCardContribution(id: number): Promise<KnowledgeCardContribution> {
    return toKnowledgeCardContribution(
      await apiRequest({
        path: `/knowledge/teacher/cards/${segment(id)}/disable`,
        method: 'POST',
        schema: apiKnowledgeCardContributionSchema,
        invalidateCache: ['/knowledge/cards', '/knowledge/review-queue'],
      }),
    )
  }

  async getProblems(): Promise<Problem[]> {
    return (await apiRequest({ path: '/problems', schema: apiProblemListSchema, cacheTtlMs: 30_000 })).map(toProblem)
  }

  async findProblem(id: string): Promise<Problem | undefined> {
    return apiRequest({
      path: `/problems/${segment(id)}`,
      schema: apiProblemSchema,
      cacheTtlMs: 30_000,
    })
      .then(toProblem)
      .catch((error) => undefinedOnNotFound<Problem>(error))
  }

  async saveProblems(_problems: Problem[]): Promise<void> {
    throw new AppError('API 模式不支持批量覆盖问题数据', { code: 'UNSUPPORTED_OPERATION' })
  }

  async upsertProblem(problem: Problem): Promise<Problem> {
    const numericId = Number(problem.id)
    const saved = Number.isFinite(numericId)
      ? await apiRequest({
          path: `/problems/${segment(numericId)}`,
          method: 'PUT',
          body: problemPayload(problem),
          schema: apiProblemSchema,
          invalidateCache: ['/problems', '/student/questions'],
        })
      : await apiRequest({
          path: '/problems',
          method: 'POST',
          body: problemPayload(problem),
          schema: apiProblemSchema,
          invalidateCache: ['/problems', '/student/questions'],
        })
    return toProblem(saved)
  }

  async publishProblem(id: string): Promise<Problem | null> {
    const problem = await apiRequest<ApiProblem>({
      path: `/problems/${segment(id)}/publish`,
      method: 'POST',
      schema: apiProblemSchema,
      invalidateCache: ['/problems', '/student/questions'],
    }).catch((error) => undefinedOnNotFound<ApiProblem>(error))
    return problem ? toProblem(problem) : null
  }

  async rejectProblem(id: string): Promise<Problem | null> {
    const problem = await apiRequest<ApiProblem>({
      path: `/problems/${segment(id)}/reject`,
      method: 'POST',
      schema: apiProblemSchema,
      invalidateCache: ['/problems', '/student/questions'],
    }).catch((error) => undefinedOnNotFound<ApiProblem>(error))
    return problem ? toProblem(problem) : null
  }

  async resetProblems(): Promise<Problem[]> {
    throw new AppError('API 模式不支持恢复本地示例数据', { code: 'UNSUPPORTED_OPERATION' })
  }

  async getDemoCaseProblemsAsync(): Promise<Problem[]> {
    return []
  }

  async getGuidedCasesAsync(): Promise<Problem[]> {
    return (await this.getProblems()).filter((item) => item.contentType === 'guided_case')
  }

  async deleteGuidedCaseAsync(id: string): Promise<void> {
    await apiRequest<void>({
      path: `/problems/${segment(id)}`,
      method: 'DELETE',
      invalidateCache: invalidates,
    })
  }

  async getCaseAuthoringAsync(id: string): Promise<CaseDraftGenerateResult | undefined> {
    return apiRequest({
      path: `/problems/${segment(id)}/authoring`,
      schema: apiCaseAuthoringSchema,
      cacheTtlMs: 30_000,
    })
      .then(toAuthoring)
      .catch((error) => undefinedOnNotFound<CaseDraftGenerateResult>(error))
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

  async publishGuidedCaseAsync(id: string): Promise<Problem | undefined> {
    return apiRequest({
      path: `/problems/${segment(id)}/publish`,
      method: 'POST',
      schema: apiProblemSchema,
      invalidateCache: invalidates,
    })
      .then(toProblem)
      .catch((error) => undefinedOnNotFound<Problem>(error))
  }

  async submitGuidedCaseForReviewAsync(id: string): Promise<Problem | undefined> {
    return apiRequest({
      path: `/problems/${segment(id)}/medical-review/submit`,
      method: 'POST',
      schema: apiProblemSchema,
      invalidateCache: invalidates,
    })
      .then(toProblem)
      .catch((error) => undefinedOnNotFound<Problem>(error))
  }

  async getMedicalReviewQueueAsync(status = 'pending'): Promise<Problem[]> {
    return (
      await apiRequest({
        path: '/problems/review-queue',
        query: { status },
        schema: apiProblemListSchema,
        cacheTtlMs: 30_000,
      })
    ).map(toProblem)
  }

  async getMedicalReviewViewAsync(id: string): Promise<MedicalReviewRecord | undefined> {
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
      return undefinedOnNotFound<MedicalReviewRecord>(error)
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
      .catch((error) => undefinedOnNotFound<Problem>(error))
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

  async saveGuidedCaseAsync(
    draft: CaseDraftGenerateResult,
    id?: string,
    metadata?: { slug?: string; knowledgePointCodes?: string[] },
  ) {
    const body = {
      type: '病例分析' as const,
      title: draft.title,
      description: draft.description,
      target: 'all' as const,
      target_label: '全体学生',
      target_ids: [],
      content_type: 'guided_case' as const,
      slug: metadata?.slug || (id ? undefined : `case-${Date.now()}`),
      specialty: draft.specialty,
      difficulty: draft.difficulty,
      estimated_minutes: draft.estimatedMinutes,
      version: 1,
      case_definition: toApiDefinition(draft.caseDefinition),
      rubric: toApiRubric(draft.rubric),
      capability_tags: [...new Set((draft.caseDefinition.practiceBlueprints || []).map((item) => item.dimensionId))],
      ...(metadata?.knowledgePointCodes ? { knowledge_point_codes: [...metadata.knowledgePointCodes] } : {}),
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

function toQuestionBankItem(value: ReturnType<typeof teacherQuestionBankItemSchema.parse>): TeacherQuestionBankItem {
  return {
    id: value.id,
    version: value.version,
    status: value.status,
    taskType: value.task_type,
    title: value.title,
    prompt: value.prompt,
    options: value.options,
    answer: value.answer,
    explanation: value.explanation,
    pointCodes: value.point_codes,
    dimensionIds: value.dimension_ids,
    medicalReviewStatus: value.medical_review_status,
    updatedAt: value.updated_at,
  }
}

function toQuestionBankSource(
  value: ReturnType<typeof teacherQuestionBankSourceSchema.parse>,
): TeacherQuestionBankSource {
  return {
    sourceType: value.source_type,
    sourceId: value.source_id,
    sourceDigest: value.source_digest,
    taskType: value.task_type,
    title: value.title,
    prompt: value.prompt,
    options: value.options,
    answer: value.answer,
    explanation: value.explanation,
    pointCodes: value.point_codes,
    dimensionIds: value.dimension_ids,
  }
}

function questionBankContentPayload(value: TeacherQuestionBankContent) {
  return teacherQuestionBankContentSchema.parse({
    task_type: value.taskType,
    title: value.title,
    prompt: value.prompt,
    options: value.options,
    answer: value.answer,
    explanation: value.explanation,
    point_codes: value.pointCodes,
    dimension_ids: value.dimensionIds,
  })
}
