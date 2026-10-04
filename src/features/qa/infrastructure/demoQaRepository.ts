import * as conversations from './demoConversationStore'
import { AppError } from '@/types/errors'
import { getSessionContext } from '@/platform/session/context'
import type { QaRepository } from '@/features/qa/domain/ports'
import type { ProblemRepository } from '@/features/content/domain/ports'
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
  constructor(_problems: Pick<ProblemRepository, 'getProblems'>) {}

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
    return paginate(
      newest(
        conversations.map((conversation) => {
          return {
            id: conversation.conversationId,
            conversationId: conversation.conversationId,
            messagePreview: conversation.messages[0]?.content.slice(0, 160) || '',
            messageCount: conversation.messages.length,
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
    return []
  }

  async findStudentQuestion(_id: string): Promise<StudentQuestion | undefined> {
    requireUser('student')
    return undefined
  }

  async getQuestionThread(_id: string): Promise<QuestionThread | undefined> {
    requireUser('student')
    return undefined
  }

  async saveQuestionThread(_thread: QuestionThread): Promise<void> {
    requireUser('student')
    throw new AppError('开放讨论题流程已退役', { code: 'RETIRED_FLOW', statusCode: 409 })
  }
}
