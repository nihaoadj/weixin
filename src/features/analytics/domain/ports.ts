import type { AnalyticsCase, AnalyticsKnowledge, AnalyticsOverview, AnalyticsStudent } from '@/types/teacher'

export interface AnalyticsRepository {
  getAnalyticsOverview(classId?: number, dateFrom?: string, dateTo?: string): Promise<AnalyticsOverview>
  getAnalyticsCase(problemId: number, classId?: number, dateFrom?: string, dateTo?: string): Promise<AnalyticsCase>
  getAnalyticsStudent(
    studentId: number,
    classId?: number,
    dateFrom?: string,
    dateTo?: string,
  ): Promise<AnalyticsStudent>
  getAnalyticsKnowledge(classId: number): Promise<AnalyticsKnowledge>
}
