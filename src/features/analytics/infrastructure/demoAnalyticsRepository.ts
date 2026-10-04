import type { AnalyticsRepository } from '@/features/analytics/domain/ports'
import type { TeacherInsightsStudentFilters } from '../domain/teacherInsights'
import { demoTeacherInsights } from './demoTeacherInsights'

export const demoAnalyticsRepository: AnalyticsRepository = {
  async getTeacherInsightsOverview(filters = {}) {
    return demoTeacherInsights.overview(filters)
  },
  async getTeacherInsightsStudents(filters = {}, limit, offset) {
    return demoTeacherInsights.students(filters, limit, offset)
  },
  async getTeacherInsightsStudent(studentId, filters: TeacherInsightsStudentFilters) {
    return demoTeacherInsights.student(studentId, filters)
  },
  async getTeacherInsightsKnowledge(filters = {}) {
    return demoTeacherInsights.knowledge(filters)
  },
  async getTeacherInsightsDiagnostics(filters = {}, limit, offset) {
    return demoTeacherInsights.diagnostics(filters, limit, offset)
  },
}
