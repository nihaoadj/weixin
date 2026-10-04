import { describe, expect, it } from 'vitest'
import { readTeacherTestFixtures } from '@/test/demoTeacherTestFixtures'
import {
  archiveTeacherQuestionBankItem,
  getTeacherQuestionBankItem,
  importTeacherQuestionBankItem,
  listTeacherQuestionBank,
  updateTeacherQuestionBankItem,
} from '@/features/content/public'
import { saveSession } from '@/features/identity/public'
import {
  demoLearningRoutes,
  getDemoTeacherQuestionBankSource,
  readDemoTeacherClassroomRoutes,
} from '@/features/learning/infrastructure/demoLearningRoutes'

describe('Demo teacher question bank', () => {
  it('copies only an explicitly selected released route question and keeps bank edits isolated', async () => {
    saveSession({
      openid: 'demo_teacher',
      role: 'teacher',
      nickName: '演示教师',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    expect(await listTeacherQuestionBank({ status: 'active' })).toMatchObject({ items: [], total: 0 })
    const tests = await readTeacherTestFixtures({ demoLearningRoutes, readDemoTeacherClassroomRoutes }, 1)
    const releasedTest = tests.items.find((item) => item.reviewState === 'released')
    expect(releasedTest).toBeDefined()
    const selectedQuestion = releasedTest?.questions.find((question) => question.id !== null)
    if (!selectedQuestion?.id) throw new Error('发布的课堂测试没有可导入题目编号。')
    const source = await getDemoTeacherQuestionBankSource(selectedQuestion.id)
    const content = {
      taskType: source.taskType,
      title: source.title,
      prompt: source.prompt,
      options: [...source.options],
      answer: { ...source.answer },
      explanation: source.explanation,
      pointCodes: [...source.pointCodes],
      dimensionIds: [...source.dimensionIds],
    }
    const request = {
      ...content,
      sourceType: 'route_test_question' as const,
      sourceId: source.sourceId,
      sourceDigest: source.sourceDigest,
      clientRequestId: `bank-test-${source.sourceId}`,
      deidentified: true as const,
    }
    const imported = await importTeacherQuestionBankItem(request)
    expect(await importTeacherQuestionBankItem(request)).toMatchObject({ id: imported.id, version: 1 })
    await expect(
      importTeacherQuestionBankItem({ ...request, prompt: '同一请求标识不能覆盖题库副本。' }),
    ).rejects.toThrow('入库请求标识已用于其他题目')
    expect(imported.medicalReviewStatus).toBeNull()
    await expect(
      importTeacherQuestionBankItem({
        ...request,
        clientRequestId: `bank-private-${source.sourceId}`,
        prompt: '学生姓名：张同学的诊断',
      }),
    ).rejects.toThrow('去标识化')

    const active = await listTeacherQuestionBank({
      status: 'active',
      pointCode: source.pointCodes[0],
      taskType: source.taskType,
    })
    expect(active.items.map((item) => item.id)).toContain(imported.id)
    const edited = await updateTeacherQuestionBankItem(imported.id, imported.version, {
      ...content,
      prompt: `${content.prompt}（教师个人副本修订）`,
    })
    expect(edited).toMatchObject({ id: imported.id, version: 2, medicalReviewStatus: 'not_required' })
    await expect(updateTeacherQuestionBankItem(imported.id, imported.version, content)).rejects.toThrow(
      '题库版本已更新',
    )
    expect(await getDemoTeacherQuestionBankSource(source.sourceId)).toMatchObject({
      sourceDigest: source.sourceDigest,
      prompt: source.prompt,
      options: source.options,
    })

    const archived = await archiveTeacherQuestionBankItem(imported.id, edited.version, `archive-${imported.id}`)
    expect(archived.status).toBe('archived')
    expect((await listTeacherQuestionBank({ status: 'active' })).items).toHaveLength(0)
    expect((await listTeacherQuestionBank({ status: 'archived' })).items).toHaveLength(0)

    saveSession({
      openid: 'other-demo-teacher',
      role: 'teacher',
      nickName: '其他教师',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    expect((await listTeacherQuestionBank({ status: 'archived' })).items).toHaveLength(0)
    await expect(getTeacherQuestionBankItem(imported.id)).rejects.toThrow('个人题库题目不存在')
    await expect(updateTeacherQuestionBankItem(imported.id, archived.version, content)).rejects.toThrow(
      '个人题库题目不存在',
    )
    await expect(
      archiveTeacherQuestionBankItem(imported.id, archived.version, 'other-teacher-archive'),
    ).rejects.toThrow('个人题库题目不存在')
    await expect(importTeacherQuestionBankItem(request)).rejects.toThrow()
  })
})
