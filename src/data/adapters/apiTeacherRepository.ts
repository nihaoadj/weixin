import { ApiCaseRepository } from './apiCaseRepository'
import {
  apiAnalyticsCaseSchema,
  apiAnalyticsDimensionSchema,
  apiAnalyticsOverviewSchema,
  apiAnalyticsStudentSchema,
  apiTeacherClassListSchema,
  apiTeacherClassSchema,
  apiTeacherStudentListSchema,
} from '@/data/contracts/teacher'
import type { MedicalReviewRecord as MedicalReviewView } from '@/types/review'
import { apiRequest, encodePathSegment } from '@/services/apiClient'
import type { Problem } from '@/types/records'
import type {
  AnalyticsCase,
  AnalyticsDimension,
  AnalyticsOverview,
  AnalyticsStudent,
  TeacherClass,
  TeacherStudent,
} from '@/types/teacher'
const caseRepository = new ApiCaseRepository()

const LIST_TTL = 30_000
const ANALYTICS_TTL = 60_000

function toClass(value: ReturnType<typeof apiTeacherClassSchema.parse>): TeacherClass {
  return {
    id: value.id,
    name: value.name,
    code: value.code,
    status: value.status,
    teacherId: value.teacher_id,
    createdAt: value.created_at,
  }
}

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

export async function getTeacherClasses(): Promise<TeacherClass[]> {
  const values = await apiRequest({
    path: '/classes',
    cacheTtlMs: LIST_TTL,
    schema: apiTeacherClassListSchema,
  })
  return values.map(toClass)
}

export async function createTeacherClass(name: string, code: string): Promise<TeacherClass> {
  return toClass(
    await apiRequest({
      path: '/classes',
      method: 'POST',
      body: { name, code },
      schema: apiTeacherClassSchema,
      invalidateCache: ['/classes', '/analytics'],
    }),
  )
}

export async function updateTeacherClass(
  classId: number,
  payload: { name?: string; status?: 'active' | 'archived' },
): Promise<TeacherClass> {
  return toClass(
    await apiRequest({
      path: `/classes/${encodePathSegment(classId)}`,
      method: 'PATCH',
      body: payload,
      schema: apiTeacherClassSchema,
      invalidateCache: ['/classes', '/analytics'],
    }),
  )
}

export async function getClassStudents(classId: number): Promise<TeacherStudent[]> {
  const values = await apiRequest({
    path: `/classes/${encodePathSegment(classId)}/students`,
    cacheTtlMs: LIST_TTL,
    schema: apiTeacherStudentListSchema,
  })
  return values.map((value) => ({
    id: value.id,
    nickname: value.nickname,
    externalId: value.external_id,
    joinedAt: value.joined_at,
  }))
}

export async function addStudentToClass(classId: number, studentExternalId: string): Promise<void> {
  await apiRequest({
    path: `/classes/${encodePathSegment(classId)}/members`,
    method: 'POST',
    body: { student_external_id: studentExternalId },
    invalidateCache: ['/classes', '/analytics'],
  })
}

export async function removeStudentFromClass(classId: number, studentId: number): Promise<void> {
  await apiRequest({
    path: `/classes/${encodePathSegment(classId)}/members/${encodePathSegment(studentId)}`,
    method: 'DELETE',
    invalidateCache: ['/classes', '/analytics'],
  })
}

export async function getAnalyticsOverview(
  classId?: number,
  dateFrom?: string,
  dateTo?: string,
): Promise<AnalyticsOverview> {
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
}

export async function getReviewQueue(status = 'pending'): Promise<Problem[]> {
  return caseRepository.getMedicalReviewQueueAsync(status)
}

export async function getReviewView(problemId: string): Promise<MedicalReviewView | undefined> {
  return caseRepository.getMedicalReviewViewAsync(problemId)
}

export async function getAnalyticsCase(
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
}

export async function getAnalyticsStudent(
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
}

export async function submitMedicalReview(
  problemId: string,
  decision: 'approved' | 'rejected',
  comment: string,
): Promise<Problem> {
  const result = await caseRepository.decideGuidedCaseReviewAsync(problemId, decision, comment)
  if (!result) throw new Error('病例不存在')
  return result
}

export async function submitCaseForMedicalReview(problemId: string): Promise<Problem> {
  const result = await caseRepository.submitGuidedCaseForReviewAsync(problemId)
  if (!result) throw new Error('病例不存在')
  return result
}

import type { TeacherRepository } from '@/data/repositories/teacher'
export const apiTeacherRepository: TeacherRepository = {
  getTeacherClasses,
  createTeacherClass,
  updateTeacherClass,
  getClassStudents,
  addStudentToClass,
  removeStudentFromClass,
  getAnalyticsOverview,
  getReviewQueue,
  getReviewView,
  getAnalyticsCase,
  getAnalyticsStudent,
  submitMedicalReview,
  submitCaseForMedicalReview,
}
