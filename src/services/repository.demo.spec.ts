import { describe, expect, it } from 'vitest'
import { ensureDemoData, getConversations, getReports, saveSession } from './repository'

const student = {
  openid: 'demo_student',
  role: 'student' as const,
  nickName: '示例学生',
  avatarUrl: '',
  classIds: ['demo_class_1'],
  createdAt: new Date(0).toISOString(),
}

const teacher = {
  openid: 'demo_teacher',
  role: 'teacher' as const,
  nickName: '示例教师',
  avatarUrl: '',
  createdAt: new Date(0).toISOString(),
}

describe('demo data', () => {
  it('provides the seeded student conversation and teacher report without duplication', () => {
    ensureDemoData()
    ensureDemoData()

    saveSession(student)
    expect(getConversations()).toHaveLength(1)
    expect(getReports()).toHaveLength(1)

    saveSession(teacher)
    expect(getReports()).toHaveLength(1)
    expect(getReports()[0]?.status).toBe('待批阅')
  })
})
