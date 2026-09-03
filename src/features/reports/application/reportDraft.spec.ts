import { describe, expect, it, vi } from 'vitest'
import { saveReportDraft } from '@/features/reports/application/reportDraft'
import type { ReportDraftInput, ReportDraftPersistence } from '@/features/reports/domain/ports'
import type { Report } from '@/types/records'

const input: ReportDraftInput = {
  conversationId: 'client-conversation-1',
  messages: [{ id: 'message-1', role: 'user', content: '回答', timestamp: '2026-08-30T00:00:00Z' }],
  analysis: { errors: [], score: 88, summary: '结构完整' },
  createdAt: '2026-08-30T00:00:00Z',
}

const savedReport: Report = {
  ...input,
  id: 'report-1',
  studentId: 'student-1',
  studentName: '学生',
  status: 'draft',
}

describe('saveReportDraft', () => {
  it('persists the conversation before persisting the draft with the resolved conversation id', async () => {
    const calls: string[] = []
    const persistence: ReportDraftPersistence = {
      persistConversation: vi.fn(async (conversation) => {
        calls.push(`conversation:${conversation.conversationId}`)
        expect(conversation.messages).toEqual(input.messages)
        return 'server-conversation-1'
      }),
      persistDraft: vi.fn(async (conversationId, draft) => {
        calls.push(`draft:${conversationId}`)
        expect(draft).toBe(input)
        return savedReport
      }),
    }

    await expect(saveReportDraft(input, persistence)).resolves.toBe(savedReport)
    expect(calls).toEqual(['conversation:client-conversation-1', 'draft:server-conversation-1'])
  })

  it('propagates a second-step failure after the conversation has been persisted and does not retry either step', async () => {
    const failure = new Error('draft persistence failed')
    const persistence: ReportDraftPersistence = {
      persistConversation: vi.fn(async () => 'server-conversation-1'),
      persistDraft: vi.fn(async () => Promise.reject(failure)),
    }

    await expect(saveReportDraft(input, persistence)).rejects.toBe(failure)
    expect(persistence.persistConversation).toHaveBeenCalledTimes(1)
    expect(persistence.persistDraft).toHaveBeenCalledWith('server-conversation-1', input)
    expect(persistence.persistDraft).toHaveBeenCalledTimes(1)
  })
})
