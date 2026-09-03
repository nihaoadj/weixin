import type { ReportDraftInput, ReportDraftPersistence } from '@/features/reports/domain/ports'
import type { Report } from '@/types/records'

export async function saveReportDraft(input: ReportDraftInput, persistence: ReportDraftPersistence): Promise<Report> {
  const id = await persistence.persistConversation({
    conversationId: input.conversationId,
    messages: input.messages,
    createdAt: input.createdAt,
    updatedAt: new Date().toISOString(),
  })
  return persistence.persistDraft(id, input)
}
