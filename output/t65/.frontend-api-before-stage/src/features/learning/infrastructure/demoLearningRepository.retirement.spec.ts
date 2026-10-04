import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearSession, saveSession } from '@/features/identity/public'
import { clearApiCache } from '@/platform/http/apiClient'
import { respond } from '@/test/http'
import type { LearningRepository } from '../domain/ports'
import { demoLearningRepository } from './demoLearningRepository'
import { apiLearningRepository } from './apiLearningRepository'

const login = (role: 'student' | 'teacher') =>
  saveSession({ openid: `t63-${role}`, role, nickName: role, avatarUrl: '', createdAt: new Date(0).toISOString() })
const writes = (repository: LearningRepository) => [
  () => repository.createExitQuiz(['pathology.cell-injury.adaptation']),
  () => repository.gradeObjectiveCard('pathology.cell-injury.adaptation.practice', 1, 'low'),
  () => repository.revealRecallCard(1),
  () => repository.rateRecallCard(1, 'again'),
  () =>
    repository.captureManualReviewItem({
      pointCode: 'pathology.cell-injury.adaptation',
      sourceType: 'manual',
      sourceId: 't63-old-item',
    }),
  () => repository.dismissReviewItem(1),
]
afterEach(() => {
  clearApiCache()
  vi.unstubAllEnvs()
})

describe('T63 Demo legacy learning retirement', () => {
  it('checks student identity before all retired writes and compatibility reads', async () => {
    const reads = [() => demoLearningRepository.getReviewDashboard(), () => demoLearningRepository.getDueReviewQueue()]
    clearSession()
    for (const action of [...writes(demoLearningRepository), ...reads])
      await expect(action()).rejects.toMatchObject({ code: 'AUTH_REQUIRED', statusCode: 401 })
    login('teacher')
    for (const action of [...writes(demoLearningRepository), ...reads])
      await expect(action()).rejects.toMatchObject({ code: 'FORBIDDEN', statusCode: 403 })
  })

  it('matches API empty review projections and retired writes without adding knowledge evidence', async () => {
    login('student')
    const before = await demoLearningRepository.getKnowledgeMap()
    expect(before.length).toBeGreaterThan(0)
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
    vi.mocked(uni.request).mockImplementation((options) => {
      const path = new URL(String(options.url)).pathname
      respond(
        options,
        options.method === 'GET'
          ? path.endsWith('/review-dashboard')
            ? { due_count: 0, weak_point_codes: [], items: [] }
            : []
          : { detail: { code: 'RETIRED_FLOW', message: '旧复习流程已退役' } },
        options.method === 'GET' ? 200 : 409,
      )
      return undefined as never
    })
    for (const repository of [demoLearningRepository, apiLearningRepository]) {
      expect(await repository.getReviewDashboard()).toEqual({ dueCount: 0, weakPointCodes: [], items: [] })
      expect(await repository.getDueReviewQueue()).toEqual([])
      for (const action of writes(repository))
        await expect(action()).rejects.toMatchObject({ code: 'RETIRED_FLOW', statusCode: 409 })
    }
    expect(await demoLearningRepository.getKnowledgeMap()).toEqual(before)
  })
})
