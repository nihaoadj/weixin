import { z, type ZodType } from 'zod'
import { reportSchema, storage, storageKeys } from '@/platform/storage/storage'
import { getSessionContext } from '@/platform/session/context'
import type { Report } from '@/types/domain'

const MAX_CONVERSATION_MESSAGES = 100
const MAX_REPORTS = 100
type ReportDraftInput = Omit<Report, 'studentId' | 'studentName' | 'status'>

function readArray<T>(key: string, itemSchema: ZodType<T>): T[] {
  return storage.read(key, z.array(itemSchema), [])
}

function writeArray<T>(key: string, value: T[], itemSchema: ZodType<T>): void {
  storage.write(key, value, z.array(itemSchema))
}

function getAllReports(): Report[] {
  return readArray(storageKeys.reports, reportSchema)
}

function writeReports(reports: Report[]): void {
  writeArray(storageKeys.reports, reports.slice(-MAX_REPORTS), reportSchema)
}

export function getReports(): Report[] {
  const session = getSessionContext()
  if (!session) return []
  const reports = getAllReports()
  return session.role === 'teacher' ? reports : reports.filter((report) => report.studentId === session.openid)
}

export function saveDraftReport(input: ReportDraftInput): Report {
  const session = getSessionContext()
  if (!session || session.role !== 'student') throw new Error('只有学生可以生成报告')

  const reports = getAllReports()
  const index = reports.findIndex(
    (report) => report.conversationId === input.conversationId && report.studentId === session.openid,
  )
  const existing = index >= 0 ? reports[index] : undefined
  if (existing && existing.status !== '草稿') return existing

  const draft: Report = {
    ...input,
    id:
      existing?.id ||
      input.id ||
      `demo-report:${encodeURIComponent(session.openid)}:${encodeURIComponent(input.conversationId)}`,
    updatedAt: new Date().toISOString(),
    messages: input.messages.slice(-MAX_CONVERSATION_MESSAGES),
    createdAt: existing?.createdAt || input.createdAt,
    studentId: session.openid,
    studentName: session.nickName,
    status: '草稿',
  }
  if (index >= 0) reports[index] = draft
  else reports.push(draft)
  writeReports(reports)
  return draft
}

export function submitReportForReview(conversationId: string): Report | null {
  const session = getSessionContext()
  if (!session || session.role !== 'student') return null
  const reports = getAllReports()
  const index = reports.findIndex(
    (report) => report.conversationId === conversationId && report.studentId === session.openid,
  )
  const report = index >= 0 ? reports[index] : undefined
  if (!report || report.status !== '草稿') return null
  const submitted: Report = { ...report, status: '待批阅', updatedAt: new Date().toISOString() }
  reports[index] = submitted
  writeReports(reports)
  return submitted
}

export function reviewReport(
  conversationId: string,
  score: number,
  feedback: string,
  reviewTopicCodes: string[] = [],
): Report | null {
  const session = getSessionContext()
  if (!session || session.role !== 'teacher') return null
  const reports = getAllReports()
  const index = reports.findIndex((report) => report.id === conversationId || report.conversationId === conversationId)
  const report = index >= 0 ? reports[index] : undefined
  if (!report || (report.status !== '待批阅' && report.status !== '已批阅')) return null
  const reviewed: Report = {
    ...report,
    status: '已批阅',
    updatedAt: new Date().toISOString(),
    teacherScore: score,
    teacherFeedback: feedback,
    reviewTopicCodes: [...new Set(reviewTopicCodes)].slice(0, 3),
  }
  reports[index] = reviewed
  writeReports(reports)
  return reviewed
}
