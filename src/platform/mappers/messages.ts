import type { ApiMessage } from '@/platform/contracts/core'
import type { ChatMessage } from '@/types/records'
import { AppError } from '@/types/errors'

export function toChatMessage(message: ApiMessage): ChatMessage {
  if (message.role !== 'user' && message.role !== 'assistant') {
    throw new AppError('消息角色不符合领域契约', { code: 'CONTRACT_ERROR' })
  }
  return { id: String(message.id), role: message.role, content: message.content, timestamp: message.created_at }
}
