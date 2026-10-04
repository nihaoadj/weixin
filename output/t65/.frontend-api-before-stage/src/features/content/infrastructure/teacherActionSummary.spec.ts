import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiContentRepository } from './apiContentRepository'
import { DemoContentRepository } from './demoContentRepository'
import { teacherContentActionSummarySchema } from '@/platform/contracts/contentActions'
import { saveSession } from '@/features/identity/public'
import { demoSaveCaseDraft } from './demoCaseContentStore'
import { showcaseDraft } from './demoSeeds'
import { claimProblemOwner, upsertProblem } from './demoProblemStore'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/platform/http/apiClient', async (original) => ({
  ...(await original<typeof import('@/platform/http/apiClient')>()),
  apiRequest: request,
}))
const user = (openid: string, permissions: 'medical_review'[] = []) =>
  saveSession({
    openid,
    role: 'teacher',
    nickName: openid,
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
    permissions,
  })
const cardInput = {
  pointCode: 'pathology.inflammation.vascular',
  cardType: 'recall' as const,
  prompt: '知识说明',
  options: [],
  explanation: '机制解释',
  reference: '',
}
const problem = (id: string) => ({
  id,
  type: '医学常识' as const,
  title: '讨论问题',
  description: 'PRIVATE_BODY',
  status: 'draft' as const,
  target: 'all' as const,
  time: new Date(0).toISOString(),
})

describe('Content action summary', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('strictly maps counts without caching or downloading resource bodies', async () => {
    const payload = {
      cases_draft: 2,
      cases_rejected: 1,
      cases_approved: 0,
      questions_draft: 3,
      questions_rejected: 0,
      cards_draft: 4,
      cards_rejected: 0,
      medical_cases_pending: null,
      medical_cards_pending: null,
      as_of: '2026-10-01T00:00:00Z',
    }
    request.mockResolvedValue(payload)
    const value = await new ApiContentRepository().getTeacherContentActionSummary()
    expect(value).toMatchObject({ casesDraft: 2, questionsDraft: 3, cardsDraft: 4, medicalCasesPending: null })
    expect(request).toHaveBeenCalledWith({
      path: '/problems/teacher-action-summary',
      schema: teacherContentActionSummarySchema,
      cacheTtlMs: 0,
    })
    expect(teacherContentActionSummarySchema.safeParse({ ...payload, questions_draft: -1 }).success).toBe(false)
    expect(teacherContentActionSummarySchema.safeParse({ ...payload, prompt: 'PRIVATE_BODY' }).success).toBe(false)
    request.mockRejectedValueOnce(new Error('NETWORK_ERROR'))
    await expect(new ApiContentRepository().getTeacherContentActionSummary()).rejects.toThrow('NETWORK_ERROR')
  })

  it('maps server resource actions and rejects unknown permission hints', async () => {
    const payload = {
      id: 12,
      type: '讨论问题',
      title: '问题',
      target: 'all',
      target_label: '全体学生',
      status: 'draft',
      created_at: '2026-10-01T00:00:00Z',
    }
    request.mockResolvedValue([{ ...payload, allowed_actions: ['edit', 'publish'] }])
    const repository = new ApiContentRepository()
    expect((await repository.getProblems())[0].allowedActions).toEqual(['edit', 'publish'])
    request.mockResolvedValue([payload])
    expect((await repository.getProblems())[0].allowedActions).toEqual([])
    request.mockResolvedValue([{ ...payload, allowed_actions: ['delete_all'] }])
    await expect(repository.getProblems()).rejects.toThrow()
  })

  it('keeps case actions while retired questions and cards have zero active counts', async () => {
    const repository = new DemoContentRepository()
    user('summary-owner')
    claimProblemOwner('summary-own-question')
    upsertProblem({ ...problem('summary-own-question'), status: '待审核' })
    upsertProblem({ ...problem('unclaimed'), status: '待审核' })
    await expect(repository.createKnowledgeCardContribution(cardInput)).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
    const ownCase = demoSaveCaseDraft({ ...showcaseDraft, title: '本人病例' })
    expect((await repository.getProblems()).some((item) => item.id === 'summary-own-question')).toBe(false)
    expect((await repository.getProblems()).find((item) => item.id === ownCase.id)?.allowedActions).toEqual([
      'edit',
      'delete',
    ])
    expect(await repository.getTeacherContentActionSummary()).toMatchObject({
      questionsDraft: 0,
      questionsRejected: 0,
      cardsDraft: 0,
      cardsRejected: 0,
      casesDraft: 0,
      medicalCasesPending: null,
      medicalCardsPending: null,
    })
    expect(await repository.getTeacherContentActionSummary()).toMatchObject({ casesDraft: 0 })
    user('summary-other')
    expect((await repository.getGuidedCasesAsync()).find((item) => item.id === ownCase.id)?.allowedActions).toEqual([])
    await expect(repository.publishProblem('summary-own-question')).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    user('summary-reviewer', ['medical_review'])
    expect(await repository.getTeacherContentActionSummary()).toMatchObject({
      medicalCasesPending: 0,
      medicalCardsPending: 0,
    })
    user('summary-owner', ['medical_review'])
    expect(await repository.getTeacherContentActionSummary()).toMatchObject({
      medicalCasesPending: 0,
      medicalCardsPending: 0,
    })
  })
})
