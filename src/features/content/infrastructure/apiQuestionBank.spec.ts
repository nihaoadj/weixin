import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiContentRepository } from './apiContentRepository'

const apiRequest = vi.hoisted(() => vi.fn())
vi.mock('@/platform/http/apiClient', () => ({
  apiRequest,
  encodePathSegment: (value: string | number) => encodeURIComponent(String(value)),
  undefinedOnNotFound: () => undefined,
}))

const item = (patch: Record<string, unknown> = {}) => ({
  id: 17,
  version: 1,
  status: 'active',
  task_type: 'retest',
  title: '血管反应验证',
  prompt: '炎症时哪一项变化促进液体外渗？',
  options: ['通透性增加', '通透性降低'],
  answer: { correct_option: 0 },
  explanation: '通透性增加可促进液体与蛋白外渗。',
  point_codes: ['pathology.inflammation.vascular'],
  dimension_ids: [],
  medical_review_status: 'approved',
  updated_at: '2026-09-24T00:00:00Z',
  ...patch,
})

describe('API teacher question bank adapter', () => {
  beforeEach(() => apiRequest.mockReset())

  it('maps the owner-scoped list, explicit import, revision edit and archive contracts', async () => {
    const repository = new ApiContentRepository()
    apiRequest.mockResolvedValueOnce({ items: [item()], total: 1, limit: 20, offset: 0 })
    expect(
      await repository.listTeacherQuestionBank({ pointCode: 'pathology.inflammation.vascular', taskType: 'retest' }),
    ).toMatchObject({ total: 1, items: [{ id: 17, taskType: 'retest', answer: { correct_option: 0 } }] })
    expect(apiRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        path: '/teacher/question-bank',
        query: expect.objectContaining({
          status: undefined,
          point_code: 'pathology.inflammation.vascular',
          task_type: 'retest',
        }),
      }),
    )

    apiRequest.mockResolvedValueOnce(item())
    const content = {
      taskType: 'retest' as const,
      title: '血管反应验证',
      prompt: '炎症时哪一项变化促进液体外渗？',
      options: ['通透性增加', '通透性降低'],
      answer: { correct_option: 0 },
      explanation: '通透性增加可促进液体与蛋白外渗。',
      pointCodes: ['pathology.inflammation.vascular'],
      dimensionIds: [],
    }
    await repository.importTeacherQuestionBankItem({
      ...content,
      sourceType: 'route_test_question',
      sourceId: '91111111-1111-4111-8111-111111111111',
      sourceDigest: 'a'.repeat(64),
      clientRequestId: 'teacher-copy-81',
      deidentified: true,
    })
    expect(apiRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        path: '/teacher/question-bank/import',
        method: 'POST',
        body: expect.objectContaining({
          source_type: 'route_test_question',
          source_id: '91111111-1111-4111-8111-111111111111',
          source_digest: 'a'.repeat(64),
          deidentified: true,
          client_request_id: 'teacher-copy-81',
        }),
      }),
    )

    apiRequest.mockResolvedValueOnce(item({ version: 2, medical_review_status: 'pending_review' }))
    await repository.updateTeacherQuestionBankItem(17, 1, { ...content, prompt: '教师独立修订的题干。' })
    expect(apiRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        path: '/teacher/question-bank/17',
        method: 'PUT',
        body: expect.objectContaining({ version: 1, prompt: '教师独立修订的题干。' }),
      }),
    )

    apiRequest.mockResolvedValueOnce(item({ version: 3, status: 'archived' }))
    await repository.archiveTeacherQuestionBankItem(17, 2, 'archive-17-v2')
    expect(apiRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        path: '/teacher/question-bank/17/archive',
        method: 'POST',
        body: { version: 2, client_request_id: 'archive-17-v2' },
      }),
    )
  })
})
