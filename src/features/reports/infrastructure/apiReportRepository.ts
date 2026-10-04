import { apiReportSchema } from '@/platform/contracts/core'
import { apiRequest, encodePathSegment, undefinedOnNotFound } from '@/platform/http/apiClient'
import type { ReportRepository } from '@/features/reports/domain/ports'
import type { Report } from '@/types/records'
import { toReport } from './mappers/report'

const LIST_TTL = 30_000

/** API adapter for the retained student-owned report history only. */
export class ApiReportRepository implements ReportRepository {
  async findReportByConversation(conversationId: string): Promise<Report | undefined> {
    return apiRequest({
      path: `/reports/by-conversation/${encodePathSegment(conversationId)}`,
      schema: apiReportSchema,
      cacheTtlMs: LIST_TTL,
    })
      .then(toReport)
      .catch(undefinedOnNotFound<Report>)
  }

  async findReport(identifier: string): Promise<Report | undefined> {
    try {
      const value = await apiRequest({
        path: `/reports/${encodePathSegment(identifier)}`,
        schema: apiReportSchema,
        cacheTtlMs: LIST_TTL,
      })
      return toReport(value)
    } catch (error) {
      return undefinedOnNotFound<Report>(error)
    }
  }
}
