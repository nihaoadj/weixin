import type { ClassroomRepository } from '@/features/classroom/domain/ports'
import type { TeacherClass, TeacherStudent } from '@/types/teacher'
import { AppError } from '@/types/errors'

export const demoClassroomRepository: ClassroomRepository = {
  async getTeacherClasses(): Promise<TeacherClass[]> {
    return [{ id: 1, name: '病理学演示班', code: 'demo_class_1', status: 'active', teacherId: 1 }]
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
    return _classId === 1 ? ['demo_student', 'demo_student_b'].map((externalId, index) => ({
      id: index + 1, externalId, nickname: index ? '演示学生（二）' : '演示学生', joinedAt: new Date(0).toISOString(),
    })) : []
  },
  async addStudentToClass(_classId: number, _studentExternalId: string): Promise<void> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async removeStudentFromClass(_classId: number, _studentId: number): Promise<void> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
}
