import {
  apiConversationListSchema,
  apiConversationSchema,
  apiConversationSummaryPageSchema,
  apiProblemListSchema,
  apiProblemSchema,
  apiQuestionThreadSchema,
  apiReportListSchema,
  apiReportSchema,
  apiReportSummaryPageSchema,
  apiStudentQuestionListSchema,
  studentQuestionSchema,
} from '@/data/contracts/core'
import type { ApiConversation, ApiReport, ApiProblem, ApiQuestionThread } from '@/data/contracts/core'
import { toConversation, toReport, toProblem, toThread, undefinedOnNotFound, problemPayload } from '@/data/mappers/core'
import type { CoreRepository, ReportDraftInput } from '@/data/repositories/core'
import { apiRequest, encodePathSegment } from '@/services/apiClient'
import type {
  Conversation,
  ConversationSummary,
  Page,
  Problem,
  QuestionThread,
  Report,
  ReportSummary,
  ReportSummaryPage,
  StudentQuestion,
} from '@/types/records'
import { AppError } from '@/types/errors'
import { saveReportDraft } from '@/data/usecases/reportDraft'
const LIST_TTL = 30_000
const THREAD_TTL = 15_000

export class ApiCoreRepository implements CoreRepository {
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

  async getConversations(): Promise<Conversation[]> {
    const conversations = await apiRequest<ApiConversation[]>({
      path: '/conversations',
      cacheTtlMs: LIST_TTL,
      schema: apiConversationListSchema,
    })
    return conversations.map(toConversation)
  }

  async getConversationSummaries(limit: number, offset: number): Promise<Page<ConversationSummary>> {
    const page = await apiRequest({
      path: '/conversations/summaries',
      query: { limit, offset },
      cacheTtlMs: LIST_TTL,
      schema: apiConversationSummaryPageSchema,
    })
    return {
      items: page.items.map((item) => ({
        id: String(item.id),
        conversationId: item.client_id,
        messagePreview: item.message_preview || '',
        messageCount: item.message_count || 0,
        reportId: item.report_id == null ? undefined : String(item.report_id),
        reportStatus: item.report_status ?? undefined,
        createdAt: item.created_at,
        updatedAt: item.updated_at,
      })),
      total: page.total,
      limit: page.limit,
      offset: page.offset,
    }
  }

  async findConversation(conversationId: string): Promise<Conversation | undefined> {
    return apiRequest<ApiConversation>({
      path: `/conversations/by-client/${encodePathSegment(conversationId)}`,
      cacheTtlMs: LIST_TTL,
      schema: apiConversationSchema,
    })
      .then(toConversation)
      .catch((error) => undefinedOnNotFound<Conversation>(error))
  }

  async upsertConversation(conversation: Conversation): Promise<void> {
    await this.upsertRemoteConversation(conversation)
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

  async reviewReport(identifier: string, score: number, feedback: string): Promise<Report | null> {
    const report = await this.findReport(identifier)
    if (!report?.id) return null
    const reviewed = await apiRequest<ApiReport>({
      path: `/reports/${encodePathSegment(report.id)}/review`,
      method: 'POST',
      schema: apiReportSchema,
      invalidateCache: ['/reports', '/conversations'],
      body: { teacher_score: score, teacher_feedback: feedback },
    })
    return toReport(reviewed)
  }

  async getProblems(): Promise<Problem[]> {
    const problems = await apiRequest<ApiProblem[]>({
      path: '/problems',
      cacheTtlMs: LIST_TTL,
      schema: apiProblemListSchema,
    })
    return problems.map(toProblem)
  }

  async findProblem(id: string): Promise<Problem | undefined> {
    return apiRequest<ApiProblem>({
      path: `/problems/${encodePathSegment(id)}`,
      cacheTtlMs: LIST_TTL,
      schema: apiProblemSchema,
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
      ? await apiRequest<ApiProblem>({
          path: `/problems/${encodePathSegment(numericId)}`,
          method: 'PUT',
          body: problemPayload(problem),
          schema: apiProblemSchema,
          invalidateCache: ['/problems', '/student/questions'],
        })
      : await apiRequest<ApiProblem>({
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
      path: `/problems/${encodePathSegment(id)}/publish`,
      method: 'POST',
      schema: apiProblemSchema,
      invalidateCache: ['/problems', '/student/questions'],
    }).catch(undefinedOnNotFound<ApiProblem>)
    return problem ? toProblem(problem) : null
  }

  async rejectProblem(id: string): Promise<Problem | null> {
    const problem = await apiRequest<ApiProblem>({
      path: `/problems/${encodePathSegment(id)}/reject`,
      method: 'POST',
      schema: apiProblemSchema,
      invalidateCache: ['/problems', '/student/questions'],
    }).catch(undefinedOnNotFound<ApiProblem>)
    return problem ? toProblem(problem) : null
  }

  async resetProblems(): Promise<Problem[]> {
    throw new AppError('API 模式不支持恢复本地示例数据', { code: 'UNSUPPORTED_OPERATION' })
  }

  async getStudentQuestions(): Promise<StudentQuestion[]> {
    const items = await apiRequest({
      path: '/student/questions',
      cacheTtlMs: LIST_TTL,
      schema: apiStudentQuestionListSchema,
    })
    return items.map((item) => ({
      id: String(item.id),
      type: item.type,
      title: item.title,
      description: item.description,
      time: item.published_at,
      status: item.status,
    }))
  }

  async findStudentQuestion(id: string): Promise<StudentQuestion | undefined> {
    try {
      const item = await apiRequest({
        path: `/student/questions/${encodePathSegment(id)}`,
        schema: studentQuestionSchema,
        cacheTtlMs: LIST_TTL,
      })
      return {
        id: String(item.id),
        type: item.type,
        title: item.title,
        description: item.description,
        time: item.published_at,
        status: item.status,
      }
    } catch (error) {
      return undefinedOnNotFound<StudentQuestion>(error)
    }
  }

  async getQuestionThread(questionId: string): Promise<QuestionThread | undefined> {
    return apiRequest<ApiQuestionThread>({
      path: `/problems/${encodePathSegment(questionId)}/thread`,
      cacheTtlMs: THREAD_TTL,
      schema: apiQuestionThreadSchema,
    })
      .then(toThread)
      .catch((error) => undefinedOnNotFound<QuestionThread>(error))
  }

  async saveQuestionThread(thread: QuestionThread): Promise<void> {
    await apiRequest<ApiQuestionThread>({
      path: `/problems/${encodePathSegment(thread.questionId)}/thread`,
      method: 'POST',
      schema: apiQuestionThreadSchema,
      invalidateCache: ['/problems', '/student/questions'],
      body: { messages: thread.messages.map(({ role, content }) => ({ role, content })) },
    })
  }
}
