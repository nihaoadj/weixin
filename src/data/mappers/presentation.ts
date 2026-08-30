import type * as Domain from '@/types/records'
import type * as View from '@/types/domain'
import { reportLabels, problemLabels } from './status'
const reportStates = { 草稿: 'draft', 待批阅: 'pending_review', 已批阅: 'reviewed' } as const
const problemStates = { 待审核: 'draft', 已发布: 'published', 已拒绝: 'rejected' } as const
export const toReportView = (value: Domain.Report): View.Report => ({ ...value, status: reportLabels[value.status] })
export const fromReportView = (value: View.Report): Domain.Report => ({ ...value, status: reportStates[value.status] })
export function toProblemView<T extends Pick<Domain.Problem, 'status'>>(
  value: T,
): Omit<T, 'status'> & Pick<View.Problem, 'status'> {
  return { ...value, status: problemLabels[value.status] }
}
export function fromProblemView<T extends Pick<View.Problem, 'status'>>(
  value: T,
): Omit<T, 'status'> & Pick<Domain.Problem, 'status'> {
  return { ...value, status: problemStates[value.status] }
}
export const toQuestionView = (value: Domain.StudentQuestion): View.StudentQuestion => ({
  ...value,
  status: value.status === 'answered' ? '已回答' : '未回答',
})
export const fromQuestionView = (value: View.StudentQuestion): Domain.StudentQuestion => ({
  ...value,
  status: value.status === '已回答' ? 'answered' : 'unanswered',
})
export const toConversationSummaryView = (value: Domain.ConversationSummary): View.ConversationSummary => ({
  ...value,
  reportStatus: value.reportStatus ? reportLabels[value.reportStatus] : undefined,
})
export const toReportSummaryView = (value: Domain.ReportSummary): View.ReportSummary => ({
  ...value,
  status: reportLabels[value.status],
})
export function optional<T, U>(value: T | undefined, mapper: (value: T) => U): U | undefined {
  return value === undefined ? undefined : mapper(value)
}
export function nullable<T, U>(value: T | null, mapper: (value: T) => U): U | null {
  return value === null ? null : mapper(value)
}
