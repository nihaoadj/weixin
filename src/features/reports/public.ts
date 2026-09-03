import { getApplicationServices } from '@/bootstrap/wiring'
import type { ReportDraftInput } from '@/features/reports/domain/ports'
import { nullable, optional, toReportSummaryView, toReportView } from '@/shared/mappers/presentation'
import type { Report } from '@/types/domain'

const reports = () => getApplicationServices().reports

export const findReportByConversationAsync = async (id: string) =>
  optional(await reports().findReportByConversation(id), toReportView)
export const getReportsAsync = async () => (await reports().getReports()).map(toReportView)
export const getReportSummariesAsync = async (limit = 20, offset = 0) => {
  const page = await reports().getReportSummaries(limit, offset)
  return { ...page, items: page.items.map(toReportSummaryView) }
}
export const findReportAsync = async (id: string) => optional(await reports().findReport(id), toReportView)
export const saveDraftReportAsync = async (input: ReportDraftInput) =>
  toReportView(await reports().saveDraftReport(input))
export const submitReportForReviewAsync = async (conversationId: string) =>
  nullable(await reports().submitReportForReview(conversationId), toReportView)
export const reviewReportAsync = async (id: string, score: number, feedback: string, reviewTopicCodes: string[] = []) =>
  nullable(await reports().reviewReport(id, score, feedback, reviewTopicCodes), toReportView)

export type { ReportDraftInput }
export type { Report }
