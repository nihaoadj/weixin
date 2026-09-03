import * as conversations from './demoConversationStore'
import * as questions from './demoQuestionStore'
import { fromQuestionView } from '@/shared/mappers/presentation'
import { AppError } from '@/types/errors'
import { getSessionContext } from '@/platform/session/context'
import type { QaRepository } from '@/features/qa/domain/ports'
import type { ProblemRepository } from '@/features/content/domain/ports'
import type { ReportRepository } from '@/features/reports/domain/ports'
import type { Conversation, ConversationSummary, Page, QuestionThread, StudentQuestion } from '@/types/records'
import type { UserRole } from '@/types/domain'

function requireUser(role?: UserRole) {
  const user = getSessionContext()
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

export class DemoQaRepository implements QaRepository {
  constructor(
    private readonly problems: Pick<ProblemRepository, 'getProblems'>,
    private readonly reports: Pick<ReportRepository, 'getReports'>,
  ) {}

  async getConversations(): Promise<Conversation[]> {
    requireUser('student')
    return conversations.getConversations()
  }

  async getConversationSummaries(
    limit: number,
    offset: number,
    topicCode?: string,
  ): Promise<Page<ConversationSummary>> {
    const conversations = (await this.getConversations()).filter(
      (conversation) => !topicCode || conversation.topicCodes?.includes(topicCode),
    )
    const reports = new Map((await this.reports.getReports()).map((report) => [report.conversationId, report]))
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
            topicCodes: conversation.topicCodes || [],
          }
        }),
      ),
      limit,
      offset,
    )
  }

  async findConversation(id: string): Promise<Conversation | undefined> {
    requireUser('student')
    return conversations.findConversation(id)
  }

  async upsertConversation(value: Conversation): Promise<void> {
    requireUser('student')
    conversations.upsertConversation(value)
  }

  async getStudentQuestions(): Promise<StudentQuestion[]> {
    requireUser('student')
    const available = await this.problems.getProblems()
    const visibleQuestionIds = new Set(
      available.filter((problem) => problem.contentType !== 'guided_case').map((problem) => problem.id),
    )
    return questions
      .getStudentQuestions(
        available.map((problem) => ({
          ...problem,
          status: problem.status === 'published' ? '已发布' : problem.status === 'draft' ? '待审核' : '已拒绝',
        })),
      )
      .filter((question) => visibleQuestionIds.has(question.id))
      .map((question) => ({
        ...fromQuestionView(question),
        status: questions.getQuestionThread(question.id) ? ('answered' as const) : fromQuestionView(question).status,
      }))
  }

  async findStudentQuestion(id: string): Promise<StudentQuestion | undefined> {
    return (await this.getStudentQuestions()).find((question) => question.id === id)
  }

  async getQuestionThread(id: string): Promise<QuestionThread | undefined> {
    requireUser('student')
    return (await this.findStudentQuestion(id)) ? questions.getQuestionThread(id) : undefined
  }

  async saveQuestionThread(thread: QuestionThread): Promise<void> {
    requireUser('student')
    if (!(await this.findStudentQuestion(thread.questionId)))
      throw new AppError('题目不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
    questions.saveQuestionThread(thread)
  }
}
