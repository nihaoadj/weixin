import { describe, expect, it } from 'vitest'
import { saveSession } from '@/features/identity/public'
import { DemoContentRepository } from './demoContentRepository'
import * as problems from './demoProblemStore'
import { demoSaveCaseDraft } from './demoCaseContentStore'
import { showcaseDraft } from './demoSeeds'

const login = (role: 'student' | 'teacher') =>
  saveSession({
    openid: `t63-${role}`,
    role,
    nickName: role,
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
  })
const oldQuestion = {
  id: 't63-old-question',
  type: '医学常识' as const,
  title: '历史问题',
  description: '保留的内容',
  target: 'all' as const,
  status: '已发布' as const,
  time: new Date(0).toISOString(),
}

describe('T63 Demo content retirement', () => {
  it('preserves historical records while projecting only real guided cases', async () => {
    login('teacher')
    problems.claimProblemOwner(oldQuestion.id)
    problems.upsertProblem(oldQuestion)
    const before = problems.getProblems()
    const ownCase = demoSaveCaseDraft({ ...showcaseDraft, title: 'T63病例草稿' }, 't63-guided-draft')
    const repository = new DemoContentRepository()
    const active = await repository.getProblems()
    expect(active.every((item) => item.contentType === 'guided_case')).toBe(true)
    expect(active.filter((item) => item.id === ownCase.id)).toHaveLength(1)
    expect(active.find((item) => item.id === ownCase.id)?.allowedActions).toEqual(['edit', 'delete'])
    expect(await repository.findProblem(oldQuestion.id)).toBeUndefined()
    for (const action of [
      () => repository.saveProblems([]),
      () => repository.upsertProblem({ ...oldQuestion, status: 'draft' as const }),
      () => repository.publishProblem(oldQuestion.id),
      () => repository.publishGuidedCaseAsync(oldQuestion.id),
      () => repository.rejectProblem(oldQuestion.id),
      () => repository.resetProblems(),
    ])
      await expect(action()).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
    expect(problems.getProblems()).toEqual(before)
    await expect(repository.publishProblem(ownCase.id)).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
    await expect(repository.rejectProblem(ownCase.id)).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
    login('student')
    expect(await repository.findProblem(ownCase.id)).toMatchObject({ status: 'published' })
    expect((await repository.getProblems()).length).toBeGreaterThan(0)
    expect(problems.getProblems()).toEqual(before)
  })
})
