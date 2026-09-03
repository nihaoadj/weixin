import type { AnalyticsRepository } from '@/features/analytics/domain/ports'
import {
  apiAnalyticsCaseSchema,
  apiAnalyticsDimensionSchema,
  apiAnalyticsKnowledgeSchema,
  apiAnalyticsOverviewSchema,
  apiAnalyticsStudentSchema,
} from '@/platform/contracts/teacher'
import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import type {
  AnalyticsCase,
  AnalyticsDimension,
  AnalyticsKnowledge,
  AnalyticsOverview,
  AnalyticsStudent,
} from '@/types/teacher'

const ANALYTICS_TTL = 60_000

function toDimension(value: ReturnType<typeof apiAnalyticsDimensionSchema.parse>): AnalyticsDimension {
  return {
    dimensionId: value.dimension_id,
    label: value.label,
    averageScore: value.average_score,
    baselineScore: value.baseline_score,
    currentScore: value.current_score,
    delta: value.delta,
    studentCount: value.student_count,
    rate: value.rate,
  }
}

export const apiAnalyticsRepository: AnalyticsRepository = {
  async getAnalyticsOverview(classId?: number, dateFrom?: string, dateTo?: string): Promise<AnalyticsOverview> {
    const value = await apiRequest({
      path: '/analytics/overview',
      query: { class_id: classId, date_from: dateFrom, date_to: dateTo },
      cacheTtlMs: ANALYTICS_TTL,
      schema: apiAnalyticsOverviewSchema,
    })
    return {
      scope: {
        classId: value.scope.class_id,
        className: value.scope.class_name,
        dateFrom: value.scope.date_from,
        dateTo: value.scope.date_to,
      },
      studentCount: value.student_count,
      publishedCaseCount: value.published_case_count,
      eligiblePairs: value.eligible_pairs,
      startedPairs: value.started_pairs,
      completedPairs: value.completed_pairs,
      completionRate: value.completion_rate,
      currentAverageScore: value.current_average_score,
      averageImprovement: value.average_improvement,
      dimensions: value.dimensions.map(toDimension),
      weakDimensions: value.weak_dimensions.map(toDimension),
      cases: value.cases.map((item) => ({
        problemId: item.problem_id,
        title: item.title,
        completed: item.completed,
        assigned: item.assigned,
        averageScore: item.average_score,
      })),
      students: value.students.map((item) => ({
        studentId: item.student_id,
        nickname: item.nickname,
        completed: item.completed,
        assigned: item.assigned,
        averageScore: item.average_score,
      })),
    }
  },
  async getAnalyticsCase(
    problemId: number,
    classId?: number,
    dateFrom?: string,
    dateTo?: string,
  ): Promise<AnalyticsCase> {
    const value = await apiRequest({
      path: `/analytics/cases/${encodePathSegment(problemId)}`,
      query: { class_id: classId, date_from: dateFrom, date_to: dateTo },
      cacheTtlMs: ANALYTICS_TTL,
      schema: apiAnalyticsCaseSchema,
    })
    return {
      problem: value.problem,
      eligiblePairs: value.eligible_pairs,
      startedPairs: value.started_pairs,
      completedPairs: value.completed_pairs,
      completionRate: value.completion_rate,
      currentAverageScore: value.current_average_score,
      averageImprovement: value.average_improvement,
      averageDurationMinutes: value.average_duration_minutes,
      dimensions: value.dimensions.map(toDimension),
      distribution: value.distribution,
      students: value.students.map((item) => ({
        studentId: item.student_id,
        nickname: item.nickname,
        status: item.status,
        baseline: item.baseline,
        current: item.current,
        delta: item.delta,
        focusStage: item.focus_stage,
        lastAssessedAt: item.last_assessed_at,
      })),
    }
  },
  async getAnalyticsStudent(
    studentId: number,
    classId?: number,
    dateFrom?: string,
    dateTo?: string,
  ): Promise<AnalyticsStudent> {
    const value = await apiRequest({
      path: `/analytics/students/${encodePathSegment(studentId)}`,
      query: { class_id: classId, date_from: dateFrom, date_to: dateTo },
      cacheTtlMs: ANALYTICS_TTL,
      schema: apiAnalyticsStudentSchema,
    })
    return {
      student: value.student,
      assigned: value.assigned,
      started: value.started,
      completed: value.completed,
      completionRate: value.completion_rate,
      currentAverageScore: value.current_average_score,
      averageImprovement: value.average_improvement,
      dimensions: value.dimensions.map(toDimension),
      cases: value.cases.map((item) => ({
        problemId: item.problem_id,
        title: item.title,
        version: item.version,
        firstScore: item.first_score,
        latestScore: item.latest_score,
        delta: item.delta,
        attemptCount: item.attempt_count,
        focusStage: item.focus_stage,
        lastAssessedAt: item.last_assessed_at,
      })),
      timeline: value.timeline.map((item) => ({
        attemptId: item.attempt_id,
        problemId: item.problem_id,
        score: item.score,
        assessedAt: item.assessed_at,
      })),
      learningPlan: value.learning_plan
        ? {
            id: value.learning_plan.id,
            status: value.learning_plan.status,
            targetDimensionIds: value.learning_plan.target_dimension_ids,
            dueAt: value.learning_plan.due_at,
          }
        : null,
      practiceMastery: Object.fromEntries(
        Object.entries(value.practice_mastery).map(([key, item]) => [
          key,
          { averageScore: item.average_score, attemptCount: item.attempt_count },
        ]),
      ),
    }
  },
  async getAnalyticsKnowledge(classId: number): Promise<AnalyticsKnowledge> {
    const value = await apiRequest({
      path: `/analytics/classes/${encodePathSegment(classId)}/knowledge`,
      cacheTtlMs: ANALYTICS_TTL,
      schema: apiAnalyticsKnowledgeSchema,
    })
    return {
      classId: value.class_id,
      className: value.class_name,
      participantCount: value.participant_count,
      dueBacklog: value.due_backlog,
      objectiveCorrectRate: value.objective_correct_rate,
      weakPoints: value.weak_points.map((item) => ({ pointCode: item.point_code, studentCount: item.student_count })),
      rankingsSuppressed: value.rankings_suppressed,
    }
  },
}
