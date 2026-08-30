import * as local from '@/services/repository'
import type { CoreRepository, ReportDraftInput } from '@/data/repositories/core'
import type {
  Conversation,
  Page,
  Problem,
  QuestionThread,
  Report,
  ReportSummary,
  ReportSummaryPage,
  UserRole,
} from '@/types/records'
import { fromProblemView, fromQuestionView, fromReportView, toProblemView, optional } from '@/data/mappers/presentation'
import { AppError } from '@/types/errors'
import { saveReportDraft } from '@/data/usecases/reportDraft'

function requireUser(role?: UserRole) {
  const user = local.getSession()
  if (!user) throw new AppError('请先登录', { code: 'AUTH_REQUIRED', statusCode: 401 })
  if (role && user.role !== role) throw new AppError('无权执行此操作', { code: 'FORBIDDEN', statusCode: 403 })
  return user
}
function paginate<T>(items: T[], limit: number, offset: number): Page<T> {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0)
    throw new AppError('分页参数无效', { code: 'VALIDATION_ERROR', statusCode: 422 })
  return { items: items.slice(offset, offset + limit), total: items.length, limit, offset }
}
function newest<T extends { updatedAt: string; id: string }>(items: T[]): T[] {
  return items.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt) || b.id.localeCompare(a.id))
}
function conflict(): never {
  throw new AppError('当前状态不允许此操作', { code: 'STATE_CONFLICT', statusCode: 409 })
}

export class DemoCoreRepository implements CoreRepository {
  async getConversations() {
    requireUser('student')
    return local.getConversations()
  }
  async getConversationSummaries(limit: number, offset: number) {
    const conversations = await this.getConversations()
    const reports = new Map((await this.getReports()).map((report) => [report.conversationId, report]))
    return paginate(
      newest(
        conversations.map((conversation) => {
          const report = reports.get(conversation.conversationId)
          return {
            id: conversation.conversationId,
            conversationId: conversation.conversationId,
            messagePreview: conversation.messages[0]?.content.slice(0, 160) || '',
            messageCount: conversation.messages.length,
            reportId: report?.id,
            reportStatus: report?.status,
            createdAt: conversation.createdAt,
            updatedAt: conversation.updatedAt,
          }
        }),
      ),
      limit,
      offset,
    )
  }
  async findConversation(id: string) {
    requireUser('student')
    return local.findConversation(id)
  }
  async upsertConversation(value: Conversation) {
    requireUser('student')
    local.upsertConversation(value)
  }
  async getReports() {
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
  async findReportByConversation(id: string) {
    const matches = (await this.getReports()).filter((report) => report.conversationId === id)
    if (matches.length > 1) conflict()
    return matches[0]
  }
  async findReport(id: string) {
    const reports = await this.getReports()
    const byId = reports.find((report) => report.id === id)
    if (byId) return byId
    const matches = reports.filter((report) => report.conversationId === id)
    if (matches.length > 1) conflict()
    return matches[0]
  }
  async saveDraftReport(input: ReportDraftInput) {
    requireUser('student')
    return saveReportDraft(input, {
      persistConversation: async (value) => {
        local.upsertConversation(value)
        return value.conversationId
      },
      persistDraft: async (_id, value) => fromReportView(local.saveDraftReport(value)),
    })
  }
  async submitReportForReview(id: string): Promise<Report | null> {
    requireUser('student')
    const report = await this.findReport(id)
    if (!report) return null
    if (report.status !== 'draft') conflict()
    return optional(local.submitReportForReview(report.conversationId) ?? undefined, fromReportView) ?? null
  }
  async reviewReport(id: string, score: number, feedback: string): Promise<Report | null> {
    requireUser('teacher')
    const report = await this.findReport(id)
    if (!report) return null
    if (score < 0 || score > 100) throw new AppError('评分超出范围', { code: 'VALIDATION_ERROR', statusCode: 422 })
    return (
      optional(local.reviewReport(report.id || report.conversationId, score, feedback) ?? undefined, fromReportView) ??
      null
    )
  }
  async getProblems() {
    const user = requireUser()
    const all = local.getProblems().map(fromProblemView)
    if (user.role === 'teacher') return all
    return all.filter(
      (p) =>
        p.status === 'published' &&
        (p.target === 'all' ||
          (p.target === 'individual'
            ? p.targetIds?.includes(user.openid)
            : user.classIds?.some((id) => p.targetIds?.includes(id)))),
    )
  }
  async findProblem(id: string) {
    return (await this.getProblems()).find((item) => item.id === id)
  }
  async saveProblems(problems: Problem[]) {
    requireUser('teacher')
    local.saveProblems(problems.map(toProblemView))
  }
  async upsertProblem(problem: Problem) {
    requireUser('teacher')
    local.upsertProblem(toProblemView(problem))
    return problem
  }
  async publishProblem(id: string) {
    requireUser('teacher')
    const problem = await this.findProblem(id)
    return problem
      ? this.upsertProblem({ ...problem, status: 'published', publishTime: new Date().toISOString() })
      : null
  }
  async rejectProblem(id: string) {
    requireUser('teacher')
    const problem = await this.findProblem(id)
    return problem ? this.upsertProblem({ ...problem, status: 'rejected' }) : null
  }
  async resetProblems() {
    requireUser('teacher')
    return local.resetProblems().map(fromProblemView)
  }
  async getStudentQuestions() {
    requireUser('student')
    const visible = new Set((await this.getProblems()).filter((p) => p.contentType !== 'guided_case').map((p) => p.id))
    return local
      .getStudentQuestions()
      .filter((q) => visible.has(q.id))
      .map((q) => ({
        ...fromQuestionView(q),
        status: local.getQuestionThread(q.id) ? ('answered' as const) : fromQuestionView(q).status,
      }))
  }
  async findStudentQuestion(id: string) {
    return (await this.getStudentQuestions()).find((q) => q.id === id)
  }
  async getQuestionThread(id: string) {
    requireUser('student')
    return (await this.findStudentQuestion(id)) ? local.getQuestionThread(id) : undefined
  }
  async saveQuestionThread(thread: QuestionThread) {
    requireUser('student')
    if (!(await this.findStudentQuestion(thread.questionId)))
      throw new AppError('题目不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
    local.saveQuestionThread(thread)
  }
}
