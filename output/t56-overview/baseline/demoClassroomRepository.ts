import type { ClassroomRepository } from '@/features/classroom/domain/ports'
import type { StudentActiveClass, TeacherClass, TeacherStudent } from '@/types/teacher'
import { AppError } from '@/types/errors'

let referenceStudents: TeacherStudent[] = []
export function configureDemoReferenceStudents(
  students: Array<{ studentId: number; openid: string; name: string }>,
): void {
  referenceStudents = students.map((student) => ({
    id: student.studentId,
    externalId: student.openid,
    nickname: student.name,
    joinedAt: '2026-10-02T00:00:00Z',
  }))
}

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
    return _classId === 1
      ? [
          ...['demo_student', 'demo_student_b'].map((externalId, index) => ({
            id: index + 1,
            externalId,
            nickname: index ? '演示学生（二）' : '演示学生',
            joinedAt: new Date(0).toISOString(),
          })),
          ...referenceStudents,
        ]
      : []
  },
  async addStudentToClass(_classId: number, _studentExternalId: string): Promise<void> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async removeStudentFromClass(_classId: number, _studentId: number): Promise<void> {
    throw new AppError('该操作仅在 API 模式可用', { code: 'UNSUPPORTED_OPERATION' })
  },
  async getStudentActiveClasses(): Promise<StudentActiveClass[]> {
    return demoStudentClassesProvider()
  },
}

// Demo membership mirrors the API contract: the default experience is one
// active class; tests can override through this provider for 0/multi states
// without changing the shipped demo data.
let studentClassesProvider: () => Promise<StudentActiveClass[]> = async () => [
  { id: 1, name: '病理学演示班', code: 'demo_class_1' },
]

function demoStudentClassesProvider(): Promise<StudentActiveClass[]> {
  return studentClassesProvider()
}

export function configureDemoStudentClasses(provider: () => Promise<StudentActiveClass[]>): void {
  studentClassesProvider = provider
}
