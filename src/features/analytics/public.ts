import { getApplicationServices } from '@/bootstrap/wiring'
import type { TeacherInsightsFilters, TeacherInsightsStudentFilters } from './domain/teacherInsights'

const analytics = () => getApplicationServices().analytics

export const getTeacherInsightsOverview = (filters?: TeacherInsightsFilters) =>
  analytics().getTeacherInsightsOverview(filters)
export const getTeacherInsightsStudents = (filters?: TeacherInsightsFilters, limit?: number, offset?: number) =>
  analytics().getTeacherInsightsStudents(filters, limit, offset)
export const getTeacherInsightsStudent = (studentId: number, filters: TeacherInsightsStudentFilters) =>
  analytics().getTeacherInsightsStudent(studentId, filters)
export const getTeacherInsightsKnowledge = (filters?: TeacherInsightsFilters) =>
  analytics().getTeacherInsightsKnowledge(filters)
export const getTeacherInsightsDiagnostics = (filters?: TeacherInsightsFilters, limit?: number, offset?: number) =>
  analytics().getTeacherInsightsDiagnostics(filters, limit, offset)

export type {
  TeacherInsightsCohortProgress,
  TeacherInsightsDiagnosis,
  TeacherInsightsDiagnosisPage,
  TeacherInsightsDiscussion,
  TeacherInsightsDiscussionProgress,
  TeacherInsightsFinding,
  TeacherInsightsFindingGroup,
  TeacherInsightsFilters,
  TeacherInsightsKnowledgePage,
  TeacherInsightsKnowledgeRow,
  TeacherInsightsMetricBasis,
  TeacherInsightsOverview,
  TeacherInsightsPeriodResults,
  TeacherInsightsResultSummary,
  TeacherInsightsRouteProgress,
  TeacherInsightsScope,
  TeacherInsightsSessionId,
  TeacherInsightsStudent,
  TeacherInsightsStudentDetail,
  TeacherInsightsStudentFilters,
  TeacherInsightsStudentPage,
} from './domain/teacherInsights'
