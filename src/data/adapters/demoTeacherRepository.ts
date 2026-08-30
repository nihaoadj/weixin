import { DemoCaseRepository } from './demoCaseRepository'
import type { AnalyticsCase, AnalyticsOverview, AnalyticsStudent, TeacherClass, TeacherStudent } from '@/types/teacher'
import type { Problem } from '@/types/records'
import type { MedicalReviewRecord as MedicalReviewView } from '@/types/review'
import { AppError } from '@/types/errors'
import type { TeacherRepository } from '@/data/repositories/teacher'
const caseRepository = new DemoCaseRepository()

export const demoTeacherRepository: TeacherRepository = {
  async getTeacherClasses(): Promise<TeacherClass[]> {
    return []
  },
  async createTeacherClass(_name: string, _code: string): Promise<TeacherClass> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async updateTeacherClass(
    _classId: number,
    _payload: { _name?: string; status?: 'active' | 'archived' },
  ): Promise<TeacherClass> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async getClassStudents(_classId: number): Promise<TeacherStudent[]> {
    return []
  },
  async addStudentToClass(_classId: number, _studentExternalId: string): Promise<void> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async removeStudentFromClass(_classId: number, _studentId: number): Promise<void> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async getAnalyticsOverview(classId?: number, dateFrom?: string, dateTo?: string): Promise<AnalyticsOverview> {
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
  },
  async getReviewQueue(status = 'pending'): Promise<Problem[]> {
    return caseRepository.getMedicalReviewQueueAsync(status)
  },
  async getReviewView(problemId: string): Promise<MedicalReviewView | undefined> {
    return caseRepository.getMedicalReviewViewAsync(problemId)
  },
  async getAnalyticsCase(
    problemId: number,
    _classId?: number,
    _dateFrom?: string,
    _dateTo?: string,
  ): Promise<AnalyticsCase> {
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
  },
  async getAnalyticsStudent(
    studentId: number,
    _classId?: number,
    _dateFrom?: string,
    _dateTo?: string,
  ): Promise<AnalyticsStudent> {
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
  },
  async submitMedicalReview(problemId: string, decision: 'approved' | 'rejected', comment: string): Promise<Problem> {
    const result = await caseRepository.decideGuidedCaseReviewAsync(problemId, decision, comment)
    if (!result) throw new Error('病例不存在')
    return result
  },
  async submitCaseForMedicalReview(problemId: string): Promise<Problem> {
    const result = await caseRepository.submitGuidedCaseForReviewAsync(problemId)
    if (!result) throw new Error('病例不存在')
    return result
  },
}
