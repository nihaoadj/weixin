import type { ClassroomRepository } from '@/features/classroom/domain/ports'
import type { TeacherClass, TeacherStudent } from '@/types/teacher'
import { AppError } from '@/types/errors'

export const demoClassroomRepository: ClassroomRepository = {
  async getTeacherClasses(): Promise<TeacherClass[]> {
    return []
  },
  async createTeacherClass(_name: string, _code: string): Promise<TeacherClass> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async updateTeacherClass(
    _classId: number,
    _payload: { name?: string; status?: 'active' | 'archived' },
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
}
