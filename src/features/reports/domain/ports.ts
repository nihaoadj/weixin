import type { Conversation, Report, ReportSummaryPage } from '@/types/records'

export type ReportDraftInput = Omit<Report, 'studentId' | 'studentName' | 'status'>

export interface ReportRepository {
  getReports(): Promise<Report[]>
  getReportSummaries(limit: number, offset: number): Promise<ReportSummaryPage>
  findReport(conversationIdOrReportId: string): Promise<Report | undefined>
  findReportByConversation(conversationId: string): Promise<Report | undefined>
  saveDraftReport(input: ReportDraftInput): Promise<Report>
  submitReportForReview(conversationId: string): Promise<Report | null>
  reviewReport(
    conversationIdOrReportId: string,
    score: number,
    feedback: string,
    reviewTopicCodes?: string[],
  ): Promise<Report | null>
}

export interface ReportDraftPersistence {
  persistConversation(value: Conversation): Promise<string>
  persistDraft(conversationId: string, input: ReportDraftInput): Promise<Report>
}
