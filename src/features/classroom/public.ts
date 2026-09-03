import { getApplicationServices } from '@/bootstrap/wiring'

const classroom = () => getApplicationServices().classroom

export const getTeacherClasses = () => classroom().getTeacherClasses()
export const createTeacherClass = (name: string, code: string) => classroom().createTeacherClass(name, code)
export const updateTeacherClass = (classId: number, payload: { name?: string; status?: 'active' | 'archived' }) =>
  classroom().updateTeacherClass(classId, payload)
export const getClassStudents = (classId: number) => classroom().getClassStudents(classId)
export const addStudentToClass = (classId: number, studentExternalId: string) =>
  classroom().addStudentToClass(classId, studentExternalId)
export const removeStudentFromClass = (classId: number, studentId: number) =>
  classroom().removeStudentFromClass(classId, studentId)

export type { TeacherClass, TeacherStudent } from '@/types/teacher'
