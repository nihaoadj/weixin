import { getApplicationServices } from '@/bootstrap/wiring'

const analytics = () => getApplicationServices().analytics

export const getAnalyticsOverview = (classId?: number, dateFrom?: string, dateTo?: string) =>
  analytics().getAnalyticsOverview(classId, dateFrom, dateTo)
export const getAnalyticsCase = (problemId: number, classId?: number, dateFrom?: string, dateTo?: string) =>
  analytics().getAnalyticsCase(problemId, classId, dateFrom, dateTo)
export const getAnalyticsStudent = (studentId: number, classId?: number, dateFrom?: string, dateTo?: string) =>
  analytics().getAnalyticsStudent(studentId, classId, dateFrom, dateTo)
export const getAnalyticsKnowledge = (classId: number) => analytics().getAnalyticsKnowledge(classId)

export type { AnalyticsCase, AnalyticsDimension, AnalyticsKnowledge, AnalyticsOverview, AnalyticsStudent } from '@/types/teacher'
