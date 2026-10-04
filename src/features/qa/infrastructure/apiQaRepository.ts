import {
  apiConversationListSchema,
  apiConversationSchema,
  apiConversationSummaryPageSchema,
  apiQuestionThreadSchema,
  apiStudentQuestionListSchema,
  studentQuestionSchema,
} from '@/platform/contracts/core'
import type { ApiConversation, ApiQuestionThread } from '@/platform/contracts/core'
import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import { toConversation, toThread, undefinedOnNotFound } from './mappers/core'
import type { Conversation, ConversationSummary, Page, QuestionThread, StudentQuestion } from '@/types/records'
import type { QaRepository } from '@/features/qa/domain/ports'

const LIST_TTL = 30_000
const THREAD_TTL = 15_000

export class ApiQaRepository implements QaRepository {
  private async upsertRemoteConversation(conversation: Conversation): Promise<ApiConversation> {
    return apiRequest<ApiConversation>({
      path: '/conversations',
      method: 'POST',
      schema: apiConversationSchema,
      invalidateCache: ['/conversations'],
      body: {
        client_id: conversation.conversationId,
        messages: conversation.messages.map(({ role, content }) => ({ role, content })),
        topic_codes: conversation.topicCodes || [],
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

  async getConversationSummaries(
    limit: number,
    offset: number,
    topicCode?: string,
  ): Promise<Page<ConversationSummary>> {
    const page = await apiRequest({
      path: '/conversations/summaries',
      query: { limit, offset, knowledge_point_code: topicCode || undefined },
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
        topicCodes: item.topic_codes,
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
      topicCodes: item.topic_codes,
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
        topicCodes: item.topic_codes,
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
