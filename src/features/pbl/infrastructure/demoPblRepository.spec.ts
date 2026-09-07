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
  it('uses one dialogue contract for direct and guided communication', async () => {
    ensureDemoData()
    const repository = new DemoPblRepository(new DemoContentRepository())
    login('student', 'demo_student')
    expect(await repository.classes()).toEqual([{ id: '1', name: '病理学演示班', code: 'demo-class' }])
    const input = {
      clientSessionId: 'direct-1',
      classId: '1',
      interactionStyle: 'direct' as const,
      goalPointCodes: ['pathology.inflammation.vascular'],
    }
    const created = await repository.createDialogue(input)
    expect((await repository.createDialogue(input)).session.id).toBe(created.session.id)
    expect(created.session.sessionKind).toBe('student_initiated')
    expect(created.participation?.interactionStyle).toBe('direct')
    await expect(repository.startDialogue(created.session.id, 'guided')).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
    })
    const first = await repository.message(created.session.id, '为什么会局部红肿？', 'direct-message-1')
    expect(first.diagnostic?.assistantReply).toContain('先说明')
    expect(first.diagnostic?.knowledgeGaps).toEqual([])
  })

  it('keeps message retries stable, adopts edited content and returns learning evidence to the teacher', async () => {
    ensureDemoData()
    const repository = new DemoPblRepository(new DemoContentRepository())
    login('student', 'demo_student')
    const first = await repository.message('demo-pbl-1', '合成问题', 'first')
    await repository.message('demo-pbl-1', '补充自己的解释', 'second')
    await repository.message('demo-pbl-1', '列出支持与反对证据及限制', 'third')
    await repository.message('demo-pbl-1', '整合机制、证据与剩余疑问', 'fourth')
    expect(await repository.message('demo-pbl-1', '合成问题', 'first')).toEqual(first)
    expect((await repository.report('demo-pbl-1')).status).toBe('awaiting_learning')
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
    for (const task of plan.tasks.filter((item) => item.status === 'pending')) {
      plan = await repository.submitTask(
        task.id,
        String(task.id),
        task.public_definition.options ? { selected_option: 0 } : { text: '形态与机制的依据' },
      )
    }
    expect(plan.verification_status).toBe('improved')
    const report = await repository.report('demo-pbl-1')
    expect(report.status).toBe('improved')
    expect(report.plans[0].evaluations).toHaveLength(1)
    expect((await repository.reports()).summary.statusCounts.improved).toBe(1)
    login('teacher', 'demo_teacher')
    expect((await repository.summary((await repository.active())[0])).objective_retest_count).toBe(1)
  })

  it('activates only the second-cycle variant and exhausts after a repeated failed retest', async () => {
    ensureDemoData()
    const repository = new DemoPblRepository(new DemoContentRepository())
    login('student', 'demo_student')
    for (const [index, content] of ['问题表征', '机制假设与不确定性', '支持反对证据与限制', '综合解释'].entries())
      await repository.message('demo-pbl-1', content, `cycle-${index}`)
    login('teacher', 'demo_teacher')
    const diagnostic = (await repository.diagnostics()).items[0]
    await repository.adopt(diagnostic.recommendedQuestions![0])
    login('student', 'demo_student')
    let plan = (await repository.plans())[0]
    const firstVariants = plan.tasks.filter((task) => task.cycle_number === 1).map((task) => task.variant_code)
    for (const task of plan.tasks.filter((item) => item.status === 'pending')) {
      plan = await repository.submitTask(
        task.id,
        `first-${task.id}`,
        task.public_definition.options
          ? { selected_option: task.task_type === 'retest' ? 1 : 0 }
          : { text: '首轮证据' },
      )
    }
    expect(plan.current_cycle).toBe(2)
    expect(plan.decision_basis.result).toBe('next_cycle_activated')
    const second = plan.tasks.filter((task) => task.cycle_number === 2 && task.status === 'pending')
    expect(second.some((task) => firstVariants.includes(task.variant_code))).toBe(false)
    for (const task of second) {
      plan = await repository.submitTask(
        task.id,
        `second-${task.id}`,
        task.public_definition.options
          ? { selected_option: task.task_type === 'retest' ? 1 : 0 }
          : { text: '第二轮证据' },
      )
    }
    expect(plan.verification_status).toBe('needs_reinforcement')
    expect(plan.automation_exhausted).toBe(true)
    expect(plan.decision_basis.offline_support_required).toBe(true)
    const report = await repository.report('demo-pbl-1')
    expect(report.status).toBe('support_needed')
    expect(report.plans[0].evaluations.map((item) => item.cycle_number)).toEqual([1, 2])
    expect(report.targetProgress[0].cycles.map((item) => item.passed)).toEqual([false, false])
  })
})
