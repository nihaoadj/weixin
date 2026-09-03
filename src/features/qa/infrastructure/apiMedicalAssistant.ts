import { z } from 'zod'
import { apiRequest } from '@/platform/http/apiClient'
import type { MedicalAssistantPort, MedicalChatRequest } from '@/features/qa/application/medicalAssistant'

const MAX_PROMPT_LENGTH = 4000
const MAX_HISTORY_MESSAGES = 20
const medicalChatResponseSchema = z.object({ content: z.string().min(1) }).transform((value) => value.content)

export const apiMedicalAssistant: MedicalAssistantPort = {
  async request(request: MedicalChatRequest): Promise<string> {
    const previousHistory = request.history
      .slice(-MAX_HISTORY_MESSAGES)
      .filter((message, index, messages) => {
        const isCurrentPrompt =
          index === messages.length - 1 && message.role === 'user' && message.content.trim() === request.prompt
        return !isCurrentPrompt
      })
      .map(({ role, content }) => ({ role, content: content.slice(0, MAX_PROMPT_LENGTH) }))

    const content = await apiRequest({
      path: '/v1/medical-chat',
      method: 'POST',
      schema: medicalChatResponseSchema,
      body: {
        prompt: request.prompt,
        mode: request.mode || request.question?.type || '自由问答',
        messages: previousHistory,
        topic_codes: request.topicCodes || [],
      },
    })
    return content.trim()
  },
}
