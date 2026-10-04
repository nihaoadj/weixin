import type { ClassroomRepository } from '@/features/classroom/domain/ports'
import {
  apiStudentActiveClassListSchema,
  apiTeacherClassListSchema,
  apiTeacherClassSchema,
  apiTeacherStudentListSchema,
} from '@/platform/contracts/teacher'
import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import type { StudentActiveClass, TeacherClass, TeacherStudent } from '@/types/teacher'

const LIST_TTL = 30_000

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

export const apiClassroomRepository: ClassroomRepository = {
  async getTeacherClasses(): Promise<TeacherClass[]> {
    return (await apiRequest({ path: '/classes', cacheTtlMs: LIST_TTL, schema: apiTeacherClassListSchema })).map(
      toClass,
    )
  },
  async createTeacherClass(name: string, code: string): Promise<TeacherClass> {
    return toClass(
      await apiRequest({
        path: '/classes',
        method: 'POST',
        body: { name, code },
        schema: apiTeacherClassSchema,
        invalidateCache: ['/classes', '/analytics'],
      }),
    )
  },
  async updateTeacherClass(
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
  },
  async getClassStudents(classId: number): Promise<TeacherStudent[]> {
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
  },
  async addStudentToClass(classId: number, studentExternalId: string): Promise<void> {
    await apiRequest({
      path: `/classes/${encodePathSegment(classId)}/members`,
      method: 'POST',
      body: { student_external_id: studentExternalId },
      invalidateCache: ['/classes', '/analytics'],
    })
  },
  async removeStudentFromClass(classId: number, studentId: number): Promise<void> {
    await apiRequest({
      path: `/classes/${encodePathSegment(classId)}/members/${encodePathSegment(studentId)}`,
      method: 'DELETE',
      invalidateCache: ['/classes', '/analytics'],
    })
  },
  async getStudentActiveClasses(): Promise<StudentActiveClass[]> {
    return apiRequest({
      path: '/classes/my-active',
      cacheTtlMs: LIST_TTL,
      schema: apiStudentActiveClassListSchema,
    })
  },
}
