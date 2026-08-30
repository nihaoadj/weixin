import { apiRequest, isRemoteApiEnabled } from '@/services/apiClient'
import {
  decideGuidedCaseReviewAsync,
  getMedicalReviewQueueAsync,
  getMedicalReviewViewAsync,
  submitGuidedCaseForReviewAsync,
} from '@/services/caseRepositoryAsync'
import type { MedicalReviewView } from '@/services/caseRepositoryAsync'
import type { Problem } from '@/types/domain'

export interface TeacherClass {
  id: number
  name: string
  code: string
  status: string
  teacherId: number
  createdAt?: string
}

export interface TeacherStudent {
  id: number
  nickname: string
  externalId: string
  joinedAt: string
}

export interface AnalyticsDimension {
  dimensionId: string
  label: string
  averageScore: number | null
  baselineScore?: number | null
  currentScore?: number | null
  delta?: number | null
  studentCount?: number
  rate?: number | null
}

export interface AnalyticsOverview {
  scope: { classId: number | null; className: string | null; dateFrom: string; dateTo: string }
  studentCount: number
  publishedCaseCount: number
  eligiblePairs: number
  startedPairs: number
  completedPairs: number
  completionRate: number | null
  currentAverageScore: number | null
  averageImprovement: number | null
  dimensions: AnalyticsDimension[]
  weakDimensions: AnalyticsDimension[]
  cases: Array<{ problemId: number; title: string; completed: number; assigned: number; averageScore: number | null }>
  students: Array<{
    studentId: number
    nickname: string
    completed: number
    assigned: number
    averageScore: number | null
  }>
}

export interface AnalyticsCase {
  problem: { id: number; title: string; version: number; slug?: string | null }
  eligiblePairs: number
  startedPairs: number
  completedPairs: number
  completionRate: number | null
  currentAverageScore: number | null
  averageImprovement: number | null
  averageDurationMinutes: number | null
  dimensions: AnalyticsDimension[]
  distribution: Record<string, number>
  students: Array<{
    studentId: number
    nickname: string
    status: string
    baseline: number | null
    current: number | null
    delta: number | null
    focusStage: string | null
    lastAssessedAt: string | null
  }>
}

export interface AnalyticsStudent {
  student: { id: number; nickname: string }
  assigned: number
  started: number
  completed: number
  completionRate: number | null
  currentAverageScore: number | null
  averageImprovement: number | null
  dimensions: AnalyticsDimension[]
  cases: Array<{
    problemId: number
    title: string
    version: number
    firstScore: number | null
    latestScore: number | null
    delta: number | null
    attemptCount: number
    focusStage: string | null
    lastAssessedAt: string | null
  }>
  timeline: Array<{ attemptId: number; problemId: number; score: number; assessedAt: string | null }>
  learningPlan: { id: number; status: string; targetDimensionIds: string[]; dueAt: string } | null
  practiceMastery: Record<string, { averageScore: number; attemptCount: number }>
}

const camel = <T>(value: unknown): T => {
  if (Array.isArray(value)) return value.map(camel) as T
  if (!value || typeof value !== 'object') return value as T
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, item]) => [
      key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase()),
      camel(item),
    ]),
  ) as T
}

export async function getTeacherClasses(): Promise<TeacherClass[]> {
  if (!isRemoteApiEnabled()) return []
  return camel<TeacherClass[]>(await apiRequest({ path: '/classes' }))
}

export async function createTeacherClass(name: string, code: string): Promise<TeacherClass> {
  return camel<TeacherClass>(await apiRequest({ path: '/classes', method: 'POST', body: { name, code } }))
}

export async function updateTeacherClass(
  classId: number,
  payload: { name?: string; status?: 'active' | 'archived' },
): Promise<TeacherClass> {
  return camel<TeacherClass>(await apiRequest({ path: `/classes/${classId}`, method: 'PATCH', body: payload }))
}

export async function getClassStudents(classId: number): Promise<TeacherStudent[]> {
  return camel<TeacherStudent[]>(await apiRequest({ path: `/classes/${classId}/students` }))
}

export async function addStudentToClass(classId: number, studentExternalId: string): Promise<void> {
  await apiRequest({
    path: `/classes/${classId}/members`,
    method: 'POST',
    body: { student_external_id: studentExternalId },
  })
}

export async function removeStudentFromClass(classId: number, studentId: number): Promise<void> {
  await apiRequest({ path: `/classes/${classId}/members/${studentId}`, method: 'DELETE' })
}

export async function getAnalyticsOverview(
  classId?: number,
  dateFrom?: string,
  dateTo?: string,
): Promise<AnalyticsOverview> {
  if (!isRemoteApiEnabled())
    return {
      scope: { classId: classId || null, className: null, dateFrom: dateFrom || '', dateTo: dateTo || '' },
      studentCount: 0,
      publishedCaseCount: 0,
      eligiblePairs: 0,
      startedPairs: 0,
      completedPairs: 0,
      completionRate: null,
      currentAverageScore: null,
      averageImprovement: null,
      dimensions: [],
      weakDimensions: [],
      cases: [],
      students: [],
    }
  const query = new URLSearchParams()
  if (classId) query.set('class_id', String(classId))
  if (dateFrom) query.set('date_from', dateFrom)
  if (dateTo) query.set('date_to', dateTo)
  return camel<AnalyticsOverview>(
    await apiRequest({ path: `/analytics/overview${query.toString() ? `?${query}` : ''}` }),
  )
}

export async function getReviewQueue(status = 'pending'): Promise<Problem[]> {
  return getMedicalReviewQueueAsync(status)
}

export async function getReviewView(problemId: string): Promise<MedicalReviewView | undefined> {
  return getMedicalReviewViewAsync(problemId)
}

export async function getAnalyticsCase(
  problemId: number,
  classId?: number,
  dateFrom?: string,
  dateTo?: string,
): Promise<AnalyticsCase> {
  if (!isRemoteApiEnabled())
    return {
      problem: { id: problemId, title: '', version: 1 },
      eligiblePairs: 0,
      startedPairs: 0,
      completedPairs: 0,
      completionRate: null,
      currentAverageScore: null,
      averageImprovement: null,
      averageDurationMinutes: null,
      dimensions: [],
      distribution: {},
      students: [],
    }
  const query = new URLSearchParams()
  if (classId) query.set('class_id', String(classId))
  if (dateFrom) query.set('date_from', dateFrom)
  if (dateTo) query.set('date_to', dateTo)
  return camel<AnalyticsCase>(
    await apiRequest({ path: `/analytics/cases/${problemId}${query.toString() ? `?${query}` : ''}` }),
  )
}

export async function getAnalyticsStudent(
  studentId: number,
  classId?: number,
  dateFrom?: string,
  dateTo?: string,
): Promise<AnalyticsStudent> {
  if (!isRemoteApiEnabled())
    return {
      student: { id: studentId, nickname: '' },
      assigned: 0,
      started: 0,
      completed: 0,
      completionRate: null,
      currentAverageScore: null,
      averageImprovement: null,
      dimensions: [],
      cases: [],
      timeline: [],
      learningPlan: null,
      practiceMastery: {},
    }
  const query = new URLSearchParams()
  if (classId) query.set('class_id', String(classId))
  if (dateFrom) query.set('date_from', dateFrom)
  if (dateTo) query.set('date_to', dateTo)
  return camel<AnalyticsStudent>(
    await apiRequest({ path: `/analytics/students/${studentId}${query.toString() ? `?${query}` : ''}` }),
  )
}

export async function submitMedicalReview(
  problemId: string,
  decision: 'approved' | 'rejected',
  comment: string,
): Promise<Problem> {
  const result = await decideGuidedCaseReviewAsync(problemId, decision, comment)
  if (!result) throw new Error('病例不存在')
  return result
}

export async function submitCaseForMedicalReview(problemId: string): Promise<Problem> {
  const result = await submitGuidedCaseForReviewAsync(problemId)
  if (!result) throw new Error('病例不存在')
  return result
}
