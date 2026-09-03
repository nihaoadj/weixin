import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { storage, storageKeys } from '@/platform/storage/storage'
import { ensureDemoData, getConversationsAsync } from '@/features/qa/public'
import { getReportsAsync } from '@/features/reports/public'
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
  it('provides the seeded student conversation and teacher report without duplication', async () => {
    ensureDemoData()
    ensureDemoData()

    saveSession(student)
    expect(await getConversationsAsync()).toHaveLength(1)
    expect(await getReportsAsync()).toHaveLength(1)

    saveSession(teacher)
    expect(await getReportsAsync()).toHaveLength(1)
    expect((await getReportsAsync())[0]?.status).toBe('待批阅')
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

    // conv-a 的报告被学生 A 认领；conv-b 无法归属，不得串到 A 名下。
    const reports = await getReportsAsync()
    expect(reports).toHaveLength(1)
    expect(reports[0]?.conversationId).toBe('conv-a')
    expect(reports[0]?.studentId).toBe('student-a')
  })
})
