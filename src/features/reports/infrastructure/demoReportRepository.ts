import * as local from './demoReportStore'
import { fromReportView, optional } from '@/shared/mappers/presentation'
import { saveReportDraft } from '@/features/reports/application/reportDraft'
import type { ReportDraftInput, ReportRepository } from '@/features/reports/domain/ports'
import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'
import type { Report, ReportSummary, ReportSummaryPage } from '@/types/records'
import type { ConversationRepository } from '@/features/qa/domain/ports'
import type { UserRole } from '@/types/domain'

function requireUser(role?: UserRole) {
  const user = getSessionContext()
  if (!user) throw new AppError('请先登录', { code: 'AUTH_REQUIRED', statusCode: 401 })
  if (role && user.role !== role) throw new AppError('无权执行此操作', { code: 'FORBIDDEN', statusCode: 403 })
  return user
}

function paginate<T>(items: T[], limit: number, offset: number) {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0)
    throw new AppError('分页参数无效', { code: 'VALIDATION_ERROR', statusCode: 422 })
  return { items: items.slice(offset, offset + limit), total: items.length, limit, offset }
}

function newest<T extends { updatedAt: string; id: string }>(items: T[]): T[] {
  return items.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt) || b.id.localeCompare(a.id))
}

export class DemoReportRepository implements ReportRepository {
  constructor(private readonly conversations: Pick<ConversationRepository, 'upsertConversation'>) {}

  async getReports(): Promise<Report[]> {
    const user = requireUser()
    return local
      .getReports()
      .map(fromReportView)
      .filter((report) => user.role === 'student' || report.status !== 'draft')
  }

  async getReportSummaries(limit: number, offset: number): Promise<ReportSummaryPage> {
    const reports = await this.getReports()
    const items: ReportSummary[] = reports.map((report) => ({
      id: report.id || report.conversationId,
      conversationId: report.conversationId,
      studentId: report.studentId,
      studentName: report.studentName,
      status: report.status,
      aiScore: report.analysis.score,
      teacherScore: report.teacherScore,
      messagePreview: report.messages[0]?.content.slice(0, 160) || '',
      messageCount: report.messages.length,
      createdAt: report.createdAt,
      updatedAt: report.updatedAt || report.createdAt,
    }))
    return {
      ...paginate(newest(items), limit, offset),
      pendingCount: reports.filter((item) => item.status === 'pending_review').length,
      reviewedCount: reports.filter((item) => item.status === 'reviewed').length,
    }
  }

  async findReportByConversation(id: string): Promise<Report | undefined> {
    const matches = (await this.getReports()).filter((report) => report.conversationId === id)
    if (matches.length > 1) throw new AppError('报告数据存在冲突', { code: 'STATE_CONFLICT', statusCode: 409 })
    return matches[0]
  }

  async findReport(id: string): Promise<Report | undefined> {
    const reports = await this.getReports()
    const byId = reports.find((report) => report.id === id)
    if (byId) return byId
    const matches = reports.filter((report) => report.conversationId === id)
    if (matches.length > 1) throw new AppError('报告数据存在冲突', { code: 'STATE_CONFLICT', statusCode: 409 })
    return matches[0]
  }

  async saveDraftReport(input: ReportDraftInput): Promise<Report> {
    requireUser('student')
    return saveReportDraft(input, {
      persistConversation: async (value) => {
        await this.conversations.upsertConversation(value)
        return value.conversationId
      },
      persistDraft: async (_id, value) => fromReportView(local.saveDraftReport(value)),
    })
  }

  async submitReportForReview(id: string): Promise<Report | null> {
    requireUser('student')
    const report = await this.findReport(id)
    if (!report) return null
    if (report.status !== 'draft')
      throw new AppError('当前状态不允许此操作', { code: 'STATE_CONFLICT', statusCode: 409 })
    return optional(local.submitReportForReview(report.conversationId) || undefined, fromReportView) || null
  }

  async reviewReport(
    id: string,
    score: number,
    feedback: string,
    reviewTopicCodes: string[] = [],
  ): Promise<Report | null> {
    requireUser('teacher')
    const report = await this.findReport(id)
    if (!report) return null
    if (score < 0 || score > 100) throw new AppError('评分超出范围', { code: 'VALIDATION_ERROR', statusCode: 422 })
    return (
      optional(
        local.reviewReport(report.id || report.conversationId, score, feedback, reviewTopicCodes) || undefined,
        fromReportView,
      ) || null
    )
  }
}
