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
/** 兼容旧班级页的学生班级读取；T30 不再用于问答总结或自主 PBL 提交。 */
export const getStudentActiveClasses = () => classroom().getStudentActiveClasses()

export type { TeacherClass, TeacherStudent, StudentActiveClass } from '@/types/teacher'
