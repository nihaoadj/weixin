import type { AnalyticsCase, AnalyticsOverview, AnalyticsStudent, TeacherClass, TeacherStudent } from '@/types/teacher'
import type { Problem } from '@/types/records'
import type { MedicalReviewRecord as MedicalReviewView } from '@/types/review'

export interface TeacherRepository {
  getTeacherClasses(): Promise<TeacherClass[]>
  createTeacherClass(name: string, code: string): Promise<TeacherClass>
  updateTeacherClass(classId: number, payload: { name?: string; status?: 'active' | 'archived' }): Promise<TeacherClass>
  getClassStudents(classId: number): Promise<TeacherStudent[]>
  addStudentToClass(classId: number, studentExternalId: string): Promise<void>
  removeStudentFromClass(classId: number, studentId: number): Promise<void>
  getAnalyticsOverview(classId?: number, dateFrom?: string, dateTo?: string): Promise<AnalyticsOverview>
  getReviewQueue(status?: string): Promise<Problem[]>
  getReviewView(problemId: string): Promise<MedicalReviewView | undefined>
  getAnalyticsCase(problemId: number, classId?: number, dateFrom?: string, dateTo?: string): Promise<AnalyticsCase>
  getAnalyticsStudent(
    studentId: number,
    classId?: number,
    dateFrom?: string,
    dateTo?: string,
  ): Promise<AnalyticsStudent>
  submitMedicalReview(problemId: string, decision: 'approved' | 'rejected', comment: string): Promise<Problem>
  submitCaseForMedicalReview(problemId: string): Promise<Problem>
}
