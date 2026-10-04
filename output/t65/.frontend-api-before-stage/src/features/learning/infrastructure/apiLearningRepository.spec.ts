import { describe, expect, it, vi } from 'vitest'
import { apiLearningRepository } from './apiLearningRepository'

const apiRequest = vi.hoisted(() => vi.fn())

vi.mock('@/platform/http/apiClient', () => ({
  apiRequest,
  encodePathSegment: (value: string | number) => encodeURIComponent(String(value)),
}))

describe('api learning repository cache invalidation', () => {
  it('invalidates the personal knowledge map after each action that can change learning evidence', async () => {
    apiRequest.mockResolvedValue({
      card_code: 'card',
      correct: true,
      rating: 'good',
      explanation: '',
      due_at: '2026-09-08',
    })
    await apiLearningRepository.gradeObjectiveCard('card', 0, 'medium')
    await apiLearningRepository.rateRecallCard(1, 'good')
    apiRequest.mockResolvedValueOnce({
      id: 1,
      point_code: 'pathology.cell-injury.adaptation',
      card_code: null,
      source_type: 'manual',
      source_id: 'source',
      note: '',
      active: true,
      created_at: '2026-09-07',
      updated_at: '2026-09-07',
    })
    await apiLearningRepository.captureManualReviewItem({
      pointCode: 'pathology.cell-injury.adaptation',
      sourceType: 'manual',
      sourceId: 'source',
    })
    await apiLearningRepository.dismissReviewItem(1)

    for (const request of apiRequest.mock.calls.map(([options]) => options)) {
      expect(request.invalidateCache).toContain('/learning/knowledge-map')
    }
  })
})
