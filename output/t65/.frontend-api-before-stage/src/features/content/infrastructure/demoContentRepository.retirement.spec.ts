import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearSession, saveSession } from '@/features/identity/public'
import { clearApiCache } from '@/platform/http/apiClient'
import { respond } from '@/test/http'
import { DemoContentRepository } from './demoContentRepository'
import { ApiContentRepository } from './apiContentRepository'
import * as problems from './demoProblemStore'
import { demoSaveCaseDraft } from './demoCaseContentStore'
import { showcaseDraft } from './demoSeeds'

const login = (role: 'student' | 'teacher', permissions: string[] = []) =>
  saveSession({
    openid: `t63-${role}`,
    role,
    permissions,
    nickName: role,
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
  })
const card = {
  pointCode: 'pathology.inflammation.vascular',
  cardType: 'recall' as const,
  prompt: '教师补充卡',
  options: [],
  explanation: '解析',
  reference: '',
}
const oldQuestion = {
  id: 't63-old-question',
  type: '医学常识' as const,
  title: '历史问题',
  description: '保留的内容',
  target: 'all' as const,
  status: '已发布' as const,
  time: new Date(0).toISOString(),
}

afterEach(() => {
  clearApiCache()
  vi.unstubAllEnvs()
})

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

  it('checks authentication, teacher role and reviewer permissions before retired card responses', async () => {
    const repository = new DemoContentRepository()
    clearSession()
    await expect(repository.getKnowledgeCardContributions()).rejects.toMatchObject({
      code: 'AUTH_REQUIRED',
      statusCode: 401,
    })
    await expect(repository.createKnowledgeCardContribution(card)).rejects.toMatchObject({
      code: 'AUTH_REQUIRED',
      statusCode: 401,
    })
    login('student')
    expect(await repository.getKnowledgeCardContributions()).toEqual([])
    await expect(repository.createKnowledgeCardContribution(card)).rejects.toMatchObject({
      code: 'FORBIDDEN',
      statusCode: 403,
    })
    login('teacher')
    for (const action of [
      () => repository.getKnowledgeCardReviewQueue(),
      () => repository.reviewKnowledgeCardContribution(1, 'approved', ''),
      () => repository.disableKnowledgeCardContribution(1),
    ])
      await expect(action()).rejects.toMatchObject({ code: 'FORBIDDEN', statusCode: 403 })
    login('teacher', ['medical_review'])
    expect(await repository.getKnowledgeCardReviewQueue()).toEqual([])
    await expect(repository.reviewKnowledgeCardContribution(999, 'approved', '')).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
  })

  it('matches API retired card writes and empty active card lists', async () => {
    login('teacher', ['medical_review'])
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
    vi.mocked(uni.request).mockImplementation((options) => {
      respond(
        options,
        options.method === 'GET' ? [] : { detail: { code: 'RETIRED_FLOW', message: '流程已退役' } },
        options.method === 'GET' ? 200 : 409,
      )
      return undefined as never
    })
    for (const repository of [new DemoContentRepository(), new ApiContentRepository()]) {
      expect(await repository.getKnowledgeCardContributions()).toEqual([])
      expect(await repository.getKnowledgeCardReviewQueue()).toEqual([])
      for (const action of [
        () => repository.createKnowledgeCardContribution(card),
        () => repository.updateKnowledgeCardContribution(1, card),
        () => repository.submitKnowledgeCardContribution(1),
        () => repository.reviewKnowledgeCardContribution(1, 'approved', ''),
        () => repository.disableKnowledgeCardContribution(1),
      ])
        await expect(action()).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
    }
  })
})
