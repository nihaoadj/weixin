import { z, type ZodType } from 'zod'
import { conversationSchema, storage, storageKeys } from '@/platform/storage/storage'
import { getSessionContext } from '@/platform/session/context'
import type { Conversation } from '@/types/domain'

const MAX_CONVERSATION_MESSAGES = 100
const MAX_CONVERSATIONS = 10

function userScopedKey(baseKey: string, openid?: string): string | null {
  const userId = openid || getSessionContext()?.openid
  return userId ? storage.scopedKey(baseKey, userId) : null
}

function readArray<T>(key: string, itemSchema: ZodType<T>): T[] {
  return storage.read(key, z.array(itemSchema), [])
}

function writeArray<T>(key: string, value: T[], itemSchema: ZodType<T>): void {
  storage.write(key, value, z.array(itemSchema))
}

export function getConversations(): Conversation[] {
  const scopedKey = userScopedKey(storageKeys.conversations)
  return scopedKey ? readArray(scopedKey, conversationSchema) : []
}

export function findConversation(conversationId: string): Conversation | undefined {
  return getConversations().find((item) => item.conversationId === conversationId)
}

export function upsertConversation(conversation: Conversation): void {
  const scopedKey = userScopedKey(storageKeys.conversations)
  if (!scopedKey) throw new Error('保存对话前必须登录')
  const history = getConversations()
  const index = history.findIndex((item) => item.conversationId === conversation.conversationId)
  if (index >= 0) history.splice(index, 1)
  history.unshift({ ...conversation, messages: conversation.messages.slice(-MAX_CONVERSATION_MESSAGES) })
  writeArray(scopedKey, history.slice(0, MAX_CONVERSATIONS), conversationSchema)
}
