import type { ReportDraftInput } from '@/data/repositories/core'
import type { Conversation, Report } from '@/types/records'

/** Business ordering is shared; adapters supply persistence without leaking DTOs. */
export interface ReportDraftPersistence {
  persistConversation(value: Conversation): Promise<string>
  persistDraft(conversationId: string, input: ReportDraftInput): Promise<Report>
}

export async function saveReportDraft(input: ReportDraftInput, persistence: ReportDraftPersistence): Promise<Report> {
  const id = await persistence.persistConversation({
    conversationId: input.conversationId,
    messages: input.messages,
    createdAt: input.createdAt,
    updatedAt: new Date().toISOString(),
  })
  return persistence.persistDraft(id, input)
}
