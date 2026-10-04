import { beforeEach, describe, expect, it, vi } from 'vitest'
import { saveSession } from '@/features/identity/public'
import { AppError } from '@/types/errors'
import type { TeacherQuestionBankContent, TeacherQuestionBankSource } from '../domain/questionBank'
import { ApiContentRepository } from './apiContentRepository'
import { DemoContentRepository, configureDemoTeacherQuestionBankSource } from './demoContentRepository'
import { teacherQuestionBankSourceSchema } from '@/platform/contracts/questionBank'

const apiRequest = vi.hoisted(() => vi.fn())
vi.mock('@/platform/http/apiClient', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/platform/http/apiClient')>()),
  apiRequest,
  encodePathSegment: (value: string | number) => encodeURIComponent(String(value)),
  undefinedOnNotFound: () => undefined,
}))

const sourceId = '91111111-1111-4111-8111-111111111111'
const sourceId2 = '92222222-2222-4222-8222-222222222222'

function makeSource(patch: Partial<TeacherQuestionBankSource> = {}): TeacherQuestionBankSource {
  return {
    sourceType: 'route_test_question',
    sourceId,
    sourceDigest: 'a'.repeat(64),
    taskType: 'retest',
    title: '病理知识单选题',
    prompt: '炎症时哪一项变化促进液体外渗？',
    options: ['通透性增加', '通透性降低'],
    answer: { correct_option: 0 },
    explanation: '通透性增加可促进液体与蛋白外渗。',
    pointCodes: ['pathology.inflammation.vascular'],
    dimensionIds: [],
    ...patch,
  }
}

function importInput(source: TeacherQuestionBankSource, clientRequestId: string) {
  return {
    ...source,
    clientRequestId,
    deidentified: true as const,
  }
}

function sourceContent(source: TeacherQuestionBankSource): TeacherQuestionBankContent {
  return {
    taskType: source.taskType,
    title: source.title,
    prompt: source.prompt,
    options: source.options,
    answer: source.answer,
    explanation: source.explanation,
    pointCodes: source.pointCodes,
    dimensionIds: source.dimensionIds,
  }
}

function asApiSource(source: TeacherQuestionBankSource) {
  return {
    source_type: source.sourceType,
    source_id: source.sourceId,
    source_digest: source.sourceDigest,
    task_type: source.taskType,
    title: source.title,
    prompt: source.prompt,
    options: source.options,
    answer: source.answer,
    explanation: source.explanation,
    point_codes: source.pointCodes,
    dimension_ids: source.dimensionIds,
  }
}

function setTeacher(openid = 't53-content-teacher', permissions: 'medical_review'[] = []) {
  saveSession({
    openid,
    role: 'teacher',
    nickName: '演示教师',
    avatarUrl: '',
    permissions,
    createdAt: new Date(0).toISOString(),
  })
}

describe('T53 teacher question bank source', () => {
  beforeEach(() => apiRequest.mockReset())

  it('reads only the minimal route question source and maps the API response explicitly', async () => {
    const source = makeSource()
    apiRequest.mockResolvedValueOnce(asApiSource(source))

    const result = await new ApiContentRepository().getTeacherQuestionBankSource(sourceId)

    expect(result).toEqual(source)
    expect(Object.keys(result).sort()).toEqual(
      [
        'answer',
        'dimensionIds',
        'explanation',
        'options',
        'pointCodes',
        'prompt',
        'sourceDigest',
        'sourceId',
        'sourceType',
        'taskType',
        'title',
      ].sort(),
    )
    expect(apiRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        path: `/teacher/question-bank/sources/route-test-questions/${sourceId}`,
        schema: teacherQuestionBankSourceSchema,
        cacheTtlMs: 0,
      }),
    )
    expect(() => teacherQuestionBankSourceSchema.parse({ ...asApiSource(source), private_rubric: {} })).toThrow()
  })

  it('keeps the source copy intact, permits only exact first import, and matches import retry semantics', async () => {
    setTeacher()
    const original = makeSource()
    let latest = original
    const getSource = vi.fn(async (id: string) => {
      if (id !== latest.sourceId)
        throw new AppError('课堂题目来源不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
      return { ...latest, medicalReviewStatus: null, privateRubric: { correct_option: 0 } } as TeacherQuestionBankSource
    })
    configureDemoTeacherQuestionBankSource({ getTeacherQuestionBankSource: getSource })
    const repository = new DemoContentRepository()
    const preview = await repository.getTeacherQuestionBankSource(sourceId)
    expect(preview).toEqual(original)
    expect(Object.keys(preview).sort()).toEqual(Object.keys(original).sort())
    await expect(repository.getTeacherQuestionBankSource(sourceId2)).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })

    const request = importInput(original, 't53-bank-import-1')
    await expect(
      repository.importTeacherQuestionBankItem({ ...request, prompt: '教师改写来源题干' }),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT' })

    const imported = await repository.importTeacherQuestionBankItem(request)
    expect(imported).toMatchObject({
      ...sourceContent(original),
      id: expect.any(Number),
      version: 1,
      medicalReviewStatus: null,
    })
    const readsAfterImport = getSource.mock.calls.length
    latest = makeSource({
      ...original,
      sourceDigest: 'd'.repeat(64),
      prompt: '上游来源更新后的题干。',
    })
    expect(await repository.importTeacherQuestionBankItem(request)).toMatchObject({ id: imported.id, version: 1 })
    expect(getSource).toHaveBeenCalledTimes(readsAfterImport)
    await expect(
      repository.importTeacherQuestionBankItem({ ...request, clientRequestId: 't53-bank-import-2' }),
    ).rejects.toThrow('该来源版本已脱钩')

    const editedContent: TeacherQuestionBankContent = { ...original, prompt: '教师独立修订的个人副本。' }
    const edited = await repository.updateTeacherQuestionBankItem(imported.id, imported.version, editedContent)
    expect(edited).toMatchObject({ prompt: editedContent.prompt, version: 2 })
    expect(await repository.getTeacherQuestionBankSource(sourceId)).toEqual(latest)

    const staleSource = makeSource({ sourceId: sourceId2, sourceDigest: 'b'.repeat(64) })
    latest = makeSource({
      ...staleSource,
      sourceDigest: 'c'.repeat(64),
      prompt: '来源题已更新，必须重新预览。',
    })
    await expect(
      repository.importTeacherQuestionBankItem(importInput(staleSource, 't53-bank-stale-source')),
    ).rejects.toThrow('来源题目已更新')
  })
})
