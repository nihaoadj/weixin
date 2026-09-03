import type { ApiConversation, ApiQuestionThread } from '@/platform/contracts/core'
import { toChatMessage } from '@/platform/mappers/messages'
import type { Conversation, QuestionThread } from '@/types/records'
import { AppError } from '@/types/errors'
export { toChatMessage } from '@/platform/mappers/messages'

type ApiConversationWithTopics = ApiConversation & { topic_codes?: string[] }

export function toConversation(conversation: ApiConversationWithTopics): Conversation {
  return {
    conversationId: conversation.client_id,
    messages: (conversation.messages || []).map(toChatMessage),
    createdAt: conversation.created_at,
    updatedAt: conversation.updated_at,
    topicCodes: conversation.topic_codes || [],
  }
}

export function toThread(thread: ApiQuestionThread): QuestionThread {
  return {
    questionId: String(thread.question_id),
    messages: (thread.messages || []).map(toChatMessage),
    updatedAt: thread.updated_at,
  }
}

export function undefinedOnNotFound<T>(error: unknown): T | undefined {
  if (error instanceof AppError && error.statusCode === 404) return undefined
  throw error
}
