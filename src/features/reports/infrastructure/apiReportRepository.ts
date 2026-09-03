import {
  apiConversationSchema,
  apiReportListSchema,
  apiReportSchema,
  apiReportSummaryPageSchema,
} from '@/platform/contracts/core'
import type { ApiConversation, ApiReport } from '@/platform/contracts/core'
import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import { saveReportDraft } from '@/features/reports/application/reportDraft'
import type { ReportDraftInput, ReportRepository } from '@/features/reports/domain/ports'
import { AppError } from '@/types/errors'
import type { Conversation, Report, ReportSummary, ReportSummaryPage } from '@/types/records'
import { toReport } from './mappers/report'
import { undefinedOnNotFound } from '@/platform/http/apiClient'

const LIST_TTL = 30_000

export class ApiReportRepository implements ReportRepository {
  private async upsertRemoteConversation(conversation: Conversation): Promise<ApiConversation> {
    return apiRequest<ApiConversation>({
      path: '/conversations',
      method: 'POST',
      schema: apiConversationSchema,
      invalidateCache: ['/conversations', '/reports'],
      body: {
        client_id: conversation.conversationId,
        messages: conversation.messages.map(({ role, content }) => ({ role, content })),
      },
    })
  }

  async getReports(): Promise<Report[]> {
    const reports = await apiRequest<ApiReport[]>({
      path: '/reports',
      cacheTtlMs: LIST_TTL,
      schema: apiReportListSchema,
    })
    return reports.map(toReport)
  }

  async getReportSummaries(limit: number, offset: number): Promise<ReportSummaryPage> {
    const page = await apiRequest({
      path: '/reports/summaries',
      query: { limit, offset },
      cacheTtlMs: LIST_TTL,
      schema: apiReportSummaryPageSchema,
    })
    const items: ReportSummary[] = page.items.map((item) => ({
      id: String(item.id),
      conversationId: item.conversation_client_id,
      studentId: String(item.student_id),
      studentName: item.student_name,
      status: item.status,
      aiScore: item.ai_score,
      teacherScore: item.teacher_score ?? undefined,
      messagePreview: item.message_preview || '',
      messageCount: item.message_count || 0,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    }))
    return {
      items,
      total: page.total,
      pendingCount: page.pending_count,
      reviewedCount: page.reviewed_count,
      limit: page.limit,
      offset: page.offset,
    }
  }

  async findReportByConversation(conversationId: string): Promise<Report | undefined> {
    return apiRequest<ApiReport>({
      path: `/reports/by-conversation/${encodePathSegment(conversationId)}`,
      schema: apiReportSchema,
      cacheTtlMs: LIST_TTL,
    })
      .then(toReport)
      .catch(undefinedOnNotFound<Report>)
  }

  async findReport(identifier: string): Promise<Report | undefined> {
    const getByConversation = () =>
      apiRequest<ApiReport>({
        path: `/reports/by-conversation/${encodePathSegment(identifier)}`,
        cacheTtlMs: LIST_TTL,
        schema: apiReportSchema,
      })
    try {
      const report = /^\d+$/.test(identifier)
        ? await apiRequest<ApiReport>({
            path: `/reports/${encodePathSegment(identifier)}`,
            cacheTtlMs: LIST_TTL,
            schema: apiReportSchema,
          }).catch((error) => {
            if (error instanceof AppError && error.statusCode === 404) return getByConversation()
            throw error
          })
        : await getByConversation()
      return toReport(report)
    } catch (error) {
      return undefinedOnNotFound<Report>(error)
    }
  }

  async saveDraftReport(input: ReportDraftInput): Promise<Report> {
    return saveReportDraft(input, {
      persistConversation: async (value) => String((await this.upsertRemoteConversation(value)).id),
      persistDraft: (id, value) => this.persistDraft(id, value),
    })
  }

  private async persistDraft(conversationId: string, input: ReportDraftInput): Promise<Report> {
    const report = await apiRequest<ApiReport>({
      path: '/reports',
      method: 'POST',
      schema: apiReportSchema,
      invalidateCache: ['/reports', '/conversations'],
      body: {
        conversation_id: Number(conversationId),
        ai_score: input.analysis.score,
        ai_summary: input.analysis.summary,
        analysis: {
          errors: input.analysis.errors,
          strengths: input.analysis.strengths || [],
          general_suggestions: input.analysis.generalSuggestions || [],
        },
      },
    })
    return toReport(report)
  }

  async submitReportForReview(conversationId: string): Promise<Report | null> {
    const report = await this.findReportByConversation(conversationId)
    if (!report?.id) return null
    const submitted = await apiRequest<ApiReport>({
      path: `/reports/${encodePathSegment(report.id)}/submit`,
      method: 'POST',
      schema: apiReportSchema,
      invalidateCache: ['/reports', '/conversations'],
    })
    return toReport(submitted)
  }

  async reviewReport(
    identifier: string,
    score: number,
    feedback: string,
    reviewTopicCodes: string[] = [],
  ): Promise<Report | null> {
    const report = await this.findReport(identifier)
    if (!report?.id) return null
    const reviewed = await apiRequest<ApiReport>({
      path: `/reports/${encodePathSegment(report.id)}/review`,
      method: 'POST',
      schema: apiReportSchema,
      invalidateCache: ['/reports', '/conversations'],
      body: {
        teacher_score: score,
        teacher_feedback: feedback,
        review_topic_codes: reviewTopicCodes,
      },
    })
    return toReport(reviewed)
  }
}
