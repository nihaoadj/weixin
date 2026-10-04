import type { z } from 'zod'
import type {
  TeacherInsightsCohortProgress,
  TeacherInsightsDiagnosis,
  TeacherInsightsDiagnosisPage,
  TeacherInsightsFindingGroup,
  TeacherInsightsKnowledgePage,
  TeacherInsightsKnowledgeRow,
  TeacherInsightsOverview,
  TeacherInsightsPeriodResults,
  TeacherInsightsResultSummary,
  TeacherInsightsRouteProgress,
  TeacherInsightsScope,
  TeacherInsightsStudent,
  TeacherInsightsStudentDetail,
  TeacherInsightsStudentPage,
} from '@/features/analytics/domain/teacherInsights'
import {
  apiTeacherInsightsDiagnosticsSchema,
  apiTeacherInsightsKnowledgeSchema,
  apiTeacherInsightsOverviewSchema,
  apiTeacherInsightsStudentSchema,
  apiTeacherInsightsStudentsSchema,
} from '@/platform/contracts/teacherInsights'

type ApiOverview = z.infer<typeof apiTeacherInsightsOverviewSchema>
type ApiStudents = z.infer<typeof apiTeacherInsightsStudentsSchema>
type ApiStudent = z.infer<typeof apiTeacherInsightsStudentSchema>
type ApiKnowledge = z.infer<typeof apiTeacherInsightsKnowledgeSchema>
type ApiDiagnostics = z.infer<typeof apiTeacherInsightsDiagnosticsSchema>
type ApiCohort = ApiOverview['cohort']
type ApiPeriodResults = ApiOverview['period_results']
type ApiInsightStudent = ApiStudents['items'][number]
type ApiKnowledgeRow = ApiKnowledge['items'][number]
type ApiDiagnosis = ApiDiagnostics['items'][number]
type ApiFindingGroup = ApiDiagnostics['knowledge_gaps'][number]
type ApiResultSummary = ApiStudent['results'][number]
type ApiRouteProgress = ApiStudent['routes'][number]

const mapScope = (value: ApiOverview['scope']): TeacherInsightsScope => ({
  classId: value.class_id,
  className: value.class_name,
  classIds: value.class_ids,
  sessionId: value.session_id,
  dateFrom: value.date_from,
  dateTo: value.date_to,
  timezone: value.timezone,
  asOf: value.as_of,
  metricBasis: value.metric_basis,
})

const mapCohort = (value: ApiCohort): TeacherInsightsCohortProgress => ({
  publishedRoutes: value.published_routes,
  completedTests: value.completed_tests,
  completionRate: value.completion_rate,
  gradingTests: value.grading_tests,
})

const mapPeriodResults = (value: ApiPeriodResults): TeacherInsightsPeriodResults => ({
  completedTests: value.completed_tests,
  averageScore: value.average_score,
  formatCounts: value.format_counts,
})

const mapStudent = (value: ApiInsightStudent): TeacherInsightsStudent => ({
  studentId: value.student_id,
  studentName: value.student_name,
  classIds: value.class_ids,
  cohort: mapCohort(value.cohort),
  periodResults: mapPeriodResults(value.period_results),
  diagnosisCount: value.diagnosis_count,
  lastCompletedAt: value.last_completed_at,
  discussionProgress: value.discussion_progress,
})

const mapKnowledge = (value: ApiKnowledgeRow): TeacherInsightsKnowledgeRow => ({
  pointCode: value.point_code,
  correctCount: value.correct_count,
  objectiveCount: value.objective_count,
  invalidObjectiveCount: value.invalid_objective_count,
  accuracyRate: value.accuracy_rate,
  shortAnswerCount: value.short_answer_count,
  invalidShortAnswerCount: value.invalid_short_answer_count,
  pointsAwarded: value.points_awarded,
  pointsPossible: value.points_possible,
  shortAnswerScoreRate: value.short_answer_score_rate,
})

const mapDiagnosis = (value: ApiDiagnosis): TeacherInsightsDiagnosis => ({
  participationId: value.participation_id,
  sessionId: value.session_id,
  classId: value.class_id,
  className: value.class_name,
  studentId: value.student_id,
  studentName: value.student_name,
  completedAt: value.completed_at,
  knowledgeGapCodes: value.knowledge_gap_codes,
  reasoningIssueCodes: value.reasoning_issue_codes,
  knowledgeGaps: value.knowledge_gaps.map((finding) => ({ code: finding.code, summary: finding.summary })),
  reasoningIssues: value.reasoning_issues.map((finding) => ({ code: finding.code, summary: finding.summary })),
})

const mapFindingGroup = (value: ApiFindingGroup): TeacherInsightsFindingGroup => ({
  code: value.code,
  studentCount: value.student_count,
  diagnosisCount: value.diagnosis_count,
  lastCompletedAt: value.last_completed_at,
})

const mapResultSummary = (value: ApiResultSummary): TeacherInsightsResultSummary => ({
  resultId: value.result_id,
  routeId: value.route_id,
  classId: value.class_id,
  sessionId: value.session_id,
  studentId: value.student_id,
  score: value.score,
  completedAt: value.completed_at,
  formatVersion: value.format_version,
})

const mapRouteProgress = (value: ApiRouteProgress): TeacherInsightsRouteProgress => ({
  routeId: value.route_id,
  studentId: value.student_id,
  classId: value.class_id,
  sessionId: value.session_id,
  publishedAt: value.published_at,
  resultId: value.result_id,
  testGenerationState: value.test_generation_state,
  testReviewState: value.test_review_state,
  attemptStatus: value.attempt_status,
  completedSteps: value.completed_steps,
  totalSteps: value.total_steps,
  readingSeconds: value.reading_seconds,
})

export function mapTeacherInsightsOverview(value: ApiOverview): TeacherInsightsOverview {
  return {
    scope: mapScope(value.scope),
    cohort: mapCohort(value.cohort),
    periodResults: mapPeriodResults(value.period_results),
    diagnosisCount: value.diagnosis_count,
    studentCount: value.student_count,
  }
}

export function mapTeacherInsightsStudents(value: ApiStudents): TeacherInsightsStudentPage {
  return {
    scope: mapScope(value.scope),
    items: value.items.map(mapStudent),
    total: value.total,
    limit: value.limit,
    offset: value.offset,
  }
}

export function mapTeacherInsightsStudent(value: ApiStudent): TeacherInsightsStudentDetail {
  return {
    scope: mapScope(value.scope),
    summary: mapStudent(value.summary),
    discussions: value.discussions.map((item) => ({
      participationId: item.participation_id,
      sessionId: item.session_id,
      classId: item.class_id,
      studentId: item.student_id,
      phase: item.phase,
      status: item.status,
      startedAt: item.started_at,
      completedAt: item.completed_at,
    })),
    routes: value.routes.map(mapRouteProgress),
    results: value.results.map(mapResultSummary),
    diagnoses: value.diagnoses.map(mapDiagnosis),
    knowledge: value.knowledge.map(mapKnowledge),
  }
}

export function mapTeacherInsightsKnowledge(value: ApiKnowledge): TeacherInsightsKnowledgePage {
  return {
    scope: mapScope(value.scope),
    items: value.items.map(mapKnowledge),
    resultCount: value.result_count,
  }
}

export function mapTeacherInsightsDiagnostics(value: ApiDiagnostics): TeacherInsightsDiagnosisPage {
  return {
    scope: mapScope(value.scope),
    items: value.items.map(mapDiagnosis),
    total: value.total,
    limit: value.limit,
    offset: value.offset,
    knowledgeGaps: value.knowledge_gaps.map(mapFindingGroup),
    reasoningIssues: value.reasoning_issues.map(mapFindingGroup),
  }
}
