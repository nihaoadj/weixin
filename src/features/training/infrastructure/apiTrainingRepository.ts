import type { CaseRepository } from '@/features/training/domain/ports'
import { apiRequest, encodePathSegment as segment, undefinedOnNotFound } from '@/platform/http/apiClient'
import {
  apiCaseAssessmentSchema,
  apiCaseAttemptListSchema,
  apiCaseAttemptSchema,
  apiPatientMessageSchema,
  apiStageSubmissionSchema,
} from '@/platform/contracts/case'
import { toApiAnswer, toCaseAssessment, toCaseAttempt, toCaseAttemptSummary, toCaseMessage } from './mappers/case'
import type { StageAnswer } from '@/types/case'

const invalidates = ['/attempts', '/learning', '/notifications', '/analytics']
const ttl = 15_000

export class ApiTrainingRepository implements CaseRepository {
  async getCaseAttemptsAsync() {
    return (await apiRequest({ path: '/attempts', schema: apiCaseAttemptListSchema, cacheTtlMs: ttl })).map(
      toCaseAttemptSummary,
    )
  }

  async getCaseAttemptAsync(id: string) {
    return apiRequest({ path: `/attempts/${segment(id)}`, schema: apiCaseAttemptSchema, cacheTtlMs: ttl })
      .then(toCaseAttempt)
      .catch((error) => undefinedOnNotFound<ReturnType<typeof toCaseAttempt>>(error))
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
      .catch((error) => undefinedOnNotFound<ReturnType<typeof toCaseAssessment>>(error))
  }
}
