import type { Conversation, ConversationSummary, Page, QuestionThread, StudentQuestion } from '@/types/records'

export interface ConversationRepository {
  getConversations(): Promise<Conversation[]>
  getConversationSummaries(limit: number, offset: number, topicCode?: string): Promise<Page<ConversationSummary>>
  findConversation(conversationId: string): Promise<Conversation | undefined>
  upsertConversation(conversation: Conversation): Promise<void>
}

export interface QuestionRepository {
  getStudentQuestions(): Promise<StudentQuestion[]>
  findStudentQuestion(id: string): Promise<StudentQuestion | undefined>
  getQuestionThread(questionId: string): Promise<QuestionThread | undefined>
  saveQuestionThread(thread: QuestionThread): Promise<void>
}

export interface QaRepository extends ConversationRepository, QuestionRepository {}

/** Legacy aggregate type retained only for the old adapter contract. */
export type CoreRepository = QaRepository
