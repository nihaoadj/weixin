import { getApplicationServices } from '@/bootstrap/wiring'
import { optional, toConversationSummaryView, toQuestionView } from '@/shared/mappers/presentation'
import type { Conversation, QuestionThread } from '@/types/domain'
export {
  detectEmergency,
  type MedicalAssistantPort,
  type MedicalChatRequest,
} from '@/features/qa/application/medicalAssistant'

const qa = () => getApplicationServices().qa

export function ensureDemoData(): void {
  getApplicationServices().ensureDemoData()
}

export const getConversationsAsync = () => qa().getConversations()
export const getConversationSummariesAsync = async (limit = 20, offset = 0, topicCode?: string) => {
  const page = await qa().getConversationSummaries(limit, offset, topicCode)
  return { ...page, items: page.items.map(toConversationSummaryView) }
}
export const findConversationAsync = (conversationId: string) => qa().findConversation(conversationId)
export const upsertConversationAsync = (conversation: Conversation) => qa().upsertConversation(conversation)

export const getStudentQuestionsAsync = async () => (await qa().getStudentQuestions()).map(toQuestionView)
export const findStudentQuestionAsync = async (id: string) =>
  optional(await qa().findStudentQuestion(id), toQuestionView)
export const getQuestionThreadAsync = (questionId: string) => qa().getQuestionThread(questionId)
export const saveQuestionThreadAsync = (thread: QuestionThread) => qa().saveQuestionThread(thread)

export async function requestMedicalAssistant(
  request: import('@/features/qa/application/medicalAssistant').MedicalChatRequest,
): Promise<string> {
  return getApplicationServices().medicalAssistant.request(request)
}

/** Structured T08 compatibility facade; deterministic until an AI gateway supplies candidates. */
export async function requestLearningAssistant(
  request: import('@/features/qa/application/medicalAssistant').MedicalChatRequest,
): Promise<{
  answer: string
  safetyNotice?: string
  learning: { confirmedTopicCodes: string[]; candidateTopicCodes: string[]; followUpPrompts: string[] }
}> {
  const answer = await requestMedicalAssistant(request)
  return {
    answer,
    learning: {
      confirmedTopicCodes: request.topicCodes || [],
      candidateTopicCodes: request.topicCodes || [],
      followUpPrompts: [],
    },
  }
}

export const getConversationLearningContext = async (conversationId: string) =>
  (await findConversationAsync(conversationId))?.topicCodes || []
export async function setConversationLearningContext(conversationId: string, topicCodes: string[]): Promise<void> {
  const conversation = await findConversationAsync(conversationId)
  if (!conversation) throw new Error('对话不存在')
  await upsertConversationAsync({ ...conversation, topicCodes: [...new Set(topicCodes)].slice(0, 3) })
}
export const getTopicConversationSummaries = async (topicCode: string) =>
  (await getConversationSummariesAsync(100, 0, topicCode)).items
