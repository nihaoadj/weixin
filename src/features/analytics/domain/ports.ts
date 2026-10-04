import type {
  TeacherInsightsDiagnosisPage,
  TeacherInsightsFilters,
  TeacherInsightsKnowledgePage,
  TeacherInsightsOverview,
  TeacherInsightsStudentDetail,
  TeacherInsightsStudentFilters,
  TeacherInsightsStudentPage,
} from './teacherInsights'

export interface AnalyticsRepository {
  getTeacherInsightsOverview(filters?: TeacherInsightsFilters): Promise<TeacherInsightsOverview>
  getTeacherInsightsStudents(
    filters?: TeacherInsightsFilters,
    limit?: number,
    offset?: number,
  ): Promise<TeacherInsightsStudentPage>
  getTeacherInsightsStudent(
    studentId: number,
    filters: TeacherInsightsStudentFilters,
  ): Promise<TeacherInsightsStudentDetail>
  getTeacherInsightsKnowledge(filters?: TeacherInsightsFilters): Promise<TeacherInsightsKnowledgePage>
  getTeacherInsightsDiagnostics(
    filters?: TeacherInsightsFilters,
    limit?: number,
    offset?: number,
  ): Promise<TeacherInsightsDiagnosisPage>
}
