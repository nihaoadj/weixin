import type { StudentActiveClass, TeacherClass, TeacherStudent } from '@/types/teacher'

export interface ClassroomRepository {
  getTeacherClasses(): Promise<TeacherClass[]>
  createTeacherClass(name: string, code: string): Promise<TeacherClass>
  updateTeacherClass(classId: number, payload: { name?: string; status?: 'active' | 'archived' }): Promise<TeacherClass>
  getClassStudents(classId: number): Promise<TeacherStudent[]>
  addStudentToClass(classId: number, studentExternalId: string): Promise<void>
  removeStudentFromClass(classId: number, studentId: number): Promise<void>
  /** The signed-in student's own active classes; server-verified membership. */
  getStudentActiveClasses(): Promise<StudentActiveClass[]>
}
