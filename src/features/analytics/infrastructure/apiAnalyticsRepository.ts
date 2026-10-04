import type { AnalyticsRepository } from '@/features/analytics/domain/ports'
import {
  apiTeacherInsightsDiagnosticsSchema,
  apiTeacherInsightsKnowledgeSchema,
  apiTeacherInsightsOverviewSchema,
  apiTeacherInsightsStudentSchema,
  apiTeacherInsightsStudentsSchema,
} from '@/platform/contracts/teacherInsights'
import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import { AppError } from '@/types/errors'
import type { TeacherInsightsFilters, TeacherInsightsStudentFilters } from '../domain/teacherInsights'
import {
  mapTeacherInsightsDiagnostics,
  mapTeacherInsightsKnowledge,
  mapTeacherInsightsOverview,
  mapTeacherInsightsStudent,
  mapTeacherInsightsStudents,
} from './teacherInsightsMapper'

function teacherInsightsQuery(filters: TeacherInsightsFilters = {}) {
  let sessionId = filters.sessionId
  if (typeof sessionId === 'string') {
    if (!/^[1-9]\d*$/.test(sessionId)) throw new AppError('课堂编号无效', { code: 'VALIDATION_ERROR' })
    sessionId = Number(sessionId)
  }
  return {
    class_id: filters.classId,
    session_id: sessionId,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
  }
}

export const apiAnalyticsRepository: AnalyticsRepository = {
  async getTeacherInsightsOverview(filters = {}) {
    return mapTeacherInsightsOverview(
      await apiRequest({
        path: '/analytics/teacher-insights/overview',
        query: teacherInsightsQuery(filters),
        schema: apiTeacherInsightsOverviewSchema,
      }),
    )
  },
  async getTeacherInsightsStudents(filters = {}, limit = 20, offset = 0) {
    return mapTeacherInsightsStudents(
      await apiRequest({
        path: '/analytics/teacher-insights/students',
        query: { ...teacherInsightsQuery(filters), limit, offset },
        schema: apiTeacherInsightsStudentsSchema,
      }),
    )
  },
  async getTeacherInsightsStudent(studentId, filters: TeacherInsightsStudentFilters) {
    return mapTeacherInsightsStudent(
      await apiRequest({
        path: `/analytics/teacher-insights/students/${encodePathSegment(studentId)}`,
        query: teacherInsightsQuery(filters),
        schema: apiTeacherInsightsStudentSchema,
      }),
    )
  },
  async getTeacherInsightsKnowledge(filters = {}) {
    return mapTeacherInsightsKnowledge(
      await apiRequest({
        path: '/analytics/teacher-insights/knowledge',
        query: teacherInsightsQuery(filters),
        schema: apiTeacherInsightsKnowledgeSchema,
      }),
    )
  },
  async getTeacherInsightsDiagnostics(filters = {}, limit = 20, offset = 0) {
    return mapTeacherInsightsDiagnostics(
      await apiRequest({
        path: '/analytics/teacher-insights/diagnostics',
        query: { ...teacherInsightsQuery(filters), limit, offset },
        schema: apiTeacherInsightsDiagnosticsSchema,
      }),
    )
  },
}
