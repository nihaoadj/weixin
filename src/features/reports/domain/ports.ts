import type { Report } from '@/types/records'

export interface ReportRepository {
  findReport(conversationIdOrReportId: string): Promise<Report | undefined>
  findReportByConversation(conversationId: string): Promise<Report | undefined>
}
