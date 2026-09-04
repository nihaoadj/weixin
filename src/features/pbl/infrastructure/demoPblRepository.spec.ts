import { describe, expect, it } from 'vitest'
import { DemoPblRepository } from './demoPblRepository'
import { saveSession } from '@/features/identity/public'
import { ensureDemoData } from '@/features/qa/public'
import { findProblemAsync } from '@/features/content/public'
import { DemoContentRepository } from '@/features/content/infrastructure/demoContentRepository'

const login = (role: 'student' | 'teacher', openid: string) =>
  saveSession({
    role,
    openid,
    nickName: openid,
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
    classIds: ['demo_class_1'],
  })
describe('PBL Demo contract', () => {
  it('keeps message retries stable, adopts edited content and returns learning evidence to the teacher', async () => {
    ensureDemoData()
    const repository = new DemoPblRepository(new DemoContentRepository())
    login('student', 'demo_student')
    const first = await repository.message('demo-pbl-1', '合成问题', 'first')
    await repository.message('demo-pbl-1', '补充自己的解释', 'second')
    expect(await repository.message('demo-pbl-1', '合成问题', 'first')).toEqual(first)
    login('teacher', 'demo_teacher')
    const diagnostic = (await repository.diagnostics()).items[0]
    const suggestion = { ...diagnostic.recommendedQuestions![0], title: '当前编辑标题' }
    const published = await repository.adopt(suggestion)
    expect(await repository.adopt(suggestion)).toEqual(published)
    expect((await findProblemAsync(published.problemId!))?.title).toBe('当前编辑标题')
    login('student', 'demo_student_b')
    expect(await repository.plans()).toEqual([])
    login('student', 'demo_student')
    let plan = (await repository.plans())[0]
    for (const task of plan.tasks) {
      plan = await repository.submitTask(
        task.id,
        String(task.id),
        task.public_definition.options ? { selected_option: 0 } : { text: '形态与机制的依据' },
      )
    }
    expect(plan.verification_status).toBe('pending_teacher')
    login('teacher', 'demo_teacher')
    expect((await repository.verify(plan, 'improved', '依据已核对')).verification_status).toBe('improved')
    expect((await repository.summary((await repository.active())[0])).objective_retest_count).toBe(1)
    await expect(repository.verify(plan, 'improved', '重复')).rejects.toThrow()
  })
})
