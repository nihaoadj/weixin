import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearSession, saveSession } from '@/features/identity/public'
import { clearApiCache } from '@/platform/http/apiClient'
import { storage, storageKeys } from '@/platform/storage/storage'
import { DemoContentRepository, configureDemoTeacherQuestionBankSource } from './demoContentRepository'
import { ApiContentRepository } from './apiContentRepository'
import { showcaseDraft } from './demoSeeds'
import { DemoPblRepository } from '@/features/pbl/infrastructure/demoPblRepository'
import { demoComplete, demoMessage, demoStart, demoSubmit } from '@/features/training/infrastructure/demoCaseStore'
import { deleteGuidedCaseAsync, saveGuidedCaseAsync } from '../public'
import type { StageAnswer } from '@/types/case'

const login = (openid: string, role: 'teacher' | 'student' = 'teacher') =>
  saveSession({ openid, role, nickName: openid, avatarUrl: '', createdAt: new Date(0).toISOString() })
const source = {
  sourceType: 'route_test_question' as const,
  sourceId: '94444444-4444-4444-8444-444444444444',
  sourceDigest: 'e'.repeat(64),
  taskType: 'retest' as const,
  title: '炎症机制',
  prompt: '何者促进液体外渗？',
  options: ['通透性增加', '通透性降低'],
  answer: { correct_option: 0 },
  explanation: '通透性增加促进外渗。',
  pointCodes: ['pathology.inflammation.vascular'],
  dimensionIds: [],
}
const bankInput = (clientRequestId: string) => ({ ...source, clientRequestId, deidentified: true as const })

afterEach(() => {
  vi.unstubAllEnvs()
  clearApiCache()
  vi.restoreAllMocks()
})

describe('T64 direct maintenance and deletion', () => {
  it('sends explicit knowledge bindings and omits them for legacy edits that preserve server bindings', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://t64.example.test')
    login('t64-api-binding')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({
        statusCode: 200,
        data: {
          id: 71,
          type: '病例分析',
          title: showcaseDraft.title,
          description: showcaseDraft.description,
          target: 'all',
          target_label: '全体学生',
          status: 'published',
          content_type: 'guided_case',
          created_at: new Date(0).toISOString(),
          medical_review_status: 'not_required',
        },
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
      return undefined as never
    })
    const repository = new ApiContentRepository()
    const codes = ['pathology.cell-injury.adaptation']
    await repository.saveGuidedCaseAsync(showcaseDraft, undefined, { knowledgePointCodes: codes })
    expect(uni.request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        url: 'https://t64.example.test/problems',
        method: 'POST',
        data: expect.objectContaining({ knowledge_point_codes: codes }),
      }),
    )
    await repository.saveGuidedCaseAsync(showcaseDraft, '71')
    const payload = vi.mocked(uni.request).mock.calls.at(-1)?.[0].data
    expect(payload).not.toHaveProperty('knowledge_point_codes')
  })
  it('uses real 204 DELETE requests with encoded ids, revision receipts and no response DTO parsing', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://t64.example.test')
    login('t64-api')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({ statusCode: 204, data: '', header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })
    const repository = new ApiContentRepository()
    await expect(repository.deleteGuidedCaseAsync('case/a')).resolves.toBeUndefined()
    expect(uni.request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        url: 'https://t64.example.test/problems/case%2Fa',
        method: 'DELETE',
      }),
    )
    await expect(repository.deleteTeacherQuestionBankItem(17, 3, 'delete-17-v3')).resolves.toBeUndefined()
    expect(uni.request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        url: 'https://t64.example.test/teacher/question-bank/17',
        method: 'DELETE',
        data: { version: 3, client_request_id: 'delete-17-v3' },
      }),
    )
  })

  it('persists owner-scoped deletion and idempotency receipts without resurrecting a deleted import', async () => {
    login('t64-bank-owner')
    configureDemoTeacherQuestionBankSource({ getTeacherQuestionBankSource: async () => source })
    const repository = new DemoContentRepository()
    const request = bankInput('t64-bank-copy')
    const item = await repository.importTeacherQuestionBankItem(request)
    const edited = await repository.updateTeacherQuestionBankItem(item.id, item.version, {
      ...source,
      title: '个人修订',
    })
    expect(edited).toMatchObject({ version: 2, medicalReviewStatus: 'not_required' })
    await expect(repository.deleteTeacherQuestionBankItem(item.id, item.version, 't64-stale')).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
    })
    login('t64-bank-other')
    await expect(repository.deleteTeacherQuestionBankItem(item.id, edited.version, 't64-other')).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    login('t64-bank-owner')
    await repository.deleteTeacherQuestionBankItem(item.id, edited.version, 't64-delete')
    await expect(
      repository.deleteTeacherQuestionBankItem(item.id, edited.version, 't64-delete'),
    ).resolves.toBeUndefined()
    await expect(repository.deleteTeacherQuestionBankItem(item.id, 99, 't64-delete')).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
    })
    expect(await repository.listTeacherQuestionBank()).toMatchObject({ items: [], total: 0 })
    expect(await repository.listTeacherQuestionBank({ status: 'archived' })).toMatchObject({ items: [], total: 0 })
    await expect(repository.getTeacherQuestionBankItem(item.id)).rejects.toMatchObject({ statusCode: 404 })
    await expect(repository.importTeacherQuestionBankItem(request)).rejects.toMatchObject({ statusCode: 404 })
    await expect(
      repository.importTeacherQuestionBankItem({ ...request, clientRequestId: 't64-new-copy' }),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT' })
    expect(source.title).toBe('炎症机制')
    vi.resetModules()
    const fresh = await import('./demoContentRepository')
    const freshIdentity = await import('@/features/identity/public')
    freshIdentity.saveSession({
      openid: 't64-bank-owner',
      role: 'teacher',
      nickName: '教师',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    fresh.configureDemoTeacherQuestionBankSource({ getTeacherQuestionBankSource: async () => source })
    const reloaded = new fresh.DemoContentRepository()
    expect(await reloaded.listTeacherQuestionBank()).toMatchObject({ total: 0 })
    await expect(reloaded.deleteTeacherQuestionBankItem(item.id, edited.version, 't64-delete')).resolves.toBeUndefined()
    await expect(reloaded.importTeacherQuestionBankItem(request)).rejects.toMatchObject({ statusCode: 404 })
  })

  it('keeps a bank item available when local deletion persistence fails', async () => {
    login('t64-bank-storage')
    configureDemoTeacherQuestionBankSource({ getTeacherQuestionBankSource: async () => source })
    const repository = new DemoContentRepository()
    const item = await repository.importTeacherQuestionBankItem(bankInput('t64-storage-copy'))
    vi.mocked(uni.setStorageSync).mockImplementationOnce(() => {
      throw new Error('quota')
    })
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    await expect(repository.deleteTeacherQuestionBankItem(item.id, item.version, 't64-storage-delete')).rejects.toThrow(
      '本地存储空间不足',
    )
    expect(await repository.getTeacherQuestionBankItem(item.id)).toMatchObject({
      version: item.version,
      status: 'active',
    })
    expect(consoleError).toHaveBeenCalledTimes(1)
    await repository.deleteTeacherQuestionBankItem(item.id, item.version, 't64-storage-delete')
    expect(await repository.listTeacherQuestionBank()).toMatchObject({ total: 0 })
  })

  it('aborts pending import when the teacher identity changes', async () => {
    login('t64-bank-waiting')
    let resolveSource!: (value: typeof source) => void
    configureDemoTeacherQuestionBankSource({
      getTeacherQuestionBankSource: () =>
        new Promise((resolve) => {
          resolveSource = resolve
        }),
    })
    const repository = new DemoContentRepository()
    const pending = repository.importTeacherQuestionBankItem(bankInput('t64-identity-copy'))
    login('t64-bank-switched')
    resolveSource(source)
    await expect(pending).rejects.toMatchObject({ code: 'STATE_CONFLICT' })
    expect(await repository.listTeacherQuestionBank()).toMatchObject({ total: 0 })
    login('t64-bank-waiting')
    expect(await repository.listTeacherQuestionBank()).toMatchObject({ total: 0 })
    clearSession()
    await expect(repository.deleteTeacherQuestionBankItem(1, 1, 'unauth')).rejects.toMatchObject({ statusCode: 401 })
  })

  it('freezes existing attempts and classroom context before an editable case is changed and deleted', async () => {
    login('demo_teacher')
    const boundCodes = ['pathology.cell-injury.adaptation']
    const saved = await saveGuidedCaseAsync({ ...showcaseDraft, title: 'T64原病例' }, undefined, {
      knowledgePointCodes: boundCodes,
    })
    const content = new DemoContentRepository()
    const classroom = new DemoPblRepository(content)
    const selected = (await content.getGuidedCasesAsync()).find((item) => item.id === saved.id)!
    expect(selected).toMatchObject({ status: 'published', medicalReviewStatus: 'not_required' })
    expect(selected.knowledgePointCodes).toEqual(boundCodes)
    const goal = selected.knowledgePointCodes![0]
    const session = await classroom.createSession('1', 'pathology.cell-injury', saved.id, [goal])
    await expect(classroom.createSession('1', 'pathology.cell-injury', saved.id, ['unbound-point'])).rejects.toThrow(
      '目标',
    )
    login('t64-history-student', 'student')
    const attempt = demoStart(saved.id)
    // Simulate a pre-T64 persisted attempt with no frozen draft.
    storage.remove(`${storage.scopedKey(storageKeys.caseAttempts, 't64-history-student')}:drafts`)
    login('demo_teacher')
    const updatedDraft = structuredClone(showcaseDraft)
    updatedDraft.title = 'T64修改后病例'
    updatedDraft.caseDefinition.facts[0].value = '修改后的事实'
    await saveGuidedCaseAsync(updatedDraft, saved.id)
    expect((await content.findProblem(saved.id))?.knowledgePointCodes).toEqual(boundCodes)
    await expect(saveGuidedCaseAsync(updatedDraft, saved.id, { knowledgePointCodes: [] })).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
    })
    await deleteGuidedCaseAsync(saved.id)
    expect(await content.findProblem(saved.id)).toBeUndefined()
    expect(await content.getCaseAuthoringAsync(saved.id)).toBeUndefined()
    await expect(classroom.createSession('1', 'pathology.cell-injury', saved.id, [goal])).rejects.toThrow('可用病例')
    expect((await classroom.sessions('1')).find((item) => item.id === session.id)).toMatchObject({
      caseContext: { title: 'T64原病例' },
      caseVersion: 1,
    })
    login('t64-history-student', 'student')
    expect(() => demoStart(saved.id)).toThrow('病例不存在')
    const reply = demoMessage(attempt.id, showcaseDraft.caseDefinition.facts[0].triggers[0])
    expect(reply.messages.at(-1)?.content).toContain(showcaseDraft.caseDefinition.facts[0].value)
    expect(reply.messages.at(-1)?.content).not.toContain('修改后的事实')
    const stages: StageAnswer[] = [
      { stageId: 'history', summary: '病史', keyFindings: [] },
      { stageId: 'problem_representation', summary: '表征' },
      { stageId: 'differential', items: [] },
      { stageId: 'tests', items: [] },
      { stageId: 'management', items: [], safetyConsiderations: [] },
    ]
    for (const answer of stages) demoSubmit(attempt.id, answer)
    expect(demoComplete(attempt.id)).toMatchObject({ attemptId: attempt.id })
    await expect(content.deleteGuidedCaseAsync(saved.id)).rejects.toMatchObject({ statusCode: 403 })
  })
})
