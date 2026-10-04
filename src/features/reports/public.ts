import { getApplicationServices } from '@/bootstrap/wiring'
import { optional, toReportView } from '@/shared/mappers/presentation'

const reports = () => getApplicationServices().reports

export const findReportByConversationAsync = async (id: string) =>
  optional(await reports().findReportByConversation(id), toReportView)
export const findReportAsync = async (id: string) => optional(await reports().findReport(id), toReportView)
