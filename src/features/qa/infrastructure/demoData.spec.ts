import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { storage, storageKeys } from '@/platform/storage/storage'
import { ensureDemoData, getConversationsAsync } from '@/features/qa/public'
import { findReportByConversationAsync } from '@/features/reports/public'
import { saveSession } from '@/features/identity/public'

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
  it('provides the seeded student conversations and retained history without duplication', async () => {
    ensureDemoData()
    ensureDemoData()

    saveSession(student)
    // Reports are retained only as private, read-only student history.
    expect(await getConversationsAsync()).toHaveLength(2)
    expect((await findReportByConversationAsync('pathology-demo-conversation-v2'))?.status).toBe('待批阅')
    expect((await findReportByConversationAsync('pathology-demo-draft-conversation'))?.status).toBe('草稿')

    saveSession(teacher)
    await expect(findReportByConversationAsync('pathology-demo-conversation-v2')).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
  })
})

describe('legacy report migration ownership', () => {
  beforeEach(() => {
    for (const key of [
      storageKeys.reports,
      storageKeys.conversations,
      storageKeys.schemaVersion,
      storageKeys.user,
      storageKeys.openid,
      storageKeys.role,
    ]) {
      storage.remove(key)
    }
  })

  afterEach(() => {
    for (const key of [storageKeys.reports, storageKeys.conversations, storageKeys.schemaVersion]) {
      storage.remove(key)
    }
  })

  function legacyReport(conversationId: string) {
    return {
      conversationId,
      messages: [{ id: 'm1', role: 'user', content: '问题', timestamp: new Date(0).toISOString() }],
      analysis: { errors: [], score: 80, summary: '小结' },
      createdAt: new Date(0).toISOString(),
      studentName: '旧学生',
      status: '待批阅',
    }
  }

  it('claims ownerless reports only when their conversation belongs to the migrating user', async () => {
    // 学生 A 的作用域会话：迁移时会以此为归属判定依据。
    uni.setStorageSync(`${storageKeys.conversations}:${encodeURIComponent('student-a')}`, [
      {
        conversationId: 'conv-a',
        messages: [],
        createdAt: new Date(0).toISOString(),
        updatedAt: new Date(0).toISOString(),
      },
    ])
    // 旧版全局无主报告：conv-a 属于学生 A，conv-b 属于其他学生。
    uni.setStorageSync(storageKeys.reports, [legacyReport('conv-a'), legacyReport('conv-b')])
    storage.remove(storageKeys.schemaVersion)

    saveSession({
      openid: 'student-a',
      role: 'student',
      nickName: '学生A',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })

    // Historical reports remain private to the student whose conversation
    // uniquely proves ownership; unrelated legacy records stay hidden.
    await expect(findReportByConversationAsync('conv-a')).resolves.toMatchObject({
      conversationId: 'conv-a',
      studentId: 'student-a',
    })
    await expect(findReportByConversationAsync('conv-b')).resolves.toBeUndefined()
  })
})
