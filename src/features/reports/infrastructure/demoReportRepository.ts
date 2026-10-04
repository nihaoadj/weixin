import * as local from './demoReportStore'
import { fromReportView } from '@/shared/mappers/presentation'
import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'
import type { ReportRepository } from '@/features/reports/domain/ports'
import type { Report } from '@/types/records'

function requireStudent() {
  const user = getSessionContext()
  if (!user) throw new AppError('请先登录', { code: 'AUTH_REQUIRED', statusCode: 401 })
  if (user.role !== 'student')
    throw new AppError('历史问答总结仅对本人开放', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
}

/** Demo keeps the seeded legacy reports as student-owned, read-only history. */
export class DemoReportRepository implements ReportRepository {
  async findReportByConversation(id: string): Promise<Report | undefined> {
    requireStudent()
    const report = local.getReports().find((item) => item.conversationId === id)
    return report ? fromReportView(report) : undefined
  }

  async findReport(id: string): Promise<Report | undefined> {
    requireStudent()
    const reports = local.getReports()
    const report = reports.find((item) => item.id === id || item.conversationId === id)
    return report ? fromReportView(report) : undefined
  }
}
